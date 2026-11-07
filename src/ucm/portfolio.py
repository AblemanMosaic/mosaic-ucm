"""Governed multi-application UCM integration portfolio."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
from pathlib import Path
from typing import Any
import zipfile

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root, strict_loads

from .amcas import BOUNDARY
from .journal import CampaignJournal
from .stage1 import verify_stage1_bundle
from .composition import build_preflight_from_bytes, verify_declaration
from .artifacts import verify_deterministic_zip
from .stage3 import instruction as build_stage3_instruction, plan_template, validate_plan


SCHEMA = "mosaic.ucm.integration-portfolio.v0.1"
COURT_EVIDENCE_SCHEMA = "mosaic.ucm.amcas-correspondence-court-evidence.v0.1"
COURT_EVIDENCE_ROLE = "UCM_AMCAS_CORRESPONDENCE_COURT_EVIDENCE"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            __import__("os").fsync(stream.fileno())
    except FileExistsError as error:
        raise ValueError("PORTFOLIO_OUTPUT_EXISTS") from error


def _write_new_bytes(path: Path, raw: bytes) -> None:
    require(type(raw) is bytes, "PORTFOLIO_CAS_OBJECT_INVALID")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            __import__("os").fsync(stream.fileno())
    except FileExistsError as error:
        raise ValueError("PORTFOLIO_OUTPUT_EXISTS") from error


def validate_roster(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "portfolio_id", "applications",
                              "standing", "authority_effect", "real_a5", "g0", "roster_root"})
    require(item["schema"] == SCHEMA, "PORTFOLIO_SCHEMA_INVALID")
    require(type(item["portfolio_id"]) is str and bool(item["portfolio_id"]),
            "PORTFOLIO_ID_INVALID")
    require(type(item["applications"]) is list and bool(item["applications"]),
            "PORTFOLIO_APPLICATIONS_EMPTY")
    ids = set()
    threads = set()
    for raw in item["applications"]:
        row = exact_keys(raw, {"id", "name", "thread_id", "kit"})
        require(type(row["id"]) is str and row["id"] and row["id"] not in ids,
                "PORTFOLIO_APPLICATION_ID_INVALID")
        require(type(row["name"]) is str and row["name"]
                and type(row["thread_id"]) is str and row["thread_id"]
                and row["thread_id"] not in threads
                and type(row["kit"]) is str and row["kit"],
                "PORTFOLIO_APPLICATION_INVALID")
        ids.add(row["id"]); threads.add(row["thread_id"])
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "PORTFOLIO_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "roster_root"}
    require(item["roster_root"] == root(body), "PORTFOLIO_ROSTER_ROOT_INVALID")
    return deepcopy(item)


class PortfolioCampaign:
    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)
        self.roster_path = self.workspace / "PORTFOLIO.json"
        self.journal = CampaignJournal(self.workspace / "journal")

    @classmethod
    def create(cls, workspace: Path, roster: Any) -> "PortfolioCampaign":
        roster = validate_roster(roster)
        campaign = cls(workspace)
        require(not campaign.workspace.exists(), "PORTFOLIO_WORKSPACE_EXISTS")
        campaign.workspace.mkdir(parents=True)
        _write_new(campaign.roster_path, roster)
        campaign.journal.initialize()
        campaign.journal.append(event_id="portfolio-created", event_type="CAMPAIGN_CREATED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"portfolio_id": roster["portfolio_id"],
                     "roster_root": roster["roster_root"],
                     "application_ids": [row["id"] for row in roster["applications"]]})
        return campaign

    def roster(self) -> dict[str, Any]:
        return validate_roster(strict_loads(self.roster_path.read_bytes()))

    def _application(self, application_id: str) -> dict[str, Any]:
        rows = {row["id"]: row for row in self.roster()["applications"]}
        require(application_id in rows, "PORTFOLIO_APPLICATION_UNKNOWN")
        return rows[application_id]

    def _cas_path(self, artifact_sha256: str, suffix: str = ".zip") -> Path:
        require_root(artifact_sha256)
        require(suffix in {".zip", ".json"}, "PORTFOLIO_CAS_SUFFIX_INVALID")
        return self.workspace / "cas" / "sha256" / artifact_sha256[:2] / (artifact_sha256 + suffix)

    def _store_cas_object(self, raw: bytes, suffix: str = ".zip") -> tuple[str, Path]:
        digest = _sha(raw)
        path = self._cas_path(digest, suffix)
        if path.exists():
            require(path.is_file() and path.read_bytes() == raw,
                    "PORTFOLIO_CAS_OBJECT_COLLISION")
        else:
            _write_new_bytes(path, raw)
        return digest, path

    def _verify_cas_object(self, artifact_sha256: str, suffix: str = ".zip") -> bool:
        path = self._cas_path(artifact_sha256, suffix)
        return path.is_file() and _sha(path.read_bytes()) == artifact_sha256

    def _operations(self, application_id: str | None = None) -> list[dict[str, Any]]:
        operations = [event["payload"]["operation"] for event in self.journal.verify()
                      if event["event_type"] == "OPERATION_PLANNED"]
        if application_id is not None:
            operations = [row for row in operations if row.get("application_id") == application_id]
        return operations

    def _latest_operation(self, application_id: str, action: str) -> dict[str, Any] | None:
        rows = [row for row in self._operations(application_id)
                if row["portfolio_action"] == action]
        return rows[-1] if rows else None

    def _record(self, *, action: str, application_id: str, artifact_sha256: str,
                details: dict[str, Any], event_id_prefix: str) -> dict[str, Any]:
        application = self._application(application_id)
        require_root(artifact_sha256)
        existing = [event for event in self.journal.verify()
                    if event["event_id"].startswith(event_id_prefix + ":")]
        allowed_ids = {event_id_prefix + suffix for suffix in
                       (":plan", ":sentinel", ":witness", ":diagnostic")}
        require(all(event["event_id"] in allowed_ids for event in existing),
                "PORTFOLIO_EVENT_PREFIX_INVALID")
        operation = {
            "schema": "mosaic.ucm.portfolio-operation.v0.1",
            "portfolio_action": action,
            "application_id": application_id,
            "thread_id": application["thread_id"],
            "artifact_sha256": artifact_sha256,
            "details": deepcopy(details),
            **BOUNDARY,
        }
        planned = self.journal.append(event_id=event_id_prefix + ":plan",
            event_type="OPERATION_PLANNED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"operation_id": event_id_prefix, "operation": operation,
                     "operation_root": root(operation)})
        sentinel_body = {
            "schema": "mosaic.ucm.portfolio-sentinel.v0.1",
            "gate": "G1_SENTINEL",
            "gate_namespace": "UCM.INTEGRATION.G1",
            "operation_id": event_id_prefix,
            "operation_root": root(operation),
            "journal_predecessor": planned["event_root"],
            "execution_authorized": False,
            "native_ugk_receipt_verified": False,
            **BOUNDARY,
        }
        sentinel = {**sentinel_body, "receipt_root": root(sentinel_body)}
        self.journal.append(event_id=event_id_prefix + ":sentinel",
            event_type="SENTINEL_RECEIPTED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"operation_id": event_id_prefix, "sentinel": sentinel})
        witness_body = {
            "schema": "mosaic.ucm.portfolio-witness.v0.1",
            "gate": "G2_WITNESS",
            "gate_namespace": "UCM.INTEGRATION.G2",
            "operation_id": event_id_prefix,
            "sentinel_root": sentinel["receipt_root"],
            "artifact_sha256": artifact_sha256,
            "outcome": "PASS_RECORDED",
            **BOUNDARY,
        }
        witness = {**witness_body, "receipt_root": root(witness_body)}
        self.journal.append(event_id=event_id_prefix + ":witness",
            event_type="WITNESS_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"operation_id": event_id_prefix, "witness": witness})
        diagnostic_body = {
            "schema": "mosaic.ucm.portfolio-diagnostic.v0.1",
            "gate": "G3_DIAGNOSTIC",
            "gate_namespace": "UCM.INTEGRATION.G3",
            "operation_id": event_id_prefix,
            "witness_root": witness["receipt_root"],
            "classification": "SUCCESS",
            "constitutional_acceptance": "NOT_GRANTED",
            **BOUNDARY,
        }
        diagnostic = {**diagnostic_body, "receipt_root": root(diagnostic_body)}
        self.journal.append(event_id=event_id_prefix + ":diagnostic",
            event_type="DIAGNOSTIC_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"operation_id": event_id_prefix, "diagnostic": diagnostic})
        return {"application_id": application_id, "action": action,
                "artifact_sha256": artifact_sha256,
                "sentinel_root": sentinel["receipt_root"],
                "witness_root": witness["receipt_root"],
                "diagnostic_root": diagnostic["receipt_root"], **BOUNDARY}

    def _record_portfolio(self, *, action: str, artifact_sha256: str,
                          details: dict[str, Any], event_id_prefix: str) -> dict[str, Any]:
        """Record a portfolio-wide information-only operation through G1/G2/G3."""
        require_root(artifact_sha256)
        existing = [event for event in self.journal.verify()
                    if event["event_id"].startswith(event_id_prefix + ":")]
        allowed_ids = {event_id_prefix + suffix for suffix in
                       (":plan", ":sentinel", ":witness", ":diagnostic")}
        require(all(event["event_id"] in allowed_ids for event in existing),
                "PORTFOLIO_EVENT_PREFIX_INVALID")
        operation = {
            "schema": "mosaic.ucm.portfolio-operation.v0.1",
            "portfolio_action": action,
            "application_id": None,
            "thread_id": None,
            "artifact_sha256": artifact_sha256,
            "details": deepcopy(details),
            **BOUNDARY,
        }
        planned = self.journal.append(event_id=event_id_prefix + ":plan",
            event_type="OPERATION_PLANNED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"operation_id": event_id_prefix, "operation": operation,
                     "operation_root": root(operation)})
        sentinel_body = {
            "schema": "mosaic.ucm.portfolio-sentinel.v0.1",
            "gate": "G1_SENTINEL", "gate_namespace": "UCM.INTEGRATION.G1",
            "operation_id": event_id_prefix, "operation_root": root(operation),
            "journal_predecessor": planned["event_root"],
            "execution_authorized": False, "native_ugk_receipt_verified": False,
            **BOUNDARY,
        }
        sentinel = {**sentinel_body, "receipt_root": root(sentinel_body)}
        self.journal.append(event_id=event_id_prefix + ":sentinel",
            event_type="SENTINEL_RECEIPTED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"operation_id": event_id_prefix, "sentinel": sentinel})
        witness_body = {
            "schema": "mosaic.ucm.portfolio-witness.v0.1",
            "gate": "G2_WITNESS", "gate_namespace": "UCM.INTEGRATION.G2",
            "operation_id": event_id_prefix, "sentinel_root": sentinel["receipt_root"],
            "artifact_sha256": artifact_sha256, "outcome": "PASS_RECORDED", **BOUNDARY,
        }
        witness = {**witness_body, "receipt_root": root(witness_body)}
        self.journal.append(event_id=event_id_prefix + ":witness",
            event_type="WITNESS_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"operation_id": event_id_prefix, "witness": witness})
        diagnostic_body = {
            "schema": "mosaic.ucm.portfolio-diagnostic.v0.1",
            "gate": "G3_DIAGNOSTIC", "gate_namespace": "UCM.INTEGRATION.G3",
            "operation_id": event_id_prefix, "witness_root": witness["receipt_root"],
            "classification": "SUCCESS", "constitutional_acceptance": "NOT_GRANTED",
            **BOUNDARY,
        }
        diagnostic = {**diagnostic_body, "receipt_root": root(diagnostic_body)}
        self.journal.append(event_id=event_id_prefix + ":diagnostic",
            event_type="DIAGNOSTIC_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"operation_id": event_id_prefix, "diagnostic": diagnostic})
        return {"portfolio_id": self.roster()["portfolio_id"], "action": action,
                "artifact_sha256": artifact_sha256,
                "sentinel_root": sentinel["receipt_root"],
                "witness_root": witness["receipt_root"],
                "diagnostic_root": diagnostic["receipt_root"], **BOUNDARY}

    def record_intake(self, value: Any, *, event_id_prefix: str) -> dict[str, Any]:
        item = exact_keys(value, {"schema", "application_id", "thread_id",
                                  "response_sha256", "subject_status", "subject_root"})
        application = self._application(item["application_id"])
        require(item["schema"] == "mosaic.ucm.portfolio-intake.v0.1"
                and item["thread_id"] == application["thread_id"],
                "PORTFOLIO_INTAKE_BINDING_INVALID")
        require_root(item["response_sha256"])
        require(item["subject_status"] in {"BOUND_IMMUTABLE", "BOUND_WORKING_BASELINE",
                                           "SOURCE_BOUNDARY_REQUIRED"},
                "PORTFOLIO_SUBJECT_STATUS_INVALID")
        require(item["subject_root"] is None or require_root(item["subject_root"]),
                "PORTFOLIO_SUBJECT_ROOT_INVALID")
        return self._record(action="RECORD_INTAKE", application_id=item["application_id"],
                            artifact_sha256=item["response_sha256"], details=item,
                            event_id_prefix=event_id_prefix)

    def record_instruction(self, value: Any, *, event_id_prefix: str) -> dict[str, Any]:
        item = exact_keys(value, {"schema", "application_id", "thread_id",
                                  "instruction_sha256"})
        application = self._application(item["application_id"])
        require(item["schema"] == "mosaic.ucm.portfolio-instruction.v0.1"
                and item["thread_id"] == application["thread_id"],
                "PORTFOLIO_INSTRUCTION_BINDING_INVALID")
        require_root(item["instruction_sha256"])
        return self._record(action="DELIVER_INSTRUCTION", application_id=item["application_id"],
                            artifact_sha256=item["instruction_sha256"], details=item,
                            event_id_prefix=event_id_prefix)

    def import_stage1(self, raw: bytes, *, event_id_prefix: str) -> dict[str, Any]:
        verified = verify_stage1_bundle(raw)
        artifact_sha256, cas_path = self._store_cas_object(raw)
        result = self._record(action="IMPORT_STAGE_I1",
            application_id=verified["application_id"], artifact_sha256=artifact_sha256,
            details=verified, event_id_prefix=event_id_prefix)
        return {**result, "stage_i1": verified,
                "cas": {"algorithm": "sha256", "digest": artifact_sha256,
                        "path": cas_path.relative_to(self.workspace).as_posix(),
                        "status": "STORED_VERIFIED"}}

    def import_stage2(self, raw: bytes, *, event_id_prefix: str) -> dict[str, Any]:
        """Admit a canonical I2 declaration against the exact current I1 object."""
        require(type(raw) is bytes, "PORTFOLIO_STAGE_I2_BYTES_INVALID")
        value = strict_loads(raw)
        require(type(value) is dict and type(value.get("application_id")) is str,
                "PORTFOLIO_STAGE_I2_DECLARATION_INVALID")
        application_id = value["application_id"]
        self._application(application_id)
        stage1 = self._latest_operation(application_id, "IMPORT_STAGE_I1")
        require(stage1 is not None, "PORTFOLIO_STAGE_I2_STAGE_I1_MISSING")
        stage1_path = self._cas_path(stage1["artifact_sha256"], ".zip")
        require(stage1_path.is_file(), "PORTFOLIO_STAGE_I2_STAGE_I1_CAS_MISSING")
        checked = verify_declaration(value, expected_i1=stage1_path.read_bytes())
        canonical = canonical_bytes(checked)
        artifact_sha256, cas_path = self._store_cas_object(raw, ".json")
        revision = 1 + len([row for row in self._operations(application_id)
                            if row["portfolio_action"] == "IMPORT_STAGE_I2"])
        result = self._record(action="IMPORT_STAGE_I2", application_id=application_id,
            artifact_sha256=artifact_sha256,
            details={"declaration_root": checked["declaration_root"],
                     "stage_i1_artifact_sha256": checked["stage_i1_artifact_sha256"],
                     "declared_relations_status": checked["declared_relations_status"],
                     "canonical_sha256": _sha(canonical),
                     "input_canonical": raw == canonical,
                     "export_count": len(checked["exports"]),
                     "import_count": len(checked["imports"]),
                     "revision": revision},
            event_id_prefix=event_id_prefix)
        return {**result, "stage_i2": checked,
                "revision": revision,
                "cas": {"algorithm": "sha256", "digest": artifact_sha256,
                        "path": cas_path.relative_to(self.workspace).as_posix(),
                        "status": "STORED_VERIFIED"}}

    def import_correspondence_court(self, raw: bytes, *, event_id_prefix: str,
                                    expected_handoff_sha256: str,
                                    expected_portfolio_sha256: str) -> dict[str, Any]:
        """Import a sealed operator-run court without converting it into authority."""
        require(type(raw) is bytes, "PORTFOLIO_COURT_BYTES_INVALID")
        require_root(expected_handoff_sha256); require_root(expected_portfolio_sha256)
        manifest = verify_deterministic_zip(raw, expected_schema=COURT_EVIDENCE_SCHEMA,
                                            expected_role=COURT_EVIDENCE_ROLE)
        expected_paths = {"CORRESPONDENCE-COURT-RESULT.json", "REPORT.md",
                          "RUN-CORRESPONDENCE-COURT.py"}
        require({row["path"] for row in manifest["files"]} == expected_paths,
                "PORTFOLIO_COURT_FILE_SET_INVALID")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            result = strict_loads(archive.read("CORRESPONDENCE-COURT-RESULT.json"))
        result = exact_keys(result, {"schema", "handoff_sha256", "portfolio_sha256",
            "baseline", "rows", "counts", "status", "standing", "authority_effect",
            "real_a5", "g0", "court_root"})
        require(result["schema"] == "mosaic.ucm.amcas-correspondence-court-result.v0.1",
                "PORTFOLIO_COURT_SCHEMA_INVALID")
        require({key: result[key] for key in BOUNDARY} == BOUNDARY,
                "PORTFOLIO_COURT_AUTHORITY_CEILING_INVALID")
        body = {key: deepcopy(value) for key, value in result.items() if key != "court_root"}
        require(result["court_root"] == root(body), "PORTFOLIO_COURT_ROOT_INVALID")
        require(result["handoff_sha256"] == expected_handoff_sha256
                and result["portfolio_sha256"] == expected_portfolio_sha256,
                "PORTFOLIO_COURT_SUBJECT_BINDING_INVALID")
        counts = exact_keys(result["counts"], {"PASS", "FAIL"})
        require(type(result["rows"]) is list and bool(result["rows"])
                and counts["PASS"] == len(result["rows"]) and counts["FAIL"] == 0
                and result["status"] == "PASS", "PORTFOLIO_COURT_RESULT_INVALID")
        for row in result["rows"]:
            checked_row = exact_keys(row, {"id", "expected", "observed", "status"})
            require(all(type(checked_row[key]) is str and checked_row[key]
                        for key in ("id", "expected", "observed"))
                    and checked_row["status"] == "PASS", "PORTFOLIO_COURT_ROW_INVALID")
        baseline = exact_keys(result["baseline"], {"applications", "matched_edges",
                                                   "preflight_root", "preflight_status",
                                                   "composition_authorized"})
        preflight = self.composition_preflight()
        require(baseline["applications"] == len(self.roster()["applications"])
                and baseline["matched_edges"] == len(
                    [edge for edge in preflight["edges"] if edge["status"] == "MATCHED"])
                and baseline["preflight_root"] == preflight["preflight_root"]
                and baseline["preflight_status"] == preflight["status"]
                and baseline["composition_authorized"] is False
                and preflight["composition_authorized"] is False,
                "PORTFOLIO_COURT_PREFLIGHT_BINDING_INVALID")
        artifact_sha256, cas_path = self._store_cas_object(raw, ".zip")
        details = {"claim": "OPERATOR_REPRODUCED_ADVERSARIAL_EVIDENCE",
                   "court_root": result["court_root"], "court_status": result["status"],
                   "case_count": len(result["rows"]),
                   "preflight_root": baseline["preflight_root"],
                   "handoff_sha256": result["handoff_sha256"],
                   "portfolio_sha256": result["portfolio_sha256"],
                   "independent_reviewer_authored": False,
                   "composition_authorized": False,
                   "stage_i3_shadow_authorized": False}
        recorded = self._record_portfolio(action="IMPORT_CORRESPONDENCE_COURT",
            artifact_sha256=artifact_sha256, details=details,
            event_id_prefix=event_id_prefix)
        return {**recorded, "court": details,
                "cas": {"algorithm": "sha256", "digest": artifact_sha256,
                        "path": cas_path.relative_to(self.workspace).as_posix(),
                        "status": "STORED_VERIFIED"}}

    def issue_stage3_instructions(self, *, pipeline_release_sha256: str,
                                  predecessor_portfolio_raw: bytes,
                                  predecessor_portfolio_sha256: str,
                                  expected_status_root: str,
                                  event_id_prefix: str) -> list[dict[str, Any]]:
        """Issue a fixed-denominator set of planning-only Stage I3 instructions."""
        require_root(pipeline_release_sha256); require_root(predecessor_portfolio_sha256)
        require_root(expected_status_root)
        require(type(predecessor_portfolio_raw) is bytes
                and _sha(predecessor_portfolio_raw) == predecessor_portfolio_sha256,
                "STAGE_I3_PREDECESSOR_PORTFOLIO_HASH_INVALID")
        verify_deterministic_zip(predecessor_portfolio_raw,
            expected_schema="mosaic.ucm.amcas-integration-portfolio-snapshot.v0.4",
            expected_role="PORTABLE_CANONICAL_INTEGRATION_PORTFOLIO")
        with zipfile.ZipFile(io.BytesIO(predecessor_portfolio_raw)) as archive:
            predecessor_status = strict_loads(archive.read("PORTFOLIO-STATUS.json"))
        require(predecessor_status.get("status_root") == expected_status_root
                and predecessor_status.get("ready_for_stage_i3_shadow_planning") is True
                and predecessor_status.get("stage_i3_shadow_authorized") is False,
                "STAGE_I3_PREDECESSOR_STATUS_INVALID")
        status = self.status()
        require(status["ready_for_stage_i3_shadow_planning"] is True
                and status["stage_i3_shadow_authorized"] is False,
                "STAGE_I3_PORTFOLIO_NOT_READY")
        preflight = self.composition_preflight()
        stage1_rows = {row["application_id"]: row for row in status["applications"]}
        outputs = []
        for index, application in enumerate(self.roster()["applications"], 1):
            application_id = application["id"]
            row = stage1_rows[application_id]
            relations = [deepcopy(edge) for edge in preflight["edges"]
                         if edge["consumer_application_id"] == application_id
                         and edge["status"] == "MATCHED"]
            value = build_stage3_instruction(
                application=application,
                pipeline_release_sha256=pipeline_release_sha256,
                predecessor_portfolio_sha256=predecessor_portfolio_sha256,
                portfolio_status_root=expected_status_root,
                preflight_root=preflight["preflight_root"],
                court_root=status["correspondence_court_root"],
                court_evidence_sha256=status["correspondence_court_artifact_sha256"],
                stage_i1_artifact_sha256=row["artifact_sha256"],
                stage_i2_artifact_sha256=row["stage_i2_artifact_sha256"],
                stage_i1_status=row["stage_i1_status"], matched_relations=relations)
            raw = canonical_bytes(value)
            artifact_sha256, cas_path = self._store_cas_object(raw, ".json")
            prefix = f"{event_id_prefix}:{index:02d}:{application_id}"
            receipt = self._record(action="ISSUE_STAGE_I3_SHADOW_INSTRUCTION",
                application_id=application_id, artifact_sha256=artifact_sha256,
                details={"instruction_root": value["instruction_root"],
                         "pipeline_release_sha256": pipeline_release_sha256,
                         "predecessor_portfolio_sha256": predecessor_portfolio_sha256,
                         "matched_relation_count": len(relations), "mode": "PLAN_ONLY",
                         "stage_i3_shadow_authorized": False},
                event_id_prefix=prefix)
            outputs.append({"application_id": application_id, "instruction": value,
                            "template": plan_template(value), "receipt": receipt,
                            "cas": {"algorithm": "sha256", "digest": artifact_sha256,
                                    "path": cas_path.relative_to(self.workspace).as_posix(),
                                    "status": "STORED_VERIFIED"}})
        return outputs

    def import_stage3_plan(self, raw: bytes, *, event_id_prefix: str) -> dict[str, Any]:
        """Import a session-authored plan without authorizing its execution."""
        require(type(raw) is bytes, "STAGE_I3_PLAN_BYTES_INVALID")
        value = strict_loads(raw)
        require(type(value) is dict and type(value.get("application_id")) is str,
                "STAGE_I3_PLAN_INVALID")
        application_id = value["application_id"]
        self._application(application_id)
        issued = self._latest_operation(application_id,
                                        "ISSUE_STAGE_I3_SHADOW_INSTRUCTION")
        require(issued is not None, "STAGE_I3_INSTRUCTION_MISSING")
        instruction_path = self._cas_path(issued["artifact_sha256"], ".json")
        require(instruction_path.is_file(), "STAGE_I3_INSTRUCTION_CAS_MISSING")
        checked = validate_plan(value,
            expected_instruction=strict_loads(instruction_path.read_bytes()))
        canonical = canonical_bytes(checked)
        artifact_sha256, cas_path = self._store_cas_object(raw, ".json")
        revision = 1 + len([row for row in self._operations(application_id)
                            if row["portfolio_action"] == "IMPORT_STAGE_I3_SHADOW_PLAN"])
        receipt = self._record(action="IMPORT_STAGE_I3_SHADOW_PLAN",
            application_id=application_id, artifact_sha256=artifact_sha256,
            details={"plan_root": checked["plan_root"],
                     "instruction_root": checked["instruction_root"],
                     "plan_status": checked["plan_status"],
                     "capability_projection_count": len(checked["capability_projections"]),
                     "correspondence_case_count": len(checked["correspondence_cases"]),
                     "hold_count": len(checked["holds"]),
                     "canonical_sha256": _sha(canonical),
                     "input_canonical": raw == canonical, "revision": revision,
                     "stage_i3_shadow_authorized": False,
                     "composition_authorized": False},
            event_id_prefix=event_id_prefix)
        return {**receipt, "stage_i3": checked, "revision": revision,
                "cas": {"algorithm": "sha256", "digest": artifact_sha256,
                        "path": cas_path.relative_to(self.workspace).as_posix(),
                        "status": "STORED_VERIFIED"}}

    def composition_preflight(self) -> dict[str, Any]:
        """Derive I2 preflight only from the latest journaled CAS objects."""
        bundle_raws = []
        declarations = []
        for application in self.roster()["applications"]:
            stage1 = self._latest_operation(application["id"], "IMPORT_STAGE_I1")
            require(stage1 is not None, "PORTFOLIO_COMPOSITION_STAGE_I1_MISSING")
            stage1_path = self._cas_path(stage1["artifact_sha256"], ".zip")
            require(stage1_path.is_file(), "PORTFOLIO_COMPOSITION_STAGE_I1_CAS_MISSING")
            bundle_raws.append(stage1_path.read_bytes())
            stage2 = self._latest_operation(application["id"], "IMPORT_STAGE_I2")
            if stage2 is not None:
                stage2_path = self._cas_path(stage2["artifact_sha256"], ".json")
                require(stage2_path.is_file(), "PORTFOLIO_COMPOSITION_STAGE_I2_CAS_MISSING")
                declarations.append(strict_loads(stage2_path.read_bytes()))
        return build_preflight_from_bytes(bundle_raws, declarations)

    def status(self) -> dict[str, Any]:
        roster = self.roster()
        events = self.journal.verify()
        rows = []
        for app in roster["applications"]:
            operations = [event["payload"]["operation"]
                          for event in events if event["event_type"] == "OPERATION_PLANNED"
                          and event["payload"]["operation"].get("application_id") == app["id"]]
            actions = [operation["portfolio_action"] for operation in operations]
            imports = [operation for operation in operations
                       if operation["portfolio_action"] == "IMPORT_STAGE_I1"]
            current = imports[-1] if imports else None
            cas_status = ("STORED_VERIFIED" if current is not None
                          and self._verify_cas_object(current["artifact_sha256"])
                          else "MISSING" if current is not None else "NOT_APPLICABLE")
            thr_status = (current["details"].get("thr_status", "NOT_PRESENT_LEGACY")
                          if current is not None else "NOT_APPLICABLE")
            stage2_imports = [operation for operation in operations
                              if operation["portfolio_action"] == "IMPORT_STAGE_I2"]
            stage2 = stage2_imports[-1] if stage2_imports else None
            stage2_cas = ("STORED_VERIFIED" if stage2 is not None
                          and self._verify_cas_object(stage2["artifact_sha256"], ".json")
                          else "MISSING" if stage2 is not None else "NOT_APPLICABLE")
            stage3_instructions = [operation for operation in operations
                if operation["portfolio_action"] == "ISSUE_STAGE_I3_SHADOW_INSTRUCTION"]
            stage3_instruction = stage3_instructions[-1] if stage3_instructions else None
            stage3_instruction_cas = ("STORED_VERIFIED" if stage3_instruction is not None
                and self._verify_cas_object(stage3_instruction["artifact_sha256"], ".json")
                else "MISSING" if stage3_instruction is not None else "NOT_APPLICABLE")
            stage3_plans = [operation for operation in operations
                if operation["portfolio_action"] == "IMPORT_STAGE_I3_SHADOW_PLAN"]
            stage3_plan = stage3_plans[-1] if stage3_plans else None
            stage3_plan_cas = ("STORED_VERIFIED" if stage3_plan is not None
                and self._verify_cas_object(stage3_plan["artifact_sha256"], ".json")
                else "MISSING" if stage3_plan is not None else "NOT_APPLICABLE")
            rows.append({"application_id": app["id"],
                         "intake": "BOUND" if "RECORD_INTAKE" in actions else "PENDING",
                         "instruction": "DELIVERED" if "DELIVER_INSTRUCTION" in actions else "PENDING",
                         "stage_i1": "IMPORTED" if current is not None else "PENDING",
                         "stage_i1_status": (current["details"]["stage_i1_status"]
                                             if current is not None else None),
                         "artifact_sha256": (current["artifact_sha256"]
                                             if current is not None else None),
                         "cas": cas_status,
                         "thr": thr_status,
                         "stage_i2": "IMPORTED" if stage2 is not None else "PENDING",
                         "stage_i2_revision": (stage2["details"]["revision"]
                                               if stage2 is not None else None),
                         "stage_i2_artifact_sha256": (stage2["artifact_sha256"]
                                                     if stage2 is not None else None),
                         "stage_i2_cas": stage2_cas,
                         "stage_i3_instruction": ("ISSUED" if stage3_instruction else "PENDING"),
                         "stage_i3_instruction_sha256": (stage3_instruction["artifact_sha256"]
                                                         if stage3_instruction else None),
                         "stage_i3_instruction_cas": stage3_instruction_cas,
                         "stage_i3_plan": ("IMPORTED" if stage3_plan else "PENDING"),
                         "stage_i3_plan_status": (stage3_plan["details"]["plan_status"]
                                                  if stage3_plan else None),
                         "stage_i3_plan_sha256": (stage3_plan["artifact_sha256"]
                                                  if stage3_plan else None),
                         "stage_i3_plan_cas": stage3_plan_cas})
        stage1_ready = all(row["stage_i1"] == "IMPORTED"
                           and row["cas"] == "STORED_VERIFIED"
                           and row["thr"] == "PASS_SEPARATED" for row in rows)
        preflight = self.composition_preflight() if stage1_ready else None
        court_rows = [operation for operation in self._operations()
                      if operation["portfolio_action"] == "IMPORT_CORRESPONDENCE_COURT"]
        court = court_rows[-1] if court_rows else None
        court_cas = ("STORED_VERIFIED" if court is not None
                     and self._verify_cas_object(court["artifact_sha256"], ".zip")
                     else "MISSING" if court is not None else "NOT_APPLICABLE")
        shadow_ready = bool(preflight is not None and court is not None
                            and court_cas == "STORED_VERIFIED"
                            and court["details"]["court_status"] == "PASS"
                            and court["details"]["preflight_root"] == preflight["preflight_root"])
        instructions_complete = all(row["stage_i3_instruction"] == "ISSUED"
                                    and row["stage_i3_instruction_cas"] == "STORED_VERIFIED"
                                    for row in rows)
        plans_complete = all(row["stage_i3_plan"] == "IMPORTED"
                             and row["stage_i3_plan_cas"] == "STORED_VERIFIED"
                             for row in rows)
        body = {"schema": "mosaic.ucm.integration-portfolio-status.v0.4",
                "portfolio_id": roster["portfolio_id"],
                "fixed_workflow_denominator": len(rows),
                "applications": rows,
                "journal_head": self.journal.head(),
                "ready_for_composition": stage1_ready,
                "composition_preflight_status": (preflight["status"] if preflight else
                                                 "STAGE_I1_REQUIRED"),
                "composition_preflight_root": (preflight["preflight_root"] if preflight else None),
                "correspondence_court": ("IMPORTED" if court is not None else "PENDING"),
                "correspondence_court_claim": (court["details"]["claim"] if court else None),
                "correspondence_court_root": (court["details"]["court_root"] if court else None),
                "correspondence_court_artifact_sha256": (court["artifact_sha256"]
                                                          if court else None),
                "correspondence_court_cas": court_cas,
                "ready_for_stage_i3_shadow_planning": shadow_ready,
                "stage_i3_instruction_denominator_complete": instructions_complete,
                "stage_i3_plan_denominator_complete": plans_complete,
                "ready_for_stage_i3_shadow_review": plans_complete,
                "stage_i3_shadow_authorized": False,
                "composition_authorized": False,
                **BOUNDARY}
        return {**body, "status_root": root(body)}
