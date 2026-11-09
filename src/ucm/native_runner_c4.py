"""Authority-safe native HeadlessRunner preflight for Stage I4 c4."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY
from .native_runner import NATIVE_OWNER, validate_binding
from .stage4_c4 import (validate_authority_policy, validate_run_contract,
                        validate_trust_anchors)


PREFLIGHT_SCHEMA = "mosaic.ucm.native-headless-runner-preflight.v0.2"


def build_preflight(*, run_contract: Any, trust_anchors: Any,
                    expected_trust_anchors_root: str,
                    execution_authority_policy: Any) -> dict[str, Any]:
    """Derive a preflight without caller-provided roots or authorization flags."""
    anchors = validate_trust_anchors(
        trust_anchors, expected_root=expected_trust_anchors_root)
    contract = validate_run_contract(
        run_contract, expected_trust_anchors_root=anchors["trust_anchors_root"])
    authority = validate_authority_policy(
        execution_authority_policy,
        expected_root=anchors["authority_policy_root"],
    )
    binding = validate_binding(contract["native_runner_binding"])
    require(binding["binding_root"] == anchors["native_runner_binding_root"]
            and contract["trust_anchors"] == anchors
            and contract["execution_authority_policy"] == authority,
            "NATIVE_RUNNER_PREFLIGHT_TRUST_BINDING_INVALID")
    effects = sorted({row["effect_class"] for row in contract["case_schedule"]})
    reason = (binding["reason_code"] if binding["binding_status"] != "BOUND"
              else authority["reason_code"])
    body = {
        "schema": PREFLIGHT_SCHEMA,
        "run_contract_root": contract["run_contract_root"],
        "execution_context_root": contract["execution_context"]["context_root"],
        "trust_anchors_root": anchors["trust_anchors_root"],
        "authority_policy_root": authority["authority_policy_root"],
        "binding_root": binding["binding_root"],
        "native_owner": NATIVE_OWNER,
        "provider": binding["provider"],
        "requested_effect_classes": effects,
        "decision": "REFUSE",
        "reason_code": reason,
        "fallback_execution_allowed": False,
        **BOUNDARY,
    }
    return {**body, "preflight_root": root(body)}


def validate_preflight(value: Any, *, expected_run_contract: Any,
                       expected_trust_anchors_root: str) -> dict[str, Any]:
    contract = validate_run_contract(
        expected_run_contract,
        expected_trust_anchors_root=expected_trust_anchors_root,
    )
    item = exact_keys(value, {
        "schema", "run_contract_root", "execution_context_root",
        "trust_anchors_root", "authority_policy_root", "binding_root",
        "native_owner", "provider", "requested_effect_classes", "decision",
        "reason_code", "fallback_execution_allowed", "standing",
        "authority_effect", "real_a5", "g0", "preflight_root",
    })
    expected = build_preflight(
        run_contract=contract,
        trust_anchors=contract["trust_anchors"],
        expected_trust_anchors_root=expected_trust_anchors_root,
        execution_authority_policy=contract["execution_authority_policy"],
    )
    require(item == expected, "NATIVE_RUNNER_PREFLIGHT_INVALID")
    return deepcopy(item)


def refuse_native_receipt_under_authority_none(*, expected_preflight: Any,
                                               expected_run_contract: Any,
                                               expected_trust_anchors_root: str) -> None:
    preflight = validate_preflight(
        expected_preflight, expected_run_contract=expected_run_contract,
        expected_trust_anchors_root=expected_trust_anchors_root)
    require(preflight["decision"] == "ALLOW",
            "NATIVE_RUNNER_RECEIPT_UNAVAILABLE_AUTHORITY_NONE")

