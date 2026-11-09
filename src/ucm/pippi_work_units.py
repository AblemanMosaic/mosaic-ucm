"""P/PPI work-unit preflight, no-replay continuation, and bundle records."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import root

from .pippi_global import BOUNDARY, HubRefusal


EFFECT_CLASSES={"NONE","PURE_COMPUTATION","READ_ONLY","LOCAL_ARTIFACT_PREPARATION",
                "WRITE_WORKSPACE","DELETE_WORKSPACE","NETWORK","INSTALL",
                "PERSISTENT_HOST_STATE","AUTHORITY_CHANGE"}
LIFECYCLE=("DORMANT_CANDIDATE","ISOLATED_INSTALL","CONNECTED","UPDATED","ROLLBACK_PROVED",
           "UNINSTALLED","LIVE_ADMISSION_PENDING")
WORK_CLASSES={"DIRECT_ACCEPTANCE_CLOSURE","SHARED_INFRASTRUCTURE"}
CASE_STATUSES={"UNMET","BLOCKED"}


def _strings(value: Any, code: str) -> list[str]:
    if not isinstance(value,list) or value != sorted(set(value)) or not all(isinstance(x,str) and x for x in value):
        raise HubRefusal(code)
    return deepcopy(value)


def _root(value: Any, code: str) -> str:
    if not isinstance(value,str) or len(value)!=64 or any(ch not in "0123456789abcdef" for ch in value):
        raise HubRefusal(code)
    return value


def build_acceptance_case(*, acceptance_case_id: str, subject_root: str,
                          requirement_root: str, verification_surface: str,
                          expected_result_code: str, current_status: str) -> dict[str,Any]:
    """Name the exact externally meaningful case that implementation must close."""
    if not isinstance(acceptance_case_id,str) or not acceptance_case_id:
        raise HubRefusal("PIPPI_ACCEPTANCE_CASE_ID_INVALID")
    if not isinstance(verification_surface,str) or not verification_surface:
        raise HubRefusal("PIPPI_ACCEPTANCE_SURFACE_INVALID")
    if not isinstance(expected_result_code,str) or not expected_result_code:
        raise HubRefusal("PIPPI_ACCEPTANCE_RESULT_CODE_INVALID")
    if current_status not in CASE_STATUSES:
        raise HubRefusal("PIPPI_ACCEPTANCE_CASE_STATUS_INVALID")
    body={"schema":"mosaic.ucm.pippi-acceptance-case.v0.1",
          "acceptance_case_id":acceptance_case_id,
          "subject_root":_root(subject_root,"PIPPI_ACCEPTANCE_SUBJECT_ROOT_INVALID"),
          "requirement_root":_root(requirement_root,"PIPPI_ACCEPTANCE_REQUIREMENT_ROOT_INVALID"),
          "verification_surface":verification_surface,
          "expected_result_code":expected_result_code,
          "current_status":current_status,**BOUNDARY}
    return {**body,"acceptance_case_root":root(body)}


def build_infrastructure_block(*, acceptance_case: dict[str,Any], blocker_code: str,
                               blocker_evidence_roots: list[str],
                               required_capability: str,
                               unblock_criterion: str) -> dict[str,Any]:
    """Prove that a named case is blocked before shared infrastructure may be selected."""
    case=validate_acceptance_case(acceptance_case)
    if case["current_status"]!="BLOCKED":
        raise HubRefusal("PIPPI_INFRASTRUCTURE_CASE_NOT_BLOCKED")
    if not isinstance(blocker_code,str) or not blocker_code:
        raise HubRefusal("PIPPI_INFRASTRUCTURE_BLOCKER_CODE_INVALID")
    if not isinstance(required_capability,str) or not required_capability:
        raise HubRefusal("PIPPI_INFRASTRUCTURE_CAPABILITY_INVALID")
    if not isinstance(unblock_criterion,str) or not unblock_criterion:
        raise HubRefusal("PIPPI_INFRASTRUCTURE_UNBLOCK_CRITERION_INVALID")
    evidence=_strings(blocker_evidence_roots,"PIPPI_INFRASTRUCTURE_EVIDENCE_INVALID")
    if not evidence:
        raise HubRefusal("PIPPI_INFRASTRUCTURE_EVIDENCE_REQUIRED")
    for value in evidence:
        _root(value,"PIPPI_INFRASTRUCTURE_EVIDENCE_INVALID")
    body={"schema":"mosaic.ucm.pippi-infrastructure-block.v0.1",
          "acceptance_case_root":case["acceptance_case_root"],
          "blocker_code":blocker_code,"blocker_evidence_roots":evidence,
          "required_capability":required_capability,
          "unblock_criterion":unblock_criterion,**BOUNDARY}
    return {**body,"infrastructure_block_root":root(body)}


def validate_acceptance_case(value: Any) -> dict[str,Any]:
    if not isinstance(value,dict): raise HubRefusal("PIPPI_ACCEPTANCE_CASE_INVALID")
    expected=build_acceptance_case(
        acceptance_case_id=value.get("acceptance_case_id"),subject_root=value.get("subject_root"),
        requirement_root=value.get("requirement_root"),
        verification_surface=value.get("verification_surface"),
        expected_result_code=value.get("expected_result_code"),current_status=value.get("current_status"))
    if value!=expected: raise HubRefusal("PIPPI_ACCEPTANCE_CASE_INVALID")
    return deepcopy(value)


def validate_infrastructure_block(value: Any, *, acceptance_case_root: str) -> dict[str,Any]:
    if not isinstance(value,dict): raise HubRefusal("PIPPI_INFRASTRUCTURE_BLOCK_REQUIRED")
    required={"schema","acceptance_case_root","blocker_code","blocker_evidence_roots",
              "required_capability","unblock_criterion","standing","authority_effect",
              "real_a5","g0","infrastructure_block_root"}
    if set(value)!=required or value.get("schema")!="mosaic.ucm.pippi-infrastructure-block.v0.1":
        raise HubRefusal("PIPPI_INFRASTRUCTURE_BLOCK_INVALID")
    if value["acceptance_case_root"]!=acceptance_case_root:
        raise HubRefusal("PIPPI_INFRASTRUCTURE_CASE_MISMATCH")
    body={key:value[key] for key in value if key!="infrastructure_block_root"}
    if root(body)!=value["infrastructure_block_root"] or any(body.get(k)!=v for k,v in BOUNDARY.items()):
        raise HubRefusal("PIPPI_INFRASTRUCTURE_BLOCK_INVALID")
    _strings(value["blocker_evidence_roots"],"PIPPI_INFRASTRUCTURE_EVIDENCE_INVALID")
    for item in value["blocker_evidence_roots"]:
        _root(item,"PIPPI_INFRASTRUCTURE_EVIDENCE_INVALID")
    for field in ("blocker_code","required_capability","unblock_criterion"):
        if not isinstance(value[field],str) or not value[field]:
            raise HubRefusal("PIPPI_INFRASTRUCTURE_BLOCK_INVALID")
    return deepcopy(value)


def build_work_selection(*, acceptance_case: dict[str,Any], work_class: str,
                         direct_closure_check_id: str,
                         infrastructure_block: dict[str,Any] | None) -> dict[str,Any]:
    """Authorize bounded implementation selection without authorizing effects."""
    case=validate_acceptance_case(acceptance_case)
    if work_class not in WORK_CLASSES: raise HubRefusal("PIPPI_WORK_CLASS_INVALID")
    if not isinstance(direct_closure_check_id,str) or not direct_closure_check_id:
        raise HubRefusal("PIPPI_DIRECT_CLOSURE_CHECK_REQUIRED")
    block=None
    if work_class=="DIRECT_ACCEPTANCE_CLOSURE":
        if infrastructure_block is not None:
            raise HubRefusal("PIPPI_DIRECT_WORK_INFRASTRUCTURE_BLOCK_FORBIDDEN")
        selection_basis="DIRECT_CASE_CLOSURE"
    else:
        block=validate_infrastructure_block(
            infrastructure_block,acceptance_case_root=case["acceptance_case_root"])
        selection_basis="DEMONSTRATED_ACCEPTANCE_BLOCKER"
    body={"schema":"mosaic.ucm.pippi-work-selection.v0.1",
          "acceptance_case_root":case["acceptance_case_root"],"work_class":work_class,
          "direct_closure_check_id":direct_closure_check_id,
          "infrastructure_block_root":None if block is None else block["infrastructure_block_root"],
          "selection_basis":selection_basis,"implementation_effect_authorized":False,**BOUNDARY}
    return {**body,"work_selection_root":root(body)}


def build_work_unit_state(*, work_unit_id: str, lifecycle_phase: str,
                          acceptance_case: dict[str,Any], work_class: str,
                          direct_closure_check_id: str,
                          infrastructure_block: dict[str,Any] | None,
                          execution_holds: list[str], release_blockers: list[str],
                          qualification_gaps: list[str], user_acceptance_pending: bool,
                          allowed_effect_classes: list[str], forbidden_targets: list[str],
                          retry_limit: int, repair_attempts: int,
                          implemented_work_packages: int, total_work_packages: int,
                          proof_level: str, operational_maturity: str,
                          required_next_gate: str) -> dict[str,Any]:
    if lifecycle_phase not in LIFECYCLE: raise HubRefusal("PIPPI_LIFECYCLE_PHASE_INVALID")
    case=validate_acceptance_case(acceptance_case)
    selection=build_work_selection(acceptance_case=case,work_class=work_class,
        direct_closure_check_id=direct_closure_check_id,infrastructure_block=infrastructure_block)
    execution_holds=_strings(execution_holds,"PIPPI_EXECUTION_HOLDS_INVALID")
    release_blockers=_strings(release_blockers,"PIPPI_RELEASE_BLOCKERS_INVALID")
    qualification_gaps=_strings(qualification_gaps,"PIPPI_QUALIFICATION_GAPS_INVALID")
    effects=_strings(allowed_effect_classes,"PIPPI_EFFECT_CLASSES_INVALID")
    if not set(effects)<=EFFECT_CLASSES: raise HubRefusal("PIPPI_EFFECT_CLASSES_INVALID")
    forbidden_targets=_strings(forbidden_targets,"PIPPI_FORBIDDEN_TARGETS_INVALID")
    if not isinstance(retry_limit,int) or retry_limit<0 or repair_attempts<0 or repair_attempts>retry_limit:
        raise HubRefusal("PIPPI_RETRY_BUDGET_INVALID")
    if not (isinstance(total_work_packages,int) and total_work_packages>0 and
            isinstance(implemented_work_packages,int) and 0<=implemented_work_packages<=total_work_packages):
        raise HubRefusal("PIPPI_PROGRESS_INVALID")
    state="HELD" if execution_holds else "ACTIVE"
    body={"schema":"mosaic.ucm.pippi-work-unit-state.v0.2","work_unit_id":work_unit_id,
          "acceptance_case_root":case["acceptance_case_root"],"work_class":work_class,
          "direct_closure_check_id":direct_closure_check_id,
          "infrastructure_block_root":selection["infrastructure_block_root"],
          "selection_basis":selection["selection_basis"],
          "work_selection_root":selection["work_selection_root"],
          "lifecycle_phase":lifecycle_phase,"process_state":state,"execution_holds":execution_holds,
          "release_blockers":release_blockers,"qualification_gaps":qualification_gaps,
          "user_acceptance_pending":bool(user_acceptance_pending),"allowed_effect_classes":effects,
          "forbidden_targets":forbidden_targets,"retry_limit":retry_limit,"repair_attempts":repair_attempts,
          "progress":{"implemented_work_packages":implemented_work_packages,
                      "total_work_packages":total_work_packages},
          "proof_level":proof_level,"operational_maturity":operational_maturity,
          "required_next_gate":required_next_gate,**BOUNDARY}
    return {**body,"work_unit_state_root":root(body)}


def assess_work_unit_outcome(*, work_unit_state: dict[str,Any],
                             acceptance_case: dict[str,Any],
                             observed_result_code: str,
                             evidence_roots: list[str],
                             infrastructure_block: dict[str,Any] | None = None) -> dict[str,Any]:
    """Separate direct acceptance closure from prerequisite completion."""
    case=validate_acceptance_case(acceptance_case)
    if work_unit_state.get("acceptance_case_root")!=case["acceptance_case_root"]:
        raise HubRefusal("PIPPI_WORK_OUTCOME_CASE_MISMATCH")
    if not isinstance(observed_result_code,str) or not observed_result_code:
        raise HubRefusal("PIPPI_WORK_OUTCOME_RESULT_INVALID")
    evidence=_strings(evidence_roots,"PIPPI_WORK_OUTCOME_EVIDENCE_INVALID")
    if not evidence: raise HubRefusal("PIPPI_WORK_OUTCOME_EVIDENCE_REQUIRED")
    for value in evidence: _root(value,"PIPPI_WORK_OUTCOME_EVIDENCE_INVALID")
    if work_unit_state.get("work_class")=="DIRECT_ACCEPTANCE_CLOSURE":
        if infrastructure_block is not None:
            raise HubRefusal("PIPPI_WORK_OUTCOME_INFRASTRUCTURE_BLOCK_FORBIDDEN")
        matched=observed_result_code==case["expected_result_code"]
        expected_result_code=case["expected_result_code"]
        infrastructure_block_root=None
        outcome="ACCEPTANCE_CASE_CLOSED" if matched else "ACCEPTANCE_CASE_UNMET"
    elif work_unit_state.get("work_class")=="SHARED_INFRASTRUCTURE":
        block=validate_infrastructure_block(
            infrastructure_block,acceptance_case_root=case["acceptance_case_root"])
        if work_unit_state.get("infrastructure_block_root")!=block["infrastructure_block_root"]:
            raise HubRefusal("PIPPI_WORK_OUTCOME_INFRASTRUCTURE_BLOCK_MISMATCH")
        expected_result_code=block["unblock_criterion"]
        infrastructure_block_root=block["infrastructure_block_root"]
        matched=observed_result_code==expected_result_code
        outcome="PREREQUISITE_SATISFIED_FOLLOW_ON_DIRECT_STEP_REQUIRED" if matched else "PREREQUISITE_UNMET"
    else:
        raise HubRefusal("PIPPI_WORK_CLASS_INVALID")
    body={"schema":"mosaic.ucm.pippi-work-unit-outcome.v0.1",
          "work_unit_state_root":work_unit_state["work_unit_state_root"],
          "acceptance_case_root":case["acceptance_case_root"],
          "work_class":work_unit_state["work_class"],
          "expected_result_code":expected_result_code,
          "infrastructure_block_root":infrastructure_block_root,
          "observed_result_code":observed_result_code,
          "evidence_roots":evidence,"outcome":outcome,
          "acceptance_case_closed":outcome=="ACCEPTANCE_CASE_CLOSED",**BOUNDARY}
    return {**body,"work_unit_outcome_root":root(body)}


def build_no_replay_capsule(*, work_unit_state: dict[str,Any], completed_effects: list[dict[str,Any]],
                            remaining_operations: list[str], expected_journal_head: str,
                            expected_process_head: str) -> dict[str,Any]:
    for value in (expected_journal_head,expected_process_head):
        if not isinstance(value,str) or len(value)!=64: raise HubRefusal("PIPPI_EXPECTED_HEAD_INVALID")
    receipts=[]
    for row in completed_effects:
        if set(row)!={"effect_id","effect_class","receipt_root"} or row["effect_class"] not in EFFECT_CLASSES or len(row["receipt_root"])!=64:
            raise HubRefusal("PIPPI_COMPLETED_EFFECT_INVALID")
        receipts.append(deepcopy(row))
    if receipts != sorted(receipts,key=lambda x:x["effect_id"]): raise HubRefusal("PIPPI_COMPLETED_EFFECT_ORDER_INVALID")
    if (not isinstance(remaining_operations,list) or
            len(remaining_operations)!=len(set(remaining_operations)) or
            not all(isinstance(value,str) and value for value in remaining_operations)):
        raise HubRefusal("PIPPI_REMAINING_OPERATIONS_INVALID")
    remaining=deepcopy(remaining_operations)
    body={"schema":"mosaic.ucm.pippi-no-replay-capsule.v0.1",
          "work_unit_state_root":work_unit_state["work_unit_state_root"],
          "completed_effects":receipts,"remaining_operations":remaining,
          "expected_journal_head":expected_journal_head,"expected_process_head":expected_process_head,
          "retry_budget_remaining":work_unit_state["retry_limit"]-work_unit_state["repair_attempts"],**BOUNDARY}
    resume_token=root(body)
    return {**body,"resume_token":resume_token,"capsule_root":root({**body,"resume_token":resume_token})}


def preflight_record_bundle(*, expected_head: str, records: list[dict[str,Any]],
                            planned_effect_classes: list[str]) -> dict[str,Any]:
    if not isinstance(expected_head,str) or len(expected_head)!=64: raise HubRefusal("PIPPI_BUNDLE_HEAD_INVALID")
    effects=_strings(planned_effect_classes,"PIPPI_EFFECT_CLASSES_INVALID")
    if not set(effects)<=EFFECT_CLASSES: raise HubRefusal("PIPPI_EFFECT_CLASSES_INVALID")
    if not isinstance(records,list) or not records: raise HubRefusal("PIPPI_BUNDLE_RECORDS_INVALID")
    record_roots=[];schemas=[]
    for index,record in enumerate(records):
        if not isinstance(record,dict) or not isinstance(record.get("schema"),str):
            raise HubRefusal("PIPPI_BUNDLE_RECORD_INVALID",f"/{index}/schema")
        root_fields=[key for key in record if key.endswith("_root") and key not in {"authority_effect"}]
        candidates=[record[key] for key in root_fields if isinstance(record[key],str) and len(record[key])==64]
        if not candidates: raise HubRefusal("PIPPI_BUNDLE_RECORD_ROOT_MISSING",f"/{index}")
        schemas.append(record["schema"]);record_roots.append(sorted(candidates)[-1])
    body={"schema":"mosaic.ucm.pippi-record-bundle-preflight.v0.1","expected_head":expected_head,
          "record_schemas":schemas,"record_roots":record_roots,"planned_effect_classes":effects,
          "diagnostic":{"record_count":len(records),"canonical_order":"PASS","uniqueness":"PASS",
                        "effect_ceiling":"PASS"},"status":"PASS",**BOUNDARY}
    return {**body,"preflight_root":root(body)}


def build_prepared_bundle(*, preflight: dict[str,Any], no_replay_capsule: dict[str,Any] | None) -> dict[str,Any]:
    if preflight.get("status")!="PASS": raise HubRefusal("PIPPI_BUNDLE_PREFLIGHT_REQUIRED")
    body={"schema":"mosaic.ucm.pippi-prepared-record-bundle.v0.1",
          "preflight_root":preflight["preflight_root"],
          "no_replay_capsule_root":None if no_replay_capsule is None else no_replay_capsule["capsule_root"],
          "bundle_state":"PREPARED","idempotent_finish_required":True,**BOUNDARY}
    return {**body,"prepared_bundle_root":root(body)}

