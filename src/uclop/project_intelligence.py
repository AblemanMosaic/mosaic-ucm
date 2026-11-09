"""Information-only UCM Project Intelligence prototype.

A *planning and evidence-inspection* tool, not a constitutional verifier,
authority provider, test executor, or deployment gate. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import unicodedata
from typing import Any

SCHEMA = "ucl.ucm.project_intelligence.snapshot.v1"
ROOT_DOMAIN = b"ucl.ucm.project_intelligence.snapshot.v1\0"
STANDING = "INFORMATION_ONLY"
AUTHORITY_EFFECT = "NONE"
C2_SOURCE_ROOT = "a8f5e4c254c105a0ea74f78eb3df6508d1c71edbc173774db303fac3c301dd4c"
KIND_PREFIX = {
    "REQUIREMENT": "REQ-",
    "DESIGN_DECISION": "DES-",
    "IMPLEMENTATION_ARTIFACT": "ART-",
    "VERIFICATION_OBLIGATION": "VER-",
    "AUTHORIZATION_DECISION": "AUTH-",
}
STATES = {
    "REQUIREMENT": {"OPEN", "DOCUMENTED", "SUPERSEDED"},
    "DESIGN_DECISION": {"PROPOSED", "DOCUMENTED", "SUPERSEDED"},
    "IMPLEMENTATION_ARTIFACT": {"PLANNED", "PRESENT"},
    "VERIFICATION_OBLIGATION": {"OPEN", "EVIDENCE_SUBMITTED"},
    "AUTHORIZATION_DECISION": {"CLOSED", "PROPOSED", "DOCUMENTED"},
}
EXTRA_FIELDS = {
    "REQUIREMENT": {"criterion"},
    "DESIGN_DECISION": {"rationale", "alternatives"},
    "IMPLEMENTATION_ARTIFACT": {"path", "sha256"},
    "VERIFICATION_OBLIGATION": {"evidence"},
    "AUTHORIZATION_DECISION": {"scope", "condition"},
}
COMMON_FIELDS = {"id", "kind", "title", "summary", "state", "depends_on"}
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", *("COM" + str(n) for n in range(1, 10)), *("LPT" + str(n) for n in range(1, 10))}
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 10_000


class ProjectError(ValueError):
    """A stable refusal with no authority effects."""


def refuse(code: str, detail: str = "") -> None:
    raise ProjectError(code + (": " + detail if detail else ""))


def exact_keys(value: Any, names: set[str], where: str) -> None:
    if type(value) is not dict or set(value) != names:
        refuse("PROJECT_SCHEMA_INVALID", where)


def nonempty(value: Any, where: str) -> None:
    if type(value) is not str or not value or value.strip() != value or any(ord(c) < 32 for c in value) or len(value) > 5000:
        refuse("PROJECT_FIELD_INVALID", where)


def sha(value: Any, where: str) -> None:
    if type(value) is not str or not SHA_RE.fullmatch(value):
        refuse("PROJECT_DIGEST_INVALID", where)


def strictly_sorted_unique(items: Any, where: str) -> None:
    if type(items) is not list or any(type(x) is not str for x in items) or items != sorted(set(items)):
        refuse("PROJECT_ORDER_INVALID", where)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")


def rooted(body: dict[str, Any]) -> str:
    return hashlib.sha256(ROOT_DOMAIN + canonical(body)).hexdigest()


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in pairs:
        if key in out:
            refuse("PROJECT_DUPLICATE_JSON_KEY", key)
        out[key] = val
    return out


def strict_load(raw: bytes) -> Any:
    if len(raw) > MAX_JSON_BYTES:
        refuse("PROJECT_DOCUMENT_TOO_LARGE")
    try:
        return json.loads(raw, object_pairs_hook=_pairs_unique,
                          parse_constant=lambda x: refuse("PROJECT_NONFINITE_NUMBER", x))
    except ProjectError:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        refuse("PROJECT_JSON_INVALID", str(exc))


def portable_path(name: Any) -> str:
    if type(name) is not str or not name or len(name) > 1024 or name.startswith("/") or "\\" in name or ":" in name:
        refuse("PROJECT_PATH_INVALID", str(name))
    parts = name.split("/")
    if any(p in ("", ".", "..") or p.endswith((" ", ".")) or any(ord(c) < 32 or c in '<>"|?*' for c in p)
           or p.split(".")[0].upper() in WINDOWS_DEVICES for p in parts):
        refuse("PROJECT_PATH_INVALID", name)
    return name


def safe_file(workspace: Path, relative: str) -> bytes:
    """Read a non-link local file without traversing symlink ancestors.

    This is an inspector, not a TOCTOU-proof protected-path verifier. Caller
    must supply a trusted non-concurrently-modified workspace.
    """
    portable_path(relative)
    try:
        base = workspace.resolve(strict=True)
        if not base.is_dir():
            refuse("PROJECT_WORKSPACE_INVALID")
        candidate = base
        parts = relative.split("/")
        for index, part in enumerate(parts):
            candidate = candidate / part
            st = candidate.lstat()
            if stat.S_ISLNK(st.st_mode):
                refuse("PROJECT_PATH_LINK_REFUSED", relative)
            if index < len(parts) - 1 and not stat.S_ISDIR(st.st_mode):
                refuse("PROJECT_PATH_NOT_DIRECTORY", relative)
        if not stat.S_ISREG(st.st_mode):
            refuse("PROJECT_NOT_REGULAR_FILE", relative)
        if st.st_size > MAX_JSON_BYTES:
            refuse("PROJECT_FILE_TOO_LARGE", relative)
        with candidate.open("rb") as handle:
            data = handle.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            refuse("PROJECT_FILE_TOO_LARGE", relative)
        return data
    except (FileNotFoundError, PermissionError, OSError) as exc:
        refuse("PROJECT_FILE_UNAVAILABLE", relative + " (" + type(exc).__name__ + ")")


def _check_assertions(checks: Any, label: str) -> None:
    if type(checks) is not list or not checks or len(checks) > 100:
        refuse("PROJECT_EVIDENCE_CHECKS_INVALID", label)
    paths: list[str] = []
    for i, check in enumerate(checks):
        exact_keys(check, {"pointer", "equals"}, label + "/" + str(i))
        pointer = check["pointer"]
        if type(pointer) is not str or not pointer.startswith("/") or pointer == "/" or len(pointer) > 512:
            refuse("PROJECT_EVIDENCE_POINTER_INVALID", label)
        if type(check["equals"]) not in (str, bool, int, type(None)):
            refuse("PROJECT_EVIDENCE_EXPECTED_INVALID", label)
        paths.append(pointer)
    strictly_sorted_unique(paths, label + "/pointers")


def _verify_record_shape(record: Any) -> None:
    if type(record) is not dict or type(record.get("kind")) is not str or record["kind"] not in KIND_PREFIX:
        refuse("PROJECT_RECORD_KIND_INVALID")
    kind = record["kind"]
    exact_keys(record, COMMON_FIELDS | EXTRA_FIELDS[kind], kind)
    nonempty(record["id"], "id")
    if not ID_RE.fullmatch(record["id"]) or not record["id"].startswith(KIND_PREFIX[kind]):
        refuse("PROJECT_RECORD_ID_INVALID", record["id"])
    nonempty(record["title"], record["id"] + "/title")
    nonempty(record["summary"], record["id"] + "/summary")
    if type(record["state"]) is not str or record["state"] not in STATES[kind]:
        refuse("PROJECT_RECORD_STATE_INVALID", record["id"])
    strictly_sorted_unique(record["depends_on"], record["id"] + "/depends_on")
    if record["id"] in record["depends_on"]:
        refuse("PROJECT_SELF_DEPENDENCY", record["id"])
    if kind == "REQUIREMENT":
        nonempty(record["criterion"], record["id"] + "/criterion")
    elif kind == "DESIGN_DECISION":
        nonempty(record["rationale"], record["id"] + "/rationale")
        strictly_sorted_unique(record["alternatives"], record["id"] + "/alternatives")
    elif kind == "IMPLEMENTATION_ARTIFACT":
        portable_path(record["path"])
        if record["state"] == "PRESENT":
            sha(record["sha256"], record["id"])
        elif record["sha256"] is not None:
            refuse("PROJECT_PLANNED_ARTIFACT_PIN_INVALID", record["id"])
    elif kind == "VERIFICATION_OBLIGATION":
        evidence = record["evidence"]
        if type(evidence) is not list or len(evidence) > 12:
            refuse("PROJECT_EVIDENCE_INVALID", record["id"])
        if record["state"] == "OPEN" and evidence:
            refuse("PROJECT_OPEN_HAS_EVIDENCE", record["id"])
        if record["state"] == "EVIDENCE_SUBMITTED" and not evidence:
            refuse("PROJECT_EVIDENCE_MISSING", record["id"])
        paths = []
        for i, row in enumerate(evidence):
            label = record["id"] + "/evidence/" + str(i)
            exact_keys(row, {"path", "sha256", "assertions"}, label)
            portable_path(row["path"])
            sha(row["sha256"], label)
            _check_assertions(row["assertions"], label)
            paths.append(row["path"])
        strictly_sorted_unique(paths, record["id"] + "/evidence_paths")
    else:
        if record["scope"] != "REVIEW_RECOMMENDATION_ONLY":
            refuse("PROJECT_AUTHORITY_SCOPE_INVALID", record["id"])
        nonempty(record["condition"], record["id"] + "/condition")


def validate_project(doc: Any, *, expected_source_root: str | None = None) -> dict[str, Any]:
    exact_keys(doc, {"schema", "project_id", "baseline", "standing", "authority_effect", "records", "snapshot_root"}, "document")
    if doc["schema"] != SCHEMA or doc["standing"] != STANDING or doc["authority_effect"] != AUTHORITY_EFFECT:
        refuse("PROJECT_BOUNDARY_INVALID")
    nonempty(doc["project_id"], "project_id")
    base = doc["baseline"]
    exact_keys(base, {"subject", "source_root", "review_disposition"}, "baseline")
    nonempty(base["subject"], "baseline/subject")
    sha(base["source_root"], "baseline/source_root")
    if type(base["review_disposition"]) is not str or base["review_disposition"] not in ("HOLD_FOR_REPAIR", "UNREVIEWED", "QUALIFIED_RECOMMENDATION_ONLY"):
        refuse("PROJECT_BASELINE_DISPOSITION_INVALID")
    if expected_source_root is not None and base["source_root"] != expected_source_root:
        refuse("PROJECT_BASELINE_PIN_MISMATCH")
    records = doc["records"]
    if type(records) is not list or not records or len(records) > MAX_RECORDS:
        refuse("PROJECT_RECORD_SET_INVALID")
    for record in records:
        _verify_record_shape(record)
    ids = [r["id"] for r in records]
    strictly_sorted_unique(ids, "records")
    nodes = {r["id"]: r for r in records}
    for item in records:
        deps = item["depends_on"]
        if any(dep not in nodes for dep in deps):
            refuse("PROJECT_UNKNOWN_DEPENDENCY", item["id"])
        kind = item["kind"]
        kinds = {nodes[dep]["kind"] for dep in deps}
        if kind == "DESIGN_DECISION" and "REQUIREMENT" not in kinds:
            refuse("PROJECT_DECISION_UNTRACED", item["id"])
        if kind == "IMPLEMENTATION_ARTIFACT" and not (kinds & {"REQUIREMENT", "DESIGN_DECISION"}):
            refuse("PROJECT_ARTIFACT_UNTRACED", item["id"])
        if kind == "VERIFICATION_OBLIGATION" and not (kinds & {"REQUIREMENT", "IMPLEMENTATION_ARTIFACT", "DESIGN_DECISION"}):
            refuse("PROJECT_OBLIGATION_UNTRACED", item["id"])
        if kind == "AUTHORIZATION_DECISION" and "VERIFICATION_OBLIGATION" not in kinds:
            refuse("PROJECT_AUTHORIZATION_UNTRACED", item["id"])
        if kind == "REQUIREMENT" and deps and any(nodes[d]["kind"] != "REQUIREMENT" for d in deps):
            refuse("PROJECT_REQUIREMENT_DEPENDENCY_INVALID", item["id"])
    # Refuse ambiguous logical file paths, including case/Unicode aliases
    # among implicit directory components on case-insensitive targets.
    portable_nodes: dict[str, tuple[str, str]] = {}
    for item in records:
        if item["kind"] != "IMPLEMENTATION_ARTIFACT":
            continue
        parts = item["path"].split("/")
        for offset in range(1, len(parts) + 1):
            prefix = "/".join(parts[:offset])
            key = unicodedata.normalize("NFC", prefix).casefold()
            node_type = "FILE" if offset == len(parts) else "DIRECTORY"
            previous = portable_nodes.get(key)
            if previous is not None and previous != (prefix, node_type):
                refuse("PROJECT_PATH_ALIAS_INVALID", item["id"])
            if previous is not None and node_type == "FILE":
                refuse("PROJECT_ARTIFACT_PATH_DUPLICATE", prefix)
            portable_nodes[key] = (prefix, node_type)
    # Iterative cycle check, bounded by validated input size.
    indegree = {n: len(nodes[n]["depends_on"]) for n in nodes}
    consumers: dict[str, list[str]] = {n: [] for n in nodes}
    for r in records:
        for dep in r["depends_on"]:
            consumers[dep].append(r["id"])
    ready = sorted(n for n in nodes if indegree[n] == 0)
    popped = 0
    from collections import deque
    queue = deque(ready)
    while queue:
        n = queue.popleft()
        popped += 1
        for consumer in sorted(consumers[n]):
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                queue.append(consumer)
    if popped != len(records):
        refuse("PROJECT_DEPENDENCY_CYCLE")
    sha(doc["snapshot_root"], "snapshot_root")
    body = {key: value for key, value in doc.items() if key != "snapshot_root"}
    if rooted(body) != doc["snapshot_root"]:
        refuse("PROJECT_SNAPSHOT_ROOT_MISMATCH")
    return nodes


def load_project(path: Path, *, expected_source_root: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        doc = strict_load(path.read_bytes())
    except (OSError, PermissionError) as exc:
        refuse("PROJECT_SNAPSHOT_UNAVAILABLE", type(exc).__name__)
    return doc, validate_project(doc, expected_source_root=expected_source_root)


def _pointer(document: Any, pointer: str) -> tuple[bool, Any]:
    cursor = document
    for token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", token):
            return False, None
        token = token.replace("~1", "/").replace("~0", "~")
        if type(cursor) is dict and token in cursor:
            cursor = cursor[token]
        elif type(cursor) is list and re.fullmatch(r"(?:0|[1-9][0-9]*)", token) and int(token) < len(cursor):
            cursor = cursor[int(token)]
        else:
            return False, None
    return True, cursor


def inspect_evidence(row: dict[str, Any], workspace: Path) -> dict[str, Any]:
    path = row["path"]
    try:
        blob = safe_file(workspace, path)
        if hashlib.sha256(blob).hexdigest() != row["sha256"]:
            return {"path": path, "status": "DIGEST_MISMATCH"}
        obj = strict_load(blob)
    except ProjectError as exc:
        return {"path": path, "status": "EVIDENCE_UNAVAILABLE_OR_INVALID", "reason": str(exc)}
    for check in row["assertions"]:
        found, actual = _pointer(obj, check["pointer"])
        if not found or type(actual) is not type(check["equals"]) or actual != check["equals"]:
            return {"path": path, "status": "ASSERTION_MISMATCH", "pointer": check["pointer"]}
    return {"path": path, "status": "DECLARED_CHECKS_MATCH", "sha256": row["sha256"]}


def inspect_artifact(row: dict[str, Any], workspace: Path) -> dict[str, Any]:
    if row["state"] == "PLANNED":
        return {"id": row["id"], "path": row["path"], "status": "PLANNED_UNVERIFIED"}
    try:
        blob = safe_file(workspace, row["path"])
    except ProjectError as exc:
        return {"id": row["id"], "path": row["path"], "status": "UNAVAILABLE", "reason": str(exc)}
    if hashlib.sha256(blob).hexdigest() != row["sha256"]:
        return {"id": row["id"], "path": row["path"], "status": "DIGEST_MISMATCH"}
    return {"id": row["id"], "path": row["path"], "status": "BYTES_MATCH_PIN"}


def project_dashboard(doc: dict[str, Any], workspace: Path) -> dict[str, Any]:
    nodes = validate_project(doc)
    artifacts = [inspect_artifact(r, workspace) for r in doc["records"] if r["kind"] == "IMPLEMENTATION_ARTIFACT"]
    obligations = []
    for r in doc["records"]:
        if r["kind"] != "VERIFICATION_OBLIGATION":
            continue
        evidences = [inspect_evidence(e, workspace) for e in r["evidence"]]
        state = "EVIDENCE_CONSISTENT_NOT_INDEPENDENTLY_QUALIFIED" if evidences and all(e["status"] == "DECLARED_CHECKS_MATCH" for e in evidences) else "OPEN_OR_UNCONFIRMED"
        obligations.append({"id": r["id"], "declared_state": r["state"], "assessment": state, "evidence": evidences})
    counts = {kind: sum(r["kind"] == kind for r in nodes.values()) for kind in KIND_PREFIX}
    pending = sorted(r["id"] for r in doc["records"] if r["kind"] == "AUTHORIZATION_DECISION")
    return {
        "schema": "ucl.ucm.project_intelligence.dashboard.v1",
        "project_id": doc["project_id"], "snapshot_root": doc["snapshot_root"],
        "baseline": doc["baseline"], "counts_by_kind": counts,
        "artifacts": artifacts, "obligations": obligations,
        "authorization_records": pending,
        "review_disposition": "REVIEW_REQUIRED",
        "release_authorized": False,
        "notes": ["Evidence integrity and declared JSON-field checks do not prove checker correctness or execution provenance.",
                  "No record, including DOCUMENTED authorizations, grants runtime or constitutional authority."],
        "standing": STANDING, "authority_effect": AUTHORITY_EFFECT,
    }


def impact_analysis(doc: dict[str, Any], changed_ids: list[str], changed_paths: list[str] | None = None) -> dict[str, Any]:
    nodes = validate_project(doc)
    paths = changed_paths or []
    for name in paths:
        portable_path(name)
    path_index: dict[str, list[str]] = {}
    for r in nodes.values():
        if r["kind"] == "IMPLEMENTATION_ARTIFACT":
            path_index.setdefault(r["path"], []).append(r["id"])
    unknown_paths = sorted(set(p for p in paths if p not in path_index))
    unknown_ids = sorted(set(i for i in changed_ids if i not in nodes))
    selected = set(changed_ids) & nodes.keys()
    for p in paths:
        selected.update(path_index.get(p, []))
    parents: dict[str, set[str]] = {k: set() for k in nodes}
    for r in nodes.values():
        for dep in r["depends_on"]:
            parents[dep].add(r["id"])
    depth: dict[str, int] = {r: 0 for r in selected}
    from collections import deque
    queue = deque(sorted(selected))
    while queue:
        item = queue.popleft()
        for parent in sorted(parents[item]):
            if parent not in depth or depth[parent] > depth[item] + 1:
                depth[parent] = depth[item] + 1
                queue.append(parent)
    impacted = sorted(depth)
    by_kind = {kind: [n for n in impacted if nodes[n]["kind"] == kind] for kind in KIND_PREFIX}
    # This mapping is a declared project subgraph. Completeness of all UCM
    # constitutional/frozen dependencies has *not* been established.
    return {
        "schema": "ucl.ucm.project_intelligence.impact.v1",
        "project_id": doc["project_id"], "snapshot_root": doc["snapshot_root"],
        "selected_changed_ids": sorted(selected),
        "unknown_changed_ids": unknown_ids,
        "unknown_changed_paths": unknown_paths,
        "impact_completeness": "UNKNOWN_OUTSIDE_DECLARED_GRAPH",
        "impacted": [{"id": n, "kind": nodes[n]["kind"], "dependency_distance": depth[n]} for n in impacted],
        "impacted_by_kind": by_kind,
        "recheck_obligations": by_kind["VERIFICATION_OBLIGATION"],
        "review_authorizations": by_kind["AUTHORIZATION_DECISION"],
        "minimum_review_lane_recommendation": "QUALIFICATION",
        "review_disposition": "REVIEW_REQUIRED",
        "standing": STANDING, "authority_effect": AUTHORITY_EFFECT,
    }


def work_order(doc: dict[str, Any], impact: dict[str, Any], workspace: Path) -> dict[str, Any]:
    dashboard = project_dashboard(doc, workspace)
    evidence_by_id = {r["id"]: r for r in dashboard["obligations"]}
    nodes = {r["id"]: r for r in doc["records"]}
    tasks = []
    for row in sorted(impact["impacted"], key=lambda r: (r["dependency_distance"], r["id"])):
        record = nodes[row["id"]]
        task = {"id": row["id"], "kind": row["kind"], "title": record["title"],
                "dependency_distance": row["dependency_distance"],
                "action": "REASSESS_AND_REVALIDATE" if row["dependency_distance"] else "INSPECT_REQUESTED_CHANGE"}
        if row["kind"] == "VERIFICATION_OBLIGATION":
            task["evidence_assessment"] = evidence_by_id[row["id"]]["assessment"]
            task["action"] = "REEXECUTE_REQUIRED_CHECK_AND_REVIEW_EVIDENCE"
        if row["kind"] == "AUTHORIZATION_DECISION":
            task["action"] = "KEEP_CLOSED_PENDING_INDEPENDENT_DISPOSITION"
        tasks.append(task)
    return {
        "schema": "ucl.ucm.project_intelligence.work_order.v1",
        "project_id": doc["project_id"], "snapshot_root": doc["snapshot_root"],
        "baseline_source_root": doc["baseline"]["source_root"],
        "changed": impact["selected_changed_ids"],
        "unknown_changed_ids": impact["unknown_changed_ids"],
        "unknown_changed_paths": impact["unknown_changed_paths"],
        "tasks": tasks,
        "required_qualification": "FULL_FRESH_QUALIFICATION_RECOMMENDED",
        "preserve_frozen_predecessors": True,
        "advance_authority": False,
        "disposition": "REVIEW_REQUIRED",
        "standing": STANDING, "authority_effect": AUTHORITY_EFFECT,
    }


def work_order_markdown(order: dict[str, Any]) -> str:
    lines = ["# UCM Project Intelligence — review work order", "",
             "**Project:** " + order["project_id"],
             "**Pinned snapshot:** `" + order["snapshot_root"] + "`",
             "**Frozen source baseline:** `" + order["baseline_source_root"] + "`",
             "**Standing:** INFORMATION_ONLY; **authority effect:** NONE; **disposition:** REVIEW_REQUIRED", "",
             "This is a planning proposal only. It is not an executed test result, accepted court, or deployment authorization.", "",
             "## Requested changes", ""]
    lines += ["- `" + x + "`" for x in order["changed"]] or ["- None among known records"]
    if order["unknown_changed_ids"] or order["unknown_changed_paths"]:
        lines += ["", "**Unknown input; impact is not complete:**"]
        lines += ["- `" + x + "`" for x in order["unknown_changed_ids"] + order["unknown_changed_paths"]]
    lines += ["", "## Work items", ""]
    for task in order["tasks"]:
        lines.append("- [ ] **" + task["id"] + "** — " + task["title"] + " — " + task["action"])
    lines += ["", "## Gates", "", "- Fresh qualification is recommended; do not silently downgrade to FAST or INCREMENTAL.",
              "- Independently verify each required obligation and its evidence.",
              "- Preserve frozen c2 bytes. Implement changes in a separately pinned successor.",
              "- Authorization remains closed; no installation, publication, release, real A5 or G0 transition.", ""]
    return "\n".join(lines)
