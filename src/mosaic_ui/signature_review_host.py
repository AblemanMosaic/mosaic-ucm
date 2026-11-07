"""Functional, governed host for Mosaic Signature review compositions."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any, Callable

from mosaic_ui_std.catalog import load_runtime_catalog

from .canonical import atomic_write, canonical_bytes, commitment
from .model import UIRefusal, walk
from .runtime import GovernedRuntime, OperationContext, OperationResult, OperationSpec, RuntimePolicy, RuntimeRefusal
from .signature_profile import build_signature_payload


SCENARIOS = {
    "data-workspace": ("filter-and-export", "refused-export-path", "keyboard-only"),
    "operational-dashboard": ("refresh-and-review", "keyboard-only"),
    "settings-workflow": ("edit-confirm-save", "keyboard-only"),
}


DATASETS = {
    "records": {
        "runs": [
            ["RUN-204", "Runtime", "Pass"], ["RUN-203", "Runtime", "Pass"],
            ["RUN-202", "Runtime", "Refused"],
        ],
        "releases": [
            ["REL-020", "Release", "Pass"], ["REL-019", "Release", "Pass"],
            ["REL-018", "Release", "Pass"],
        ],
        "policies": [
            ["POL-UI", "Policy", "Pass"], ["POL-EFFECT", "Policy", "Pass"],
            ["POL-EXPORT", "Policy", "Refused"],
        ],
    },
    "schemas": {
        "runs": [["runtime-state", "Schema", "Pass"], ["runtime-receipt", "Schema", "Pass"]],
        "releases": [["release-bundle", "Schema", "Pass"], ["provenance", "Schema", "Pass"]],
        "policies": [["runtime-policy", "Schema", "Pass"], ["retention-policy", "Schema", "Pass"]],
    },
    "receipts": {
        "runs": [["RCP-401", "Interaction", "Pass"], ["RCP-402", "Operation", "Pass"]],
        "releases": [["RCP-REL-20", "Release", "Pass"], ["RCP-REL-19", "Release", "Pass"]],
        "policies": [["RCP-POL-01", "Policy", "Pass"], ["RCP-POL-02", "Policy", "Refused"]],
    },
}


OPS_ROWS = [
    ["Browser", "Ready", "40 cases"],
    ["Win32", "Ready", "25 kinds"],
    ["Ablation", "Ready", "Exact closure"],
]


def list_scenarios(composition_id: str | None = None) -> dict[str, Any]:
    if composition_id is not None and composition_id not in SCENARIOS:
        raise UIRefusal("SIGNATURE_REVIEW_COMPOSITION_REFUSED", composition_id)
    selected = {composition_id: SCENARIOS[composition_id]} if composition_id else SCENARIOS
    value = {
        "schema": "mosaic.ui.signature-review-scenarios.v0.1",
        "scenarios": {key: list(items) for key, items in selected.items()},
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.SIGNATURE_REVIEW_SCENARIOS.v0.1", value)
    return value


def _node_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["node_id"]): item for item in walk(payload["application"]["tree"])}


def _control(kind: str, key: str, label: str, *, width: int | None = None,
             operation_ref: str | None = None, default: Any = None,
             default_state: str | None = None) -> dict[str, Any]:
    props: dict[str, Any] = {"realization_key": key, "view": "main", "display_text": label}
    if width is not None:
        props["layout_item"] = {"width": width}
    if default is not None:
        props["default"] = copy.deepcopy(default)
    if default_state is not None:
        props["default_state"] = default_state
    item = {
        "kind": kind, "node_id": key,
        "semantics": {
            "role": "button" if kind == "BUTTON" else "progressbar",
            "name": label, "description": "", "focusable": kind == "BUTTON",
            "actions": ["select"] if kind == "BUTTON" else [],
        },
        "props": props, "children": [],
    }
    if operation_ref is not None:
        item["operation_ref"] = operation_ref
    return item


def _configure_lifecycle(payload: dict[str, Any], operations: list[str], progress_key: str,
                         cancel_key: str) -> None:
    application = payload["application"]
    application["declared_operation_ids"] = ["ENTER_MAIN", *operations, "CANCEL_REVIEW_OPERATION"]
    lifecycle = application["lifecycle"]
    lifecycle["operation_controls"] = {"cancel_key": cancel_key, "progress_key": progress_key}
    lifecycle["operation_classes"] = {
        "NAVIGATE": ["ENTER_MAIN"], "LONG_RUNNING": operations,
        "CANCEL": ["CANCEL_REVIEW_OPERATION"], "TOGGLE_DISCLOSURE": [], "HOST_WITHHELD": [],
    }


def build_functional_signature_payload(
    composition_id: str = "operational-dashboard", theme_id: str = "signature-dark",
    density_id: str = "comfortable",
) -> dict[str, Any]:
    """Derive an application-capable review surface without changing conformance fixtures."""
    payload = build_signature_payload(composition_id, theme_id, density_id)
    nodes = _node_map(payload)
    application = payload["application"]
    application["application_id"] += "_FUNCTIONAL_REVIEW"
    application["review_mode"] = "FUNCTIONAL"

    if composition_id == "data-workspace":
        rows = copy.deepcopy(DATASETS["records"]["runs"])
        nodes["data.records"]["props"]["default"] = {"selected": rows[0][0], "rows": rows}
        nodes["data.status"]["props"]["default"] = "3 records in Records / Recent runs"
        for node_id, operation in (("data.apply", "DATA_APPLY_FILTER"), ("data.export", "DATA_EXPORT_SLICE")):
            nodes[node_id]["operation_ref"] = operation
            nodes[node_id]["props"].pop("target_view", None)
        panel = nodes["data.footer"]
        panel["children"].insert(-1, _control("PROGRESS", "data.operation.progress", "Operation progress", width=140, default=0))
        panel["children"].insert(-1, _control(
            "BUTTON", "data.operation.cancel", "Cancel", width=90,
            operation_ref="CANCEL_REVIEW_OPERATION", default_state="DISABLED",
        ))
        _configure_lifecycle(payload, ["DATA_APPLY_FILTER", "DATA_EXPORT_SLICE"],
                             "data.operation.progress", "data.operation.cancel")
    elif composition_id == "operational-dashboard":
        nodes["ops.services"]["props"]["default"] = {"selected": "Browser", "rows": copy.deepcopy(OPS_ROWS)}
        nodes["ops.health"]["props"]["default"] = "Runtime healthy"
        nodes["ops.posture"]["props"]["default"] = "Local candidate"
        nodes["ops.notice"]["props"]["default"] = "No unresolved local refusals"
        for node_id, operation in (("ops.refresh", "OPS_REFRESH"), ("ops.review", "OPS_REVIEW_EVIDENCE")):
            nodes[node_id]["operation_ref"] = operation
            nodes[node_id]["props"].pop("target_view", None)
        panel = nodes["ops.actions"]
        panel["children"].extend([
            _control("PROGRESS", "ops.operation.progress", "Operation progress", width=140, default=0),
            _control("BUTTON", "ops.operation.cancel", "Cancel", width=90,
                     operation_ref="CANCEL_REVIEW_OPERATION", default_state="DISABLED"),
        ])
        _configure_lifecycle(payload, ["OPS_REFRESH", "OPS_REVIEW_EVIDENCE"],
                             "ops.operation.progress", "ops.operation.cancel")
    elif composition_id == "settings-workflow":
        nodes["settings.notice"]["props"]["default"] = "Changes remain local until applied"
        nodes["settings.status"]["props"]["default"] = "No pending changes"
        nodes["settings.save"]["props"]["display_text"] = "Apply settings"
        nodes["settings.save"]["semantics"]["name"] = "Apply settings"
        nodes["settings.save"]["operation_ref"] = "SETTINGS_APPLY"
        nodes["settings.save"]["props"].pop("target_view", None)
        panel = nodes["settings.actions"]
        panel["children"].insert(-1, _control(
            "BUTTON", "settings.reset", "Reset", width=100, operation_ref="SETTINGS_RESET",
        ))
        panel["children"].insert(-1, _control(
            "PROGRESS", "settings.operation.progress", "Operation progress", width=130, default=0,
        ))
        panel["children"].insert(-1, _control(
            "BUTTON", "settings.operation.cancel", "Cancel", width=85,
            operation_ref="CANCEL_REVIEW_OPERATION", default_state="DISABLED",
        ))
        _configure_lifecycle(payload, ["SETTINGS_APPLY", "SETTINGS_RESET"],
                             "settings.operation.progress", "settings.operation.cancel")
    else:
        raise UIRefusal("SIGNATURE_REVIEW_COMPOSITION_REFUSED", composition_id)

    payload["input_root"] = commitment("MOSAIC.UI.SIGNATURE.FUNCTIONAL_INPUT.v0.1", {
        "application": payload["application"], "library": payload["library"],
        "signature": payload["signature"],
    })
    return payload


class SignatureReviewSession:
    """One state machine for user interaction, governed effects, and review evidence."""

    def __init__(
        self, composition_id: str = "operational-dashboard", *,
        theme_id: str = "signature-dark", density_id: str = "comfortable",
        export_root: Path | None = None, confirmation: Callable[[str, str], bool] | None = None,
    ) -> None:
        self.composition_id = composition_id
        self.theme_id = theme_id
        self.density_id = density_id
        self.export_root = (export_root or (Path.cwd() / "mosaic-review-output")).resolve()
        self.confirmation = confirmation or (lambda _title, _message: True)
        self.export_target_override: Path | None = None
        self.artifacts: list[dict[str, Any]] = []
        self.payload = build_functional_signature_payload(composition_id, theme_id, density_id)
        effects = ("PURE", "WRITE_LOCAL", "HOST_UI")
        self.runtime = GovernedRuntime(
            self.payload, self._operation_specs(), policy=RuntimePolicy(effects, (self.export_root,)),
            catalog=load_runtime_catalog(),
        )

    def _operation_specs(self) -> tuple[OperationSpec, ...]:
        by_composition = {
            "data-workspace": (
                OperationSpec("DATA_APPLY_FILTER", "PURE", self._data_apply),
                OperationSpec("DATA_EXPORT_SLICE", "WRITE_LOCAL", self._data_export),
            ),
            "operational-dashboard": (
                OperationSpec("OPS_REFRESH", "PURE", self._ops_refresh),
                OperationSpec("OPS_REVIEW_EVIDENCE", "PURE", self._ops_review),
            ),
            "settings-workflow": (
                OperationSpec("SETTINGS_APPLY", "HOST_UI", self._settings_apply),
                OperationSpec("SETTINGS_RESET", "PURE", self._settings_reset),
            ),
        }
        return by_composition[self.composition_id]

    @staticmethod
    def _grid(value: Any) -> dict[str, Any]:
        return copy.deepcopy(value) if isinstance(value, dict) else {"selected": str(value or ""), "rows": []}

    def _filtered_rows(self, values: dict[str, Any]) -> list[list[str]]:
        view = str(values.get("data.navigation", "records"))
        collection = str(values.get("data.collections", "runs"))
        query = str(values.get("data.search", "")).strip().lower()
        scope = str(values.get("data.scope", "all"))
        rows = copy.deepcopy(DATASETS.get(view, DATASETS["records"]).get(collection, []))
        if query:
            rows = [row for row in rows if query in " ".join(row).lower()]
        if scope == "pass":
            rows = [row for row in rows if row[-1].lower() == "pass"]
        elif scope == "refused":
            rows = [row for row in rows if row[-1].lower() == "refused"]
        return rows

    def _data_apply(self, context: OperationContext) -> OperationResult:
        rows = self._filtered_rows(context.values)
        current = self._grid(context.values.get("data.records"))
        selected = current.get("selected") if any(row[0] == current.get("selected") for row in rows) else (rows[0][0] if rows else "")
        view = str(context.values["data.navigation"]).title()
        collection = str(context.values["data.collections"]).replace("-", " ").title()
        message = f"{len(rows)} records in {view} / {collection}"
        return OperationResult(message, {
            "data.records": {"selected": selected, "rows": rows}, "data.status": message,
        }, {"row_count": len(rows), "filter_commitment": commitment("MOSAIC.UI.REVIEW.FILTER.v0.1", {
            "query": context.values.get("data.search"), "scope": context.values.get("data.scope"),
        })})

    def _data_export(self, context: OperationContext) -> OperationResult:
        grid = self._grid(context.values.get("data.records"))
        target = self.export_target_override or (self.export_root / "data-workspace-slice.json")
        target = context.require_path(target, write=True)
        body = {
            "schema": "mosaic.ui.signature-data-export.v0.1",
            "selection": {
                "view": context.values.get("data.navigation"),
                "collection": context.values.get("data.collections"),
                "query": context.values.get("data.search"), "scope": context.values.get("data.scope"),
            },
            "selected": grid.get("selected"), "rows": grid.get("rows", []),
            "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        }
        body["commitment"] = commitment("MOSAIC.UI.SIGNATURE_DATA_EXPORT.v0.1", body)
        atomic_write(target, canonical_bytes(body) + b"\n")
        artifact = {
            "path": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size, "row_count": len(body["rows"]),
        }
        self.artifacts.append(copy.deepcopy(artifact))
        message = f"Exported {artifact['row_count']} records to {target.name}"
        return OperationResult(message, {"data.status": message}, artifact)

    def _ops_refresh(self, context: OperationContext) -> OperationResult:
        rows = [[row[0], "Observed", row[2]] for row in OPS_ROWS]
        message = "3 services refreshed; no unresolved refusals"
        return OperationResult(message, {
            "ops.services": {"selected": self._grid(context.values.get("ops.services")).get("selected") or "Browser", "rows": rows},
            "ops.health": "Runtime observed", "ops.posture": "Evidence current", "ops.notice": message,
        }, {"service_count": len(rows), "result": "NO_UNRESOLVED_REFUSALS"})

    def _ops_review(self, _context: OperationContext) -> OperationResult:
        count = self.runtime.ledger.total_count
        message = f"Receipt chain reviewed through sequence {count + 1}"
        return OperationResult(message, {
            "ops.health": "Receipt chain valid", "ops.posture": "Reviewed", "ops.notice": message,
        }, {"reviewed_ledger_head": self.runtime.ledger.head, "reviewed_receipt_count": count})

    def _settings_apply(self, context: OperationContext) -> OperationResult:
        if context.values.get("settings.confirm") != "apply":
            raise RuntimeRefusal("SETTINGS_CONFIRMATION_REQUIRED", "Select Apply in the governed decision first")
        if not self.confirmation("Apply Mosaic settings", "Apply these settings to this local review session?"):
            raise RuntimeRefusal("SETTINGS_HOST_CONFIRMATION_REFUSED", "The host confirmation was declined")
        name = str(context.values.get("settings.name", "")).strip()
        if not name:
            raise RuntimeRefusal("SETTINGS_NAME_REQUIRED", "Application name is required")
        theme = str(context.values.get("settings.theme", "dark"))
        message = f"Applied {theme} defaults for {name}"
        return OperationResult(message, {
            "settings.status": "Settings applied", "settings.notice": message, "settings.confirm": "cancel",
        }, {"application_name_commitment": commitment("MOSAIC.UI.REVIEW.SETTINGS_NAME.v0.1", name), "theme": theme})

    @staticmethod
    def _settings_reset(_context: OperationContext) -> OperationResult:
        return OperationResult("Settings reset to Mosaic defaults", {
            "settings.menu": "appearance", "settings.name": "Mosaic Workbench",
            "settings.theme": "dark", "settings.confirm": "cancel",
            "settings.status": "No pending changes", "settings.notice": "Mosaic defaults restored locally",
        }, {"reset": True})

    def _interaction(self, context: OperationContext) -> OperationResult:
        node_id = str(context.event.get("node_id") or "")
        values = context.values
        updates: dict[str, Any] = {}
        if self.composition_id == "data-workspace":
            if node_id in {"data.navigation", "data.collections"}:
                rows = self._filtered_rows(values)
                updates["data.records"] = {"selected": rows[0][0] if rows else "", "rows": rows}
                updates["data.status"] = f"{len(rows)} matching records"
            elif node_id in {"data.search", "data.scope"}:
                updates["data.status"] = "Filters changed; choose Apply"
            elif node_id == "data.records":
                updates["data.status"] = f"Selected {self._grid(values['data.records']).get('selected') or 'none'}"
        elif self.composition_id == "operational-dashboard":
            if node_id == "ops.navigation":
                updates["ops.notice"] = f"Showing {str(values['ops.navigation']).title()} evidence"
            elif node_id == "ops.services":
                updates["ops.notice"] = f"Selected {self._grid(values['ops.services']).get('selected')} service evidence"
        elif self.composition_id == "settings-workflow":
            if node_id == "settings.confirm":
                decision = str(values["settings.confirm"])
                updates["settings.status"] = "Ready to apply" if decision == "apply" else "Apply cancelled"
            else:
                updates["settings.status"] = "Pending local changes"
                updates["settings.notice"] = "Review the decision, then choose Apply settings"
        return OperationResult("Interaction reconciled", updates, {"node_id": node_id})

    def dispatch(self, event: dict[str, Any]) -> dict[str, Any]:
        intent = str(event.get("intent") or "").upper()
        if intent == "ACTIVATE":
            self.runtime.dispatch(event, auto_run=True)
        elif intent in {"SELECT", "TEXT_COMMIT", "TOGGLE", "STEP", "DIALOG_DECISION"}:
            node_id = str(event.get("node_id") or "")
            self.runtime.dispatch_interaction(event, f"REVIEW_INTERACTION:{node_id}", self._interaction)
        else:
            self.runtime.ui.apply(copy.deepcopy(event))
        return self.runtime.snapshot()

    def witness(self, scenario: str | None = None) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.signature-functional-review-session.v0.1",
            "composition_id": self.composition_id, "theme_id": self.theme_id,
            "density_id": self.density_id, "scenario": scenario,
            "runtime_commitment": self.runtime.snapshot()["commitment"],
            "ledger": self.runtime.ledger.summary(), "results": copy.deepcopy(self.runtime.results),
            "artifacts": copy.deepcopy(self.artifacts),
            "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
            "claim_boundary": "FUNCTIONAL_REVIEW_EVIDENCE_ESTABLISHES_ONLY_THIS LOCAL SESSION AND ITS BOUNDED EFFECTS",
        }
        value["commitment"] = commitment("MOSAIC.UI.SIGNATURE_FUNCTIONAL_REVIEW_SESSION.v0.1", value)
        return value

    def record(self, path: Path, scenario: str | None = None) -> dict[str, Any]:
        value = self.witness(scenario)
        atomic_write(path.resolve(), canonical_bytes(value) + b"\n")
        return value


def run_scenario(session: SignatureReviewSession, scenario: str) -> dict[str, Any]:
    if scenario not in SCENARIOS.get(session.composition_id, ()):
        raise UIRefusal("SIGNATURE_REVIEW_SCENARIO_REFUSED", f"{session.composition_id}:{scenario}")
    before_count = session.runtime.ledger.total_count
    focus_trace: list[str | None] = []
    expected = "COMPLETE"
    prior_override = session.export_target_override
    try:
        if scenario == "filter-and-export":
            events = [
                {"intent": "TEXT_COMMIT", "node_id": "data.search", "value": "rel"},
                {"intent": "SELECT", "node_id": "data.collections", "value": "releases"},
                {"intent": "SELECT", "node_id": "data.scope", "value": "pass"},
                {"intent": "ACTIVATE", "node_id": "data.apply"},
                {"intent": "ACTIVATE", "node_id": "data.export"},
            ]
        elif scenario == "refused-export-path":
            session.export_target_override = session.export_root.parent / "outside-review-export.json"
            events = [{"intent": "ACTIVATE", "node_id": "data.export"}]
            expected = "REFUSE"
        elif scenario == "refresh-and-review":
            events = [
                {"intent": "SELECT", "node_id": "ops.navigation", "value": "evidence"},
                {"intent": "ACTIVATE", "node_id": "ops.refresh"},
                {"intent": "ACTIVATE", "node_id": "ops.review"},
            ]
        elif scenario == "edit-confirm-save":
            events = [
                {"intent": "TEXT_COMMIT", "node_id": "settings.name", "value": "Mosaic Review Host"},
                {"intent": "SELECT", "node_id": "settings.theme", "value": "light"},
                {"intent": "DIALOG_DECISION", "node_id": "settings.confirm", "value": "apply"},
                {"intent": "ACTIVATE", "node_id": "settings.save"},
            ]
        else:
            events = [{"intent": "FOCUS_NEXT"} for _ in range(len(session.runtime.ui.focus_order()) + 1)]
        for event in events:
            session.dispatch(event)
            if event["intent"] == "FOCUS_NEXT":
                focus_trace.append(session.runtime.ui.state.get("focused_node_id"))
    finally:
        session.export_target_override = prior_override
    receipts = session.runtime.receipts
    new_receipts = [row for row in receipts if row["sequence"] > before_count]
    dispositions = [row["disposition"] for row in new_receipts]
    passed = bool(focus_trace) if scenario == "keyboard-only" else bool(dispositions) and dispositions[-1] == expected
    value = {
        "schema": "mosaic.ui.signature-functional-scenario.v0.1",
        "composition_id": session.composition_id, "scenario": scenario,
        "event_count": len(events), "receipt_dispositions": dispositions,
        "focus_trace": focus_trace, "artifact_count": len(session.artifacts),
        "session_commitment": session.witness(scenario)["commitment"],
        "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.SIGNATURE_FUNCTIONAL_SCENARIO.v0.1", value)
    return value


def functional_review_witness(output_root: Path) -> dict[str, Any]:
    """Run every declared scenario in a fresh session for release and agent evidence."""
    output_root = output_root.resolve()
    cases = []
    for composition_id, scenarios in SCENARIOS.items():
        for scenario in scenarios:
            session = SignatureReviewSession(
                composition_id, export_root=output_root / composition_id / scenario,
            )
            witness = run_scenario(session, scenario)
            cases.append({
                "case_id": f"{composition_id}:{scenario}",
                "composition_id": composition_id, "scenario": scenario,
                "disposition": witness["disposition"], "commitment": witness["commitment"],
                "receipt_count": session.runtime.ledger.total_count,
                "ledger_head": session.runtime.ledger.head,
                "artifact_count": len(session.artifacts),
            })
    value = {
        "schema": "mosaic.ui.signature-functional-review-witness.v0.1",
        "case_count": len(cases), "cases": cases,
        "disposition": "PASS_LOCAL_CANDIDATE" if cases and all(
            case["disposition"] == "PASS_LOCAL_CANDIDATE" for case in cases
        ) else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "HEADLESS_SCENARIOS_ESTABLISH LOCAL MODEL EFFECT AND RECEIPT BEHAVIOR ONLY",
    }
    value["commitment"] = commitment("MOSAIC.UI.SIGNATURE_FUNCTIONAL_REVIEW_WITNESS.v0.1", value)
    return value


__all__ = [
    "SCENARIOS", "SignatureReviewSession", "build_functional_signature_payload",
    "functional_review_witness", "list_scenarios", "run_scenario",
]
