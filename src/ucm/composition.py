"""Stage I2 portfolio composition preflight and declaration contracts."""
from __future__ import annotations

from copy import deepcopy
import io
from pathlib import Path
from typing import Any
import zipfile

from uclop.canonical import exact_keys, require, root, strict_loads

from .amcas import BOUNDARY
from .stage1 import verify_stage1_bundle


DECLARATION_SCHEMA = "mosaic.ucm.stage-i2-declaration.v0.1"
PREFLIGHT_SCHEMA = "mosaic.ucm.stage-i2-composition-preflight.v0.1"


def declaration_template(raw: bytes) -> dict[str, Any]:
    """Create an intentionally unresolved I2 declaration from a verified I1 bundle."""
    verified = verify_stage1_bundle(raw)
    require(verified["thr_status"] == "PASS_SEPARATED", "STAGE_I2_THR_REQUIRED")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        contract = strict_loads(archive.read("AMCAS-CONTRACT.json"))
        control = strict_loads(archive.read("CONTROL-PLANE-DISPOSITION.json"))
    body = {
        "schema": DECLARATION_SCHEMA,
        "application_id": verified["application_id"],
        "stage_i1_artifact_sha256": __import__("hashlib").sha256(raw).hexdigest(),
        "stage_i1_index_root": verified["index_root"],
        "thr_manifest_root": verified["thr_manifest_root"],
        "exports": [],
        "imports": [],
        "semantic_authority": control["semantic_authority"],
        "native_effect_executor": control["effect_executor"],
        "available_capabilities": [
            {"id": row["id"], "route": row["route"],
             "request_schema": row["request_schema"],
             "result_schema": row["result_schema"],
             "effect_class": row["effect_class"]}
            for row in contract["capabilities"]
        ],
        "declared_relations_status": "UNRESOLVED_DECLARATION_REQUIRED",
        "identity_binding_status": control["identity_binding_status"],
        "jurisdiction_binding_status": control["jurisdiction_binding_status"],
        **BOUNDARY,
    }
    return {**body, "declaration_root": root(body)}


def verify_declaration(value: Any, *, expected_i1: bytes) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "application_id", "stage_i1_artifact_sha256", "stage_i1_index_root",
        "thr_manifest_root", "exports", "imports", "semantic_authority",
        "native_effect_executor", "available_capabilities", "declared_relations_status",
        "identity_binding_status", "jurisdiction_binding_status", "standing",
        "authority_effect", "real_a5", "g0", "declaration_root",
    })
    template = declaration_template(expected_i1)
    for key in ("application_id", "stage_i1_artifact_sha256", "stage_i1_index_root",
                "thr_manifest_root", "semantic_authority", "native_effect_executor",
                "available_capabilities", "identity_binding_status",
                "jurisdiction_binding_status"):
        require(item[key] == template[key], "STAGE_I2_STAGE_I1_BINDING_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I2_AUTHORITY_CEILING_INVALID")
    require(item["declared_relations_status"] in {
        "UNRESOLVED_DECLARATION_REQUIRED", "DECLARED_INFORMATION_ONLY"
    }, "STAGE_I2_RELATION_STATUS_INVALID")
    capability_ids = {row["id"] for row in item["available_capabilities"]}
    for export in item["exports"]:
        row = exact_keys(export, {"capability_id", "interface_id", "schema_root",
                                  "semantic_owner", "effect_executor", "consumers"})
        require(row["capability_id"] in capability_ids and type(row["interface_id"]) is str
                and row["interface_id"] and type(row["schema_root"]) is str
                and len(row["schema_root"]) == 64 and type(row["consumers"]) is list
                and all(type(value) is str and value for value in row["consumers"]),
                "STAGE_I2_EXPORT_INVALID")
    for imported in item["imports"]:
        row = exact_keys(imported, {"provider_application_id", "interface_id",
                                    "schema_root", "required", "purpose"})
        require(type(row["provider_application_id"]) is str
                and type(row["interface_id"]) is str and row["interface_id"]
                and type(row["schema_root"]) is str and len(row["schema_root"]) == 64
                and type(row["required"]) is bool and type(row["purpose"]) is str,
                "STAGE_I2_IMPORT_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "declaration_root"}
    require(item["declaration_root"] == root(body), "STAGE_I2_DECLARATION_ROOT_INVALID")
    return deepcopy(item)


def build_preflight_from_bytes(bundle_raws: list[bytes],
                               declarations: list[Any] | None = None) -> dict[str, Any]:
    require(type(bundle_raws) is list and bundle_raws
            and all(type(raw) is bytes for raw in bundle_raws), "STAGE_I2_BUNDLES_EMPTY")
    raw_by_id: dict[str, bytes] = {}
    templates: dict[str, dict[str, Any]] = {}
    for raw in sorted(bundle_raws, key=lambda value: __import__("hashlib").sha256(value).hexdigest()):
        template = declaration_template(raw)
        app_id = template["application_id"]
        require(app_id not in raw_by_id, "STAGE_I2_APPLICATION_DUPLICATE")
        raw_by_id[app_id] = raw
        templates[app_id] = template
    provided: dict[str, dict[str, Any]] = {}
    for value in declarations or []:
        require(type(value) is dict and value.get("application_id") in raw_by_id,
                "STAGE_I2_DECLARATION_APPLICATION_UNKNOWN")
        checked = verify_declaration(value, expected_i1=raw_by_id[value["application_id"]])
        require(checked["application_id"] not in provided, "STAGE_I2_DECLARATION_DUPLICATE")
        provided[checked["application_id"]] = checked
    export_index: dict[tuple[str, str], dict[str, Any]] = {}
    for app_id, declaration in provided.items():
        for export in declaration["exports"]:
            key = (app_id, export["interface_id"])
            require(key not in export_index, "STAGE_I2_EXPORT_DUPLICATE")
            export_index[key] = export
    edges = []
    issues = []
    for app_id, declaration in provided.items():
        for imported in declaration["imports"]:
            key = (imported["provider_application_id"], imported["interface_id"])
            export = export_index.get(key)
            status = "MATCHED" if export and export["schema_root"] == imported["schema_root"] else (
                "SCHEMA_MISMATCH" if export else "PROVIDER_DECLARATION_MISSING")
            edge = {"consumer_application_id": app_id,
                    "provider_application_id": imported["provider_application_id"],
                    "interface_id": imported["interface_id"],
                    "schema_root": imported["schema_root"], "required": imported["required"],
                    "status": status}
            edges.append(edge)
            if status != "MATCHED":
                issues.append({"kind": status, **edge})
    import_keys = {
        (consumer_id, row["provider_application_id"], row["interface_id"])
        for consumer_id, declaration in provided.items() for row in declaration["imports"]
    }
    for provider_id, declaration in provided.items():
        for export in declaration["exports"]:
            for consumer_id in sorted(set(export["consumers"])):
                require(consumer_id in raw_by_id, "STAGE_I2_EXPORT_CONSUMER_UNKNOWN")
                if (consumer_id, provider_id, export["interface_id"]) not in import_keys:
                    issues.append({
                        "kind": "CONSUMER_DECLARATION_MISSING",
                        "consumer_application_id": consumer_id,
                        "provider_application_id": provider_id,
                        "interface_id": export["interface_id"],
                        "schema_root": export["schema_root"],
                        "required": False,
                        "status": "CONSUMER_DECLARATION_MISSING",
                    })
    missing = sorted(set(raw_by_id) - set(provided))
    body = {
        "schema": PREFLIGHT_SCHEMA,
        "applications": [
            {"application_id": app_id,
             "stage_i1_artifact_sha256": templates[app_id]["stage_i1_artifact_sha256"],
             "H_s": verify_stage1_bundle(raw_by_id[app_id])["thr_commitments"]["H_s"],
             "H_c": verify_stage1_bundle(raw_by_id[app_id])["thr_commitments"]["H_c"],
             "H_m": verify_stage1_bundle(raw_by_id[app_id])["thr_commitments"]["H_m"],
             "H_j": verify_stage1_bundle(raw_by_id[app_id])["thr_commitments"]["H_j"],
             "H_r": verify_stage1_bundle(raw_by_id[app_id])["thr_commitments"]["H_r"],
             "declaration_status": ("DECLARED" if app_id in provided else
                                    "UNRESOLVED_DECLARATION_REQUIRED")}
            for app_id in sorted(raw_by_id)
        ],
        "edges": sorted(edges, key=lambda row: (row["consumer_application_id"],
                                                  row["provider_application_id"],
                                                  row["interface_id"])),
        "issues": sorted(issues, key=lambda row: (row["consumer_application_id"],
                                                    row["provider_application_id"],
                                                    row["interface_id"])),
        "missing_declarations": missing,
        "status": "READY_FOR_CORRESPONDENCE_COURT" if not missing and not issues
                  else "DECLARATIONS_REQUIRED",
        "composition_authorized": False,
        **BOUNDARY,
    }
    return {**body, "preflight_root": root(body)}


def build_preflight(bundle_paths: list[Path], declarations: list[Any] | None = None) -> dict[str, Any]:
    require(type(bundle_paths) is list and bundle_paths, "STAGE_I2_BUNDLES_EMPTY")
    paths = sorted((Path(row) for row in bundle_paths), key=lambda value: value.as_posix())
    return build_preflight_from_bytes([path.read_bytes() for path in paths], declarations)
