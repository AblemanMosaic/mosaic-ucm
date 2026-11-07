from __future__ import annotations

import ast
import hashlib
import pathlib
import unicodedata
from typing import Any

from .canonical import require, require_root, root


LANES = ("FAST", "INCREMENTAL", "QUALIFICATION", "REVIEW")
QUALIFICATION_CIRCUMSTANCES = {
    "AUTHORITY_CHANGE", "COMPILER_CHANGE", "CONTROL_PLANE_CHANGE", "CUSTODY_CHANGE",
    "DEPLOYMENT_CHANGE", "FREEZE", "RELEASE_CANDIDATE", "SCHEDULER_CHANGE",
    "UNKNOWN_IMPACT", "VERIFIER_CHANGE",
}
KNOWN_CIRCUMSTANCES = QUALIFICATION_CIRCUMSTANCES | {"DOCUMENTATION", "EXTERNAL_REVIEW", "RUNTIME_CHANGE", "TEST_CHANGE"}
FAST_DOC_ALLOWLIST = {
    "docs/OEF-C1-TECHNICAL-BRIEF.md",
}
SENSITIVE_PREFIXES = (
    "src/uclop/canonical.py", "src/uclop/custody", "src/uclop/deployment_contracts.py",
    "src/uclop/effect_mediator.py", "src/uclop/foundation_runtime.py", "src/uclop/control_plane.py",
    "tools/freeze", "tools/replay", "tools/run_", "tools/court_", "tools/protected_execution_guard.py", "tools/oef_external_verify.py", "spec/OEF-C1-STAGE-CONTRACTS.json",
    "spec/OEF-C1-FOUNDATION-CONTRACT.json", "docs/OEF-C1-CHARTER.md",
)


def _normalize_path(value: Any) -> str:
    require(type(value) is str and value and "\\" not in value and not value.startswith("/"), "COURT_PATH_INVALID")
    require(unicodedata.normalize("NFC", value) == value, "COURT_PATH_INVALID")
    path = pathlib.PurePosixPath(value)
    require(".." not in path.parts and "." not in path.parts, "COURT_PATH_INVALID")
    return path.as_posix()


def build_content_graph(workspace: pathlib.Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    included_prefixes = ("src/uclop", "tests", "tools", "spec", "docs", "planning")
    excluded_names = {"__pycache__", ".pytest_cache"}
    rows: list[dict[str, Any]] = []
    path_set: set[str] = set()
    for prefix in included_prefixes:
        base = workspace / prefix
        if not base.exists():
            continue
        for path in sorted((item for item in base.rglob("*") if item.is_file() and not any(part in excluded_names for part in item.parts)), key=lambda item: item.relative_to(workspace).as_posix()):
            relative = path.relative_to(workspace).as_posix()
            data = path.read_bytes()
            rows.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
            path_set.add(relative)
    edges: list[dict[str, str]] = []
    module_paths = {"uclop." + pathlib.PurePosixPath(row["path"]).stem: row["path"] for row in rows if row["path"].startswith("src/uclop/") and row["path"].endswith(".py")}
    for row in rows:
        if not row["path"].endswith(".py"):
            continue
        try:
            tree = ast.parse((workspace / row["path"]).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError):
            continue
        dependencies: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level and row["path"].startswith("src/uclop/"):
                    for alias in node.names:
                        candidate = f"src/uclop/{alias.name}.py" if node.module is None else f"src/uclop/{node.module.split('.')[-1]}.py"
                        if candidate in path_set: dependencies.add(candidate)
                elif node.module:
                    candidate = module_paths.get(node.module)
                    if candidate: dependencies.add(candidate)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    candidate = module_paths.get(alias.name)
                    if candidate: dependencies.add(candidate)
        for dependency in sorted(dependencies):
            edges.append({"source": row["path"], "depends_on": dependency})
    body = {"schema": "ucl.ucm.oef_content_graph.v1", "files": rows, "edges": edges, "file_count": len(rows), "edge_count": len(edges)}
    return {**body, "graph_root": root(body)}


def plan_courts(*, changed_paths: list[str], circumstance: str, baseline_graph_root: str | None, current_graph: dict[str, Any], requested_lane: str | None = None) -> dict[str, Any]:
    require(type(changed_paths) is list, "COURT_CHANGED_PATHS_INVALID")
    normalized = sorted({_normalize_path(value) for value in changed_paths})
    circumstance_valid = type(circumstance) is str and circumstance == circumstance.strip().upper() and circumstance in KNOWN_CIRCUMSTANCES
    require(requested_lane is None or requested_lane in LANES, "COURT_LANE_INVALID")
    current_root = require_root(current_graph.get("graph_root"))
    files = {row["path"] for row in current_graph.get("files", [])}
    unknown = not normalized or any(path not in files for path in normalized)
    if circumstance == "EXTERNAL_REVIEW" and not normalized:
        lane, basis = "REVIEW", "FROZEN_BYTES_EXTERNAL_REVIEW"
    elif not circumstance_valid or baseline_graph_root is None or circumstance in QUALIFICATION_CIRCUMSTANCES or unknown or any(path.casefold().startswith(tuple(prefix.casefold() for prefix in SENSITIVE_PREFIXES)) for path in normalized):
        lane, basis = "QUALIFICATION", "SENSITIVE_OR_UNKNOWN_IMPACT"
    elif normalized and all(path in FAST_DOC_ALLOWLIST for path in normalized):
        lane, basis = "FAST", "EXPLICIT_DOCUMENT_ALLOWLIST"
    else:
        require_root(baseline_graph_root)
        lane, basis = "INCREMENTAL", "CONTENT_GRAPH_DEPENDENCY_SELECTION"
    rank = {"FAST": 0, "INCREMENTAL": 1, "QUALIFICATION": 2, "REVIEW": 3}
    if requested_lane is not None:
        require(rank[requested_lane] >= rank[lane], "COURT_LANE_DOWNGRADE_REFUSED")
        escalated = requested_lane != lane
        lane = requested_lane
        basis += ":CALLER_ESCALATED" if escalated else ""
    reverse: dict[str, set[str]] = {}
    for edge in current_graph.get("edges", []):
        reverse.setdefault(edge["depends_on"], set()).add(edge["source"])
    impacted = set(normalized)
    frontier = list(normalized)
    while frontier:
        dependency = frontier.pop()
        for consumer in reverse.get(dependency, set()):
            if consumer not in impacted:
                impacted.add(consumer); frontier.append(consumer)
    selected_tests = sorted(path for path in impacted if path.startswith("tests/test_") and path.endswith(".py"))
    if lane == "QUALIFICATION":
        selected_courts = ["INHERITED_43_PHASE", "LEGACY_C6_148", "OEF_FULL_TESTS", "OEF_INVARIANT", "OEF_FAULT", "DETERMINISTIC_FREEZE"]
    elif lane == "INCREMENTAL":
        selected_courts = selected_tests + ["tools/oef_c1_invariant_court.py"]
    elif lane == "FAST":
        selected_courts = ["STATIC_SCHEMA_AND_LINK_CHECK"]
    else:
        selected_courts = ["CUSTODY", "TARGETED_ADVERSARIAL", "QUALIFICATION_ON_TRIGGER"]
    body = {
        "schema": "ucl.ucm.oef_court_plan.v1", "changed_paths": normalized, "circumstance": circumstance if type(circumstance) is str else "INVALID", "circumstance_valid": circumstance_valid,
        "baseline_graph_root": baseline_graph_root, "current_graph_root": current_root,
        "lane": lane, "basis": basis, "unknown_impact": unknown or not circumstance_valid, "selected_courts": selected_courts,
        "cache_policy": "DISABLED" if lane in {"QUALIFICATION", "REVIEW"} else "CONTENT_ADDRESSED_EPHEMERAL",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "plan_root": root(body)}

