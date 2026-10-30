from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root


ROLES = ("GOVERNOR", "H_J", "H_M", "RECOVERY", "REVIEWER", "WITNESS")
_PRINCIPAL = re.compile(r"^[A-Z][A-Z0-9_.-]{2,63}$")


def make_custody_profile(
    *, subject_root: str, profile_id: str, role_public_roots: dict[str, str],
    principal_ids: dict[str, str], challenge_roots: dict[str, str],
) -> dict[str, Any]:
    require(type(profile_id) is str and 3 <= len(profile_id) <= 96, "CUSTODY_PROFILE_ID_INVALID")
    require(set(role_public_roots) == set(ROLES) == set(principal_ids) == set(challenge_roots), "CUSTODY_ROLE_SET_INVALID")
    public_values: list[str] = []
    principal_values: list[str] = []
    for role in ROLES:
        public_values.append(require_root(role_public_roots[role], f"$.role_public_roots.{role}"))
        require(type(principal_ids[role]) is str and bool(_PRINCIPAL.fullmatch(principal_ids[role])), "CUSTODY_PRINCIPAL_INVALID", f"$.principal_ids.{role}")
        principal_values.append(principal_ids[role].casefold())
        require_root(challenge_roots[role], f"$.challenge_roots.{role}")
    require(len(set(public_values)) == len(ROLES), "CUSTODY_ROLE_KEY_COLLISION")
    require(len(set(principal_values)) == len(ROLES), "CUSTODY_PRINCIPAL_COLLISION")
    require(len(set(challenge_roots.values())) == len(ROLES), "CUSTODY_CHALLENGE_REUSE")
    body = {
        "schema": "ucl.ucm.custody_profile.v1",
        "subject_root": require_root(subject_root),
        "profile_id": profile_id,
        "role_public_roots": {role: role_public_roots[role] for role in ROLES},
        "principal_ids": {role: principal_ids[role] for role in ROLES},
        "challenge_roots": {role: challenge_roots[role] for role in ROLES},
        "private_material_present": False,
        "identity_status": "UNSEATED_FIXTURE",
        "real_a5": False,
        "g0": "CLOSED",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "profile_root": root(body)}


def verify_custody_profile(value: Any, *, expected_subject_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "profile_id", "role_public_roots", "principal_ids", "challenge_roots", "private_material_present", "identity_status", "real_a5", "g0", "standing", "authority_effect", "profile_root"}, "$.custody_profile")
    expected = make_custody_profile(subject_root=expected_subject_root, profile_id=item["profile_id"], role_public_roots=item["role_public_roots"], principal_ids=item["principal_ids"], challenge_roots=item["challenge_roots"])
    require(item == expected, "CUSTODY_PROFILE_RECOMPUTATION_MISMATCH")
    return deepcopy({key: item[key] for key in item if key != "profile_root"})


class CustodyLineage:
    """Fixture-only public identity lineage. It never handles signing material."""

    def __init__(self, *, subject_root: str, profile: dict[str, Any], initial_capsule: dict[str, Any] | None = None, expected_pin: str | None = None) -> None:
        self.subject_root = require_root(subject_root)
        verify_custody_profile(profile, expected_subject_root=self.subject_root)
        self.profile = deepcopy(profile)
        self._active = deepcopy(profile["role_public_roots"])
        self._retired: dict[str, list[str]] = {role: [] for role in ROLES}
        self._events: list[dict[str, Any]] = []
        self._sequence = 0
        self._head = root({"subject_root": self.subject_root, "profile_root": profile["profile_root"], "custody_genesis": True})
        if initial_capsule is not None:
            require(expected_pin is not None, "CUSTODY_CAPSULE_PIN_REQUIRED")
            self.restore(initial_capsule, expected_pin=expected_pin)
        else:
            require(expected_pin is None, "CUSTODY_CAPSULE_REQUIRED")

    def rotate(self, *, role: str, new_public_root: str, ceremony_root: str, approval_roots: dict[str, str]) -> dict[str, Any]:
        require(role in ROLES, "CUSTODY_ROLE_INVALID")
        new_public_root = require_root(new_public_root)
        all_known = set(self._active.values()) | {item for values in self._retired.values() for item in values}
        require(new_public_root not in all_known, "CUSTODY_KEY_REUSE")
        required_approvers = {"GOVERNOR", "RECOVERY", role}
        require(set(approval_roots) == required_approvers, "CUSTODY_ROTATION_APPROVAL_SET_INVALID")
        for value in approval_roots.values(): require_root(value)
        old = self._active[role]
        self._sequence += 1
        body = {
            "schema": "ucl.ucm.custody_event.v1",
            "subject_root": self.subject_root,
            "profile_root": self.profile["profile_root"],
            "event_type": "ROTATE",
            "role": role,
            "old_public_root": old,
            "new_public_root": new_public_root,
            "ceremony_root": require_root(ceremony_root),
            "approval_roots": dict(sorted(approval_roots.items())),
            "sequence": self._sequence,
            "previous_head": self._head,
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        event = {**body, "event_root": root(body)}
        self._events.append(event)
        self._head = event["event_root"]
        self._retired[role].append(old)
        self._active[role] = new_public_root
        return deepcopy(event)

    def admission_check(self, *, role: str, proposed_public_root: str) -> dict[str, Any]:
        require(role in ROLES, "CUSTODY_ROLE_INVALID")
        proposed_public_root = require_root(proposed_public_root)
        active_elsewhere = sorted(key for key, value in self._active.items() if value == proposed_public_root and key != role)
        retired = sorted(key for key, values in self._retired.items() if proposed_public_root in values)
        status = "REFUSED" if active_elsewhere or retired or self._active[role] == proposed_public_root else "ELIGIBLE_FOR_CEREMONY"
        body = {
            "schema": "ucl.ucm.custody_admission_check.v1",
            "subject_root": self.subject_root,
            "profile_root": self.profile["profile_root"],
            "role": role,
            "proposed_public_root": proposed_public_root,
            "active_collision_roles": active_elsewhere,
            "retired_history_roles": retired,
            "status": status,
            "identity_seated": False,
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "check_root": root(body)}

    def migration_plan(self, *, target_profile_root: str, backup_root: str, rollback_root: str) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.custody_migration_plan.v1",
            "subject_root": self.subject_root,
            "source_capsule_root": self.export_capsule()["capsule_root"],
            "target_profile_root": require_root(target_profile_root),
            "backup_root": require_root(backup_root),
            "rollback_root": require_root(rollback_root),
            "requires_restore_before_use": True,
            "requires_all_role_possession_challenges": True,
            "status": "UNBOUND_PLAN",
            "executable": False,
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "plan_root": root(body)}

    def export_capsule(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.custody_lineage_capsule.v1",
            "subject_root": self.subject_root,
            "profile_root": self.profile["profile_root"],
            "sequence": self._sequence,
            "head": self._head,
            "active_public_roots": {role: self._active[role] for role in ROLES},
            "retired_public_roots": {role: list(self._retired[role]) for role in ROLES},
            "events": deepcopy(self._events),
            "identity_seated": False,
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "capsule_root": root(body)}

    def restore(self, capsule: Any, *, expected_pin: str) -> None:
        item = exact_keys(capsule, {"schema", "subject_root", "profile_root", "sequence", "head", "active_public_roots", "retired_public_roots", "events", "identity_seated", "standing", "authority_effect", "capsule_root"}, "$.custody_capsule")
        body = {key: item[key] for key in item if key != "capsule_root"}
        require(item["schema"] == "ucl.ucm.custody_lineage_capsule.v1" and item["capsule_root"] == root(body) == require_root(expected_pin), "CUSTODY_CAPSULE_PIN_MISMATCH")
        require(item["subject_root"] == self.subject_root and item["profile_root"] == self.profile["profile_root"], "CUSTODY_CAPSULE_CONTEXT_MISMATCH")
        require(set(item["active_public_roots"]) == set(ROLES) == set(item["retired_public_roots"]), "CUSTODY_CAPSULE_ROLE_SET_INVALID")
        active = deepcopy(self.profile["role_public_roots"])
        retired = {role: [] for role in ROLES}
        expected_head = root({"subject_root": self.subject_root, "profile_root": self.profile["profile_root"], "custody_genesis": True})
        for sequence, event in enumerate(item["events"], 1):
            exact_keys(event, {"schema", "subject_root", "profile_root", "event_type", "role", "old_public_root", "new_public_root", "ceremony_root", "approval_roots", "sequence", "previous_head", "standing", "authority_effect", "event_root"}, f"$.custody_capsule.events[{sequence - 1}]")
            event_body = {key: event[key] for key in event if key != "event_root"}
            require(event["event_root"] == root(event_body) and event["sequence"] == sequence and event["previous_head"] == expected_head, "CUSTODY_EVENT_CHAIN_INVALID")
            role = event["role"]
            require(role in ROLES and event["old_public_root"] == active[role], "CUSTODY_EVENT_LINEAGE_INVALID")
            require(event["event_type"] == "ROTATE" and event["subject_root"] == self.subject_root and event["profile_root"] == self.profile["profile_root"], "CUSTODY_EVENT_CONTEXT_INVALID")
            require_root(event["old_public_root"]); require_root(event["new_public_root"]); require_root(event["ceremony_root"])
            require(set(event["approval_roots"]) == {"GOVERNOR", "RECOVERY", role}, "CUSTODY_ROTATION_APPROVAL_SET_INVALID")
            for approval_root in event["approval_roots"].values(): require_root(approval_root)
            require(event["standing"] == "INFORMATION_ONLY" and event["authority_effect"] == "NONE", "CUSTODY_EVENT_AUTHORITY_INVALID")
            known = set(active.values()) | {key_root for roots in retired.values() for key_root in roots}
            require(event["new_public_root"] not in known, "CUSTODY_KEY_REUSE")
            retired[role].append(event["old_public_root"])
            active[role] = event["new_public_root"]
            expected_head = event["event_root"]
        require(item["sequence"] == len(item["events"]) and item["head"] == expected_head, "CUSTODY_CAPSULE_HEAD_MISMATCH")
        require(item["active_public_roots"] == active and item["retired_public_roots"] == retired, "CUSTODY_CAPSULE_STATE_MISMATCH")
        require(item["identity_seated"] is False and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "CUSTODY_CAPSULE_AUTHORITY_INVALID")
        self._active, self._retired, self._events = active, retired, deepcopy(item["events"])
        self._sequence, self._head = item["sequence"], item["head"]
