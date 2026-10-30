"""Pure application-session request and exact-byte evidence return contracts.

The service validates transport and declared correspondence. Native certificates
can additionally establish a bounded model result; no return completes an
application, authenticates a runtime observation or supplies independent review.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import re
from typing import Any

from . import autonomous_project_manager as apm
from . import project_intelligence as pi
from .canonical import Refusal, exact_keys, require, require_root, root, strict_loads
from .deductive_proofs import compile_contract, evidence_subject, verify_proof
from .maturity_semantics import (
    BOUNDARY, bytes_ref, ceiling, checked, result_state, seal,
    verify_digest_ref, verify_obligation_binding, verify_result_state,
)
from .workbench_contracts import reject_raw_secrets, typed_root
from .workbench_workers import _snapshot


REQUEST_SCHEMA = "ucl.ucm.maturity.application_integration_request.v1"
CASE_SCHEMA = "ucl.ucm.maturity.application_case_evidence.v1"
RETURN_SCHEMA = "ucl.ucm.maturity.application_integration_return.v1"
CHECK_SCHEMA = "ucl.ucm.maturity.application_integration_check.v1"
EVIDENCE_CLASSES = {"SIMULATION", "BOUNDED_PROOF", "RUNTIME_OBSERVATION", "INDEPENDENT_REVIEW"}
PURE_CAPABILITIES = ["EXACT_BYTE_MANIFEST_V1", "NATIVE_DEDUCTIVE_PROOF_V1", "PI_APM_CORRESPONDENCE_V1"]
PIN_MEMBERS = {"application": "application.json", "source": "source.bin", "interface": "interface.json"}
PIN_KINDS = {"application": "ARTIFACT", "source": "SOURCE", "interface": "CONTRACT"}
MAX_CASES, MAX_MEMBERS, MAX_MEMBER_BYTES, MAX_TOTAL_BYTES = 64, 256, 4 * 1024 * 1024, 16 * 1024 * 1024
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,127}\Z")
_REQUEST_KEYS = {"schema", "pins", "pin_members", "project", "work_plan", "cases", "input_manifest",
    "required_capabilities", "available_capabilities", "missing_capabilities", "real_adapter_bindings",
    "authority_ceiling", "standing", "authority_effect", "real_a5", "g0"}
_CASE_KEYS = {"case_id", "evidence_class", "project_record_id", "task_id", "obligation",
              "input_member", "return_member", "required_capabilities"}
_EVIDENCE_KEYS = {"schema", "request_root", "case_id", "evidence_class", "pins", "obligation",
    "payload", "reported_status", "receipt", "findings", "missing_capabilities",
    "application_claim_complete", "obligations_completed", "standing", "authority_effect", "real_a5", "g0"}
_RETURN_KEYS = {"schema", "request_root", "pins", "case_ids", "manifest", "case_receipts", "findings",
    "missing_capabilities", "real_adapter_bindings", "application_claim_complete", "obligations_completed",
    "standing", "authority_effect", "real_a5", "g0"}
_ROUTE_FIELDS = {"command", "shell", "script", "executable", "entrypoint", "argv", "route", "callback"}


def _typed_errors(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (KeyError, TypeError, IndexError, AttributeError, ValueError, RecursionError) as error:
            if isinstance(error, Refusal):
                raise
            raise Refusal("APPLICATION_KIT_MALFORMED_INPUT", detail=type(error).__name__) from error
    return call


def _token(value: Any) -> str:
    require(type(value) is str and bool(_TOKEN.fullmatch(value)), "APPLICATION_KIT_IDENTIFIER_INVALID")
    return value


def _tokens(value: Any) -> list[str]:
    require(type(value) is list and len(value) <= 256, "APPLICATION_KIT_TOKEN_SET_INVALID")
    for item in value:
        _token(item)
    require(value == sorted(set(value)), "APPLICATION_KIT_TOKEN_ORDER_INVALID")
    return list(value)


def _public(value: Any) -> None:
    reject_raw_secrets(value)
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is dict:
            for name, child in item.items():
                normalized = re.sub(r"[^a-z0-9]", "", name.lower())
                require(normalized not in _ROUTE_FIELDS, "APPLICATION_KIT_EXECUTABLE_ROUTE_FORBIDDEN")
                pending.append(child)
        elif type(item) is list:
            pending.extend(item)


def _boundary(item: dict) -> None:
    require(all(type(item.get(key)) is type(value) and item[key] == value
                for key, value in BOUNDARY.items()), "APPLICATION_KIT_BOUNDARY_CHANGED")


def _pins(value: Any) -> dict:
    item = exact_keys(value, set(PIN_KINDS) | {"project_snapshot_root", "work_plan_root"})
    for name, kind in PIN_KINDS.items():
        ref = verify_digest_ref(item[name], kind=kind)
        dialects = {"bytes-sha256-v1", "uclop-json-v1"} if name == "source" else {"bytes-sha256-v1"}
        require(ref["algorithm"] == "sha256" and ref["dialect"] in dialects,
                "APPLICATION_KIT_EXACT_BYTE_PIN_REQUIRED")
    require_root(item["project_snapshot_root"]); require_root(item["work_plan_root"])
    return deepcopy(item)


def _manifest(members: Any, *, kind: str) -> list[dict]:
    require(type(members) is dict and len(members) <= MAX_MEMBERS, "APPLICATION_KIT_MEMBER_SET_INVALID")
    rows, total = [], 0
    for name in sorted(members):
        pi.portable_path(name)
        data = members[name]
        require(type(data) is bytes and len(data) <= MAX_MEMBER_BYTES, "APPLICATION_KIT_EXACT_MEMBER_BYTES_REQUIRED")
        total += len(data)
        require(total <= MAX_TOTAL_BYTES, "APPLICATION_KIT_ENVELOPE_LIMIT")
        rows.append({"path": name, "length": len(data), "bytes": bytes_ref(data, kind)})
    # The PI path validator supplies the existing portable path grammar; also
    # reject aliases and file/directory collisions before constructing an envelope.
    paths = sorted(members)
    folded = [name.casefold() for name in paths]
    require(len(folded) == len(set(folded)), "APPLICATION_KIT_PATH_ALIAS")
    require(not any(other.startswith(name + "/") for name in folded for other in folded if other != name),
            "APPLICATION_KIT_PATH_COLLISION")
    return rows


def _native_contract(case: dict, members: dict[str, bytes], source_digest: str) -> dict:
    require(case["input_member"] in members, "APPLICATION_KIT_CASE_INPUT_MISSING")
    model = strict_loads(members[case["input_member"]])
    compile_contract(model)
    identity = case["obligation"]["identity"]
    require(model["subject_root"] == source_digest
            and model["obligation_id"] == identity["obligation_id"], "APPLICATION_KIT_NATIVE_SUBJECT_MISMATCH")
    require(identity["evidence_subject"] == typed_root("EVIDENCE", root(evidence_subject(model)))
            and identity["formula"] == typed_root("SEMANTIC", model["contract_root"]),
            "APPLICATION_KIT_NATIVE_OBLIGATION_MISMATCH")
    return model


def _request_shape(request: Any) -> dict:
    item = checked(request, _REQUEST_KEYS, REQUEST_SCHEMA)
    _boundary(item); _public(item)
    return item


@_typed_errors
def make_integration_request(*, application: dict, source: dict, interface: dict,
        project: dict, work_plan: dict, cases: list[dict], input_members: dict[str, bytes],
        pin_members: dict | None = None, required_capabilities: list[str] | None = None,
        available_capabilities: list[str] | None = None) -> dict:
    """Construct a no-adapter request; callers independently retain its pins."""
    nodes = pi.validate_project(project)
    tasks = apm.validate_plan(work_plan, project)
    pins = _pins({"application": application, "source": source, "interface": interface,
                  "project_snapshot_root": project["snapshot_root"], "work_plan_root": work_plan["plan_root"]})
    require(project["baseline"]["source_root"] == source["digest"], "APPLICATION_KIT_PROJECT_SOURCE_MISMATCH")
    manifest = _manifest(input_members, kind="ARTIFACT")
    selected = exact_keys(PIN_MEMBERS if pin_members is None else pin_members, set(PIN_KINDS))
    require(len(set(selected.values())) == 3, "APPLICATION_KIT_PIN_MEMBER_ALIAS")
    for name, kind in PIN_KINDS.items():
        path = pi.portable_path(selected[name])
        require(path in input_members, "APPLICATION_KIT_INPUT_PIN_MISMATCH")
        if name == "source" and pins[name]["dialect"] == "uclop-json-v1":
            require(not path.startswith("source/"), "APPLICATION_KIT_SOURCE_NAMESPACE_RESERVED")
            snapshot = _snapshot(strict_loads(input_members[path]))
            require(snapshot["source_root"] == pins[name]["digest"], "APPLICATION_KIT_SOURCE_SNAPSHOT_PIN_MISMATCH")
            source_members = {"source/" + row["path"] for row in snapshot["files"]}
            require({member for member in input_members if member.startswith("source/")} == source_members,
                    "APPLICATION_KIT_SOURCE_MEMBER_SET_MISMATCH")
            for row in snapshot["files"]:
                data = input_members["source/" + row["path"]]
                require(len(data) == row["bytes"] and bytes_ref(data)["digest"] == row["sha256"],
                        "APPLICATION_KIT_SOURCE_MEMBER_BYTES_MISMATCH")
        else:
            require(bytes_ref(input_members[path], kind) == pins[name], "APPLICATION_KIT_INPUT_PIN_MISMATCH")
    available = _tokens(PURE_CAPABILITIES if available_capabilities is None else available_capabilities)
    require(set(available) <= set(PURE_CAPABILITIES), "APPLICATION_KIT_REAL_ADAPTER_UNBOUND")
    required = _tokens([] if required_capabilities is None else required_capabilities)
    require(type(cases) is list and 0 < len(cases) <= MAX_CASES, "APPLICATION_KIT_CASE_SET_INVALID")
    rows, seen_ids, returns, bindings, covered = [], set(), set(), {}, set()
    for supplied in cases:
        case = exact_keys(supplied, _CASE_KEYS)
        identifier = _token(case["case_id"])
        require(identifier not in seen_ids and case["evidence_class"] in EVIDENCE_CLASSES,
                "APPLICATION_KIT_CASE_INVALID")
        require(type(case["project_record_id"]) is str and case["project_record_id"] in nodes
                and nodes[case["project_record_id"]]["kind"] == "VERIFICATION_OBLIGATION",
                "APPLICATION_KIT_PROJECT_OBLIGATION_MISMATCH")
        require(type(case["task_id"]) is str and case["task_id"] in tasks
                and tasks[case["task_id"]]["source_record_ids"] == [case["project_record_id"]],
                "APPLICATION_KIT_WORK_PLAN_CORRESPONDENCE_MISMATCH")
        require(type(case["obligation"]) is dict and type(case["obligation"].get("identity")) is dict,
                "APPLICATION_KIT_OBLIGATION_REQUIRED")
        binding = verify_obligation_binding(case["obligation"], expected_identity=case["obligation"]["identity"])
        previous = bindings.setdefault(case["project_record_id"], binding["identity_root"])
        require(previous == binding["identity_root"], "APPLICATION_KIT_ORIGINAL_OBLIGATION_CHANGED")
        output = pi.portable_path(case["return_member"])
        require(output not in returns, "APPLICATION_KIT_RETURN_MEMBER_DUPLICATE")
        require(case["input_member"] is None or type(case["input_member"]) is str
                and case["input_member"] in input_members, "APPLICATION_KIT_CASE_INPUT_MISSING")
        _tokens(case["required_capabilities"])
        if case["evidence_class"] == "BOUNDED_PROOF":
            require(case["input_member"] is not None, "APPLICATION_KIT_NATIVE_CONTRACT_REQUIRED")
            _native_contract(case, input_members, source["digest"])
        rows.append(deepcopy(case)); seen_ids.add(identifier); returns.add(output); covered.add(case["task_id"])
    required_tasks = {identifier for identifier, task in tasks.items()
                      if nodes[task["source_record_ids"][0]]["kind"] == "VERIFICATION_OBLIGATION"}
    require(covered == required_tasks, "APPLICATION_KIT_VERIFICATION_TASK_COVERAGE_MISMATCH")
    all_required = set(required) | {cap for case in rows for cap in case["required_capabilities"]}
    result = seal({"schema": REQUEST_SCHEMA, "pins": pins, "pin_members": dict(selected),
        "project": deepcopy(project), "work_plan": deepcopy(work_plan),
        "cases": sorted(rows, key=lambda case: case["case_id"]), "input_manifest": manifest,
        "required_capabilities": required, "available_capabilities": available,
        "missing_capabilities": sorted(all_required - set(available)), "real_adapter_bindings": [],
        "authority_ceiling": ceiling(stage_limit="PURE_COMPUTATION"), **BOUNDARY})
    _public(result)
    return result


@_typed_errors
def verify_integration_request(request: Any, *, input_members: dict[str, bytes],
        expected_request_root: str, expected_pins: dict, expected_case_ids: list[str]) -> dict:
    item = _request_shape(request)
    require(item["root"] == require_root(expected_request_root), "APPLICATION_KIT_REQUEST_PIN_MISMATCH")
    require(item["pins"] == _pins(expected_pins), "APPLICATION_KIT_EXTERNAL_PINS_MISMATCH")
    require([case["case_id"] for case in item["cases"]] == _tokens(expected_case_ids),
            "APPLICATION_KIT_EXPECTED_CASES_MISMATCH")
    expected = make_integration_request(**{name: item["pins"][name] for name in PIN_KINDS},
        project=item["project"], work_plan=item["work_plan"], cases=item["cases"],
        input_members=input_members, pin_members=item["pin_members"],
        required_capabilities=item["required_capabilities"], available_capabilities=item["available_capabilities"])
    require(item == expected, "APPLICATION_KIT_REQUEST_RECOMPUTATION_MISMATCH")
    return expected


def _findings(value: Any) -> list[dict]:
    require(type(value) is list and len(value) <= 64, "APPLICATION_KIT_FINDINGS_INVALID")
    for row in value:
        exact_keys(row, {"code", "severity", "detail"})
        _token(row["code"])
        require(row["severity"] in {"INFO", "WARNING", "ERROR"}
                and type(row["detail"]) is str and 0 < len(row["detail"]) <= 2000,
                "APPLICATION_KIT_FINDING_INVALID")
    _public(value)
    return deepcopy(value)


def _payload(evidence_class: str, value: Any) -> dict:
    if evidence_class == "BOUNDED_PROOF":
        item = exact_keys(value, {"proof_bundle"})
        require(type(item["proof_bundle"]) is dict, "APPLICATION_KIT_NATIVE_BUNDLE_INVALID")
    elif evidence_class == "SIMULATION":
        item = exact_keys(value, {"simulated", "actual_work_performed"})
        require(item["simulated"] is True and item["actual_work_performed"] is False,
                "APPLICATION_KIT_SIMULATION_BOUNDARY_INVALID")
    elif evidence_class == "RUNTIME_OBSERVATION":
        item = exact_keys(value, {"runtime", "observation", "reported_source", "reported_interface"})
        for field, kind in (("runtime", "IMPLEMENTATION"), ("observation", "EVIDENCE"),
                            ("reported_source", "SOURCE"), ("reported_interface", "CONTRACT")):
            verify_digest_ref(item[field], kind=kind)
    else:
        item = exact_keys(value, {"reviewer", "reviewed_evidence", "assessment"})
        verify_digest_ref(item["reviewer"], kind="PUBLIC_KEY")
        verify_digest_ref(item["reviewed_evidence"], kind="EVIDENCE")
        require(item["assessment"] in {"UNREVIEWED", "INCOMPLETE_REVIEW", "HOLD_FOR_REPAIR",
                "QUALIFIED_RECOMMENDATION_ONLY", "NOT_QUALIFIED"}, "APPLICATION_KIT_REVIEW_INVALID")
    _public(item)
    return deepcopy(item)


@_typed_errors
def make_case_evidence(request: Any, *, case_id: str, payload: dict,
        reported_status: str = "INFORMATION_ONLY", findings: list[dict] | None = None,
        missing_capabilities: list[str] | None = None) -> dict:
    """Prepare a public data record; its receipt deliberately stays pending."""
    item = _request_shape(request)
    cases = {case["case_id"]: case for case in item["cases"]}
    require(type(case_id) is str and case_id in cases, "APPLICATION_KIT_CASE_UNKNOWN")
    case = cases[case_id]
    require(type(reported_status) is str and reported_status in {"PASS", "FAIL", "INFORMATION_ONLY", "REFUSED", "INTERRUPTED"},
            "APPLICATION_KIT_REPORTED_STATUS_INVALID")
    inputs = [row["bytes"] for row in item["input_manifest"] if row["path"] == case["input_member"]]
    return seal({"schema": CASE_SCHEMA, "request_root": item["root"], "case_id": case_id,
        "evidence_class": case["evidence_class"], "pins": deepcopy(item["pins"]),
        "obligation": deepcopy(case["obligation"]), "payload": _payload(case["evidence_class"], payload),
        "reported_status": reported_status,
        "receipt": result_state(execution=[reported_status], completion="PENDING", inputs=inputs),
        "findings": _findings([] if findings is None else findings),
        "missing_capabilities": _tokens([] if missing_capabilities is None else missing_capabilities),
        "application_claim_complete": False, "obligations_completed": [], **BOUNDARY})


def _case_records(request: dict, returned_members: Any) -> list[dict]:
    _manifest(returned_members, kind="EVIDENCE")
    require(set(returned_members) == {case["return_member"] for case in request["cases"]},
            "APPLICATION_KIT_EXACT_RETURN_MEMBER_SET_MISMATCH")
    rows = []
    for case in request["cases"]:
        value = strict_loads(returned_members[case["return_member"]])
        evidence = checked(value, _EVIDENCE_KEYS, CASE_SCHEMA)
        _public(evidence); _boundary(evidence)
        require(evidence["case_id"] == case["case_id"] and evidence["evidence_class"] == case["evidence_class"],
                "APPLICATION_KIT_RETURN_CASE_MISMATCH")
        verify_result_state(evidence["receipt"])
        expected = make_case_evidence(request, case_id=case["case_id"], payload=evidence["payload"],
            reported_status=evidence["reported_status"], findings=evidence["findings"],
            missing_capabilities=evidence["missing_capabilities"])
        require(evidence == expected, "APPLICATION_KIT_RETURN_IDENTITY_OR_RECEIPT_CHANGED")
        rows.append(evidence)
    return rows


@_typed_errors
def make_integration_return(request: Any, *, returned_members: dict[str, bytes]) -> dict:
    """Describe all concrete return members; a root alone establishes no result."""
    item = _request_shape(request)
    records = _case_records(item, returned_members)
    return seal({"schema": RETURN_SCHEMA, "request_root": item["root"], "pins": deepcopy(item["pins"]),
        "case_ids": [case["case_id"] for case in item["cases"]],
        "manifest": _manifest(returned_members, kind="EVIDENCE"),
        "case_receipts": [{"case_id": evidence["case_id"], "receipt": deepcopy(evidence["receipt"])} for evidence in records],
        "findings": [{"case_id": evidence["case_id"], "findings": deepcopy(evidence["findings"])} for evidence in records],
        "missing_capabilities": sorted(set(item["missing_capabilities"]) |
            {cap for evidence in records for cap in evidence["missing_capabilities"]}),
        "real_adapter_bindings": [], "application_claim_complete": False, "obligations_completed": [], **BOUNDARY})


@_typed_errors
def verify_integration_return(return_packet: Any, *, request: Any,
        input_members: dict[str, bytes], returned_members: dict[str, bytes],
        expected_request_root: str, expected_pins: dict, expected_case_ids: list[str]) -> dict:
    """Check real bytes against an independently pinned request and exact cases."""
    try:
        accepted = verify_integration_request(request, input_members=input_members,
            expected_request_root=expected_request_root, expected_pins=expected_pins,
            expected_case_ids=expected_case_ids)
        packet = checked(return_packet, _RETURN_KEYS, RETURN_SCHEMA)
        _boundary(packet); _public(packet)
        expected = make_integration_return(accepted, returned_members=returned_members)
        require(packet == expected, "APPLICATION_KIT_RETURN_BYTES_OR_CONTRACT_MISMATCH")
        records = _case_records(accepted, returned_members)
        results, missing = [], set(packet["missing_capabilities"])
        for case, evidence in zip(accepted["cases"], records, strict=True):
            evidence_class = case["evidence_class"]
            native = None
            if evidence_class == "BOUNDED_PROOF":
                model = _native_contract(case, input_members, accepted["pins"]["source"]["digest"])
                native = verify_proof(model, evidence["payload"]["proof_bundle"])
                status = "BOUNDED_MODEL_" + native["outcome"]
            elif evidence_class == "SIMULATION":
                status = "SIMULATION_ONLY"
            elif evidence_class == "RUNTIME_OBSERVATION":
                require(evidence["payload"]["reported_source"] == accepted["pins"]["source"]
                        and evidence["payload"]["reported_interface"] == accepted["pins"]["interface"],
                        "APPLICATION_KIT_RUNTIME_SUBJECT_MISMATCH")
                status = "RUNTIME_OBSERVATION_UNVERIFIED"; missing.add("BOUND_RUNTIME_OBSERVATION_VERIFIER")
            else:
                status = "INDEPENDENT_REVIEW_UNVERIFIED"; missing.add("INDEPENDENT_REVIEW_VERIFIER")
            results.append({"case_id": case["case_id"], "evidence_class": evidence_class,
                "obligation": deepcopy(case["obligation"]), "status": status,
                "native_check": native, "receipt": deepcopy(evidence["receipt"]),
                "disposition": "PENDING_REGISTERED_CHECKER"})
        return seal({"schema": CHECK_SCHEMA, "request_root": accepted["root"], "return_root": packet["root"],
            "pins": deepcopy(accepted["pins"]), "case_results": results,
            "exact_manifest_bytes_checked": True,
            "capability_status": "MISSING_CAPABILITY" if missing else "PURE_CAPABILITIES_ONLY",
            "missing_capabilities": sorted(missing), "real_adapter_bindings": [],
            "transport_status": "PASS_EXACT_RETURN_BYTES", "application_claim_complete": False,
            "obligations_completed": [], "activity_execution_attested": False, "independent_review_verified": False,
            "receipt": result_state(execution=["PASS"], completion="PENDING", assessment=["UNREVIEWED"]), **BOUNDARY})
    except (KeyError, TypeError, IndexError, AttributeError, ValueError) as error:
        if isinstance(error, Refusal):
            raise
        raise Refusal("APPLICATION_KIT_MALFORMED_RETURN", detail=type(error).__name__) from error
