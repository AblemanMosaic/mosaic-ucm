"""Pure P/PPI integration records for archive, courthouse, and publication.

Architectural ownership and runtime availability are deliberately separate.
Naming an external owner never implies that its adapter is installed or bound.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile
from uclop.canonical import root
from .pippi_global import BOUNDARY,HubRefusal,validate_project
from .pippi_archive_policy import ArchivePolicyRefusal,build_transtemporal_reference
from .release_certification import META_NAMES,verify_embedded_metadata


INTEGRATION_REGISTRY_SCHEMA = "mosaic.ucm.pippi-integration-availability.v0.1"
INTEGRATION_STATUSES = {"BUILT_IN", "BOUND_EXTERNAL", "DECLARED_UNBOUND", "UNAVAILABLE"}
INTEGRATION_IDS = {
    "PIPPI_CORE", "UCM_OPERATIONAL_GATEWAY", "AOK_COURTHOUSE",
    "CRYSTAL_NETWORK", "MEMORY_VAULT", "MOSAIC_READER",
}


def _root_or_none(value: Any, code: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != 64:
        raise HubRefusal(code)
    try:
        bytes.fromhex(value)
    except ValueError as error:
        raise HubRefusal(code) from error
    return value


def build_integration_availability_registry(*, entries: list[dict[str, Any]],
                                            source: str) -> dict[str, Any]:
    """Build the exact installed/bound/unbound projection used by the UI.

    This registry records availability only.  A binding root is not a
    capability grant and does not authorize dispatch.
    """
    if source not in {"INSTALL_DEFAULT", "GOVERNED_BINDING", "LEGACY_PROJECTION"}:
        raise HubRefusal("PIPPI_INTEGRATION_SOURCE_INVALID")
    if not isinstance(entries, list):
        raise HubRefusal("PIPPI_INTEGRATIONS_INVALID")
    normalized = []
    seen: set[str] = set()
    for raw in entries:
        if not isinstance(raw, dict) or set(raw) != {
                "integration_id", "owner", "status", "binding_root",
                "evidence_roots", "local_surface"}:
            raise HubRefusal("PIPPI_INTEGRATION_ENTRY_INVALID")
        integration_id = raw["integration_id"]
        if integration_id not in INTEGRATION_IDS or integration_id in seen:
            raise HubRefusal("PIPPI_INTEGRATION_ID_INVALID")
        seen.add(integration_id)
        if raw["status"] not in INTEGRATION_STATUSES:
            raise HubRefusal("PIPPI_INTEGRATION_STATUS_INVALID")
        if not isinstance(raw["owner"], str) or not raw["owner"].strip():
            raise HubRefusal("PIPPI_INTEGRATION_OWNER_INVALID")
        if raw["local_surface"] is not None and (
                not isinstance(raw["local_surface"], str) or not raw["local_surface"].strip()):
            raise HubRefusal("PIPPI_INTEGRATION_SURFACE_INVALID")
        binding_root = _root_or_none(raw["binding_root"], "PIPPI_INTEGRATION_BINDING_INVALID")
        evidence = raw["evidence_roots"]
        if (not isinstance(evidence, list) or evidence != sorted(set(evidence))):
            raise HubRefusal("PIPPI_INTEGRATION_EVIDENCE_INVALID")
        for item in evidence:
            _root_or_none(item, "PIPPI_INTEGRATION_EVIDENCE_INVALID")
        if raw["status"] == "BOUND_EXTERNAL" and binding_root is None:
            raise HubRefusal("PIPPI_INTEGRATION_BINDING_REQUIRED")
        if raw["status"] in {"DECLARED_UNBOUND", "UNAVAILABLE"} and binding_root is not None:
            raise HubRefusal("PIPPI_INTEGRATION_UNBOUND_HAS_BINDING")
        normalized.append({**deepcopy(raw), "binding_root": binding_root,
                           "evidence_roots": list(evidence)})
    if seen != INTEGRATION_IDS:
        raise HubRefusal("PIPPI_INTEGRATION_DENOMINATOR_INVALID")
    normalized.sort(key=lambda row: row["integration_id"])
    body = {"schema": INTEGRATION_REGISTRY_SCHEMA, "source": source,
            "entries": normalized, "registry_grants_authority": False,
            **BOUNDARY}
    return {**body, "integration_registry_root": root(body)}


def default_integration_availability_registry(*, source: str = "INSTALL_DEFAULT") -> dict[str, Any]:
    entries = [
        {"integration_id": "PIPPI_CORE", "owner": "PIPPI",
         "status": "BUILT_IN", "binding_root": root({"module": "ucm.pippi"}),
         "evidence_roots": [], "local_surface": "pippi"},
        {"integration_id": "MOSAIC_READER", "owner": "MOSAIC_READER",
         "status": "BUILT_IN", "binding_root": root({"module": "mosaic_ui.reader_cli"}),
         "evidence_roots": [], "local_surface": "mosaic_ui.reader_cli"},
        {"integration_id": "UCM_OPERATIONAL_GATEWAY", "owner": "UCM",
         "status": "DECLARED_UNBOUND", "binding_root": None,
         "evidence_roots": [], "local_surface": "ucm.operation_gateway"},
        {"integration_id": "AOK_COURTHOUSE", "owner": "AOK_COURTHOUSE",
         "status": "DECLARED_UNBOUND", "binding_root": None,
         "evidence_roots": [], "local_surface": None},
        {"integration_id": "CRYSTAL_NETWORK", "owner": "CRYSTAL_NETWORK",
         "status": "DECLARED_UNBOUND", "binding_root": None,
         "evidence_roots": [], "local_surface": None},
        {"integration_id": "MEMORY_VAULT", "owner": "MEMORY_VAULT",
         "status": "DECLARED_UNBOUND", "binding_root": None,
         "evidence_roots": [], "local_surface": None},
    ]
    return build_integration_availability_registry(entries=entries, source=source)


def validate_integration_availability_registry(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
            "schema", "source", "entries", "registry_grants_authority",
            "standing", "authority_effect", "real_a5", "g0",
            "integration_registry_root"}:
        raise HubRefusal("PIPPI_INTEGRATION_REGISTRY_INVALID")
    expected = build_integration_availability_registry(entries=value["entries"],
        source=value["source"])
    if value != expected:
        raise HubRefusal("PIPPI_INTEGRATION_REGISTRY_INVALID")
    return deepcopy(value)


def bind_external_integration(*, registry: dict[str, Any], integration_id: str,
                              binding_root: str, evidence_roots: list[str]) -> dict[str, Any]:
    registry = validate_integration_availability_registry(registry)
    if integration_id not in INTEGRATION_IDS or integration_id in {"PIPPI_CORE", "MOSAIC_READER"}:
        raise HubRefusal("PIPPI_INTEGRATION_BINDING_NOT_EXTERNAL")
    _root_or_none(binding_root, "PIPPI_INTEGRATION_BINDING_INVALID")
    updated = []
    for row in registry["entries"]:
        updated.append({**row, "status": "BOUND_EXTERNAL", "binding_root": binding_root,
                        "evidence_roots": sorted(set(evidence_roots))}
                       if row["integration_id"] == integration_id else row)
    return build_integration_availability_registry(entries=updated, source="GOVERNED_BINDING")


def build_archive_reference(*, project: dict[str,Any], artifact_role: str, artifact_sha256: str,
                            artifact_bytes: int, semantic_root: str, metadata_root: str,
                            governance_root: str, backend: str,
                            backend_reference: str | None) -> dict[str,Any]:
    project=validate_project(project)
    try:
        return build_transtemporal_reference(project_root=project["project_root"],
            artifact_role=artifact_role,artifact_sha256=artifact_sha256,
            artifact_bytes=artifact_bytes,semantic_root=semantic_root,
            metadata_root=metadata_root,governance_root=governance_root,
            backend=backend,backend_reference=backend_reference)
    except ArchivePolicyRefusal as error:
        raise HubRefusal(error.code,error.detail) from error


def build_courthouse_work_order(*, project: dict[str,Any], objective: str, payload_root: str,
                                destination_jurisdiction: str) -> dict[str,Any]:
    project=validate_project(project)
    if len(payload_root)!=64 or not objective.strip() or not destination_jurisdiction.strip():
        raise HubRefusal("PIPPI_COURTHOUSE_REQUEST_INVALID")
    body={"schema":"mosaic.ucm.pippi-courthouse-work-order.v0.1","project_root":project["project_root"],
          "objective":objective,"payload_root":payload_root,"destination_jurisdiction":destination_jurisdiction,
          "transport_owner":"AOK_COURTHOUSE","pippi_role":"REQUEST_AUTHOR_AND_RESULT_IMPORTER",
          "remote_dispatch_authorized":False,**BOUNDARY}
    return {**body,"work_order_root":root(body)}


def _verify_publication_artifact(*, artifact_path: Path,
                                 expected_sha256: str) -> dict[str,Any]:
    if not artifact_path.is_file():
        raise HubRefusal("PIPPI_PUBLICATION_ARTIFACT_MISSING")
    archive_bytes=artifact_path.read_bytes()
    if hashlib.sha256(archive_bytes).hexdigest()!=expected_sha256:
        raise HubRefusal("PIPPI_PUBLICATION_ARTIFACT_PIN_MISMATCH")
    try:
        with zipfile.ZipFile(artifact_path) as archive:
            names=archive.namelist()
            if len(names)!=len(set(names)) or names.count("MANIFEST.json")!=1:
                raise HubRefusal("PIPPI_PUBLICATION_ARCHIVE_SET_INVALID")
            manifest=json.loads(archive.read("MANIFEST.json"))
            rows=manifest.get("members")
            if not isinstance(rows,list):
                raise HubRefusal("PIPPI_PUBLICATION_ARCHIVE_MANIFEST_INVALID")
            indexed={row.get("path"):row for row in rows if isinstance(row,dict)}
            if len(indexed)!=len(rows) or set(names)!={"MANIFEST.json",*indexed}:
                raise HubRefusal("PIPPI_PUBLICATION_ARCHIVE_MANIFEST_INVALID")
            manifest_body={key:value for key,value in manifest.items() if key!="root"}
            if root(manifest_body)!=manifest.get("root"):
                raise HubRefusal("PIPPI_PUBLICATION_ARCHIVE_MANIFEST_INVALID")
            for name,row in indexed.items():
                data=archive.read(name)
                if row.get("sha256")!=hashlib.sha256(data).hexdigest() or row.get("bytes")!=len(data):
                    raise HubRefusal("PIPPI_PUBLICATION_ARCHIVE_MEMBER_INVALID")
            if not set(META_NAMES)<=set(names):
                raise HubRefusal("PIPPI_PUBLICATION_CERTIFICATION_META_MISSING")
            metadata={name:archive.read(name) for name in META_NAMES}
            payload=[(name,archive.read(name)) for name in names
                     if name!="MANIFEST.json" and not name.startswith("META/")]
            thr=json.loads(metadata["META/THR-MANIFEST.json"])
            result=verify_embedded_metadata(
                payload_rows=payload,metadata=metadata,
                artifact=manifest.get("artifact"),completeness=manifest.get("completeness"),
                version=manifest.get("version"),
                engineering_revision=thr.get("meaning",{}).get("engineering_revision"),
                source_manifest_root=thr.get("admissibility",{}).get("source_manifest_root"),
                release_identity_root=thr.get("admissibility",{}).get("release_identity_root"))
            dkn=json.loads(metadata["META/DKN-BINDING.json"])
            return {**result,"public_namespace":dkn["public_namespace"]}
    except HubRefusal:
        raise
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as error:
        raise HubRefusal("PIPPI_PUBLICATION_ARTIFACT_VERIFICATION_REFUSED") from error


def build_publication_plan(*, project: dict[str,Any], artifact_path: Path,
                           artifact_sha256: str, targets: list[str],
                           dkn_public_namespace: str | None) -> dict[str,Any]:
    project=validate_project(project)
    if len(artifact_sha256)!=64 or targets!=sorted(set(targets)) or not set(targets)<={"GITHUB","USER_STORAGE","CRYSTAL_NETWORK"}:
        raise HubRefusal("PIPPI_PUBLICATION_PLAN_INVALID")
    verified=_verify_publication_artifact(
        artifact_path=Path(artifact_path),expected_sha256=artifact_sha256)
    if dkn_public_namespace is not None and (
        verified["certificate_status"]!="PASS_SELF_CERTIFIED"
        or verified["dkn_status"]!="BOUND_EXTERNAL"
        or dkn_public_namespace!=verified["public_namespace"]
    ):
        raise HubRefusal("PIPPI_PUBLICATION_DKN_SELF_CERTIFICATION_REQUIRED")
    identity_status=("DKN_SELF_CERTIFIED" if verified["certificate_status"]=="PASS_SELF_CERTIFIED"
                     else "CONTENT_ADDRESSED_NOT_DKN_SELF_CERTIFIED")
    body={"schema":"mosaic.ucm.pippi-publication-plan.v0.1","project_root":project["project_root"],
          "artifact_sha256":artifact_sha256,"targets":targets,
          "dkn_public_namespace":dkn_public_namespace,
          "thr_body_root":verified["thr_body_root"],
          "self_certificate_root":verified["certificate_root"],
          "self_certificate_status":verified["certificate_status"],
          "dkn_binding_root":verified["dkn_binding_root"],
          "publication_identity_status":identity_status,
          "publication_owner":"CRYSTAL_NETWORK","pippi_role":"PLAN_AND_PREFLIGHT",
          "provider_dispatch_authorized":False,"version":project["public_version"],"revision":project["revision"],**BOUNDARY}
    return {**body,"publication_plan_root":root(body)}


def archive_local(*, data_root: Path, data: bytes) -> tuple[str,Path]:
    digest=hashlib.sha256(data).hexdigest();path=data_root/"objects"/digest[:2]/digest
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=data:raise HubRefusal("PIPPI_ARCHIVE_COLLISION")
    if not path.exists():
        with path.open("xb") as stream:stream.write(data);stream.flush();__import__('os').fsync(stream.fileno())
    return digest,path

