"""Application-level architecture fidelity contracts.

The integration adapter derives an exact change manifest from a candidate.
This module checks that manifest against application-owned architecture rules;
it does not infer code meaning or replace application-native tests.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .system import BOUNDARY


def _paths(values: Any, code: str) -> list[str]:
    require(type(values) is list and all(type(value) is str and value for value in values)
            and len(values) == len(set(values)), code)
    for value in values:
        path = PurePosixPath(value)
        require(path.as_posix() == value and not path.is_absolute()
                and ".." not in path.parts and "\\" not in value, code)
    return list(values)


def _strings(values: Any, code: str) -> list[str]:
    require(type(values) is list and all(type(value) is str and value for value in values)
            and len(values) == len(set(values)), code)
    return list(values)


def _accepted_test_evidence(value: Any, *, subject_root: str,
                            change_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "change_root",
        "test_set_root", "failures", "errors", "skips", "status", "receipt_root"})
    require(item["schema"] == "mosaic.ucm.accepted-test-evidence.v0.1",
            "UCM_ARCHITECTURE_TEST_EVIDENCE_SCHEMA_INVALID")
    for field in ("subject_root", "change_root", "test_set_root"):
        require_root(item[field])
    require(item["subject_root"] == subject_root and item["change_root"] == change_root,
            "UCM_ARCHITECTURE_TEST_EVIDENCE_BINDING_INVALID")
    require(item["status"] == "PASS"
            and all(type(item[field]) is int and type(item[field]) is not bool
                    and item[field] == 0 for field in ("failures", "errors", "skips")),
            "UCM_ARCHITECTURE_TEST_EVIDENCE_NOT_ACCEPTED")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "receipt_root"}
    require(item["receipt_root"] == root(body),
            "UCM_ARCHITECTURE_TEST_EVIDENCE_ROOT_INVALID")
    return deepcopy(item)


def _accepted_proof_evidence(value: Any, *, subject_root: str,
                             change_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "change_root",
        "proof_contract_root", "proof_root", "checker_root", "status", "receipt_root"})
    require(item["schema"] == "mosaic.ucm.accepted-proof-evidence.v0.1",
            "UCM_ARCHITECTURE_PROOF_EVIDENCE_SCHEMA_INVALID")
    for field in ("subject_root", "change_root", "proof_contract_root", "proof_root",
                  "checker_root"):
        require_root(item[field])
    require(item["subject_root"] == subject_root and item["change_root"] == change_root,
            "UCM_ARCHITECTURE_PROOF_EVIDENCE_BINDING_INVALID")
    require(item["status"] == "PASS", "UCM_ARCHITECTURE_PROOF_EVIDENCE_NOT_ACCEPTED")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "receipt_root"}
    require(item["receipt_root"] == root(body),
            "UCM_ARCHITECTURE_PROOF_EVIDENCE_ROOT_INVALID")
    return deepcopy(item)


def validate_architecture_contract(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "contract_id", "subject_root", "impact_paths",
        "protected_paths", "required_existing_abstractions", "new_abstractions_allowed",
        "test_evidence_required", "proof_evidence_required", "scope_policy",
        "authority_ceiling", "contract_root"})
    require(item["schema"] == "mosaic.ucm.architecture-fidelity-contract.v0.1",
            "UCM_ARCHITECTURE_SCHEMA_INVALID")
    require(type(item["contract_id"]) is str and item["contract_id"],
            "UCM_ARCHITECTURE_ID_INVALID")
    require_root(item["subject_root"])
    impact = _paths(item["impact_paths"], "UCM_ARCHITECTURE_PATH_INVALID")
    protected = _paths(item["protected_paths"], "UCM_ARCHITECTURE_PATH_INVALID")
    require(not set(impact) & set(protected), "UCM_ARCHITECTURE_PATH_CONFLICT")
    _strings(item["required_existing_abstractions"], "UCM_ARCHITECTURE_ABSTRACTION_INVALID")
    require(type(item["new_abstractions_allowed"]) is bool
            and type(item["test_evidence_required"]) is bool
            and type(item["proof_evidence_required"]) is bool,
            "UCM_ARCHITECTURE_POLICY_INVALID")
    require(item["scope_policy"] == "DECLARED_IMPACT_PATHS_ONLY",
            "UCM_ARCHITECTURE_SCOPE_POLICY_UNSUPPORTED")
    require(item["authority_ceiling"] == BOUNDARY, "UCM_ARCHITECTURE_AUTHORITY_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "contract_root"}
    require(item["contract_root"] == root(body), "UCM_ARCHITECTURE_ROOT_INVALID")
    return deepcopy(item)


def check_architecture_change(contract: Any, candidate: Any) -> dict[str, Any]:
    policy = validate_architecture_contract(contract)
    item = exact_keys(candidate, {"schema", "subject_root", "changed_paths",
        "existing_abstractions_used", "introduced_abstractions", "supersession_roots",
        "test_evidence_receipts", "proof_evidence_receipts", "change_root",
        "candidate_root"})
    require(item["schema"] == "mosaic.ucm.architecture-change-manifest.v0.2",
            "UCM_ARCHITECTURE_CHANGE_SCHEMA_INVALID")
    require_root(item["subject_root"])
    changed = _paths(item["changed_paths"], "UCM_ARCHITECTURE_CHANGE_PATH_INVALID")
    used = _strings(item["existing_abstractions_used"], "UCM_ARCHITECTURE_CHANGE_ABSTRACTION_INVALID")
    introduced = _strings(item["introduced_abstractions"], "UCM_ARCHITECTURE_CHANGE_ABSTRACTION_INVALID")
    require(type(item["supersession_roots"]) is list,
            "UCM_ARCHITECTURE_SUPERSESSION_INVALID")
    for value in item["supersession_roots"]:
        require_root(value)
    require(type(item["test_evidence_receipts"]) is list
            and type(item["proof_evidence_receipts"]) is list,
            "UCM_ARCHITECTURE_EVIDENCE_INVALID")
    change_body = {key: deepcopy(item[key]) for key in (
        "schema", "subject_root", "changed_paths", "existing_abstractions_used",
        "introduced_abstractions", "supersession_roots")}
    require(item["change_root"] == root(change_body),
            "UCM_ARCHITECTURE_CHANGE_ROOT_INVALID")
    test_evidence = [_accepted_test_evidence(value,
        subject_root=item["subject_root"], change_root=item["change_root"])
        for value in item["test_evidence_receipts"]]
    proof_evidence = [_accepted_proof_evidence(value,
        subject_root=item["subject_root"], change_root=item["change_root"])
        for value in item["proof_evidence_receipts"]]
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "candidate_root"}
    require(item["candidate_root"] == root(body), "UCM_ARCHITECTURE_CHANGE_ROOT_INVALID")

    impact = set(policy["impact_paths"]); protected = set(policy["protected_paths"])
    checks = [
        {"id": "SUBJECT_BOUND", "status": "PASS" if item["subject_root"] == policy["subject_root"] else "FAIL",
         "refusal_code": "UCM_ARCHITECTURE_SUBJECT_MISMATCH"},
        {"id": "CHANGE_SCOPE", "status": "PASS" if set(changed) <= impact else "FAIL",
         "refusal_code": "UCM_ARCHITECTURE_SCOPE_VIOLATION"},
        {"id": "PROTECTED_PATHS", "status": "PASS" if not set(changed) & protected else "FAIL",
         "refusal_code": "UCM_ARCHITECTURE_PROTECTED_PATH_CHANGED"},
        {"id": "EXISTING_ABSTRACTIONS", "status": "PASS" if set(policy["required_existing_abstractions"]) <= set(used) else "FAIL",
         "refusal_code": "UCM_ARCHITECTURE_REQUIRED_ABSTRACTION_MISSING"},
        {"id": "NEW_ABSTRACTIONS", "status": "PASS" if policy["new_abstractions_allowed"] or not introduced
         or bool(item["supersession_roots"]) else "FAIL",
         "refusal_code": "UCM_ARCHITECTURE_UNJUSTIFIED_ABSTRACTION"},
        {"id": "TEST_EVIDENCE", "status": "PASS" if not policy["test_evidence_required"]
         or bool(test_evidence) else "FAIL",
         "refusal_code": "UCM_ARCHITECTURE_TEST_EVIDENCE_MISSING"},
        {"id": "PROOF_EVIDENCE", "status": "PASS" if not policy["proof_evidence_required"]
         or bool(proof_evidence) else "FAIL",
         "refusal_code": "UCM_ARCHITECTURE_PROOF_EVIDENCE_MISSING"},
    ]
    failed = [row["refusal_code"] for row in checks if row["status"] == "FAIL"]
    result = {"schema": "mosaic.ucm.architecture-change-check.v0.1",
              "contract_root": policy["contract_root"], "candidate_root": item["candidate_root"],
              "change_root": item["change_root"],
              "accepted_test_evidence_roots": [row["receipt_root"] for row in test_evidence],
              "accepted_proof_evidence_roots": [row["receipt_root"] for row in proof_evidence],
              "checks": checks, "reason_codes": failed,
              "status": "PASS_ARCHITECTURE_FIDELITY" if not failed else "REFUSED_ARCHITECTURE_DRIFT",
              "non_claims": ["EVIDENCE_RECEIPTS_NOT_REEXECUTED",
                             "NOT_MERGE_AUTHORITY"], **BOUNDARY}
    return {**result, "check_root": root(result)}
