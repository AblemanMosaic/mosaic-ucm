"""Pure adapters from ordinary tool results into pinned UCM evidence subjects."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .evidence import build_evidence_envelope
from .system import BOUNDARY


SUPPORTED_TOOLS = {"PYTEST", "UNITTEST", "TSC", "ESLINT", "COVERAGE", "SBOM", "CI"}


def build_tool_evidence_subject(*, tool: str, subject_root: str,
                                invocation_root: str, output_root: str,
                                environment_root: str, verifier_root: str,
                                policy_root: str, issuer_root: str,
                                exit_code: int, counts: dict[str, int],
                                issued_at: int, not_after: int | None) -> dict[str, Any]:
    tool = tool.upper()
    require(tool in SUPPORTED_TOOLS, "UCM_TOOL_EVIDENCE_TOOL_UNSUPPORTED")
    for value in (subject_root, invocation_root, output_root, environment_root,
                  verifier_root, policy_root, issuer_root):
        require_root(value)
    require(type(exit_code) is int and type(exit_code) is not bool,
            "UCM_TOOL_EVIDENCE_EXIT_INVALID")
    require(type(counts) is dict and all(type(name) is str and name and
            type(value) is int and type(value) is not bool and value >= 0
            for name, value in counts.items()), "UCM_TOOL_EVIDENCE_COUNTS_INVALID")
    result_body = {
        "schema": "mosaic.ucm.external-tool-result.v0.1",
        "tool": tool, "subject_root": subject_root,
        "invocation_root": invocation_root, "output_root": output_root,
        "exit_code": exit_code, "counts": dict(sorted(counts.items())),
        "status": "PASS" if exit_code == 0 else "FAIL",
        "interpretation": "PRESENCE_AND_HASH_ONLY",
        "non_claims": ["UCM_DID_NOT_RUN_THE_TOOL", "NO_DEEP_SEMANTIC_ATTESTATION"],
        **BOUNDARY,
    }
    result = {**result_body, "result_root": root(result_body)}
    envelope = build_evidence_envelope(
        evidence_id=f"EXTERNAL.{tool}.{result['result_root'][:16]}",
        subject_root=subject_root, policy_root=policy_root,
        issuer_root=issuer_root, verifier_root=verifier_root,
        environment_root=environment_root, result_root=result["result_root"],
        result_status=result["status"], issued_at=issued_at,
        not_before=issued_at, not_after=not_after)
    body = {
        "schema": "mosaic.ucm.external-tool-evidence-subject.v0.1",
        "tool_result": result, "evidence_envelope": envelope,
        "status": "PASS_BOUND" if result["status"] == "PASS" else "BOUND_FAILURE",
        **BOUNDARY,
    }
    return {**body, "evidence_subject_root": root(body)}


def validate_tool_evidence_subject(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "tool_result", "evidence_envelope",
                              "status", "standing", "authority_effect",
                              "real_a5", "g0", "evidence_subject_root"})
    result = item["tool_result"]
    require(type(result) is dict and result.get("tool") in SUPPORTED_TOOLS,
            "UCM_TOOL_EVIDENCE_INVALID")
    expected = build_tool_evidence_subject(
        tool=result["tool"], subject_root=result["subject_root"],
        invocation_root=result["invocation_root"], output_root=result["output_root"],
        environment_root=item["evidence_envelope"]["environment_root"],
        verifier_root=item["evidence_envelope"]["verifier_root"],
        policy_root=item["evidence_envelope"]["policy_root"],
        issuer_root=item["evidence_envelope"]["issuer_root"],
        exit_code=result["exit_code"], counts=result["counts"],
        issued_at=item["evidence_envelope"]["issued_at"],
        not_after=item["evidence_envelope"]["not_after"])
    require(item == expected, "UCM_TOOL_EVIDENCE_INVALID")
    return deepcopy(item)
