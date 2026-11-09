"""Checker-earned, claim-bound evidence for the canonical operational facade."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from .deductive_proofs import evidence_subject, verify_proof
from .maturity_semantics import BOUNDARY, seal

CHECKER_KINDS = {
    "BOUND_OBSERVATION": "OBSERVED",
    "DOCUMENT_ROOT_MATCH": "DOCUMENTED",
    "ENFORCEMENT_STATUS": "ENFORCED",
    "EXACT_ROOT_MATCH": "PRESERVED",
    "TRUST_DECLARATION": "TRUSTED_ASSUMPTION",
}
PRIVILEGED_OUTCOMES = {"ADMITTED", "PROVED"}


def claim_root(identifier: str, statement: str) -> str:
    require(type(identifier) is str and bool(identifier), "CLAIM_ID_INVALID")
    require(type(statement) is str and bool(statement), "CLAIM_STATEMENT_INVALID")
    return root({"id": identifier, "statement": statement})


def _checker_root(kind: str) -> str:
    require(kind in CHECKER_KINDS, "CLAIM_CHECKER_KIND_INVALID")
    return root({"schema": "ucl.ucm.claim_checker.v1", "kind": kind,
                 "outcome": CHECKER_KINDS[kind], "implementation": "UCL_NATIVE_DETERMINISTIC"})


def _run_checker(kind: str, checker_input: Any, *, subject_roots: list[str], claim_digest: str) -> dict[str, Any]:
    require(kind in CHECKER_KINDS, "CLAIM_CHECKER_KIND_INVALID")
    keys = {
        "BOUND_OBSERVATION": {"observation_root", "observed_subject_root"},
        "DOCUMENT_ROOT_MATCH": {"document_root", "expected_document_root"},
        "ENFORCEMENT_STATUS": {"policy_root", "enforcement_root", "status"},
        "EXACT_ROOT_MATCH": {"left_root", "right_root"},
        "TRUST_DECLARATION": {"assumption_root", "declaration"},
    }
    item = exact_keys(checker_input, keys[kind], "$.checker_input")
    if kind == "BOUND_OBSERVATION":
        require_root(item["observation_root"])
        require(item["observed_subject_root"] in subject_roots, "CLAIM_OBSERVATION_SUBJECT_MISMATCH")
    elif kind == "DOCUMENT_ROOT_MATCH":
        require_root(item["document_root"]); require_root(item["expected_document_root"])
        require(item["document_root"] == item["expected_document_root"], "CLAIM_DOCUMENT_ROOT_MISMATCH")
    elif kind == "ENFORCEMENT_STATUS":
        require_root(item["policy_root"]); require_root(item["enforcement_root"])
        require(item["status"] == "PASS_ENFORCED", "CLAIM_ENFORCEMENT_NOT_PASSED")
    elif kind == "EXACT_ROOT_MATCH":
        require_root(item["left_root"]); require_root(item["right_root"])
        require(item["left_root"] == item["right_root"], "CLAIM_ROOTS_NOT_PRESERVED")
    else:
        require_root(item["assumption_root"])
        require(type(item["declaration"]) is str and bool(item["declaration"]), "CLAIM_TRUST_DECLARATION_INVALID")
    body = {"schema": "ucl.ucm.claim_checker_result.v2", "checker_kind": kind,
            "checker_root": _checker_root(kind), "checker_input": deepcopy(item),
            "checker_input_root": root(item), "subject_roots": subject_roots,
            "claim_root": claim_digest, "outcome": CHECKER_KINDS[kind], "status": "PASS_CHECKED"}
    return {**body, "result_root": root(body)}


def make_claim_evidence(*, subject_roots: list[str], claim_id: str, statement: str,
                        checker_kind: str, checker_input: dict[str, Any],
                        assumptions: list[str] | None = None) -> dict[str, Any]:
    """Create ordinary evidence only by executing a known deterministic checker."""
    require(type(subject_roots) is list and subject_roots == sorted(set(subject_roots)) and bool(subject_roots),
            "CLAIM_EVIDENCE_SUBJECTS_INVALID")
    for digest in subject_roots: require_root(digest)
    assumptions = [] if assumptions is None else assumptions
    require(type(assumptions) is list and assumptions == sorted(set(assumptions))
            and all(type(item) is str and item for item in assumptions), "CLAIM_EVIDENCE_ASSUMPTIONS_INVALID")
    digest = claim_root(claim_id, statement)
    checked = _run_checker(checker_kind, checker_input, subject_roots=subject_roots, claim_digest=digest)
    require(checked["outcome"] not in PRIVILEGED_OUTCOMES, "CLAIM_PRIVILEGED_OUTCOME_REQUIRES_TYPED_CHECKER")
    return seal({"schema": "ucl.ucm.claim_evidence.v2", "subject_roots": subject_roots,
        "claim_id": claim_id, "claim_root": digest, "checker_kind": checker_kind,
        "checker_root": checked["checker_root"], "checker_input": deepcopy(checker_input),
        "checker_result": checked, "checker_result_root": checked["result_root"],
        "outcome": checked["outcome"], "assumptions": assumptions,
        "status": "PASS_CHECKED", **BOUNDARY})


def make_native_proof_claim_evidence(*, subject_roots: list[str], claim_id: str, statement: str,
                                     contract: dict[str, Any], proof_bundle: dict[str, Any],
                                     expected_contract_root: str, expected_proof_bundle_root: str) -> dict[str, Any]:
    """Produce PROVED evidence only after replaying the native proof kernel."""
    require(type(subject_roots) is list and subject_roots == sorted(set(subject_roots)) and bool(subject_roots),
            "CLAIM_EVIDENCE_SUBJECTS_INVALID")
    for digest in subject_roots: require_root(digest)
    require(contract.get("contract_root") == require_root(expected_contract_root), "PROOF_CONTRACT_PIN_MISMATCH")
    require(proof_bundle.get("proof_bundle_root") == require_root(expected_proof_bundle_root),
            "PROOF_BUNDLE_PIN_MISMATCH")
    checked = verify_proof(contract, proof_bundle)
    require(checked["outcome"] == "PROVED", "CLAIM_PROOF_NOT_UNCONDITIONAL")
    subject = evidence_subject(contract)
    require(subject["subject_root"] in subject_roots, "CLAIM_PROOF_SUBJECT_MISMATCH")
    digest = claim_root(claim_id, statement)
    checker_root = root({"schema": "ucl.ucm.native_proof_checker.v1", "kernel": checked["kernel"],
                         "theory_root": checked["theory_root"]})
    return seal({"schema": "ucl.ucm.native_proof_claim_evidence.v1", "subject_roots": subject_roots,
        "claim_id": claim_id, "claim_root": digest, "checker_root": checker_root,
        "contract": deepcopy(contract), "contract_root": contract["contract_root"],
        "proof_bundle": deepcopy(proof_bundle), "proof_bundle_root": proof_bundle["proof_bundle_root"],
        "checker_result": checked, "checker_result_root": checked["check_root"],
        "outcome": "PROVED", "assumptions": [], "status": "PASS_CHECKED", **BOUNDARY})


def _rebuild_evidence(evidence: Any, *, statement: str) -> dict[str, Any]:
    require(type(evidence) is dict, "CLAIM_EVIDENCE_INVALID")
    if evidence.get("schema") == "ucl.ucm.claim_evidence.v2":
        return make_claim_evidence(subject_roots=evidence.get("subject_roots"), claim_id=evidence.get("claim_id"),
            statement=statement, checker_kind=evidence.get("checker_kind"), checker_input=evidence.get("checker_input"),
            assumptions=evidence.get("assumptions"))
    if evidence.get("schema") == "ucl.ucm.native_proof_claim_evidence.v1":
        return make_native_proof_claim_evidence(subject_roots=evidence.get("subject_roots"),
            claim_id=evidence.get("claim_id"), statement=statement, contract=evidence.get("contract"),
            proof_bundle=evidence.get("proof_bundle"), expected_contract_root=evidence.get("contract_root"),
            expected_proof_bundle_root=evidence.get("proof_bundle_root"))
    require(False, "CLAIM_EVIDENCE_SCHEMA_INVALID")
    raise AssertionError("unreachable")


def make_evidence_acceptance_contract(*, contract_id: str, subject_roots: list[str],
                                      claims: list[dict[str, Any]]) -> dict[str, Any]:
    require(type(contract_id) is str and bool(contract_id), "EVIDENCE_CONTRACT_ID_INVALID")
    require(type(subject_roots) is list and subject_roots == sorted(set(subject_roots)) and bool(subject_roots),
            "EVIDENCE_CONTRACT_SUBJECTS_INVALID")
    for digest in subject_roots: require_root(digest)
    require(type(claims) is list and bool(claims), "EVIDENCE_CONTRACT_CLAIMS_INVALID")
    rows=[]; identifiers=set()
    for value in claims:
        row=exact_keys(value, {"id", "statement", "evidence_root", "evidence_schema", "checker_root",
                               "accepted_outcome", "assumptions"}, "$.claims")
        require(type(row["id"]) is str and row["id"] and row["id"] not in identifiers,
                "EVIDENCE_CONTRACT_CLAIM_ID_INVALID")
        require(type(row["statement"]) is str and bool(row["statement"]), "EVIDENCE_CONTRACT_STATEMENT_INVALID")
        require_root(row["evidence_root"]); require_root(row["checker_root"])
        require(row["evidence_schema"] in {"ucl.ucm.claim_evidence.v2", "ucl.ucm.native_proof_claim_evidence.v1"},
                "EVIDENCE_CONTRACT_SCHEMA_INVALID")
        require(type(row["accepted_outcome"]) is str and bool(row["accepted_outcome"]), "EVIDENCE_CONTRACT_OUTCOME_INVALID")
        require(row["accepted_outcome"] != "ADMITTED", "EVIDENCE_CONTRACT_ADMISSION_AUTHORITY_UNAVAILABLE")
        if row["accepted_outcome"] == "PROVED":
            require(row["evidence_schema"] == "ucl.ucm.native_proof_claim_evidence.v1",
                    "EVIDENCE_CONTRACT_PROOF_SCHEMA_INVALID")
        require(type(row["assumptions"]) is list and row["assumptions"] == sorted(set(row["assumptions"]))
                and all(type(item) is str and item for item in row["assumptions"]), "EVIDENCE_CONTRACT_ASSUMPTIONS_INVALID")
        identifiers.add(row["id"]); rows.append({**deepcopy(row), "claim_root": claim_root(row["id"], row["statement"])})
    return seal({"schema": "ucl.ucm.evidence_acceptance_contract.v2", "contract_id": contract_id,
        "subject_roots": subject_roots, "claims": sorted(rows, key=lambda row: row["id"]),
        "contract_semantics": "CHECKER_REEXECUTION_FOR_EXACT_EVIDENCE_BYTES; NO_SELF_CERTIFICATION", **BOUNDARY})


def verify_evidence_acceptance_contract(value: Any, *, expected_root: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == "ucl.ucm.evidence_acceptance_contract.v2",
            "EVIDENCE_CONTRACT_INVALID")
    claims=[]
    for row in value.get("claims", []):
        require(type(row) is dict and row.get("claim_root") == claim_root(row.get("id"), row.get("statement")),
                "EVIDENCE_CONTRACT_CLAIM_ROOT_INVALID")
        claims.append({key: deepcopy(row[key]) for key in ("id", "statement", "evidence_root", "evidence_schema",
                                                           "checker_root", "accepted_outcome", "assumptions")})
    rebuilt=make_evidence_acceptance_contract(contract_id=value.get("contract_id"),
        subject_roots=value.get("subject_roots"), claims=claims)
    require(canonical_bytes(value) == canonical_bytes(rebuilt) and value["root"] == require_root(expected_root),
            "EVIDENCE_CONTRACT_PIN_MISMATCH")
    return rebuilt


def accept_claim_evidence(contract: Any, evidence: Any, *, expected_contract_root: str,
                          claim_id: str) -> dict[str, Any]:
    contract=verify_evidence_acceptance_contract(contract, expected_root=expected_contract_root)
    rows={row["id"]: row for row in contract["claims"]}
    require(claim_id in rows, "EVIDENCE_CLAIM_NOT_AUTHORIZED")
    binding=rows[claim_id]
    require(type(evidence) is dict and evidence.get("schema") == binding["evidence_schema"],
            "CLAIM_EVIDENCE_SCHEMA_INVALID")
    rebuilt=_rebuild_evidence(evidence, statement=binding["statement"])
    require(canonical_bytes(evidence) == canonical_bytes(rebuilt), "CLAIM_EVIDENCE_RECONSTRUCTION_MISMATCH")
    require(evidence["root"] == binding["evidence_root"] and evidence["subject_roots"] == contract["subject_roots"]
            and evidence["claim_id"] == claim_id and evidence["claim_root"] == binding["claim_root"]
            and evidence["checker_root"] == binding["checker_root"]
            and evidence["outcome"] == binding["accepted_outcome"]
            and evidence["assumptions"] == binding["assumptions"], "CLAIM_EVIDENCE_BINDING_MISMATCH")
    return seal({"schema": "ucl.ucm.accepted_claim_evidence.v2", "acceptance_contract_root": contract["root"],
        "acceptance_contract_id": contract["contract_id"], "evidence_root": evidence["root"],
        "evidence": deepcopy(evidence), "evidence_schema": evidence["schema"],
        "subject_roots": evidence["subject_roots"], "claim_id": claim_id, "claim_root": binding["claim_root"],
        "checker_root": binding["checker_root"], "checker_result_root": evidence["checker_result_root"],
        "outcome": binding["accepted_outcome"], "assumptions": binding["assumptions"],
        "status": "ACCEPTED_BOUND_EVIDENCE", **BOUNDARY})


def verify_accepted_claim_evidence(value: Any, *, evidence_contracts: list[dict[str, Any]],
                                   expected_contract_roots: list[str]) -> dict[str, Any]:
    require(type(expected_contract_roots) is list and expected_contract_roots == sorted(set(expected_contract_roots))
            and bool(expected_contract_roots), "ACCEPTED_EVIDENCE_CONTRACT_SET_INVALID")
    for digest in expected_contract_roots: require_root(digest)
    require(type(evidence_contracts) is list and bool(evidence_contracts), "ACCEPTED_EVIDENCE_CONTRACTS_REQUIRED")
    contracts: dict[str, dict[str, Any]] = {}
    for contract in evidence_contracts:
        require(type(contract) is dict and type(contract.get("root")) is str, "ACCEPTED_EVIDENCE_CONTRACT_INVALID")
        digest = require_root(contract["root"])
        require(digest not in contracts, "ACCEPTED_EVIDENCE_CONTRACT_DUPLICATE")
        contracts[digest] = verify_evidence_acceptance_contract(contract, expected_root=digest)
    require(sorted(contracts) == expected_contract_roots, "ACCEPTED_EVIDENCE_CONTRACT_SET_MISMATCH")
    item=exact_keys(value, {"schema", "acceptance_contract_root", "acceptance_contract_id", "evidence_root",
        "evidence", "evidence_schema", "subject_roots", "claim_id", "claim_root", "checker_root", "checker_result_root",
        "outcome", "assumptions", "status", "standing", "authority_effect", "real_a5", "g0", "root"})
    require(item["schema"] == "ucl.ucm.accepted_claim_evidence.v2"
            and item["acceptance_contract_root"] in expected_contract_roots
            and item["status"] == "ACCEPTED_BOUND_EVIDENCE", "ACCEPTED_EVIDENCE_INVALID")
    for field in ("evidence_root", "claim_root", "checker_root", "checker_result_root", "root"): require_root(item[field])
    require(type(item["subject_roots"]) is list and item["subject_roots"] == sorted(set(item["subject_roots"])),
            "ACCEPTED_EVIDENCE_SUBJECTS_INVALID")
    for digest in item["subject_roots"]: require_root(digest)
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE"
            and item["real_a5"] is False and item["g0"] == "CLOSED", "ACCEPTED_EVIDENCE_AUTHORITY_INVALID")
    rebuilt = accept_claim_evidence(contracts[item["acceptance_contract_root"]], item["evidence"],
        expected_contract_root=item["acceptance_contract_root"], claim_id=item["claim_id"])
    require(canonical_bytes(item) == canonical_bytes(rebuilt), "ACCEPTED_EVIDENCE_RECONSTRUCTION_MISMATCH")
    return rebuilt
