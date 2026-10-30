"""Exact, effect-free MosaiCOS M1 preparation and native-atlas intake.

These APIs verify source bytes and prepare UNBOUND interfaces. They do not run
the Ethernet rehearsal, verify native semantics, select a target, or accept M1.
External pins are caller-supplied trust inputs; self-declared package roots are
checked for consistency and never substituted for those pins.
"""
from __future__ import annotations

import copy
import hashlib
import io
import re
import stat
import zipfile
from pathlib import PurePosixPath
from typing import Any

from .canonical import Refusal, exact_keys, require, require_root, root, strict_loads
from .maturity_semantics import BOUNDARY as _CEILING

ROLES = ("MOSAICOS_FOUNDATION", "GENESIS_SEED", "TARGET_PROFILE", "ETHERNET_BOOTSTRAP_ADAPTER")
_MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
_MAX_EXPANDED_BYTES = 256 * 1024 * 1024


def _sha(raw: bytes) -> str:
    require(type(raw) is bytes, "MOSAICOS_BYTES_REQUIRED")
    return hashlib.sha256(raw).hexdigest()


def _sealed(body: dict[str, Any]) -> dict[str, Any]:
    return {**copy.deepcopy(body), "root": root(body)}


def _native_root(item: Any, field: str, schema: str) -> dict[str, Any]:
    require(type(item) is dict and item.get("schema") == schema, "MOSAICOS_SOURCE_SCHEMA_INVALID")
    require(field in item, "MOSAICOS_SOURCE_ROOT_MISSING")
    body = {k: v for k, v in item.items() if k != field}
    require(require_root(item[field]) == root(body), "MOSAICOS_SOURCE_ROOT_MISMATCH")
    for name, expected in _CEILING.items():
        require(name in item and type(item[name]) is type(expected) and item[name] == expected, "MOSAICOS_SOURCE_CEILING_INVALID")
    return item


def _member_name(value: Any) -> str:
    require(type(value) is str and bool(value) and "\\" not in value and "\x00" not in value and ":" not in value, "MOSAICOS_ARCHIVE_PATH_INVALID")
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(p not in {"", ".", ".."} for p in value.split("/")), "MOSAICOS_ARCHIVE_PATH_INVALID")
    require(path.as_posix() == value, "MOSAICOS_ARCHIVE_PATH_INVALID")
    return value


def _archive(raw: bytes, expected_sha256: str) -> dict[str, bytes]:
    require(_sha(raw) == require_root(expected_sha256), "MOSAICOS_EXTERNAL_ARCHIVE_PIN_MISMATCH")
    require(len(raw) <= _MAX_ARCHIVE_BYTES, "MOSAICOS_ARCHIVE_BUDGET_EXCEEDED")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            require(0 < len(infos) <= 10000, "MOSAICOS_ARCHIVE_MEMBER_COUNT_INVALID")
            require(sum(x.file_size for x in infos) <= _MAX_EXPANDED_BYTES, "MOSAICOS_ARCHIVE_BUDGET_EXCEEDED")
            result: dict[str, bytes] = {}
            folded: set[str] = set()
            for info in infos:
                # ZipInfo normalizes backslashes on Windows and truncates NULs;
                # validate the original central-directory name before reading.
                original = info.orig_filename
                require(original == info.filename, "MOSAICOS_ARCHIVE_PATH_INVALID")
                name = _member_name(original[:-1] if info.is_dir() else original)
                require(name.casefold() not in folded, "MOSAICOS_ARCHIVE_DUPLICATE_PATH")
                folded.add(name.casefold())
                mode = info.external_attr >> 16
                require(not stat.S_ISLNK(mode) and not (info.flag_bits & 1), "MOSAICOS_ARCHIVE_MEMBER_TYPE_INVALID")
                if info.is_dir():
                    require(stat.S_IFMT(mode) in {0, stat.S_IFDIR} and info.file_size == 0, "MOSAICOS_ARCHIVE_MEMBER_TYPE_INVALID")
                    continue
                require(stat.S_IFMT(mode) in {0, stat.S_IFREG}, "MOSAICOS_ARCHIVE_MEMBER_TYPE_INVALID")
                require(info.file_size <= 32 * 1024 * 1024, "MOSAICOS_ARCHIVE_BUDGET_EXCEEDED")
                payload = archive.read(info)
                require(len(payload) == info.file_size, "MOSAICOS_ARCHIVE_MEMBER_LENGTH_MISMATCH")
                result[name] = payload
            # A file cannot simultaneously be an ancestor directory of a file.
            file_names = {name.casefold() for name in result}
            for name in folded:
                parts = name.split("/")
                require(all("/".join(parts[:i]) not in file_names for i in range(1, len(parts))), "MOSAICOS_ARCHIVE_PATH_COLLISION")
            return result
    except Refusal:
        raise
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, ValueError) as error:
        raise Refusal("MOSAICOS_ARCHIVE_INVALID", detail=type(error).__name__) from error


def pinned_archive_member(raw: bytes, *, expected_archive_sha256: str, member_path: str, expected_member_sha256: str) -> tuple[bytes, dict[str, Any]]:
    """Read actual member bytes under an external archive pin without extraction."""
    members = _archive(raw, expected_archive_sha256)
    name = _member_name(member_path)
    require(name in members, "MOSAICOS_ARCHIVE_MEMBER_MISSING")
    payload = members[name]
    require(_sha(payload) == require_root(expected_member_sha256), "MOSAICOS_MEMBER_PIN_MISMATCH")
    return payload, _sealed({"schema": "ucl.ucm.maturity.mosaicos_pinned_member.v1", "archive_sha256": expected_archive_sha256, "member_path": name, "member_sha256": expected_member_sha256, "length": len(payload), **_CEILING})


def _artifact(item: Any) -> None:
    require(type(item) is dict, "MOSAICOS_ARTIFACT_INVALID")
    require(type(item.get("label")) is str and bool(item["label"]), "MOSAICOS_ARTIFACT_INVALID")
    require_root(item.get("sha256"))
    require(type(item.get("length")) is int and item["length"] > 0, "MOSAICOS_ARTIFACT_INVALID")
    if "member_path" in item:
        _member_name(item["member_path"])
        require_root(item.get("container_sha256"))
        require(type(item.get("container_locator")) is str and bool(item["container_locator"]), "MOSAICOS_ARTIFACT_INVALID")
    else:
        require(type(item.get("locator")) is str and bool(item["locator"]), "MOSAICOS_ARTIFACT_INVALID")
    for field in ("manifest_root", "member_root", "package_root"):
        if field in item:
            require_root(item[field])


def _validated_inventory(inventory: dict[str, Any], receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _native_root(inventory, "inventory_root", "mosaicos.ucl_ucm_c4.m0_exact_inventory.v1")
    _native_root(receipt, "receipt_root", "mosaicos.ucl_ucm_c4.m0_receipt.v1")
    require(receipt.get("inventory_root") == inventory["inventory_root"], "MOSAICOS_M0_RECEIPT_INVENTORY_MISMATCH")
    require(receipt.get("stage") == "M0_EXACT_INVENTORY" and receipt.get("status") == "PASS_INFORMATION_ONLY_UNBOUND", "MOSAICOS_M0_STATUS_INVALID")
    require(type(receipt.get("effects")) is dict and bool(receipt["effects"]) and all(type(v) is int and v == 0 for v in receipt["effects"].values()), "MOSAICOS_M0_EFFECTS_NONZERO")
    expected_effects = {"adapter_activations", "bare_metal_contacts", "genesis_writes", "identity_bindings", "installations", "mosaicos_writes", "network_requests", "physical_media_writes"}
    require(set(receipt["effects"]) == expected_effects, "MOSAICOS_M0_EFFECT_SET_INVALID")
    require(type(inventory.get("inspected_artifacts")) is list and bool(inventory["inspected_artifacts"]), "MOSAICOS_M0_ARTIFACTS_INVALID")
    observed: dict[str, dict[str, Any]] = {}
    for artifact in inventory["inspected_artifacts"]:
        _artifact(artifact)
        require(artifact["label"] not in observed, "MOSAICOS_M0_ARTIFACT_DUPLICATE")
        observed[artifact["label"]] = artifact
    roles: dict[str, dict[str, Any]] = {}
    require(type(inventory.get("role_bindings")) is list, "MOSAICOS_ROLE_SET_INVALID")
    for role in inventory["role_bindings"]:
        exact_keys(role, {"candidate_kind", "candidates", "m1_requirement", "reason", "role", "status"})
        require(role["role"] in ROLES and role["role"] not in roles and role["status"] == "UNBOUND", "MOSAICOS_ROLE_SET_INVALID")
        require(type(role["candidate_kind"]) is str and bool(role["candidate_kind"]), "MOSAICOS_ROLE_SET_INVALID")
        require(all(type(role[k]) is str and bool(role[k]) for k in ("m1_requirement", "reason")), "MOSAICOS_ROLE_SET_INVALID")
        require(type(role["candidates"]) is list and bool(role["candidates"]), "MOSAICOS_ROLE_CANDIDATES_INVALID")
        seen: set[str] = set()
        for candidate in role["candidates"]:
            _artifact(candidate)
            label = candidate["label"]
            require(label not in seen and label in observed, "MOSAICOS_ROLE_CANDIDATE_NOT_OBSERVED")
            seen.add(label)
            require(all(candidate.get(k) == v for k, v in observed[label].items()), "MOSAICOS_ROLE_CANDIDATE_IDENTITY_MISMATCH")
        roles[role["role"]] = role
    require(set(roles) == set(ROLES), "MOSAICOS_ROLE_SET_INVALID")
    require(receipt.get("role_bindings") == [{"role": role, "status": "UNBOUND"} for role in ROLES], "MOSAICOS_M0_ROLE_RECEIPT_MISMATCH")
    foundation = roles["MOSAICOS_FOUNDATION"]["candidates"]
    require(type(inventory.get("foundation_order")) is list and bool(inventory["foundation_order"]), "MOSAICOS_FOUNDATION_ORDER_INVALID")
    require(inventory["foundation_order"] == [x["sha256"] for x in foundation] and len(set(inventory["foundation_order"])) == len(foundation), "MOSAICOS_FOUNDATION_ORDER_INVALID")
    for index, candidate in enumerate(foundation, 1):
        require(type(candidate.get("order")) is int and candidate["order"] == index, "MOSAICOS_FOUNDATION_ORDER_INVALID")
        require(sum(k in candidate for k in ("manifest_root", "member_root")) == 1, "MOSAICOS_FOUNDATION_COMMITMENT_AMBIGUOUS")
        require(type(candidate.get("role")) is str and bool(candidate["role"]), "MOSAICOS_FOUNDATION_ROLE_INVALID")
    source = inventory.get("source_selection")
    require(type(source) is dict and source.get("usb_dependency") == "NONE", "MOSAICOS_M0_SOURCE_INVALID")
    require_root(source.get("sha256"))
    require(type(receipt.get("package")) is dict and receipt["package"].get("sha256") == source["sha256"], "MOSAICOS_M0_SOURCE_INVALID")
    return roles


def prepare_m1_from_m0_archive(raw: bytes, *, expected_archive_sha256: str) -> dict[str, Any]:
    """Verify the complete M0 evidence envelope and prepare four UNBOUND roles.

    Valid ordered successor lineages are derived from pinned M0 data. No fixed
    Foundation archive hashes or fixed layer count are assumed by this API.
    """
    members = _archive(raw, expected_archive_sha256)
    require("PACKAGE-MANIFEST.json" in members, "MOSAICOS_M0_MANIFEST_MISSING")
    manifest = strict_loads(members["PACKAGE-MANIFEST.json"])
    _native_root(manifest, "manifest_root", "mosaicos.ucl_ucm_c4.m0_return_manifest.v1")
    require(manifest.get("root_convention") == "CANONICAL_JSON_POPPED_ROOT_V1", "MOSAICOS_M0_ROOT_DIALECT_INVALID")
    require(type(manifest.get("members")) is list and type(manifest.get("member_count")) is int and manifest["member_count"] == len(manifest["members"]), "MOSAICOS_M0_MEMBER_SET_INVALID")
    declared: set[str] = set()
    for row in manifest["members"]:
        exact_keys(row, {"length", "path", "sha256"})
        name = _member_name(row["path"])
        require(name not in declared and name in members and name != "PACKAGE-MANIFEST.json", "MOSAICOS_M0_MEMBER_SET_INVALID")
        declared.add(name)
        require(type(row["length"]) is int and row["length"] == len(members[name]) and _sha(members[name]) == require_root(row["sha256"]), "MOSAICOS_M0_MEMBER_BYTES_MISMATCH")
    require(set(members) == declared | {"PACKAGE-MANIFEST.json"}, "MOSAICOS_M0_MEMBER_SET_INVALID")
    require({"M0-EXACT-INVENTORY.json", "M0-RECEIPT.json", "M0-COMPATIBILITY-FINDINGS.json"} <= declared, "MOSAICOS_M0_REQUIRED_INPUT_MISSING")
    inventory = strict_loads(members["M0-EXACT-INVENTORY.json"])
    receipt = strict_loads(members["M0-RECEIPT.json"])
    findings = strict_loads(members["M0-COMPATIBILITY-FINDINGS.json"])
    roles = _validated_inventory(inventory, receipt)
    _native_root(findings, "findings_root", "mosaicos.ucl_ucm_c4.m0_compatibility_findings.v1")
    require(receipt.get("findings_root") == findings["findings_root"] and manifest.get("m0_receipt_root") == receipt["receipt_root"], "MOSAICOS_M0_EVIDENCE_LINK_MISMATCH")
    require(manifest.get("source_archive_sha256") == inventory["source_selection"]["sha256"], "MOSAICOS_M0_EVIDENCE_LINK_MISMATCH")
    foundation = _sealed({"schema": "ucl.ucm.maturity.mosaicos_ordered_foundation.v1", "status": "UNBOUND", "application_semantics": "ORDERED_LINEAGE_ONLY_NO_MERGE_OR_EXECUTION", "layers": roles["MOSAICOS_FOUNDATION"]["candidates"], "order": inventory["foundation_order"], "m0_inventory_root": inventory["inventory_root"], **_CEILING})
    genesis = _sealed({"schema": "ucl.ucm.maturity.mosaicos_genesis_correspondence.v1", "status": "UNBOUND", "foundation_set_root": foundation["root"], "seed_candidates": roles["GENESIS_SEED"]["candidates"], "native_correspondence_verified": False, "required_proof": "EXACT_CURRENT_FOUNDATION_TO_GENESIS_NATIVE_CORRESPONDENCE_OR_REVIEWED_SUCCESSOR_SEED", **_CEILING})
    target_rx = _sealed({"schema": "ucl.ucm.maturity.mosaicos_target_rx_requirements.v1", "status": "UNBOUND", "target_candidates": roles["TARGET_PROFILE"]["candidates"], "partial_ethernet_material": roles["ETHERNET_BOOTSTRAP_ADAPTER"]["candidates"], "selected_target": None, "real_target_selected": False, "network_authority": "NONE", "typed_rx_provider_verified": False, "requirements": ["GOVERNOR_SELECTED_EXACT_PROFILE_AND_TARGET_IDENTITY", "ISOLATED_OR_EMULATED_LINK_WITH_PACKET_AND_TIME_BUDGETS", "PREDECLARED_STOP_CONDITION", "COMPLETE_TARGET_SPECIFIC_TYPED_RX_AND_TX_PROVIDER", "PINNED_GENESIS_HANDSHAKE_REQUEST_RESPONSE_TRANSCRIPT", "TARGET_OBSERVATION_AND_ROLLBACK_TERMINAL_CUSTODY", "INDEPENDENT_NATIVE_PROVIDER_AND_CORRESPONDENCE_REVIEW"], **_CEILING})
    host = _sealed({"schema": "ucl.ucm.maturity.mosaicos_host_native_correspondence.v1", "status": "UNBOUND", "ucm_role": "HOST_ORCHESTRATION_CONTROL_PLANE", "trusted_guest_path": "NATIVE_PYTHON_FREE", "guest_python_authorized": False, "native_request_receipt_custody_rollback_correspondence_verified": False, **_CEILING})
    obligations = findings.get("missing_prerequisites")
    require(type(obligations) is list and bool(obligations) and all(type(x) is str and bool(x) for x in obligations), "MOSAICOS_M0_OBLIGATIONS_INVALID")
    return _sealed({"schema": "ucl.ucm.maturity.mosaicos_m1_preparation.v1", "status": "PREPARATION_ONLY", "m1_acceptance": "NOT_EARNED", "m1_stage": "M1_ETHERNET_BOOTSTRAP", "m1_rehearsal_performed": False, "m0_external_archive_sha256": expected_archive_sha256, "m0_manifest_root": manifest["manifest_root"], "m0_inventory_root": inventory["inventory_root"], "m0_receipt_root": receipt["receipt_root"], "m0_source_members": [{"path": n, "sha256": _sha(members[n]), "length": len(members[n])} for n in sorted(declared)], "role_bindings": [{"role": r, "status": "UNBOUND"} for r in ROLES], "foundation": foundation, "genesis": genesis, "target_rx": target_rx, "host_native": host, "subsystem_atlas_status": "DEEP_NATIVE_SOURCE_BYTES_NOT_SUPPLIED", "open_obligations": obligations, "additional_m1_entry_obligations": ["INDEPENDENTLY_ACCEPTED_M0_RECEIPT", "EXACT_BINDING_DECISION_REMAINS_REQUIRED", "BOUNDED_ETHERNET_REHEARSAL_AND_ORIGINAL_M1_RECEIPT_REQUIRED"], "observed_effects": [], **_CEILING})


def verify_m1_preparation(value: Any, *, expected_root: str) -> dict[str, Any]:
    """Check a pinned preparation record without elevating its claims."""
    exact_keys(value, {"schema", "status", "m1_acceptance", "m1_stage", "m1_rehearsal_performed", "m0_external_archive_sha256", "m0_manifest_root", "m0_inventory_root", "m0_receipt_root", "m0_source_members", "role_bindings", "foundation", "genesis", "target_rx", "host_native", "subsystem_atlas_status", "open_obligations", "additional_m1_entry_obligations", "observed_effects", "root"} | set(_CEILING))
    require(type(value) is dict and value.get("schema") == "ucl.ucm.maturity.mosaicos_m1_preparation.v1", "MOSAICOS_PREPARATION_SCHEMA_INVALID")
    require(value.get("root") == require_root(expected_root) == root({k: v for k, v in value.items() if k != "root"}), "MOSAICOS_PREPARATION_ROOT_MISMATCH")
    require(value.get("status") == "PREPARATION_ONLY" and value.get("m1_acceptance") == "NOT_EARNED" and value.get("m1_rehearsal_performed") is False and value.get("observed_effects") == [], "MOSAICOS_PREPARATION_ACCEPTANCE_FORBIDDEN")
    require(value.get("role_bindings") == [{"role": r, "status": "UNBOUND"} for r in ROLES], "MOSAICOS_PREPARATION_BINDING_FORBIDDEN")
    for key in ("foundation", "genesis", "target_rx", "host_native"):
        item = value.get(key)
        fields = {
            "foundation": {"schema", "status", "application_semantics", "layers", "order", "m0_inventory_root", "root"},
            "genesis": {"schema", "status", "foundation_set_root", "seed_candidates", "native_correspondence_verified", "required_proof", "root"},
            "target_rx": {"schema", "status", "target_candidates", "partial_ethernet_material", "selected_target", "real_target_selected", "network_authority", "typed_rx_provider_verified", "requirements", "root"},
            "host_native": {"schema", "status", "ucm_role", "trusted_guest_path", "guest_python_authorized", "native_request_receipt_custody_rollback_correspondence_verified", "root"},
        }
        exact_keys(item, fields[key] | set(_CEILING))
        require(type(item) is dict and item.get("status") == "UNBOUND" and item.get("root") == root({k: v for k, v in item.items() if k != "root"}), "MOSAICOS_PREPARATION_COMPONENT_INVALID")
        require(all(type(item.get(k)) is type(v) and item[k] == v for k, v in _CEILING.items()), "MOSAICOS_PREPARATION_CEILING_INVALID")
    require(all(type(value.get(k)) is type(v) and value[k] == v for k, v in _CEILING.items()), "MOSAICOS_PREPARATION_CEILING_INVALID")
    require(value["target_rx"].get("selected_target") is None and value["target_rx"].get("real_target_selected") is False and value["target_rx"].get("network_authority") == "NONE" and value["target_rx"].get("typed_rx_provider_verified") is False, "MOSAICOS_PREPARATION_TARGET_OR_RX_FORBIDDEN")
    require(value["genesis"].get("native_correspondence_verified") is False and value["genesis"].get("foundation_set_root") == value["foundation"]["root"], "MOSAICOS_PREPARATION_CORRESPONDENCE_FORBIDDEN")
    require(value["host_native"].get("guest_python_authorized") is False and value["host_native"].get("trusted_guest_path") == "NATIVE_PYTHON_FREE" and value["host_native"].get("native_request_receipt_custody_rollback_correspondence_verified") is False, "MOSAICOS_PREPARATION_GUEST_BOUNDARY_INVALID")
    require(value["host_native"].get("ucm_role") == "HOST_ORCHESTRATION_CONTROL_PLANE" and value.get("m1_stage") == "M1_ETHERNET_BOOTSTRAP", "MOSAICOS_PREPARATION_GUEST_BOUNDARY_INVALID")
    return copy.deepcopy(value)


def intake_subsystem_atlas(raw: bytes, *, expected_archive_sha256: str, atlas_member_path: str, expected_atlas_sha256: str, mapping_rows: list[dict[str, Any]], preparation: dict[str, Any], expected_preparation_root: str) -> dict[str, Any]:
    """Intake exact native payload and declared host/native subsystem mappings.

    A mapping preserves separate native and host commitment domains. Hash and
    read-set checks do not establish native semantic correspondence or atlas
    completeness. Embedded native payload claims remain untrusted source data.
    """
    verified = verify_m1_preparation(preparation, expected_root=expected_preparation_root)
    members = _archive(raw, expected_archive_sha256)
    name = _member_name(atlas_member_path)
    require(name in members and _sha(members[name]) == require_root(expected_atlas_sha256), "MOSAICOS_ATLAS_PIN_MISMATCH")
    require(len(members[name]) <= 4 * 1024 * 1024, "MOSAICOS_ATLAS_BUDGET_EXCEEDED")
    payload = strict_loads(members[name])
    require(type(payload) is dict and type(payload.get("schema")) is str and bool(payload["schema"]), "MOSAICOS_ATLAS_PAYLOAD_INVALID")
    require(type(mapping_rows) is list and 0 < len(mapping_rows) <= 1000, "MOSAICOS_ATLAS_MAPPING_INVALID")
    identifiers: set[str] = set()
    read_set = {name}
    for row in mapping_rows:
        exact_keys(row, {"subsystem_id", "native_artifacts", "host_request_contract_root", "native_request_contract_root", "native_receipt_contract_root", "custody_contract_root", "rollback_contract_root"})
        identifier = row["subsystem_id"]
        require(type(identifier) is str and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", identifier)) and identifier not in identifiers, "MOSAICOS_ATLAS_SUBSYSTEM_ID_INVALID")
        identifiers.add(identifier)
        for field in ("host_request_contract_root", "native_request_contract_root", "native_receipt_contract_root", "custody_contract_root", "rollback_contract_root"):
            require_root(row[field])
        require(type(row["native_artifacts"]) is list and bool(row["native_artifacts"]), "MOSAICOS_ATLAS_MAPPING_INVALID")
        paths: set[str] = set()
        for artifact in row["native_artifacts"]:
            exact_keys(artifact, {"path", "sha256"})
            path = _member_name(artifact["path"])
            require(path not in paths and path in members, "MOSAICOS_ATLAS_NATIVE_ARTIFACT_MISSING")
            paths.add(path)
            require(_sha(members[path]) == require_root(artifact["sha256"]), "MOSAICOS_ATLAS_NATIVE_ARTIFACT_PIN_MISMATCH")
            read_set.add(path)
    return _sealed({"schema": "ucl.ucm.maturity.mosaicos_subsystem_atlas_intake.v1", "status": "UNBOUND_DECLARED_MAPPING_ONLY", "preparation_root": verified["root"], "foundation_set_root": verified["foundation"]["root"], "source_archive_sha256": expected_archive_sha256, "atlas_member_path": name, "atlas_member_sha256": expected_atlas_sha256, "native_payload": payload, "native_payload_is_untrusted_source_data": True, "source_read_set": [{"path": p, "sha256": _sha(members[p]), "length": len(members[p])} for p in sorted(read_set)], "declared_subsystem_mappings": mapping_rows, "native_semantics_verified": False, "atlas_completeness_verified": False, "m1_acceptance": "NOT_EARNED", "observed_effects": [], **_CEILING})
