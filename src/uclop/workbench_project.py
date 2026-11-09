"""Project meaning/byte-graph adapter. A declared graph never proves completeness."""
from __future__ import annotations
import ast
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any
from .canonical import exact_keys, require, require_root, root
from . import project_intelligence as pi

OVERVIEW_ALLOWLIST = {"docs/WORKBENCH-C4-OVERVIEW.md"}
INCREMENTAL_ALLOWLIST = {"examples/project-intelligence/PCB-C2-C3-REPAIR.json": ["tests.test_ucm_project_intelligence", "tests.test_ucm_autonomous_project_manager"]}
CIRCUMSTANCES = {"DOCUMENTATION", "EXAMPLE_CHANGE", "APPLICATION_CHANGE", "TEST_CHANGE", "RUNTIME_CHANGE", "AUTHORITY_CHANGE", "CONTROL_PLANE_CHANGE", "PACKAGING_CHANGE", "FREEZE", "EXTERNAL_REVIEW", "UNKNOWN_IMPACT"}

def _path(value: Any) -> str:
    require(type(value) is str and value and "\\" not in value, "WORKBENCH_PATH_INVALID")
    p = PurePosixPath(value)
    require(not p.is_absolute() and ".." not in p.parts and p.as_posix() == value, "WORKBENCH_PATH_INVALID")
    return value

def source_graph(manifest: dict, *, expected_source_root: str) -> dict:
    exact_keys(manifest, {"schema", "files", "file_count", "source_root"})
    require(manifest["schema"] in {"ucl.ucm.workbench_c1_source_manifest.v1", "ucl.ucm.workbench_source_snapshot.v1"}, "WORKBENCH_SOURCE_SCHEMA_INVALID")
    body = {k: v for k, v in manifest.items() if k != "source_root"}
    require(manifest["source_root"] == require_root(expected_source_root) == root(body), "WORKBENCH_SOURCE_ROOT_MISMATCH")
    rows = manifest["files"]
    require(type(rows) is list and type(manifest["file_count"]) is int and manifest["file_count"] == len(rows), "WORKBENCH_SOURCE_COUNT_INVALID")
    paths = []
    for row in rows:
        exact_keys(row, {"path", "sha256", "bytes"})
        paths.append(_path(row["path"]))
        require_root(row["sha256"])
        require(type(row["bytes"]) is int and row["bytes"] >= 0, "WORKBENCH_SOURCE_SIZE_INVALID")
    require(paths == sorted(set(paths)), "WORKBENCH_SOURCE_PATH_SET_INVALID")
    nodes = [{**row, "kind": "HISTORICAL" if row["path"].startswith("historical/") else "SOURCE" if row["path"].startswith("src/") else "CONTRACT" if row["path"].startswith("spec/") else "MATERIAL"} for row in rows]
    graph = {"schema": "ucl.ucm.workbench.content_graph.v1", "source_root": expected_source_root, "nodes": nodes,
             "path_coverage": "ALL_BOUND_SOURCE_BYTES", "semantic_completeness": "NOT_ESTABLISHED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**graph, "graph_root": root(graph)}

def validate_source_bytes(workspace: Path, manifest: dict, *, expected_source_root: str) -> dict:
    graph = source_graph(manifest, expected_source_root=expected_source_root)
    base = workspace.resolve()
    for row in graph["nodes"]:
        p = base.joinpath(*PurePosixPath(row["path"]).parts)
        require(not p.is_symlink() and p.resolve().is_relative_to(base) and p.is_file(), "WORKBENCH_SOURCE_FILE_INVALID", row["path"])
        import hashlib
        data = p.read_bytes()
        require(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"], "WORKBENCH_SOURCE_BYTES_MISMATCH", row["path"])
    return graph

def choose_lane(changed_paths: list[str], circumstance: str, *, graph: dict,
                externally_pinned_graph_root: str, frozen_source_root: str | None = None,
                baseline_graph: dict | None = None,
                externally_pinned_baseline_graph_root: str | None = None) -> dict:
    """Derive changes from two pinned manifests before allowing a light lane."""
    require(type(changed_paths) is list and all(type(x) is str for x in changed_paths), "WORKBENCH_CHANGED_PATHS_INVALID")
    known = type(circumstance) is str and circumstance in CIRCUMSTANCES
    valid_graph = type(graph) is dict and graph.get("graph_root") == externally_pinned_graph_root == root({k: v for k, v in graph.items() if k != "graph_root"})
    paths = sorted(set(changed_paths))
    valid_paths = True
    for path in paths:
        try: _path(path)
        except ValueError: valid_paths = False
    baseline_valid = (type(baseline_graph) is dict
                      and baseline_graph.get("graph_root") == externally_pinned_baseline_graph_root
                      and baseline_graph.get("graph_root") == root({k: v for k, v in baseline_graph.items() if k != "graph_root"}))
    derived_paths: list[str] = []
    if valid_graph and baseline_valid:
        before = {row["path"]: (row["sha256"], row["bytes"]) for row in baseline_graph["nodes"]}
        after = {row["path"]: (row["sha256"], row["bytes"]) for row in graph["nodes"]}
        derived_paths = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    declaration_complete = baseline_valid and paths == derived_paths
    lane, modules, reason = "QUALIFICATION", [], "UNKNOWN_OR_SENSITIVE_IMPACT"
    if known and valid_graph and valid_paths:
        present = {n["path"] for n in graph["nodes"]}
        if not paths and circumstance == "EXTERNAL_REVIEW" and frozen_source_root == graph["source_root"]:
            lane, reason = "REVIEW", "EXACT_FROZEN_SUBJECT"
        elif not declaration_complete:
            reason = "BASELINE_DIFF_UNAVAILABLE_OR_DECLARATION_INCOMPLETE"
        elif paths and set(paths).issubset(present) and set(paths).issubset(OVERVIEW_ALLOWLIST) and circumstance == "DOCUMENTATION":
            lane, reason = "FAST", "ALLOWLISTED_NAVIGATION_ONLY"
            modules = ["tests.test_workbench_project"]
        elif paths and set(paths).issubset(present) and set(paths).issubset(INCREMENTAL_ALLOWLIST) and circumstance == "EXAMPLE_CHANGE":
            lane, reason = "INCREMENTAL", "EXACT_EXAMPLE_DEPENDENCY_CONTRACT"
            modules = sorted({m for p in paths for m in INCREMENTAL_ALLOWLIST[p]})
    body = {"schema": "ucl.ucm.workbench.lane_plan.v1", "lane": lane, "reason": reason, "changed_paths": paths,
            "derived_changed_paths": derived_paths, "change_declaration_complete": declaration_complete,
            "circumstance": circumstance if type(circumstance) is str else "INVALID", "source_root": graph.get("source_root") if type(graph) is dict else None,
            "graph_root": graph.get("graph_root") if type(graph) is dict else None,
            "baseline_graph_root": baseline_graph.get("graph_root") if type(baseline_graph) is dict else None,
            "selected_modules": modules,
            "reuse_permitted": False, "cache_policy": "DISABLED_REBUILD_FROM_SOURCE", "authority_effect": "NONE", "standing": "INFORMATION_ONLY"}
    return {**body, "plan_root": root(body)}


def validate_lane_plan(plan: Any, *, graph: dict, baseline_graph: dict | None = None,
                       expected_baseline_graph_root: str | None = None) -> dict:
    """Recompute a lane decision from the current byte graph.

    A plan is executable guidance only when its source and graph are current and
    every decision field is reproduced.  The plan cannot vouch for itself.
    """
    item = exact_keys(plan, {"schema", "lane", "reason", "changed_paths", "derived_changed_paths",
                             "change_declaration_complete", "circumstance", "source_root", "graph_root",
                             "baseline_graph_root", "selected_modules", "reuse_permitted",
                             "cache_policy", "authority_effect", "standing", "plan_root"})
    require(item["schema"] == "ucl.ucm.workbench.lane_plan.v1"
            and item["source_root"] == graph.get("source_root")
            and item["graph_root"] == graph.get("graph_root"),
            "WORKBENCH_LANE_PLAN_SOURCE_MISMATCH")
    if baseline_graph is not None or expected_baseline_graph_root is not None:
        require(type(baseline_graph) is dict
                and baseline_graph.get("graph_root") == expected_baseline_graph_root
                and item["baseline_graph_root"] == expected_baseline_graph_root,
                "WORKBENCH_LANE_PLAN_BASELINE_MISMATCH")
    rebuilt = choose_lane(item["changed_paths"], item["circumstance"], graph=graph,
                          externally_pinned_graph_root=graph["graph_root"],
                          frozen_source_root=graph["source_root"] if item["lane"] == "REVIEW" else None,
                          baseline_graph=baseline_graph,
                          externally_pinned_baseline_graph_root=expected_baseline_graph_root)
    require(item == rebuilt, "WORKBENCH_LANE_PLAN_INVALID")
    return deepcopy(item)

def project_view(project: dict, manifest: dict, *, expected_source_root: str) -> dict:
    pi.validate_project(project, expected_source_root=expected_source_root)
    graph = source_graph(manifest, expected_source_root=expected_source_root)
    declared = pi.impact_analysis(project, [], [])
    body = {"schema": "ucl.ucm.workbench.project_view.v1", "project_id": project["project_id"],
            "project_snapshot_root": project["snapshot_root"], "source_root": expected_source_root,
            "content_graph_root": graph["graph_root"], "records": deepcopy(project["records"]),
            "project_dependency_completeness": declared["impact_completeness"],
            "real_obligations_verified": 0, "minimum_execution_lane": "QUALIFICATION",
            "authority_effect": "NONE", "standing": "INFORMATION_ONLY"}
    return {**body, "view_root": root(body)}
