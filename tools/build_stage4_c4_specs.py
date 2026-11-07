"""Build the deterministic Stage I4 c4 trust and qualification contracts."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.native_runner import build_unavailable_binding
from ucm.stage4_c3 import CONTEXT_SCHEMA
from ucm.stage4_c4 import AUTHORITY_POLICY_SCHEMA, TRUST_ANCHORS_SCHEMA


def write(path: Path, value: dict) -> None:
    path.write_bytes(canonical_bytes(value))


def main() -> int:
    vendor = json.loads((ROOT / "vendor/aok-headless-runner/NATIVE-RUNNER-BINDING-SOURCE.json").read_text(encoding="utf-8"))
    jurisdiction_root = root({"jurisdiction": "UNBOUND_STAGE_I4_C4_QUALIFICATION"})
    authority_body = {
        "schema": AUTHORITY_POLICY_SCHEMA,
        "policy_id": "UCM.AMCAS.STAGE_I4.C4.AUTHORITY.NONE",
        "jurisdiction_root": jurisdiction_root, "generation": 1,
        "execution_authorized": False, "allowed_effect_classes": [],
        "reason_code": "EXECUTION_AUTHORITY_NOT_GRANTED", **BOUNDARY,
    }
    authority = {**authority_body, "authority_policy_root": root(authority_body)}
    context_body = {"schema": CONTEXT_SCHEMA,
        "identity_root": root({"identity": "UNBOUND"}),
        "session_root": root({"session": "QUALIFICATION_ONLY"}),
        "jurisdiction_root": jurisdiction_root, "generation": 1,
        "policy_root": root({"policy": "INFORMATION_ONLY"}),
        "budget_root": root({"budget": "NO_EFFECTS"}),
        "rollback_root": root({"rollback": "NO_EFFECTS"}), **BOUNDARY}
    context = {**context_body, "context_root": root(context_body)}
    binding = build_unavailable_binding(
        runner_id="AOK.COURTHOUSE.HEADLESS.RUNNER",
        provider="CODEX_HEADLESS_LOCAL",
        transport="FIXED_ARGV_LOCAL_PROCESS",
        source_sha256=vendor["runner_source_sha256"],
        source_manifest_root=vendor["source_manifest_root"],
        runner_contract_sha256=vendor["contract_sha256"]["R4_0_CODEX_EXEC_CONTRACT.json"],
        console_contract_sha256=vendor["contract_sha256"]["R3_9_LOCAL_HEADLESS_CONSOLE_CONTRACT.json"],
    )
    review_policy_body = {"schema": "mosaic.ucm.stage-i4-c4-review-policy-contract.v0.1",
        "accepted_review_class": "INDEPENDENT_REVIEW",
        "required_exact_pins": ["reviewer_identity_root", "archive_sha256",
            "subject_root", "source_root", "qualification_root", "file_sha256"],
        "self_certification_accepted": False, **BOUNDARY}
    review_policy = {**review_policy_body, "policy_root": root(review_policy_body)}
    anchors_body = {"schema": TRUST_ANCHORS_SCHEMA,
        "anchor_id": "UCM.AMCAS.STAGE_I4.C4.QUALIFICATION.TRUST.v1",
        "review_policy_root": review_policy["policy_root"],
        "execution_context_root": context["context_root"],
        "native_runner_binding_root": binding["binding_root"],
        "native_runner_source_sha256": binding["source_sha256"],
        "native_runner_source_manifest_root": binding["source_manifest_root"],
        "authority_policy_root": authority["authority_policy_root"],
        "jurisdiction_root": jurisdiction_root, **BOUNDARY}
    anchors = {**anchors_body, "trust_anchors_root": root(anchors_body)}
    contract_body = {"schema": "mosaic.ucm.amcas-stage-i4-c4-contract.v0.1",
        "subject": "UCM-AMCAS Stage I4 anchored operation successor",
        "happy_path": "TRUST_ANCHORED_PREPARATION_AND_TYPED_AUTHORITY_NONE_REFUSAL",
        "review_policy_root": review_policy["policy_root"],
        "trust_anchors_root": anchors["trust_anchors_root"],
        "authority_policy_root": authority["authority_policy_root"],
        "native_execution_owner": "AOK_COURTHOUSE_HEADLESS_RUNNER",
        "native_runner_fallback_allowed": False,
        "progress_semantics": "BEST_EFFORT_NONSEMANTIC",
        "qualification_class": "BUILDER_POSITIVE_QUALIFICATION",
        "operator_tier1_status": "PREPARED_NOT_EXECUTED_BY_BUILDER",
        "legacy_routes": "LABELED_COMPATIBILITY_ONLY",
        **BOUNDARY}
    contract = {**contract_body, "contract_root": root(contract_body)}
    write(ROOT / "spec/STAGE-I4-C4-AUTHORITY-POLICY.json", authority)
    write(ROOT / "spec/STAGE-I4-C4-EXECUTION-CONTEXT.json", context)
    write(ROOT / "spec/STAGE-I4-C4-NATIVE-BINDING.json", binding)
    write(ROOT / "spec/STAGE-I4-C4-REVIEW-POLICY-CONTRACT.json", review_policy)
    write(ROOT / "spec/STAGE-I4-C4-TRUST-ANCHORS.json", anchors)
    write(ROOT / "spec/STAGE-I4-C4-CONTRACT.json", contract)
    print(canonical_bytes({"status": "PASS", "contract_root": contract["contract_root"],
        "trust_anchors_root": anchors["trust_anchors_root"], **BOUNDARY}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
