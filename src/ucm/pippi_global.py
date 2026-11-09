"""Sovereign local P/PPI hub records and persistence.

The hub coordinates projects and sessions.  It stores public identity material
and opaque credential references only; it never stores provider secrets.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
from contextlib import contextmanager

from uclop.canonical import canonical_bytes, root, strict_loads


SCHEMA = "mosaic.ucm.pippi-global.v0.1"
PROJECT_SCHEMA = "mosaic.ucm.pippi-project.v0.1"
EVENT_SCHEMA = "mosaic.ucm.pippi-hub-event.v0.1"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
CHANNELS = ("MODEL_INPUT", "MODEL_DRAFT", "VISIBLE_OUTPUT", "TOOL_PROPOSAL",
            "TOOL_DISPATCH", "TOOL_RESULT", "JOURNAL_WRITE")
VERSION_POLICY = {
    "public_version": "v0.1",
    "engineering_revision_pattern": "r[0-9]{3}",
    "version_change_requires_explicit_user_authorization": True,
    "implicit_version_bumps": "REFUSED",
    "default_next_output_change": "ENGINEERING_REVISION",
    "turn_and_loop_instruction": "PRESERVE_PUBLIC_VERSION_AND_ADVANCE_REVISION_WHEN_NEEDED",
}


class HubRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code, self.detail = code, detail
        super().__init__(f"{code}:{detail}" if detail else code)


def _ident(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 192:
        raise HubRefusal(code)
    if not all(ch.isalnum() or ch in "._:-/@+" for ch in value):
        raise HubRefusal(code)
    return value


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending")
    raw = canonical_bytes(value) + b"\n"
    with temporary.open("wb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def default_data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else None
    return Path(base or Path.home() / ".local" / "share") / "Ableman Mosaic" / "Pippi" / "data"


def build_onboarding(*, governor_label: str, mosaic_id: str | None,
                     dkn_public_key: str | None, github_account: str | None,
                     github_credential_reference: str | None,
                     archive_backend: str = "MEMORY_VAULT_OPTIONAL_DEFAULT_ON") -> dict[str, Any]:
    _ident(governor_label, "PIPPI_GOVERNOR_LABEL_INVALID")
    if mosaic_id is not None: _ident(mosaic_id, "PIPPI_MOSAIC_ID_INVALID")
    if dkn_public_key is not None:
        _ident(dkn_public_key, "PIPPI_DKN_PUBLIC_KEY_INVALID")
        if (len(dkn_public_key) < 16 or
                any(mark in dkn_public_key.lower() for mark in ("private", "secret", "seed", "-----begin"))):
            raise HubRefusal("PIPPI_DKN_PUBLIC_KEY_INVALID")
    if github_account is not None: _ident(github_account, "PIPPI_GITHUB_ACCOUNT_INVALID")
    if github_credential_reference is not None:
        _ident(github_credential_reference, "PIPPI_CREDENTIAL_REFERENCE_INVALID")
        lowered = github_credential_reference.lower()
        if any(mark in lowered for mark in ("ghp_", "github_pat_", "token=", "password=")):
            raise HubRefusal("PIPPI_RAW_CREDENTIAL_REFUSED")
    if archive_backend not in {"MEMORY_VAULT_OPTIONAL_DEFAULT_ON", "LOCAL_CONTENT_STORE"}:
        raise HubRefusal("PIPPI_ARCHIVE_BACKEND_INVALID")
    body = {"schema": "mosaic.ucm.pippi-onboarding.v0.1", "governor_label": governor_label,
            "mosaic_id": mosaic_id, "dkn_public_key": dkn_public_key,
            "github_account": github_account,
            "github_credential_reference": github_credential_reference,
            "secret_storage": "EXTERNAL_PROVIDER_ONLY", "archive_backend": archive_backend,
            "archive_default_enabled": True, "version_policy": deepcopy(VERSION_POLICY), **BOUNDARY}
    return {**body, "onboarding_root": root(body)}


def validate_onboarding(value: Any) -> dict[str,Any]:
    if not isinstance(value,dict): raise HubRefusal("PIPPI_ONBOARDING_INVALID")
    expected=build_onboarding(governor_label=value.get("governor_label"),mosaic_id=value.get("mosaic_id"),
        dkn_public_key=value.get("dkn_public_key"),github_account=value.get("github_account"),
        github_credential_reference=value.get("github_credential_reference"),archive_backend=value.get("archive_backend"))
    if value!=expected: raise HubRefusal("PIPPI_ONBOARDING_INVALID")
    return deepcopy(value)


def build_project(*, project_id: str, title: str, workspace: str,
                  github_url: str | None, application_command: list[str] | None,
                  verification_command: list[str] | None,
                  readme: str | None = None, docs: list[str] | None = None,
                  public_version: str = "v0.1", revision: str = "r001") -> dict[str, Any]:
    _ident(project_id, "PIPPI_PROJECT_ID_INVALID")
    if not isinstance(title, str) or not title.strip(): raise HubRefusal("PIPPI_PROJECT_TITLE_INVALID")
    root_path = str(Path(workspace).resolve())
    if github_url is not None and not github_url.startswith("https://github.com/"):
        raise HubRefusal("PIPPI_GITHUB_URL_REFUSED")
    if public_version != VERSION_POLICY["public_version"]:
        raise HubRefusal("PIPPI_VERSION_CHANGE_REQUIRES_EXPLICIT_USER_AUTHORIZATION")
    if len(revision) != 4 or revision[0] != "r" or not revision[1:].isdigit():
        raise HubRefusal("PIPPI_REVISION_INVALID")
    for command in (application_command, verification_command):
        if command is not None and (not isinstance(command, list) or not command or
                                    not all(isinstance(x, str) and x for x in command)):
            raise HubRefusal("PIPPI_ENTRYPOINT_INVALID")
    doc_list = sorted(set(docs or []))
    body = {"schema": PROJECT_SCHEMA, "project_id": project_id, "title": title,
            "workspace": root_path, "github_url": github_url,
            "application_command": application_command,
            "verification_command": verification_command,
            "readme": readme, "docs": doc_list,
            "public_version": public_version, "revision": revision,
            "status": "REGISTERED", "holds": [], "evidence_roots": [],
            "session_roots": [], "journal_head": None, **BOUNDARY}
    return {**body, "project_root": root(body)}


def validate_project(value: Any) -> dict[str,Any]:
    if not isinstance(value,dict): raise HubRefusal("PIPPI_PROJECT_INVALID")
    body={key:deepcopy(row) for key,row in value.items() if key!="project_root"}
    if (value.get("schema")!=PROJECT_SCHEMA or value.get("project_root")!=root(body) or
            any(value.get(key)!=row for key,row in BOUNDARY.items())):
        raise HubRefusal("PIPPI_PROJECT_INVALID")
    return deepcopy(value)


def build_project_identity_transition(*, project: dict[str, Any],
                                      requested_public_version: str,
                                      requested_revision: str,
                                      external_approval: dict[str, Any] | None,
                                      expected_approval_policy_root: str | None,
                                      now: int | None) -> dict[str, Any]:
    """Advance a revision or apply an explicitly approved public-version change."""
    project = validate_project(project)
    if (not isinstance(requested_revision, str) or len(requested_revision) != 4
            or not requested_revision.startswith("r")
            or not requested_revision[1:].isdigit()
            or int(requested_revision[1:]) <= int(project["revision"][1:])):
        raise HubRefusal("PIPPI_REVISION_TRANSITION_INVALID")
    if not isinstance(requested_public_version, str) or not requested_public_version:
        raise HubRefusal("PIPPI_VERSION_POLICY_REFUSED")
    operation_body = {
        "schema": "mosaic.ucm.pippi-project-identity-transition-operation.v0.1",
        "project_id": project["project_id"],
        "predecessor_project_root": project["project_root"],
        "from_public_version": project["public_version"],
        "to_public_version": requested_public_version,
        "from_revision": project["revision"],
        "to_revision": requested_revision,
        **BOUNDARY,
    }
    operation_root = root(operation_body)
    version_changed = requested_public_version != project["public_version"]
    approval_root = None
    if version_changed:
        if (external_approval is None or expected_approval_policy_root is None
                or type(now) is not int):
            raise HubRefusal("PIPPI_VERSION_CHANGE_REQUIRES_EXPLICIT_USER_AUTHORIZATION")
        try:
            from .governance import verify_external_approval
            approval = verify_external_approval(
                external_approval, expected_operation_root=operation_root,
                expected_policy_root=expected_approval_policy_root, now=now)
        except (ValueError, TypeError) as error:
            raise HubRefusal("PIPPI_VERSION_CHANGE_AUTHORIZATION_INVALID",
                             str(error)) from error
        approval_root = approval["approval_root"]
    else:
        if external_approval is not None or expected_approval_policy_root is not None or now is not None:
            raise HubRefusal("PIPPI_REVISION_TRANSITION_APPROVAL_UNEXPECTED")
    project_body = {key: deepcopy(value) for key, value in project.items()
                    if key != "project_root"}
    project_body["public_version"] = requested_public_version
    project_body["revision"] = requested_revision
    successor = {**project_body, "project_root": root(project_body)}
    receipt_body = {
        "schema": "mosaic.ucm.pippi-project-identity-transition.v0.1",
        "operation_root": operation_root,
        "predecessor_project_root": project["project_root"],
        "successor_project_root": successor["project_root"],
        "change_class": "PUBLIC_VERSION" if version_changed else "ENGINEERING_REVISION",
        "from_public_version": project["public_version"],
        "to_public_version": requested_public_version,
        "from_revision": project["revision"], "to_revision": requested_revision,
        "external_approval_root": approval_root,
        "explicit_user_authorization_verified": version_changed,
        "default_preference_applied": not version_changed,
        **BOUNDARY,
    }
    return {"project": successor,
            "transition": {**receipt_body, "transition_root": root(receipt_body)}}


def build_context_injection(*, project: dict[str, Any], session_root: str,
                            scenario: str, requested_rules: list[str]) -> dict[str, Any]:
    project=validate_project(project)
    _ident(session_root, "PIPPI_SESSION_ROOT_INVALID")
    _ident(scenario, "PIPPI_SCENARIO_INVALID")
    rules = sorted(set(requested_rules))
    permitted = {"AUTHORITY_BOUNDARY", "VERSION_POLICY", "PROJECT_ENTRYPOINTS",
                 "ARCHIVE_POLICY", "COURTHOUSE_ROUTING", "VISIBILITY_POLICY",
                 "SEVEN_CHANNEL_COVERAGE"}
    if not set(rules) <= permitted: raise HubRefusal("PIPPI_CONTEXT_RULE_INVALID")
    exact = {"project_id": project["project_id"], "project_root": project["project_root"],
             "scenario": scenario, "rules": rules, "version_policy": VERSION_POLICY,
             "entrypoints": {"application": project["application_command"],
                              "verification": project["verification_command"]},
             "courthouse_rule": "REMOTE_OR_CROSS_JURISDICTION_ONLY",
             "visibility_rule": "PROGRESS_IS_NOT_EVIDENCE_AND_USER_VIEW_MUST_TRACK_STATE",
             "coverage_channels": list(CHANNELS)}
    body = {"schema": "mosaic.ucm.pippi-context-injection.v0.1",
            "session_root": session_root, "exact_context": exact, **BOUNDARY}
    return {**body, "context_injection_root": root(body)}


class PippiHub:
    def __init__(self, data_root: Path | None = None) -> None:
        self.root = Path(data_root or default_data_root()).resolve()
        self.projects = self.root / "projects"
        self.journal = self.root / "hub-events.jsonl"
        self.status = self.root / "STATUS.json"
        self.onboarding = self.root / "ONBOARDING.json"
        self.integrations = self.root / "INTEGRATIONS.json"
        self.turns = self.root / "turns"
        self.lock_path = self.root / "PIPPI.lock"

    @contextmanager
    def _lock(self):
        self.root.mkdir(parents=True,exist_ok=True)
        stream=self.lock_path.open("a+b")
        try:
            stream.seek(0);stream.write(b"0");stream.flush();stream.seek(0)
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
            yield
        finally:
            try:
                stream.seek(0)
                if os.name=="nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
            finally:stream.close()

    def initialize(self, onboarding: dict[str, Any],
                   integration_registry: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.root.exists() and any(self.root.iterdir()): raise HubRefusal("PIPPI_HUB_EXISTS")
        from .pippi_integrations import (default_integration_availability_registry,
                                         validate_integration_availability_registry)
        registry = validate_integration_availability_registry(integration_registry) \
            if integration_registry is not None else default_integration_availability_registry()
        self.projects.mkdir(parents=True)
        _atomic(self.onboarding, onboarding)
        _atomic(self.integrations, registry)
        event = self.append("HUB_INITIALIZED", {"onboarding_root": onboarding["onboarding_root"],
                            "integration_registry_root": registry["integration_registry_root"]})
        return {"status": "PASS", "hub_root": event["event_root"], **BOUNDARY}

    def integration_availability(self) -> dict[str, Any]:
        from .pippi_integrations import (default_integration_availability_registry,
                                         validate_integration_availability_registry)
        if not self.integrations.is_file():
            return default_integration_availability_registry(source="LEGACY_PROJECTION")
        return validate_integration_availability_registry(
            strict_loads(self.integrations.read_bytes()))

    def integration(self, integration_id: str) -> dict[str, Any]:
        _ident(integration_id, "PIPPI_INTEGRATION_ID_INVALID")
        matches = [row for row in self.integration_availability()["entries"]
                   if row["integration_id"] == integration_id]
        if len(matches) != 1: raise HubRefusal("PIPPI_INTEGRATION_UNKNOWN", integration_id)
        return deepcopy(matches[0])

    def _events(self) -> list[dict[str, Any]]:
        if not self.journal.exists(): return []
        rows=[]
        for line in self.journal.read_bytes().splitlines():
            if line: rows.append(strict_loads(line))
        previous=None
        for index, row in enumerate(rows, 1):
            body={k:deepcopy(v) for k,v in row.items() if k!="event_root"}
            if row.get("sequence") != index or row.get("previous_event_root") != previous or row.get("event_root") != root(body):
                raise HubRefusal("PIPPI_HUB_JOURNAL_INVALID")
            previous=row["event_root"]
        return rows

    def append(self, event_type: str, payload: dict[str, Any], *, expected_head: str | None=None,
               _already_locked: bool=False) -> dict[str, Any]:
        if not _already_locked:
            with self._lock():
                return self.append(event_type,payload,expected_head=expected_head,_already_locked=True)
        _ident(event_type, "PIPPI_EVENT_TYPE_INVALID")
        rows=self._events(); previous=rows[-1]["event_root"] if rows else None
        if expected_head is not None and expected_head!=previous:
            raise HubRefusal("PIPPI_EXPECTED_HEAD_MISMATCH")
        body={"schema":EVENT_SCHEMA,"sequence":len(rows)+1,"previous_event_root":previous,
              "event_type":event_type,"observed_unix_ns":time.time_ns(),"payload":deepcopy(payload),**BOUNDARY}
        event={**body,"event_root":root(body)}
        self.root.mkdir(parents=True,exist_ok=True)
        with self.journal.open("ab") as stream:
            stream.write(canonical_bytes(event)+b"\n");stream.flush();os.fsync(stream.fileno())
        _atomic(self.status,{"schema":SCHEMA,"event_count":event["sequence"],"journal_head":event["event_root"],
                             "status":"READY",**BOUNDARY})
        return event

    def add_project(self, project: dict[str, Any]) -> dict[str, Any]:
        project=validate_project(project)
        with self._lock():
            path=self.projects/f"{project['project_id']}.json"
            if path.exists(): raise HubRefusal("PIPPI_PROJECT_EXISTS")
            _atomic(path,project)
            self.append("PROJECT_REGISTERED",{"project_id":project["project_id"],"project_root":project["project_root"]},
                        _already_locked=True)
            return deepcopy(project)

    def list_projects(self) -> list[dict[str, Any]]:
        return [validate_project(strict_loads(path.read_bytes()))
                for path in sorted(self.projects.glob("*.json"),
                                   key=lambda item: item.name)]

    def get_project(self, project_id: str) -> dict[str, Any]:
        _ident(project_id,"PIPPI_PROJECT_ID_INVALID")
        path=self.projects/f"{project_id}.json"
        if not path.is_file(): raise HubRefusal("PIPPI_PROJECT_UNKNOWN",project_id)
        return validate_project(strict_loads(path.read_bytes()))

    def transition_project_identity(self, *, project_id: str,
                                    requested_public_version: str,
                                    requested_revision: str,
                                    external_approval: dict[str, Any] | None = None,
                                    expected_approval_policy_root: str | None = None,
                                    now: int | None = None) -> dict[str, Any]:
        with self._lock():
            predecessor = self.get_project(project_id)
            result = build_project_identity_transition(
                project=predecessor,
                requested_public_version=requested_public_version,
                requested_revision=requested_revision,
                external_approval=external_approval,
                expected_approval_policy_root=expected_approval_policy_root,
                now=now)
            _atomic(self.projects / f"{project_id}.json", result["project"])
            self.append("PROJECT_IDENTITY_TRANSITIONED", {
                "project_id": project_id,
                "transition_root": result["transition"]["transition_root"],
                "change_class": result["transition"]["change_class"],
                "external_approval_root": result["transition"]["external_approval_root"],
            }, _already_locked=True)
            return deepcopy(result)

    def store_project_record(self, *, project_id: str, record_kind: str,
                             record: dict[str, Any], root_field: str,
                             event_type: str) -> dict[str, Any]:
        """Persist one already-validated project record and journal its exact root."""
        _ident(project_id, "PIPPI_PROJECT_ID_INVALID")
        _ident(record_kind, "PIPPI_RECORD_KIND_INVALID")
        _ident(event_type, "PIPPI_EVENT_TYPE_INVALID")
        value_root = record.get(root_field)
        if not isinstance(value_root, str) or len(value_root) != 64:
            raise HubRefusal("PIPPI_RECORD_ROOT_INVALID")
        with self._lock():
            return self._store_project_record_locked(project_id=project_id,
                record_kind=record_kind, record=record, root_field=root_field,
                event_type=event_type)

    def _store_project_record_locked(self, *, project_id: str, record_kind: str,
                                     record: dict[str, Any], root_field: str,
                                     event_type: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        if record.get("project_root") != project["project_root"]:
            raise HubRefusal("PIPPI_RECORD_PROJECT_MISMATCH")
        value_root = record.get(root_field)
        folder = self.turns / project_id
        path = folder / f"{record_kind}-{value_root}.json"
        matching = [row for row in self._events()
                    if row["event_type"] == event_type
                    and row["payload"].get("project_id") == project_id
                    and row["payload"].get(root_field) == value_root]
        if len(matching) > 1:
            raise HubRefusal("PIPPI_RECORD_CUSTODY_INVALID")
        if path.exists():
            existing = strict_loads(path.read_bytes())
            if existing != record:
                raise HubRefusal("PIPPI_RECORD_ROOT_COLLISION")
            if matching:
                return {"record": deepcopy(record),
                        "hub_event_root": matching[0]["event_root"],
                        "path": str(path), "idempotent_replay": True,
                        "recovered_interrupted_commit": False, **BOUNDARY}
            recovered = True
        else:
            if matching:
                raise HubRefusal("PIPPI_RECORD_CUSTODY_INVALID")
            _atomic(path, record)
            recovered = False
        event = self.append(event_type, {"project_id": project_id,
            "record_kind": record_kind, root_field: value_root}, _already_locked=True)
        return {"record": deepcopy(record), "hub_event_root": event["event_root"],
                "path": str(path), "idempotent_replay": False,
                "recovered_interrupted_commit": recovered, **BOUNDARY}

    def store_turn_opening_atomic(self, record: dict[str, Any]) -> dict[str, Any]:
        from .pippi_adaptive import validate_turn_opening
        from .pippi_turn_workflow import turn_continuation_context
        opening = validate_turn_opening(record)
        with self._lock():
            project = self.get_project(opening["project_id"])
            if opening["project_root"] != project["project_root"]:
                raise HubRefusal("PIPPI_RECORD_PROJECT_MISMATCH")
            continuation = turn_continuation_context(self, project["project_id"])
            if (continuation["pending_opening_roots"]
                    and opening["turn_opening_root"] not in continuation["pending_opening_roots"]):
                raise HubRefusal("PIPPI_PREVIOUS_TURN_CLOSE_REQUIRED")
            stored = self._store_project_record_locked(project_id=project["project_id"],
                record_kind="opening", record=opening, root_field="turn_opening_root",
                event_type="TURN_OPENED")
            return {**stored, "continuation_context": continuation}

    def store_turn_bundle_atomic(self, bundle: dict[str, Any]) -> dict[str, Any]:
        from .pippi_turn_workflow import validate_turn_bundle
        value = validate_turn_bundle(bundle)
        with self._lock():
            project = self.get_project(value["project_id"])
            if value["project_root"] != project["project_root"]:
                raise HubRefusal("PIPPI_RECORD_PROJECT_MISMATCH")
            events = self._events()
            committed = {row["payload"].get("turn_bundle_root") for row in events
                         if row["event_type"] == "TURN_RECORD_SUBMITTED"
                         and row["payload"].get("project_id") == value["project_id"]}
            directory = self.turns / value["project_id"]
            same_opening = []
            if directory.is_dir():
                for path in directory.glob("turn-record-*.json"):
                    prior = validate_turn_bundle(strict_loads(path.read_bytes()))
                    if (prior["turn_opening_root"] == value["turn_opening_root"]
                            and prior["turn_bundle_root"] in committed):
                        same_opening.append(prior)
            supersedes = value.get("supersedes_turn_bundle_root")
            if supersedes is None and same_opening:
                if any(row["turn_bundle_root"] == value["turn_bundle_root"] for row in same_opening):
                    pass
                else:
                    raise HubRefusal("PIPPI_REPORT_AMENDMENT_REQUIRED")
            if supersedes is not None:
                targets = [row for row in same_opening if row["turn_bundle_root"] == supersedes]
                if len(targets) != 1:
                    raise HubRefusal("PIPPI_TURN_SUPERSESSION_TARGET_INVALID")
                if any(row.get("supersedes_turn_bundle_root") == supersedes
                       and row["turn_bundle_root"] != value["turn_bundle_root"]
                       for row in same_opening):
                    raise HubRefusal("PIPPI_TURN_SUPERSESSION_FORK_REFUSED")
            return self._store_project_record_locked(project_id=project["project_id"],
                record_kind="turn-record", record=value, root_field="turn_bundle_root",
                event_type="TURN_RECORD_SUBMITTED")

    def verify(self) -> dict[str, Any]:
        events=self._events(); projects=self.list_projects()
        if not self.onboarding.is_file(): raise HubRefusal("PIPPI_ONBOARDING_MISSING")
        onboard=validate_onboarding(strict_loads(self.onboarding.read_bytes()))
        integrations=self.integration_availability()
        if self.status.is_file():
            status=strict_loads(self.status.read_bytes())
            expected=events[-1]["event_root"] if events else None
            if status.get("journal_head")!=expected or status.get("event_count")!=len(events):
                raise HubRefusal("PIPPI_HUB_STATUS_INVALID")
        from .pippi_reviews import ReviewStore
        reviews=ReviewStore(self).list()
        body={"schema":"mosaic.ucm.pippi-hub-verification.v0.1",
              "onboarding_root":onboard["onboarding_root"],
              "integration_registry_root":integrations["integration_registry_root"],
              "journal_head":events[-1]["event_root"] if events else None,
              "event_count":len(events),"project_roots":sorted(p["project_root"] for p in projects),
              "review_record_roots":sorted(row["review_record_root"] for row in reviews),
              "protocol_channels":list(CHANNELS),"status":"PASS",**BOUNDARY}
        return {**body,"verification_root":root(body)}

