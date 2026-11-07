"""Reference Pippi sidecar persistence over the canonical campaign journal.

This adapter records observable turns and read-only governance artifacts.  It
does not call a model, dispatch tools, execute effects, or grant authority.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from uclop.canonical import canonical_bytes, exact_keys, require, root, strict_loads

from .amcas import BOUNDARY
from .constitutional_launcher import STATE_SCHEMA as LAUNCH_STATE_SCHEMA
from .development_observatory import build_development_observatory, project_development_observatory
from .development_standards import EVALUATION_SCHEMA
from .journal import CampaignJournal
from .pippi import (
    EXCEPTION_SCHEMA,
    effective_integration_mode,
    validate_human_projection,
    validate_model_draft,
    validate_pippi_context,
    validate_pippi_decision,
    validate_turn_envelope,
)


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            __import__("os").fsync(stream.fileno())
    except FileExistsError as error:
        raise ValueError("PIPPI_OUTPUT_EXISTS") from error


def _rooted_record(value: Any, *, schema: str, root_field: str, code: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == schema, code)
    item = deepcopy(value)
    body = {key: deepcopy(row) for key, row in item.items() if key != root_field}
    require(item.get(root_field) == root(body), code)
    return item


class PippiCampaign:
    """Persist a deterministic, observable Pippi session without hidden effects."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)
        self.context_path = self.workspace / "PIPPI-CONTEXT.json"
        self.journal = CampaignJournal(self.workspace / "journal")

    @classmethod
    def create(cls, workspace: Path, context: Any) -> "PippiCampaign":
        context = validate_pippi_context(context)
        campaign = cls(workspace)
        require(not campaign.workspace.exists(), "PIPPI_WORKSPACE_EXISTS")
        campaign.workspace.mkdir(parents=True)
        _write_new(campaign.context_path, context)
        campaign.journal.initialize()
        campaign.journal.append(event_id="pippi-session-created",
            event_type="PIPPI_SESSION_CREATED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"context": context, "context_root": context["context_root"],
                     "integration_mode": effective_integration_mode(context)})
        return campaign

    def context(self) -> dict[str, Any]:
        try:
            value = strict_loads(self.context_path.read_bytes())
        except OSError as error:
            raise ValueError("PIPPI_CONTEXT_UNREADABLE") from error
        return validate_pippi_context(value)

    def _events(self) -> list[dict[str, Any]]:
        return self.journal.verify_read_only()

    def record_turn(self, *, context: Any, draft: Any, decision: Any, projection: Any,
                    turn: Any, event_id: str) -> dict[str, Any]:
        context = validate_pippi_context(context)
        require(context == self.context(), "PIPPI_CONTEXT_DRIFT")
        draft = validate_model_draft(draft)
        decision = validate_pippi_decision(decision, draft=draft)
        projection = validate_human_projection(projection, draft=draft, decision=decision)
        turn = validate_turn_envelope(turn, context=context, draft=draft,
                                      decision=decision, projection=projection)
        existing_turns = [event["payload"]["turn"] for event in self._events()
                          if event["event_type"] == "PIPPI_TURN_RECORDED"]
        expected_sequence = len(existing_turns) + 1
        expected_previous = existing_turns[-1]["turn_root"] if existing_turns else None
        require(turn["sequence"] == expected_sequence
                and turn["previous_turn_root"] == expected_previous,
                "PIPPI_TURN_CHAIN_INVALID")
        event = self.journal.append(event_id=event_id, event_type="PIPPI_TURN_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"context_root": context["context_root"], "draft": draft,
                     "decision": decision, "projection": projection, "turn": turn})
        return {"turn_root": turn["turn_root"], "journal_event_root": event["event_root"],
                **BOUNDARY}

    def record_standards(self, evaluation: Any, *, event_id: str) -> dict[str, Any]:
        evaluation = _rooted_record(evaluation, schema=EVALUATION_SCHEMA,
                                    root_field="evaluation_root",
                                    code="PIPPI_STANDARDS_INVALID")
        event = self.journal.append(event_id=event_id, event_type="PIPPI_STANDARDS_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"evaluation": evaluation})
        return {"evaluation_root": evaluation["evaluation_root"],
                "journal_event_root": event["event_root"], **BOUNDARY}

    def record_launch_state(self, state: Any, *, event_id: str) -> dict[str, Any]:
        state = _rooted_record(state, schema=LAUNCH_STATE_SCHEMA,
                               root_field="launch_state_root",
                               code="PIPPI_LAUNCH_STATE_INVALID")
        event = self.journal.append(event_id=event_id,
            event_type="PIPPI_LAUNCH_STATE_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"launch_state": state})
        return {"launch_state_root": state["launch_state_root"],
                "journal_event_root": event["event_root"], **BOUNDARY}

    def record_exception(self, exception: Any, *, event_id: str) -> dict[str, Any]:
        exception = _rooted_record(exception, schema=EXCEPTION_SCHEMA,
                                   root_field="exception_root",
                                   code="PIPPI_EXCEPTION_INVALID")
        event = self.journal.append(event_id=event_id,
            event_type="PIPPI_EXCEPTION_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"exception": exception})
        return {"exception_root": exception["exception_root"],
                "journal_event_root": event["event_root"], **BOUNDARY}

    def observatory(self) -> dict[str, Any]:
        events = self._events()
        standards = [event["payload"]["evaluation"] for event in events
                     if event["event_type"] == "PIPPI_STANDARDS_RECORDED"]
        decisions = [event["payload"]["decision"] for event in events
                     if event["event_type"] == "PIPPI_TURN_RECORDED"]
        launches = [event["payload"]["launch_state"] for event in events
                    if event["event_type"] == "PIPPI_LAUNCH_STATE_RECORDED"]
        exceptions = [event["payload"]["exception"] for event in events
                      if event["event_type"] == "PIPPI_EXCEPTION_RECORDED"]
        head = strict_loads(self.journal.head_path.read_bytes())
        return build_development_observatory(subject_root=self.context()["subject_root"],
            standards_evaluations=standards, pippi_decisions=decisions,
            launch_states=launches, constitutional_exceptions=exceptions,
            journal_head_roots=[head["head"]])

    def project(self, view: str) -> dict[str, Any]:
        return project_development_observatory(state=self.observatory(), view=view)


def validate_pippi_campaign_workspace(workspace: Path) -> dict[str, Any]:
    campaign = PippiCampaign(workspace)
    context = campaign.context()
    events = campaign._events()
    require(events and events[0]["event_type"] == "PIPPI_SESSION_CREATED",
            "PIPPI_SESSION_EVENT_MISSING")
    require(events[0]["payload"]["context"] == context,
            "PIPPI_SESSION_CONTEXT_MISMATCH")
    state = campaign.observatory()
    head = strict_loads(campaign.journal.head_path.read_bytes())
    body = {"schema": "mosaic.ucm.pippi-campaign-verification.v0.1",
            "context_root": context["context_root"],
            "journal_head": head["head"],
            "event_count": len(events),
            "observatory_state_root": state["observatory_state_root"],
            "status": "PASS", **BOUNDARY}
    return {**body, "verification_root": root(body)}
