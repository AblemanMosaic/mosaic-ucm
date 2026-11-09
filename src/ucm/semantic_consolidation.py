"""Hybrid semantic-consolidation pipeline.

Deterministic code discovers policy-declared candidates and compiles exact
comparison obligations. FSC, LLM, or human judgment may propose a meaning
correspondence, but only an explicitly human-confirmed decision can mark a
candidate ready for a correspondence court. No stage claims equivalence or
authorizes consolidation.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import product
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .system import BOUNDARY


DECISIONS = {
    "CONFIRMED_FOR_CORRESPONDENCE",
    "PROVISIONAL_CANDIDATE",
    "NEEDS_EVIDENCE",
    "DISTINCT_SEMANTICS",
}
DECIDER_KINDS = {"HUMAN", "FSC", "LLM", "FSC_LLM_HYPOTHESIS", "COMPOSITE"}
COMPARISON_OBLIGATIONS = (
    "EXACT_SUBJECT_BINDING",
    "INPUT_SCHEMA_CORRESPONDENCE",
    "OUTPUT_SCHEMA_CORRESPONDENCE",
    "DECISION_AND_REFUSAL_CORRESPONDENCE",
    "EFFECT_AND_BUDGET_CORRESPONDENCE",
    "AUTHORITY_AND_JURISDICTION_PRESERVATION",
    "RECOVERY_AND_UNCERTAINTY_CORRESPONDENCE",
    "PRIVACY_AND_DISCLOSURE_CORRESPONDENCE",
)


def _body_root(value: dict[str, Any], field: str) -> str:
    return root({key: raw for key, raw in value.items() if key != field})


def _strings(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and (allow_empty or bool(value)), code)
    require(all(type(item) is str and bool(item) for item in value), code)
    require(len(value) == len(set(value)), code)
    return list(value)


def validate_discovery_policy(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "policy_id", "families", "standing",
                              "authority_effect", "real_a5", "g0", "policy_root"})
    require(item["schema"] == "mosaic.ucm.semantic-discovery-policy.v0.1",
            "UCM_SEMANTIC_POLICY_SCHEMA_INVALID")
    require(type(item["policy_id"]) is str and item["policy_id"],
            "UCM_SEMANTIC_POLICY_ID_INVALID")
    require(type(item["families"]) is list and bool(item["families"]),
            "UCM_SEMANTIC_POLICY_FAMILIES_INVALID")
    family_ids = []
    for family in item["families"]:
        checked = exact_keys(family, {"family_id", "label",
                                     "reference_application_id", "roles",
                                     "comparison_dimensions",
                                     "allowed_consolidation_forms"})
        for field in ("family_id", "label", "reference_application_id"):
            require(type(checked[field]) is str and checked[field],
                    "UCM_SEMANTIC_POLICY_FAMILY_INVALID")
        family_ids.append(checked["family_id"])
        _strings(checked["comparison_dimensions"],
                 "UCM_SEMANTIC_POLICY_DIMENSIONS_INVALID", allow_empty=False)
        _strings(checked["allowed_consolidation_forms"],
                 "UCM_SEMANTIC_POLICY_FORMS_INVALID", allow_empty=False)
        require(type(checked["roles"]) is list and bool(checked["roles"]),
                "UCM_SEMANTIC_POLICY_ROLES_INVALID")
        role_ids = []
        for role in checked["roles"]:
            row = exact_keys(role, {"role_id", "capability_tokens"})
            require(type(row["role_id"]) is str and row["role_id"],
                    "UCM_SEMANTIC_POLICY_ROLE_INVALID")
            _strings(row["capability_tokens"],
                     "UCM_SEMANTIC_POLICY_TOKENS_INVALID", allow_empty=False)
            role_ids.append(row["role_id"])
        require(len(role_ids) == len(set(role_ids)),
                "UCM_SEMANTIC_POLICY_ROLE_DUPLICATE")
    require(len(family_ids) == len(set(family_ids)),
            "UCM_SEMANTIC_POLICY_FAMILY_DUPLICATE")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "UCM_SEMANTIC_POLICY_AUTHORITY_INVALID")
    require(item["policy_root"] == _body_root(item, "policy_root"),
            "UCM_SEMANTIC_POLICY_ROOT_INVALID")
    return deepcopy(item)


def _validate_plan(value: Any) -> dict[str, Any]:
    require(type(value) is dict, "UCM_SEMANTIC_PLAN_INVALID")
    require(value.get("schema") == "mosaic.ucm.stage-i3-shadow-plan.v0.1",
            "UCM_SEMANTIC_PLAN_SCHEMA_INVALID")
    require(type(value.get("application_id")) is str and value["application_id"],
            "UCM_SEMANTIC_PLAN_APPLICATION_INVALID")
    require(type(value.get("capability_projections")) is list,
            "UCM_SEMANTIC_PLAN_CAPABILITIES_INVALID")
    require_root(value.get("plan_root"))
    require(value["plan_root"] == root({key: raw for key, raw in value.items()
                                       if key != "plan_root"}),
            "UCM_SEMANTIC_PLAN_ROOT_INVALID")
    for projection in value["capability_projections"]:
        require(type(projection) is dict, "UCM_SEMANTIC_PROJECTION_INVALID")
        for field in ("capability_id", "effect_class", "input_schema_root",
                      "output_schema_root", "native_route",
                      "control_plane_disposition"):
            require(field in projection, "UCM_SEMANTIC_PROJECTION_INVALID")
        require_root(projection["input_schema_root"])
        require_root(projection["output_schema_root"])
    return deepcopy(value)


def discover_candidates(plans: list[Any], policy_value: Any) -> dict[str, Any]:
    policy = validate_discovery_policy(policy_value)
    checked_plans = [_validate_plan(plan) for plan in plans]
    applications = [plan["application_id"] for plan in checked_plans]
    require(len(applications) == len(set(applications)),
            "UCM_SEMANTIC_APPLICATION_DUPLICATE")
    plan_roots = {plan["application_id"]: plan["plan_root"]
                  for plan in checked_plans}
    candidates = []
    comparison_count = 0
    for family in policy["families"]:
        for role in family["roles"]:
            tokens = [token.upper() for token in role["capability_tokens"]]
            members = []
            for plan in checked_plans:
                for projection in plan["capability_projections"]:
                    capability = projection["capability_id"].upper()
                    if not any(token in capability for token in tokens):
                        continue
                    body = {
                        "application_id": plan["application_id"],
                        "plan_root": plan["plan_root"],
                        "capability_id": projection["capability_id"],
                        "effect_class": projection["effect_class"],
                        "input_schema_root": projection["input_schema_root"],
                        "output_schema_root": projection["output_schema_root"],
                        "native_route": projection["native_route"],
                        "control_plane_disposition": projection[
                            "control_plane_disposition"],
                    }
                    members.append({**body, "member_root": root(body)})
            members.sort(key=lambda row: (row["application_id"],
                                          row["capability_id"]))
            applications_for_role = sorted({row["application_id"] for row in members})
            reference = family["reference_application_id"]
            if len(applications_for_role) < 2 or reference not in applications_for_role:
                continue
            reference_members = [row for row in members
                                 if row["application_id"] == reference]
            consumer_members = [row for row in members
                                if row["application_id"] != reference]
            pairs = []
            for reference_member, consumer in product(reference_members,
                                                       consumer_members):
                pair_body = {
                    "reference_member_root": reference_member["member_root"],
                    "consumer_member_root": consumer["member_root"],
                    "reference_application_id": reference,
                    "consumer_application_id": consumer["application_id"],
                }
                pairs.append({**pair_body, "pair_root": root(pair_body)})
            pairs.sort(key=lambda row: (row["consumer_application_id"],
                                        row["pair_root"]))
            comparison_count += len(pairs)
            body = {
                "candidate_id": f"{family['family_id']}:{role['role_id']}",
                "family_id": family["family_id"],
                "role_id": role["role_id"],
                "label": f"{family['label']} / {role['role_id']}",
                "reference_application_id": reference,
                "application_ids": applications_for_role,
                "members": members,
                "comparison_pairs": pairs,
                "comparison_dimensions": deepcopy(
                    family["comparison_dimensions"]),
                "allowed_consolidation_forms": deepcopy(
                    family["allowed_consolidation_forms"]),
                "claim": "CANDIDATE_DISCOVERED_BY_ROOTED_POLICY_NOT_EQUIVALENCE",
            }
            candidates.append({**body, "candidate_root": root(body)})
    candidates.sort(key=lambda row: row["candidate_id"])
    body = {
        "schema": "mosaic.ucm.semantic-candidate-discovery.v0.1",
        "policy_root": policy["policy_root"],
        "application_plan_roots": dict(sorted(plan_roots.items())),
        "candidate_count": len(candidates),
        "comparison_pair_count": comparison_count,
        "candidates": candidates,
        "status": "CANDIDATES_ONLY",
        "non_claims": ["NOT_SEMANTIC_EQUIVALENCE", "NOT_COMPOSITION",
                       "NOT_CODE_DEDUPLICATION", "NOT_EXECUTION"],
        **BOUNDARY,
    }
    return {**body, "discovery_root": root(body)}


def build_judgment_packet(discovery_value: Any) -> dict[str, Any]:
    require(type(discovery_value) is dict
            and discovery_value.get("schema")
            == "mosaic.ucm.semantic-candidate-discovery.v0.1",
            "UCM_SEMANTIC_DISCOVERY_INVALID")
    require(discovery_value.get("discovery_root")
            == _body_root(discovery_value, "discovery_root"),
            "UCM_SEMANTIC_DISCOVERY_ROOT_INVALID")
    questions = []
    for candidate in discovery_value["candidates"]:
        body = {
            "judgment_id": f"JUDGMENT:{candidate['candidate_id']}",
            "candidate_root": candidate["candidate_root"],
            "question": ("Do these application-local capabilities realize a "
                         "shared constitutional role under the declared "
                         "comparison dimensions?"),
            "required_determinations": [
                "INTENDED_MEANING",
                "DOMAIN_DISTINCTION",
                "FAILURE_SEMANTICS",
                "AUTHORITY_OWNERSHIP",
                "PRIVACY_AND_DISCLOSURE",
                "ACCEPTABLE_EVIDENCE",
            ],
            "allowed_decisions": sorted(DECISIONS),
            "human_confirmation_required_for_court": True,
        }
        questions.append({**body, "question_root": root(body)})
    body = {
        "schema": "mosaic.ucm.semantic-judgment-packet.v0.1",
        "discovery_root": discovery_value["discovery_root"],
        "questions": questions,
        "status": "AWAITING_EXTERNAL_JUDGMENT",
        "non_claims": ["LLM_OUTPUT_NOT_AUTHORITY", "FSC_OUTPUT_NOT_AUTHORITY",
                       "NO_IMPLICIT_HUMAN_APPROVAL"],
        **BOUNDARY,
    }
    return {**body, "packet_root": root(body)}



def build_judgment_submission(packet_value: Any, intent_value: Any) -> dict[str, Any]:
    """Compile a plain judgment intent into an exact rooted submission.

    This writer aid keeps humans and modeling systems out of the cryptographic
    bookkeeping. It does not elevate a decision: the human-confirmation rule
    is enforced again when the submission is recorded.
    """
    packet = packet_value
    require(type(packet) is dict and packet.get("schema")
            == "mosaic.ucm.semantic-judgment-packet.v0.1",
            "UCM_SEMANTIC_JUDGMENT_PACKET_INVALID")
    require(packet.get("packet_root") == _body_root(packet, "packet_root"),
            "UCM_SEMANTIC_JUDGMENT_PACKET_ROOT_INVALID")
    intent = exact_keys(intent_value, {
        "schema", "packet_root", "decider_kind", "decider_identity_root",
        "judgments", "standing", "authority_effect", "real_a5", "g0",
    })
    require(intent["schema"] == "mosaic.ucm.semantic-judgment-intent.v0.1"
            and intent["packet_root"] == packet["packet_root"],
            "UCM_SEMANTIC_JUDGMENT_INTENT_INVALID")
    require(intent["decider_kind"] in DECIDER_KINDS,
            "UCM_SEMANTIC_JUDGMENT_DECIDER_INVALID")
    require_root(intent["decider_identity_root"])
    require({key: intent[key] for key in BOUNDARY} == BOUNDARY,
            "UCM_SEMANTIC_JUDGMENT_AUTHORITY_INVALID")
    expected = {row["judgment_id"]: row for row in packet["questions"]}
    require(type(intent["judgments"]) is list,
            "UCM_SEMANTIC_JUDGMENTS_INVALID")
    rows = []
    seen = set()
    for raw in intent["judgments"]:
        item = exact_keys(raw, {"judgment_id", "decision", "rationale",
                                "evidence_roots", "human_confirmed"})
        require(item["judgment_id"] in expected
                and item["judgment_id"] not in seen,
                "UCM_SEMANTIC_JUDGMENT_ID_INVALID")
        seen.add(item["judgment_id"])
        require(item["decision"] in DECISIONS,
                "UCM_SEMANTIC_JUDGMENT_DECISION_INVALID")
        require(type(item["rationale"]) is str and item["rationale"],
                "UCM_SEMANTIC_JUDGMENT_RATIONALE_REQUIRED")
        _strings(item["evidence_roots"],
                 "UCM_SEMANTIC_JUDGMENT_EVIDENCE_INVALID")
        for evidence_root in item["evidence_roots"]:
            require_root(evidence_root)
        require(type(item["human_confirmed"]) is bool,
                "UCM_SEMANTIC_JUDGMENT_CONFIRMATION_INVALID")
        body = {
            "judgment_id": item["judgment_id"],
            "candidate_root": expected[item["judgment_id"]]["candidate_root"],
            "decision": item["decision"],
            "decider_kind": intent["decider_kind"],
            "decider_identity_root": intent["decider_identity_root"],
            "rationale": item["rationale"],
            "evidence_roots": item["evidence_roots"],
            "human_confirmed": item["human_confirmed"],
        }
        rows.append({**body, "judgment_root": root(body)})
    require(seen == set(expected), "UCM_SEMANTIC_JUDGMENTS_INCOMPLETE")
    rows.sort(key=lambda row: row["judgment_id"])
    body = {
        "schema": "mosaic.ucm.semantic-judgment-submission.v0.1",
        "packet_root": packet["packet_root"],
        "judgments": rows,
        **BOUNDARY,
    }
    return {**body, "submission_root": root(body)}


def record_judgments(packet_value: Any, decision_value: Any) -> dict[str, Any]:
    packet = packet_value
    require(type(packet) is dict and packet.get("schema")
            == "mosaic.ucm.semantic-judgment-packet.v0.1",
            "UCM_SEMANTIC_JUDGMENT_PACKET_INVALID")
    require(packet.get("packet_root") == _body_root(packet, "packet_root"),
            "UCM_SEMANTIC_JUDGMENT_PACKET_ROOT_INVALID")
    submitted = exact_keys(decision_value, {
        "schema", "packet_root", "judgments", "standing", "authority_effect",
        "real_a5", "g0", "submission_root"})
    require(submitted["schema"] == "mosaic.ucm.semantic-judgment-submission.v0.1"
            and submitted["packet_root"] == packet["packet_root"],
            "UCM_SEMANTIC_JUDGMENT_SUBMISSION_INVALID")
    require({key: submitted[key] for key in BOUNDARY} == BOUNDARY,
            "UCM_SEMANTIC_JUDGMENT_AUTHORITY_INVALID")
    require(submitted["submission_root"]
            == _body_root(submitted, "submission_root"),
            "UCM_SEMANTIC_JUDGMENT_SUBMISSION_ROOT_INVALID")
    expected = {row["judgment_id"]: row for row in packet["questions"]}
    require(type(submitted["judgments"]) is list,
            "UCM_SEMANTIC_JUDGMENTS_INVALID")
    rows = []
    seen = set()
    for judgment in submitted["judgments"]:
        row = exact_keys(judgment, {
            "judgment_id", "candidate_root", "decision", "decider_kind",
            "decider_identity_root", "rationale", "evidence_roots",
            "human_confirmed", "judgment_root"})
        require(row["judgment_id"] in expected and row["judgment_id"] not in seen,
                "UCM_SEMANTIC_JUDGMENT_ID_INVALID")
        seen.add(row["judgment_id"])
        require(row["candidate_root"]
                == expected[row["judgment_id"]]["candidate_root"],
                "UCM_SEMANTIC_JUDGMENT_CANDIDATE_MISMATCH")
        require(row["decision"] in DECISIONS
                and row["decider_kind"] in DECIDER_KINDS,
                "UCM_SEMANTIC_JUDGMENT_DECISION_INVALID")
        require_root(row["decider_identity_root"])
        require(type(row["rationale"]) is str and row["rationale"],
                "UCM_SEMANTIC_JUDGMENT_RATIONALE_REQUIRED")
        _strings(row["evidence_roots"], "UCM_SEMANTIC_JUDGMENT_EVIDENCE_INVALID")
        for evidence_root in row["evidence_roots"]:
            require_root(evidence_root)
        require(type(row["human_confirmed"]) is bool,
                "UCM_SEMANTIC_JUDGMENT_CONFIRMATION_INVALID")
        if row["decision"] == "CONFIRMED_FOR_CORRESPONDENCE":
            require(row["human_confirmed"]
                    and row["decider_kind"] in {"HUMAN", "COMPOSITE"},
                    "UCM_SEMANTIC_HUMAN_CONFIRMATION_REQUIRED")
        require(row["judgment_root"] == _body_root(row, "judgment_root"),
                "UCM_SEMANTIC_JUDGMENT_ROOT_INVALID")
        rows.append(deepcopy(row))
    require(seen == set(expected), "UCM_SEMANTIC_JUDGMENTS_INCOMPLETE")
    rows.sort(key=lambda row: row["judgment_id"])
    body = {
        "schema": "mosaic.ucm.semantic-judgment-register.v0.1",
        "packet_root": packet["packet_root"],
        "judgments": rows,
        "confirmed_count": sum(row["decision"]
                               == "CONFIRMED_FOR_CORRESPONDENCE" for row in rows),
        "status": "RECORDED_NO_EQUIVALENCE_GRANTED",
        "non_claims": ["JUDGMENT_NOT_BEHAVIORAL_PROOF", "NOT_COMPOSITION_AUTHORITY"],
        **BOUNDARY,
    }
    return {**body, "register_root": root(body)}


def compile_correspondence_program(discovery_value: Any,
                                   register_value: Any) -> dict[str, Any]:
    discovery = discovery_value
    register = register_value
    require(type(discovery) is dict and discovery.get("schema")
            == "mosaic.ucm.semantic-candidate-discovery.v0.1",
            "UCM_SEMANTIC_DISCOVERY_INVALID")
    require(discovery.get("discovery_root")
            == _body_root(discovery, "discovery_root"),
            "UCM_SEMANTIC_DISCOVERY_ROOT_INVALID")
    require({key: discovery.get(key) for key in BOUNDARY} == BOUNDARY,
            "UCM_SEMANTIC_DISCOVERY_AUTHORITY_INVALID")
    require(type(register) is dict and register.get("schema")
            == "mosaic.ucm.semantic-judgment-register.v0.1",
            "UCM_SEMANTIC_JUDGMENT_REGISTER_INVALID")
    require(register.get("register_root")
            == _body_root(register, "register_root"),
            "UCM_SEMANTIC_JUDGMENT_REGISTER_INVALID")
    require({key: register.get(key) for key in BOUNDARY} == BOUNDARY,
            "UCM_SEMANTIC_JUDGMENT_AUTHORITY_INVALID")
    candidate_by_root = {row["candidate_root"]: row
                         for row in discovery["candidates"]}
    require(len(candidate_by_root) == len(discovery["candidates"]),
            "UCM_SEMANTIC_CANDIDATE_DUPLICATE")
    judgment_roots = []
    for judgment in register["judgments"]:
        require(judgment.get("candidate_root") in candidate_by_root,
                "UCM_SEMANTIC_JUDGMENT_CANDIDATE_MISMATCH")
        require(judgment.get("decision") in DECISIONS,
                "UCM_SEMANTIC_JUDGMENT_DECISION_INVALID")
        require(judgment.get("judgment_root")
                == _body_root(judgment, "judgment_root"),
                "UCM_SEMANTIC_JUDGMENT_ROOT_INVALID")
        if judgment["decision"] == "CONFIRMED_FOR_CORRESPONDENCE":
            require(judgment.get("human_confirmed") is True
                    and judgment.get("decider_kind") in {"HUMAN", "COMPOSITE"},
                    "UCM_SEMANTIC_HUMAN_CONFIRMATION_REQUIRED")
        judgment_roots.append(judgment["candidate_root"])
    require(len(judgment_roots) == len(set(judgment_roots))
            and set(judgment_roots) == set(candidate_by_root),
            "UCM_SEMANTIC_JUDGMENT_REGISTER_INCOMPLETE")
    programs = []
    for judgment in register["judgments"]:
        candidate = candidate_by_root[judgment["candidate_root"]]
        obligations = []
        for pair in candidate["comparison_pairs"]:
            for obligation_kind in COMPARISON_OBLIGATIONS:
                body = {
                    "candidate_root": candidate["candidate_root"],
                    "pair_root": pair["pair_root"],
                    "obligation_kind": obligation_kind,
                    "required": True,
                    "evidence_status": "NOT_SUPPLIED",
                }
                obligations.append({**body, "obligation_root": root(body)})
        status = {
            "CONFIRMED_FOR_CORRESPONDENCE": "READY_FOR_CORRESPONDENCE_EVIDENCE",
            "PROVISIONAL_CANDIDATE": "AWAITING_HUMAN_CONFIRMATION",
            "NEEDS_EVIDENCE": "DISCOVERY_EVIDENCE_INSUFFICIENT",
            "DISTINCT_SEMANTICS": "NO_CONSOLIDATION_PROGRAM",
        }[judgment["decision"]]
        body = {
            "candidate_id": candidate["candidate_id"],
            "candidate_root": candidate["candidate_root"],
            "judgment_root": judgment["judgment_root"],
            "decision": judgment["decision"],
            "comparison_pairs": deepcopy(candidate["comparison_pairs"]),
            "cm1_obligations": obligations,
            "cm2_options": deepcopy(candidate["allowed_consolidation_forms"]),
            "status": status,
            "execution_authorized": False,
            "composition_authorized": False,
        }
        programs.append({**body, "program_root": root(body)})
    programs.sort(key=lambda row: row["candidate_id"])
    body = {
        "schema": "mosaic.ucm.semantic-consolidation-program.v0.1",
        "discovery_root": discovery["discovery_root"],
        "judgment_register_root": register["register_root"],
        "programs": programs,
        "ready_program_count": sum(row["status"]
                                   == "READY_FOR_CORRESPONDENCE_EVIDENCE"
                                   for row in programs),
        "status": "COMPILED_WITHOUT_EXECUTION",
        "non_claims": ["NOT_EQUIVALENCE", "NOT_REFACTOR_AUTHORITY",
                       "NOT_SHARED_SERVICE_ADMISSION", "NOT_EXECUTION"],
        **BOUNDARY,
    }
    return {**body, "consolidation_root": root(body)}
