"""Deterministic human and agent session state for Mosaic UI review."""
from __future__ import annotations

import copy
from typing import Any

from .canonical import commitment
from .model import UIRefusal
from .review_ontology import build_review_ontology, validate_review_ontology


REVIEW_MODES = ("EXPLORE", "GUIDED_REVIEW", "CHANGES")
REVIEW_DISPOSITIONS = ("NEEDS_REVIEW", "APPROVED", "ISSUE", "DEFERRED")


class ReviewSession:
    """Closed review workflow projected into browser, native, and agent surfaces."""

    def __init__(self, ontology: dict[str, Any] | None = None, *, realizer: str = "HEADLESS",
                 subject_id: str | None = None, theme_id: str | None = None,
                 density_id: str | None = None) -> None:
        self.ontology = copy.deepcopy(ontology or build_review_ontology())
        validate_review_ontology(self.ontology)
        self.subjects = {item["subject_id"]: item for item in self.ontology["subjects"]}
        self.condition_specs = {item["condition_id"]: item for item in self.ontology["conditions"]}
        self.view_specs = {item["view_id"]: item for item in self.ontology["inspection_views"]}
        self.subject_order = [item["subject_id"] for item in self.ontology["subjects"]]
        self.conditions = {key: spec["default"] for key, spec in self.condition_specs.items()}
        self.mode = "GUIDED_REVIEW"
        self.subject_id = subject_id or "component.button"
        self.view_id = "anatomy"
        self.reviews = {
            key: {"disposition": "NEEDS_REVIEW", "note": "", "review_count": 0}
            for key in self.subject_order
        }
        self.specimen_values = {
            key: copy.deepcopy(
                item.get("metadata", {}).get("specimen", {}).get("value_model", {}).get("default")
            )
            for key, item in self.subjects.items()
        }
        self.events: list[dict[str, Any]] = []
        self._sequence = 0
        if self.subject_id not in self.subjects:
            raise UIRefusal("REVIEW_SESSION_SUBJECT_REFUSED", self.subject_id)
        self.set_condition("realizer", realizer, record=False)
        if theme_id is not None:
            self.set_condition("theme", theme_id, record=False)
        if density_id is not None:
            self.set_condition("density", density_id, record=False)
        self.baseline = {
            "subject_id": self.subject_id,
            "conditions": copy.deepcopy(self.conditions),
            "reviews": copy.deepcopy(self.reviews),
        }
        self._record("SESSION_STARTED", "session", self.mode)

    @property
    def subject(self) -> dict[str, Any]:
        return self.subjects[self.subject_id]

    @property
    def group_id(self) -> str:
        return str(self.subject["group_id"])

    def applicable_states(self) -> tuple[str, ...]:
        states = self.subject.get("metadata", {}).get("states")
        return tuple(states) if states else (self.condition_specs["state"]["default"],)

    def state_control_context(self) -> str:
        """Describe the review lens shown when interaction-state choice is not meaningful."""
        contexts = {
            "FOUNDATION": "FOUNDATION SPECIMEN",
            "PATTERN": "WORKFLOW STAGE",
            "SURFACE": "REFERENCE SURFACE",
            "PROFILE": "PROFILE CONFIGURATION",
            "DELIVERY": "ABLATION PLAN",
        }
        return contexts.get(str(self.subject["subject_type"]), "STATIC COMPONENT")

    def action_scope(self) -> dict[str, Any]:
        """Return the controls that are meaningful for the current subject and mode."""
        changed = self.changed_subject_ids()
        interactive = bool(self.subject.get("metadata", {}).get("interactive"))
        review_enabled = self.mode != "EXPLORE"
        navigation_count = len(changed) if self.mode == "CHANGES" else len(self.subject_order)
        return {
            "review_note_enabled": review_enabled,
            "disposition_enabled": review_enabled,
            "state_control_visible": len(self.applicable_states()) > 1,
            "state_control_context": self.state_control_context(),
            "state_exercise_enabled": len(self.applicable_states()) > 1,
            "specimen_interaction_enabled": interactive and self.conditions["state"] != "DISABLED",
            "previous_enabled": navigation_count > 1,
            "next_enabled": navigation_count > 1,
            "navigation_scope": "CHANGED" if self.mode == "CHANGES"
                                else "UNRESOLVED" if self.mode == "GUIDED_REVIEW" else "ALL",
        }

    def _record(self, intent: str, target: str, value: Any) -> None:
        self._sequence += 1
        self.events.append({
            "sequence": self._sequence, "intent": intent, "target": target,
            "value": copy.deepcopy(value), "subject_id": self.subject_id,
        })
        del self.events[:-256]

    def set_mode(self, mode: str) -> None:
        if mode not in REVIEW_MODES:
            raise UIRefusal("REVIEW_SESSION_MODE_REFUSED", mode)
        self.mode = mode
        self._record("SET_MODE", "session", mode)

    def select_subject(self, subject_id: str) -> None:
        if subject_id not in self.subjects:
            raise UIRefusal("REVIEW_SESSION_SUBJECT_REFUSED", subject_id)
        self.subject_id = subject_id
        self._record("SELECT_SUBJECT", "catalog", subject_id)
        if self.conditions["state"] not in self.applicable_states():
            self.conditions["state"] = self.applicable_states()[0]
            self._record("NORMALIZE_CONDITION", "state", self.conditions["state"])

    def select_group(self, group_id: str) -> None:
        group = next((item for item in self.ontology["groups"] if item["group_id"] == group_id), None)
        if group is None or not group["subject_ids"]:
            raise UIRefusal("REVIEW_SESSION_GROUP_REFUSED", group_id)
        self.select_subject(group["subject_ids"][0])

    def select_view(self, view_id: str) -> None:
        if view_id not in self.view_specs:
            raise UIRefusal("REVIEW_SESSION_VIEW_REFUSED", view_id)
        self.view_id = view_id
        self._record("SELECT_INSPECTOR", "inspector", view_id)

    def set_condition(self, condition_id: str, value: str, *, record: bool = True) -> None:
        spec = self.condition_specs.get(condition_id)
        if spec is None or value not in spec["options"]:
            raise UIRefusal("REVIEW_SESSION_CONDITION_REFUSED", f"{condition_id}:{value}")
        if condition_id == "state" and value not in self.applicable_states():
            raise UIRefusal("REVIEW_SESSION_STATE_NOT_APPLICABLE", f"{self.subject_id}:{value}")
        self.conditions[condition_id] = value
        if record:
            self._record("SET_CONDITION", condition_id, value)

    def set_disposition(self, disposition: str, *, note: str | None = None) -> None:
        if not self.action_scope()["disposition_enabled"]:
            raise UIRefusal("REVIEW_SESSION_ACTION_NOT_APPLICABLE", "SET_DISPOSITION")
        if disposition not in REVIEW_DISPOSITIONS or disposition == "NEEDS_REVIEW":
            raise UIRefusal("REVIEW_SESSION_DISPOSITION_REFUSED", disposition)
        review = self.reviews[self.subject_id]
        review["disposition"] = disposition
        review["review_count"] += 1
        if note is not None:
            review["note"] = str(note)[:2000]
        self._record("SET_DISPOSITION", self.subject_id, disposition)

    def set_disposition_batch(self, subject_ids: Any, disposition: str, *, note: str | None = None) -> None:
        """Validate every target before atomically recording one batch decision event."""
        if not self.action_scope()["disposition_enabled"]:
            raise UIRefusal("REVIEW_SESSION_ACTION_NOT_APPLICABLE", "SET_DISPOSITION_BATCH")
        if disposition not in REVIEW_DISPOSITIONS or disposition == "NEEDS_REVIEW":
            raise UIRefusal("REVIEW_SESSION_DISPOSITION_REFUSED", disposition)
        if not isinstance(subject_ids, list) or not subject_ids or not all(isinstance(item, str) for item in subject_ids):
            raise UIRefusal("REVIEW_SESSION_BATCH_REFUSED", "SUBJECT_IDS")
        if len(set(subject_ids)) != len(subject_ids):
            raise UIRefusal("REVIEW_SESSION_BATCH_REFUSED", "DUPLICATE_SUBJECT")
        unknown = [item for item in subject_ids if item not in self.reviews]
        if unknown:
            raise UIRefusal("REVIEW_SESSION_BATCH_REFUSED", "UNKNOWN_SUBJECT:" + ",".join(unknown))
        for subject_id in subject_ids:
            review = self.reviews[subject_id]
            review["disposition"] = disposition
            review["review_count"] += 1
            if note is not None:
                review["note"] = str(note)[:2000]
        self._record(
            "SET_DISPOSITION_BATCH", "batch",
            {"subject_ids": list(subject_ids), "disposition": disposition},
        )

    def set_note(self, note: str) -> None:
        if not self.action_scope()["review_note_enabled"]:
            raise UIRefusal("REVIEW_SESSION_ACTION_NOT_APPLICABLE", "SET_NOTE")
        self.reviews[self.subject_id]["note"] = str(note)[:2000]
        self._record("SET_NOTE", self.subject_id, self.reviews[self.subject_id]["note"])

    def move(self, direction: int, *, unresolved_only: bool = False, changed_only: bool = False) -> None:
        if direction not in {-1, 1}:
            raise UIRefusal("REVIEW_SESSION_MOVE_REFUSED", str(direction))
        if unresolved_only and changed_only:
            raise UIRefusal("REVIEW_SESSION_MOVE_REFUSED", "CONFLICTING_SCOPE")
        index = self.subject_order.index(self.subject_id)
        for offset in range(1, len(self.subject_order) + 1):
            candidate = self.subject_order[(index + direction * offset) % len(self.subject_order)]
            if not unresolved_only or self.reviews[candidate]["disposition"] == "NEEDS_REVIEW":
                if not changed_only or candidate in self.changed_subject_ids():
                    self.select_subject(candidate)
                    return

    def record_interaction(self, value: str = "ACTIVATE") -> None:
        if not self.action_scope()["specimen_interaction_enabled"]:
            raise UIRefusal("REVIEW_SESSION_ACTION_NOT_APPLICABLE", "INTERACT")
        self._record("INTERACT", self.subject_id, value)

    def set_specimen_value(self, value: Any) -> None:
        """Record live specimen value without changing the simulated interaction state."""
        if not self.action_scope()["specimen_interaction_enabled"]:
            raise UIRefusal("REVIEW_SESSION_ACTION_NOT_APPLICABLE", "SET_SPECIMEN_VALUE")
        if len(repr(value)) > 2000:
            raise UIRefusal("REVIEW_SESSION_SPECIMEN_VALUE_REFUSED", "VALUE_TOO_LARGE")
        self.specimen_values[self.subject_id] = copy.deepcopy(value)
        self._record("INTERACT", self.subject_id, value)
        self.events[-1]["simulated_state"] = self.conditions["state"]

    def progress(self) -> dict[str, Any]:
        counts = {key: 0 for key in REVIEW_DISPOSITIONS}
        for review in self.reviews.values():
            counts[review["disposition"]] += 1
        reviewed = len(self.reviews) - counts["NEEDS_REVIEW"]
        return {
            "reviewed": reviewed, "total": len(self.reviews),
            "percent": round(reviewed * 100 / len(self.reviews)), "counts": counts,
        }

    def changed_subject_ids(self) -> list[str]:
        return [
            key for key in self.subject_order
            if self.reviews[key] != self.baseline["reviews"][key]
        ]

    def state(self) -> dict[str, Any]:
        progress = self.progress()
        value = {
            "schema": "mosaic.ui.review-session-state.v0.1",
            "ontology_commitment": self.ontology["commitment"],
            "mode": self.mode, "subject_id": self.subject_id, "group_id": self.group_id,
            "inspection_view": self.view_id, "conditions": copy.deepcopy(self.conditions),
            "applicable_states": list(self.applicable_states()),
            "action_scope": self.action_scope(),
            "specimen_value": copy.deepcopy(self.specimen_values[self.subject_id]),
            "current_review": copy.deepcopy(self.reviews[self.subject_id]),
            "reviews": copy.deepcopy(self.reviews), "progress": progress,
            "changed_subject_ids": self.changed_subject_ids(),
            "review_contract": copy.deepcopy(self.subject.get("review", {})),
            "event_count": len(self.events), "last_event": copy.deepcopy(self.events[-1]),
            "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
            "claim_boundary": "REVIEW_SESSION_STATE_RECORDS_LOCAL_JUDGMENT_AND_DOES_NOT_GRANT_RELEASE_AUTHORITY",
        }
        value["commitment"] = commitment("MOSAIC.UI.REVIEW_SESSION_STATE.v0.1", value)
        return value

    def snapshot(self) -> dict[str, Any]:
        value = self.state()
        value["schema"] = "mosaic.ui.review-session-snapshot.v0.1"
        value["events"] = copy.deepcopy(self.events)
        value.pop("commitment", None)
        value["commitment"] = commitment("MOSAIC.UI.REVIEW_SESSION_SNAPSHOT.v0.1", value)
        return value

    def dispatch(self, action: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(action, dict):
            raise UIRefusal("REVIEW_SESSION_ACTION_REFUSED", "NOT_OBJECT")
        intent = str(action.get("intent", ""))
        value = action.get("value")
        if intent == "SET_MODE":
            self.set_mode(str(value))
        elif intent == "SELECT_SUBJECT":
            self.select_subject(str(value))
        elif intent == "SELECT_VIEW":
            self.select_view(str(value))
        elif intent == "SET_CONDITION":
            self.set_condition(str(action.get("target", "")), str(value))
        elif intent == "SET_DISPOSITION":
            self.set_disposition(str(value), note=action.get("note"))
        elif intent == "SET_DISPOSITION_BATCH":
            self.set_disposition_batch(action.get("subject_ids"), str(value), note=action.get("note"))
        elif intent == "SET_NOTE":
            self.set_note(str(value or ""))
        elif intent == "NEXT":
            self.move(1, unresolved_only=bool(action.get("unresolved_only")),
                      changed_only=self.mode == "CHANGES")
        elif intent == "PREVIOUS":
            self.move(-1, changed_only=self.mode == "CHANGES")
        elif intent == "INTERACT":
            self.record_interaction(str(value or "ACTIVATE"))
        elif intent == "SET_SPECIMEN_VALUE":
            self.set_specimen_value(value)
        else:
            raise UIRefusal("REVIEW_SESSION_ACTION_REFUSED", intent)
        return self.state()


__all__ = ["REVIEW_DISPOSITIONS", "REVIEW_MODES", "ReviewSession"]
