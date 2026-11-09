"""Composed UCM-AMCAS integration campaign and three-gate operation protocol."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root, strict_loads

from .amcas import BOUNDARY, compile_contract, validate_contract
from .identity import load_passport, ucm_import_binding
from .journal import CampaignJournal


def _read(path: Path) -> Any:
    try:
        return strict_loads(Path(path).read_bytes())
    except OSError as error:
        raise ValueError("INTEGRATION_INPUT_UNREADABLE") from error


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            __import__("os").fsync(stream.fileno())
    except FileExistsError as error:
        raise ValueError("INTEGRATION_OUTPUT_EXISTS") from error


def _actor(kind: str = "SYSTEM", mosaic_id: str | None = None,
           session_id: str | None = None) -> dict[str, Any]:
    return {"kind": kind, "mosaic_id": mosaic_id, "session_id": session_id}


class IntegrationCampaign:
    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)
        self.contract_path = self.workspace / "CONTRACT.json"
        self.ir_path = self.workspace / "INTEGRATION-IR.json"
        self.journal = CampaignJournal(self.workspace / "journal")

    @classmethod
    def create(cls, workspace: Path, contract: Any, *,
               user_passport: Path | None = None, expected_user_id: str | None = None,
               agent_passport: Path | None = None, expected_agent_id: str | None = None) -> "IntegrationCampaign":
        contract = validate_contract(contract)
        compiled = compile_contract(contract)
        identities = (("USER", user_passport, expected_user_id, contract["identities"]["user_required"]),
                      ("AGENT", agent_passport, expected_agent_id, contract["identities"]["agent_required"]))
        imported_identities: dict[str, tuple[str, dict[str, Any]]] = {}
        for role, path, expected, required in identities:
            if required:
                require(path is not None and expected is not None, "INTEGRATION_IDENTITY_REQUIRED")
            if path is not None:
                require(expected is not None, "INTEGRATION_EXPECTED_ID_REQUIRED")
                imported = ucm_import_binding(load_passport(path), expected_mosaic_id=expected)
                imported_identities[role] = (expected, imported)
        if contract["identities"]["session_distinct"] and {"USER", "AGENT"} <= set(imported_identities):
            require(imported_identities["USER"][1]["mosaic_id"] !=
                    imported_identities["AGENT"][1]["mosaic_id"],
                    "INTEGRATION_USER_AGENT_IDENTITY_COLLISION")
        campaign = cls(workspace)
        require(not campaign.workspace.exists(), "INTEGRATION_WORKSPACE_EXISTS")
        campaign.workspace.mkdir(parents=True)
        _write_new(campaign.contract_path, contract)
        _write_new(campaign.ir_path, compiled)
        campaign.journal.initialize()
        campaign.journal.append(event_id="campaign-created", event_type="CAMPAIGN_CREATED",
            actor=_actor(), payload={"integration_id": contract["integration_id"],
                "contract_root": contract["contract_root"], "ir_root": compiled["ir_root"],
                "subject": contract["subject"], "authority_ceiling": BOUNDARY})
        campaign.journal.append(event_id="contract-compiled", event_type="CONTRACT_COMPILED",
            actor=_actor(), payload={"contract_root": contract["contract_root"],
                "ir_root": compiled["ir_root"],
                "obligation_ids": [row["id"] for row in compiled["obligations"]]})
        for role, (expected, imported) in imported_identities.items():
            campaign.journal.append(event_id=f"identity-{role.lower()}",
                event_type="IDENTITY_IMPORTED",
                actor=_actor(role, expected, None),
                payload={"role": role, "binding": imported})
        return campaign

    def contract(self) -> dict[str, Any]:
        return validate_contract(_read(self.contract_path))

    def compiled(self) -> dict[str, Any]:
        expected = compile_contract(self.contract())
        actual = _read(self.ir_path)
        require(actual == expected, "INTEGRATION_IR_DRIFT")
        return actual

    def _operation_events(self, operation_id: str) -> list[dict[str, Any]]:
        return [event for event in self.journal.verify()
                if event["payload"].get("operation_id") == operation_id]

    def _require_authenticated(self, session_id: str | None) -> None:
        policy = self.contract()["identities"]
        if policy["possession_required"]:
            require(type(session_id) is str and len(session_id) == 64,
                    "INTEGRATION_AUTHENTICATED_SESSION_REQUIRED")
            authenticated = [event for event in self.journal.verify()
                if event["event_type"] == "SESSION_AUTHENTICATED"
                and event["actor"]["session_id"] == session_id]
            require(bool(authenticated), "INTEGRATION_AUTHENTICATED_SESSION_REQUIRED")

    def plan_operation(self, operation: Any, *, event_id: str,
                       actor_mosaic_id: str | None = None,
                       session_id: str | None = None) -> dict[str, Any]:
        self._require_authenticated(session_id)
        contract = self.contract()
        item = exact_keys(operation, {
            "operation_id", "kind", "capability_id", "effect_ids", "intent",
            "inputs", "expected_outputs", "resource_budget", "rollback",
        })
        require(type(item["operation_id"]) is str and bool(item["operation_id"]),
                "INTEGRATION_OPERATION_ID_INVALID")
        require(item["kind"] in {"INTEGRATION_WORK", "CAPABILITY_GRANT"},
                "INTEGRATION_OPERATION_KIND_INVALID")
        capabilities = {row["id"]: row for row in contract["capabilities"]}
        effects = {row["id"]: row for row in contract["effects"]}
        require(item["capability_id"] in capabilities, "INTEGRATION_CAPABILITY_UNDECLARED")
        require(type(item["effect_ids"]) is list and len(item["effect_ids"]) == len(set(item["effect_ids"])),
                "INTEGRATION_EFFECT_SET_INVALID")
        require(all(effect in effects and effects[effect]["capability_id"] == item["capability_id"]
                    for effect in item["effect_ids"]), "INTEGRATION_EFFECT_UNDECLARED")
        require(type(item["intent"]) is str and bool(item["intent"]), "INTEGRATION_INTENT_INVALID")
        require(type(item["inputs"]) is list and type(item["expected_outputs"]) is list,
                "INTEGRATION_ARTIFACT_REFS_INVALID")
        for artifact in item["inputs"] + item["expected_outputs"]:
            ref = exact_keys(artifact, {"path", "sha256"})
            require(type(ref["path"]) is str and bool(ref["path"]), "INTEGRATION_ARTIFACT_PATH_INVALID")
            require_root(ref["sha256"])
        budget = exact_keys(item["resource_budget"], {"max_seconds", "max_bytes", "max_invocations"})
        require(all(type(budget[field]) is int and budget[field] >= 0 for field in budget),
                "INTEGRATION_RESOURCE_BUDGET_INVALID")
        rollback = exact_keys(item["rollback"], {"required", "plan_root"})
        require(type(rollback["required"]) is bool and
                (rollback["plan_root"] is None or require_root(rollback["plan_root"])),
                "INTEGRATION_ROLLBACK_INVALID")
        require(not self._operation_events(item["operation_id"]), "INTEGRATION_OPERATION_EXISTS")
        actor = _actor("AGENT" if actor_mosaic_id else "SYSTEM", actor_mosaic_id, session_id)
        planned = self.journal.append(event_id=event_id, event_type="OPERATION_PLANNED",
            actor=actor, payload={"operation_id": item["operation_id"], "operation": deepcopy(item),
                                  "operation_root": root(item), "contract_root": contract["contract_root"]})
        sentinel_body = {
            "schema": "mosaic.ucm.sentinel-receipt.v0.1", "gate": "G1_SENTINEL",
            "gate_namespace": "UCM.INTEGRATION.G1",
            "operation_id": item["operation_id"], "operation_root": root(item),
            "contract_root": contract["contract_root"], "journal_predecessor": planned["event_root"],
            "capability_bound": True, "effects_bound": True, "budget_bound": True,
            "rollback_bound": (not rollback["required"] or rollback["plan_root"] is not None),
            "execution_authorized": False,
            "diagnostic": "EXTERNAL_EFFECT_AUTHORITY_NOT_GRANTED",
            "H_s": root({"journal_head": planned["event_root"]}),
            "H_c": root({"contract_root": contract["contract_root"],
                          "capability": capabilities[item["capability_id"]],
                          "effects": [effects[name] for name in sorted(item["effect_ids"])]}),
            "H_m": root({"intent": item["intent"], "expected_outputs": item["expected_outputs"]}),
            "H_j": root(contract["identities"]["jurisdiction"]),
            "H_r": root({"operation_id": item["operation_id"], "gate": "G1_SENTINEL"}),
            "native_ugk_receipt_verified": False,
            "required_native_verifier": "PINNED_NATIVE_UGK_RECEIPT_VERIFIER",
            **BOUNDARY,
        }
        sentinel_body["h_body"] = root(sentinel_body)
        sentinel = {**sentinel_body, "receipt_root": root(sentinel_body)}
        event = self.journal.append(event_id=f"{event_id}:sentinel",
            event_type="SENTINEL_RECEIPTED", actor=actor,
            payload={"operation_id": item["operation_id"], "sentinel": sentinel})
        return {"operation_root": root(item), "sentinel": sentinel,
                "journal_event_root": event["event_root"], **BOUNDARY}

    def record_witness(self, witness: Any, *, event_id: str,
                       actor_mosaic_id: str | None = None,
                       session_id: str | None = None) -> dict[str, Any]:
        self._require_authenticated(session_id)
        item = exact_keys(witness, {"operation_id", "outcome", "observed_effects", "outputs",
                                    "terminal_capture", "recovery_required"})
        events = self._operation_events(item["operation_id"])
        require([event["event_type"] for event in events] ==
                ["OPERATION_PLANNED", "SENTINEL_RECEIPTED"], "INTEGRATION_WITNESS_ORDER_INVALID")
        operation = events[0]["payload"]["operation"]
        declared = {row["effect_class"] for row in self.contract()["effects"]
                    if row["id"] in operation["effect_ids"]}
        require(type(item["observed_effects"]) is list and
                set(item["observed_effects"]) <= declared, "INTEGRATION_OBSERVED_EFFECT_UNDECLARED")
        require(item["outcome"] in {"PASS", "REFUSED", "FAIL", "INTERRUPTED", "PENDING_RECOVERY"},
                "INTEGRATION_WITNESS_OUTCOME_INVALID")
        require(type(item["outputs"]) is list and all(type(row) is dict for row in item["outputs"]),
                "INTEGRATION_WITNESS_OUTPUT_INVALID")
        for output in item["outputs"]:
            exact_keys(output, {"path", "sha256"}); require_root(output["sha256"])
        capture = exact_keys(item["terminal_capture"], {"stdout_sha256", "stderr_sha256", "exit_code"})
        require_root(capture["stdout_sha256"]); require_root(capture["stderr_sha256"])
        require(type(capture["exit_code"]) is int, "INTEGRATION_EXIT_CODE_INVALID")
        require(type(item["recovery_required"]) is bool and
                (item["outcome"] != "PENDING_RECOVERY" or item["recovery_required"]),
                "INTEGRATION_RECOVERY_STATUS_INVALID")
        actor = _actor("AGENT" if actor_mosaic_id else "SYSTEM", actor_mosaic_id, session_id)
        body = {"schema": "mosaic.ucm.witness-receipt.v0.1", "gate": "G2_WITNESS",
                "gate_namespace": "UCM.INTEGRATION.G2",
                "operation_id": item["operation_id"], "operation_root": root(operation),
                "sentinel_root": events[1]["payload"]["sentinel"]["receipt_root"],
                "observation": deepcopy(item), "observation_root": root(item),
                "H_s": root({"journal_head": events[-1]["event_root"]}),
                "H_c": events[1]["payload"]["sentinel"]["H_c"],
                "H_m": events[1]["payload"]["sentinel"]["H_m"],
                "H_j": events[1]["payload"]["sentinel"]["H_j"],
                "H_r": root({"operation_id": item["operation_id"], "gate": "G2_WITNESS"}),
                "native_ugk_receipt_verified": False,
                "required_native_verifier": "PINNED_NATIVE_UGK_RECEIPT_VERIFIER", **BOUNDARY}
        body["h_body"] = root(body)
        receipt = {**body, "receipt_root": root(body)}
        event = self.journal.append(event_id=event_id, event_type="WITNESS_RECORDED",
            actor=actor, payload={"operation_id": item["operation_id"], "witness": receipt})
        return {"witness": receipt, "journal_event_root": event["event_root"], **BOUNDARY}

    def record_diagnostic(self, diagnostic: Any, *, event_id: str,
                          actor_mosaic_id: str | None = None,
                          session_id: str | None = None) -> dict[str, Any]:
        self._require_authenticated(session_id)
        item = exact_keys(diagnostic, {"operation_id", "classification", "finding_ids",
                                       "acceptance", "next_action"})
        events = self._operation_events(item["operation_id"])
        require([event["event_type"] for event in events] ==
                ["OPERATION_PLANNED", "SENTINEL_RECEIPTED", "WITNESS_RECORDED"],
                "INTEGRATION_DIAGNOSTIC_ORDER_INVALID")
        require(item["classification"] in {"SUCCESS", "EXPECTED_REFUSAL", "DEFECT", "PARTIAL",
                                              "INTERRUPTED", "RECOVERY_REQUIRED"},
                "INTEGRATION_DIAGNOSTIC_CLASS_INVALID")
        require(type(item["finding_ids"]) is list and
                all(type(value) is str for value in item["finding_ids"]),
                "INTEGRATION_FINDING_IDS_INVALID")
        require(item["acceptance"] in {"NOT_GRANTED", "READY_FOR_REVIEW", "HOLD_FOR_REPAIR"},
                "INTEGRATION_ACCEPTANCE_INVALID")
        require(type(item["next_action"]) is str and bool(item["next_action"]),
                "INTEGRATION_NEXT_ACTION_INVALID")
        witness = events[2]["payload"]["witness"]
        body = {"schema": "mosaic.ucm.diagnostic-receipt.v0.1", "gate": "G3_DIAGNOSTIC",
                "gate_namespace": "UCM.INTEGRATION.G3",
                "operation_id": item["operation_id"], "operation_root": events[0]["payload"]["operation_root"],
                "witness_root": witness["receipt_root"], "diagnostic": deepcopy(item),
                "diagnostic_root": root(item), "constitutional_acceptance": "NOT_GRANTED",
                "H_s": root({"journal_head": events[-1]["event_root"]}),
                "H_c": witness["H_c"], "H_m": witness["H_m"], "H_j": witness["H_j"],
                "H_r": root({"operation_id": item["operation_id"], "gate": "G3_DIAGNOSTIC"}),
                "native_ugk_receipt_verified": False,
                "required_native_verifier": "PINNED_NATIVE_UGK_RECEIPT_VERIFIER", **BOUNDARY}
        body["h_body"] = root(body)
        receipt = {**body, "receipt_root": root(body)}
        actor = _actor("AGENT" if actor_mosaic_id else "SYSTEM", actor_mosaic_id, session_id)
        event = self.journal.append(event_id=event_id, event_type="DIAGNOSTIC_RECORDED",
            actor=actor, payload={"operation_id": item["operation_id"], "diagnostic": receipt})
        return {"diagnostic": receipt, "journal_event_root": event["event_root"], **BOUNDARY}

    def status(self) -> dict[str, Any]:
        compiled = self.compiled()
        events = self.journal.verify()
        dispositions = {event["payload"].get("obligation_id"): event["payload"].get("status")
                        for event in events if event["event_type"] == "REQUIREMENT_DISPOSITIONED"}
        obligations = [{"id": row["id"], "required": row["required"],
                        "status": dispositions.get(row["id"], "UNRESOLVED")}
                       for row in compiled["obligations"]]
        checkpoint = self.journal.checkpoint()
        body = {"schema": "mosaic.ucm.integration-status.v0.1",
                "contract_root": compiled["contract_root"], "ir_root": compiled["ir_root"],
                "journal_head": checkpoint["head"], "obligations": obligations,
                "open_operations": checkpoint["open_operations"],
                "ready_for_review": all(not row["required"] or row["status"] == "PASS"
                                        for row in obligations)
                                    and not checkpoint["open_operations"], **BOUNDARY}
        return {**body, "status_root": root(body)}

    def disposition(self, obligation_id: str, status: str, evidence_roots: list[str], *,
                    event_id: str, actor_mosaic_id: str | None = None,
                    session_id: str | None = None) -> dict[str, Any]:
        self._require_authenticated(session_id)
        obligations = {row["id"]: row for row in self.compiled()["obligations"]}
        require(obligation_id in obligations, "INTEGRATION_OBLIGATION_UNKNOWN")
        require(status in {"PASS", "REFUSED", "FAIL", "DEFERRED", "NOT_APPLICABLE"},
                "INTEGRATION_DISPOSITION_INVALID")
        require(type(evidence_roots) is list and
                all(require_root(value) for value in evidence_roots),
                "INTEGRATION_EVIDENCE_ROOT_INVALID")
        require(not obligations[obligation_id]["evidence_required"] or bool(evidence_roots)
                or status not in {"PASS"}, "INTEGRATION_REQUIRED_EVIDENCE_MISSING")
        event = self.journal.append(event_id=event_id,
            event_type="REQUIREMENT_DISPOSITIONED",
            actor=_actor("AGENT" if actor_mosaic_id else "SYSTEM", actor_mosaic_id, session_id),
            payload={"obligation_id": obligation_id, "subject_root": obligations[obligation_id]["subject_root"],
                     "status": status, "evidence_roots": sorted(set(evidence_roots))})
        return {"obligation_id": obligation_id, "status": status,
                "journal_event_root": event["event_root"], **BOUNDARY}

    def import_session_report(self, report: Any, *, event_id_prefix: str) -> dict[str, Any]:
        item = exact_keys(report, {"schema", "contract_root", "ir_root", "session_mosaic_id",
            "source_root_observed", "requirement_dispositions", "operation_summaries",
            "findings", "artifacts", "limitations", "standing", "authority_effect",
            "real_a5", "g0", "report_root"})
        require(item["schema"] == "mosaic.ucm.session-integration-report.v0.1"
                and item["contract_root"] == self.contract()["contract_root"]
                and item["ir_root"] == self.compiled()["ir_root"]
                and item["source_root_observed"] == self.contract()["subject"]["source_root"],
                "INTEGRATION_SESSION_REPORT_BINDING_INVALID")
        require(type(item["session_mosaic_id"]) is str and len(item["session_mosaic_id"]) == 64,
                "INTEGRATION_SESSION_REPORT_ID_INVALID")
        require({key: item[key] for key in BOUNDARY} == BOUNDARY,
                "INTEGRATION_SESSION_REPORT_CEILING_INVALID")
        body = {key: deepcopy(value) for key, value in item.items() if key != "report_root"}
        require(item["report_root"] == root(body), "INTEGRATION_SESSION_REPORT_ROOT_INVALID")
        if self.contract()["identities"]["possession_required"]:
            authenticated = any(event["event_type"] == "SESSION_AUTHENTICATED"
                and event["actor"]["session_id"] == item["session_mosaic_id"]
                for event in self.journal.verify())
            require(authenticated, "INTEGRATION_SESSION_REPORT_UNAUTHENTICATED")
        imported = []
        for index, row in enumerate(item["requirement_dispositions"]):
            row = exact_keys(row, {"obligation_id", "status", "evidence_roots"})
            result = self.disposition(row["obligation_id"], row["status"], row["evidence_roots"],
                event_id=f"{event_id_prefix}:requirement:{index}",
                actor_mosaic_id=item["session_mosaic_id"], session_id=item["session_mosaic_id"]
                if self.contract()["identities"]["possession_required"] else None)
            imported.append(result["journal_event_root"])
        for index, row in enumerate(item["findings"]):
            row = exact_keys(row, {"id", "severity", "statement", "evidence_roots"})
            require(row["severity"] in {"INFO", "LOW", "MED", "HIGH"}
                    and type(row["statement"]) is str and bool(row["statement"])
                    and all(require_root(value) for value in row["evidence_roots"]),
                    "INTEGRATION_FINDING_INVALID")
            event = self.journal.append(event_id=f"{event_id_prefix}:finding:{index}",
                event_type="FINDING_RECORDED",
                actor=_actor("AGENT", item["session_mosaic_id"], item["session_mosaic_id"]),
                payload=deepcopy(row)); imported.append(event["event_root"])
        for index, row in enumerate(item["artifacts"]):
            row = exact_keys(row, {"role", "path", "sha256", "bytes"})
            require(type(row["role"]) is str and type(row["path"]) is str
                    and type(row["bytes"]) is int and row["bytes"] >= 0,
                    "INTEGRATION_ARTIFACT_INVALID")
            require_root(row["sha256"])
            event = self.journal.append(event_id=f"{event_id_prefix}:artifact:{index}",
                event_type="ARTIFACT_RECORDED",
                actor=_actor("AGENT", item["session_mosaic_id"], item["session_mosaic_id"]),
                payload=deepcopy(row)); imported.append(event["event_root"])
        require(type(item["operation_summaries"]) is list and type(item["limitations"]) is list,
                "INTEGRATION_SESSION_REPORT_FIELD_INVALID")
        event = self.journal.append(event_id=f"{event_id_prefix}:report",
            event_type="REPORT_CREATED",
            actor=_actor("AGENT", item["session_mosaic_id"], item["session_mosaic_id"]),
            payload={"report_root": item["report_root"],
                     "operation_summaries": item["operation_summaries"],
                     "limitations": item["limitations"]})
        imported.append(event["event_root"])
        return {"status": "PASS_IMPORTED", "report_root": item["report_root"],
                "event_roots": imported, **BOUNDARY}
