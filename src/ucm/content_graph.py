"""Conservative content-addressed project graph and qualification planning."""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

from uclop.canonical import canonical_bytes, require, root, strict_loads


EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "dist", ".build"}
SENSITIVE_PREFIXES = ("src/", "tools/", "spec/", "tests/", "campaign/", "skill/")
GROUPS = {
    "IDENTITY": ("src/ucm/identity.py", "tests/test_integration_identity.py"),
    "AMCAS": ("src/ucm/amcas.py", "spec/", "tests/test_amcas_integration.py"),
    "JOURNAL": ("src/ucm/journal.py", "src/ucm/reporting.py", "tests/test_integration_journal.py"),
    "GATEWAY": ("src/ucm/integration.py", "tests/test_integration_gateway.py"),
    "PACKAGING": ("src/ucm/artifacts.py", "tools/", "tests/test_integration_artifacts.py"),
    "PUBLIC_SURFACE": ("src/ucm/cli.py", "src/ucm/system.py", "src/ucm/capabilities.py"),
    "INTEGRATION_BOUNDARY": ("src/ucm/subject.py", "src/ucm/control_planes.py",
                              "src/ucm/correspondence.py", "tests/test_integration_subject_c2.py",
                              "tests/test_integration_control_planes_c2.py",
                              "tests/test_integration_correspondence_c2.py"),
    "STAGE_I1": ("src/ucm/stage1.py", "tests/test_integration_stage1_c2.py"),
    "PORTFOLIO": ("src/ucm/portfolio.py", "tests/test_integration_portfolio_c2.py"),
}


def _portable(path: Path, base: Path) -> str:
    value = path.relative_to(base).as_posix()
    require(value == PurePosixPath(value).as_posix() and ".." not in PurePosixPath(value).parts,
            "GRAPH_PATH_INVALID")
    return value


def build_graph(workspace: Path, *, excluded_prefixes: tuple[str, ...] = ()) -> dict[str, Any]:
    workspace = Path(workspace)
    require(type(excluded_prefixes) is tuple
            and all(type(value) is str and value == PurePosixPath(value).as_posix()
                    and value and ".." not in PurePosixPath(value).parts
                    for value in excluded_prefixes), "GRAPH_EXCLUSIONS_INVALID")
    rows = []
    by_digest: dict[str, list[str]] = {}
    for path in sorted((path for path in workspace.rglob("*") if path.is_file()),
                       key=lambda item: item.relative_to(workspace).as_posix()):
        relative = _portable(path, workspace)
        if any(part in EXCLUDED_PARTS for part in PurePosixPath(relative).parts):
            continue
        if any(relative == prefix or relative.startswith(prefix.rstrip("/") + "/")
               for prefix in excluded_prefixes):
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        row: dict[str, Any] = {"path": relative, "bytes": len(raw), "sha256": digest,
                               "kind": _kind(relative), "referenced_roots": []}
        if path.suffix.lower() == ".json":
            try:
                value = strict_loads(raw)
                roots: set[str] = set()
                pending = [value]
                while pending:
                    current = pending.pop()
                    if type(current) is dict:
                        pending.extend(current.values())
                    elif type(current) is list:
                        pending.extend(current)
                    elif type(current) is str and len(current) == 64 and all(ch in "0123456789abcdef" for ch in current):
                        roots.add(current)
                row["referenced_roots"] = sorted(roots)
            except Exception:
                row["json_status"] = "NOT_CANONICAL_JSON"
        rows.append(row)
        by_digest.setdefault(digest, []).append(relative)
    known = set(by_digest)
    edges = [{"from": row["path"], "to_sha256": digest,
              "resolved_paths": by_digest.get(digest, [])}
             for row in rows for digest in row["referenced_roots"] if digest in known]
    body = {"schema": "mosaic.ucm.integration-content-graph.v0.1",
            "workspace_file_count": len(rows), "nodes": rows, "edges": edges,
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "graph_root": root(body)}


def _kind(path: str) -> str:
    if path.startswith("src/"):
        return "SOURCE"
    if path.startswith("tests/"):
        return "COURT"
    if path.startswith("spec/") or path.endswith("CONTRACT.json"):
        return "CONTRACT"
    if path.startswith("campaign/"):
        return "CAMPAIGN_STATE"
    if path.startswith("tools/"):
        return "TOOL"
    if path.startswith("skill/"):
        return "AGENT_INTERFACE"
    return "ARTIFACT"


def impact_plan(changed_paths: list[str]) -> dict[str, Any]:
    require(type(changed_paths) is list and all(type(path) is str for path in changed_paths),
            "IMPACT_PATHS_INVALID")
    normalized = sorted(set(PurePosixPath(path).as_posix() for path in changed_paths))
    selected = set()
    unknown = False
    for path in normalized:
        matched = False
        for group, prefixes in GROUPS.items():
            if any(path == prefix or path.startswith(prefix) for prefix in prefixes):
                selected.add(group); matched = True
        if path.startswith("docs/") or path in {"README.md", "NOTICE", "LICENSE"}:
            selected.add("DOCUMENTATION"); matched = True
        if not matched or path.startswith(SENSITIVE_PREFIXES):
            unknown = unknown or not matched
    lane = "QUALIFICATION" if unknown or any(path.startswith(SENSITIVE_PREFIXES) for path in normalized) else "FAST"
    if not normalized:
        lane = "FAST"
    body = {"schema": "mosaic.ucm.impact-plan.v0.1", "changed_paths": normalized,
            "selected_groups": sorted(selected), "unknown_impact": unknown,
            "lane": lane, "cache_allowed": lane != "QUALIFICATION",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "plan_root": root(body)}
