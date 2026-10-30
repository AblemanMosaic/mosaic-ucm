"""Deterministic software, journal, and cross-session integration artifacts."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path, PurePosixPath
from typing import Any
import zipfile

from uclop.canonical import canonical_bytes, exact_keys, require, root, strict_loads

from .amcas import BOUNDARY, compile_contract, validate_contract
from .reporting import build_report


MAX_MEMBER = 64 * 1024 * 1024
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def _safe_path(name: str) -> str:
    require(type(name) is str and name == PurePosixPath(name).as_posix()
            and not name.startswith("/") and ".." not in PurePosixPath(name).parts
            and "\\" not in name and ":" not in name and bool(name),
            "ARTIFACT_PATH_UNSAFE")
    return name


def deterministic_zip(payloads: dict[str, bytes], *, schema: str,
                      artifact_role: str) -> bytes:
    require("MANIFEST.json" not in payloads and bool(payloads), "ARTIFACT_PAYLOAD_INVALID")
    normalized: dict[str, bytes] = {}
    for name, raw in payloads.items():
        name = _safe_path(name)
        require(type(raw) is bytes and len(raw) <= MAX_MEMBER, "ARTIFACT_MEMBER_INVALID")
        require(name not in normalized, "ARTIFACT_MEMBER_DUPLICATE")
        normalized[name] = raw
    manifest = {
        "schema": schema, "artifact_role": artifact_role,
        "files": [{"path": name, "bytes": len(raw),
                   "sha256": hashlib.sha256(raw).hexdigest()}
                  for name, raw in sorted(normalized.items())], **BOUNDARY,
    }
    normalized["MANIFEST.json"] = canonical_bytes({**manifest, "manifest_root": root(manifest)})
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(normalized.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def verify_deterministic_zip(raw: bytes, *, expected_schema: str,
                             expected_role: str) -> dict[str, Any]:
    require(type(raw) is bytes and len(raw) <= 256 * 1024 * 1024, "ARTIFACT_ARCHIVE_INVALID")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            require(len(infos) == len({info.filename for info in infos})
                    and all(info.file_size <= MAX_MEMBER and info.compress_type == zipfile.ZIP_STORED
                            for info in infos), "ARTIFACT_ARCHIVE_MEMBERS_INVALID")
            payloads = {info.filename: archive.read(info) for info in infos}
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError) as error:
        raise ValueError("ARTIFACT_ARCHIVE_INVALID") from error
    require("MANIFEST.json" in payloads, "ARTIFACT_MANIFEST_MISSING")
    manifest = strict_loads(payloads.pop("MANIFEST.json"))
    item = exact_keys(manifest, {"schema", "artifact_role", "files", "standing",
                                 "authority_effect", "real_a5", "g0", "manifest_root"})
    require(item["schema"] == expected_schema and item["artifact_role"] == expected_role,
            "ARTIFACT_IDENTITY_INVALID")
    body = {key: value for key, value in item.items() if key != "manifest_root"}
    require(item["manifest_root"] == root(body), "ARTIFACT_MANIFEST_ROOT_INVALID")
    expected = [{"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in sorted(payloads.items())]
    require(item["files"] == expected, "ARTIFACT_MANIFEST_CONTENT_MISMATCH")
    rebuilt = deterministic_zip(payloads, schema=expected_schema, artifact_role=expected_role)
    require(rebuilt == raw, "ARTIFACT_ARCHIVE_NOT_CANONICAL")
    return item


def export_journal_archive(campaign, *, software_anchor: dict[str, Any]) -> bytes:
    checkpoint = campaign.journal.checkpoint()
    report = build_report(campaign)
    payloads = {
        "CONTRACT.json": canonical_bytes(campaign.contract()),
        "INTEGRATION-IR.json": canonical_bytes(campaign.compiled()),
        "journal/EVENTS.jsonl": campaign.journal.events_path.read_bytes(),
        "journal/HEAD.json": canonical_bytes(campaign.journal.head()),
        "CHECKPOINT.json": canonical_bytes(checkpoint),
        "INTEGRATION-REPORT.json": canonical_bytes(report),
        "SOFTWARE-ANCHOR.json": canonical_bytes(software_anchor),
        "VERIFY.py": (Path(__file__).resolve().parents[2] / "VERIFY.py").read_bytes(),
        "README.txt": ("UCM-AMCAS canonical integration journal archive\n"
                       "Verify MANIFEST.json before using any record.\n"
                       "Run VERIFY.py against the original archive with the journal schema and role.\n"
                       "INFORMATION_ONLY; authority effect NONE; real A5 false; G0 closed.\n").encode("ascii"),
    }
    return deterministic_zip(payloads, schema="mosaic.ucm.integration-journal-archive.v0.1",
                             artifact_role="CANONICAL_INTEGRATION_JOURNAL")


def _build_integration_kit(contract: dict[str, Any], compiled: dict[str, Any]) -> bytes:
    template_body = {
        "schema": "mosaic.ucm.session-integration-report.v0.1",
        "contract_root": contract["contract_root"], "ir_root": compiled["ir_root"],
        "session_mosaic_id": "<64-lowercase-hex>",
        "source_root_observed": contract["subject"]["source_root"],
        "requirement_dispositions": [], "operation_summaries": [], "findings": [],
        "artifacts": [], "limitations": [], "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED",
    }
    template = {**template_body, "report_root": root(template_body)}
    instructions = f"""# UCM-AMCAS integration session kit

Subject: {contract['application']['name']} {contract['application']['version']}
Contract root: `{contract['contract_root']}`
IR root: `{compiled['ir_root']}`

1. Verify this archive and the exact application source root before work.
2. Import the user's existing MosaicID passport if supplied; create a distinct session identity.
3. Do not treat a public key, passport, namespace, session, or report as permission.
4. Map every change to a CM1 obligation and CM2 preference. CM2 never overrides CM1.
5. Route every effect and capability grant through G1 Sentinel, G2 Witness, and G3 Diagnostic receipts.
6. Keep mandatory journal evidence separate from the nonsemantic progress stream.
7. Complete SESSION-REPORT.json with exact roots and return it with generated receipts.
8. Preserve INFORMATION_ONLY, authority effect NONE, real A5 false, and G0 closed.
""".encode("utf-8")
    payloads = {
        "AMCAS-CONTRACT.json": canonical_bytes(contract),
        "INTEGRATION-IR.json": canonical_bytes(compiled),
        "SESSION-REPORT.template.json": canonical_bytes(template),
        "INTEGRATION-INSTRUCTIONS.md": instructions,
    }
    return deterministic_zip(payloads, schema="mosaic.ucm.integration-kit.v0.1",
                             artifact_role="APPLICATION_INTEGRATION_KIT")


def build_integration_kit_from_contract(contract: dict[str, Any]) -> bytes:
    """Build a pre-campaign kit from an exact, unbound AMCAS contract.

    A kit is orientation material, not an active integration campaign.  It may
    therefore be prepared before user and session passports are supplied.  A
    live campaign still refuses to start until its required identities are
    authenticated.
    """
    validated = validate_contract(contract)
    return _build_integration_kit(validated, compile_contract(validated))


def build_integration_kit(campaign) -> bytes:
    return _build_integration_kit(campaign.contract(), campaign.compiled())
