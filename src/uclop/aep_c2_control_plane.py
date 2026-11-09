from __future__ import annotations

import ast
import hashlib
import pathlib
from typing import Any

from .canonical import exact_keys, require, require_root, root


LANES = ("FAST", "INCREMENTAL", "QUALIFICATION", "REVIEW")
PREDECESSOR_SOURCE_ROOT = "34017dedf746b21d3d969992d63580c0eaf05ed55e7a52bd3825da4d30d705a4"
PREDECESSOR_QUALIFICATION_ROOT = "2bf77e084ca11e5e5cab3e92463f3c4298f2875844f253e033693302071ee7ce"
PREDECESSOR_TRANSPORT_SHA256 = "68e8c9cafcbcda3391aee2b10c2cdc839b5e3ded86c5e03c4bd67bbe502ca401"
SCANNED_ROOTS = ("src/uclop", "tests", "tools", "spec", "docs", "planning", "evidence/aep-c2-inputs")
GRAPH_EXCLUSIONS = {
    "planning/AEP-C2-CONTROL-BASELINE.json",
    "planning/AEP-C2-STATE-CAPSULE.json",
}
FAST_ALLOWLIST = {
    "docs/AEP-C2-OVERVIEW.md",
    "docs/AEP-C2-SYSTEM-MAP.md",
    "docs/AEP-C2-OPERATOR-GUIDE.md",
}
QUALIFICATION_CIRCUMSTANCES = {
    "AUTHORITY_CHANGE", "BOUNDARY_CHANGE", "CACHE_CHANGE", "CONTROL_PLANE_CHANGE", "COURT_CHANGE",
    "CUSTODY_CHANGE", "FREEZE", "PACKAGING_CHANGE", "PROTECTED_EXECUTION_CHANGE", "RELEASE_CANDIDATE",
    "RUNTIME_CHANGE", "SCHEDULER_CHANGE", "UNKNOWN_IMPACT", "VERIFIER_CHANGE",
}
KNOWN_CIRCUMSTANCES = QUALIFICATION_CIRCUMSTANCES | {
    "APPLICATION_CHANGE", "DOCUMENTATION", "EXTERNAL_REVIEW", "TEST_CHANGE",
}
SENSITIVE_PREFIXES = (
    "src/uclop/aep_c2_control_plane.py",
    "src/uclop/application_supervisor.py",
    "src/uclop/canonical.py",
    "src/uclop/platform_kernel",
    "src/uclop/platform_workbench",
    "src/uclop/protected_execution",
    "tools/aep_c2_",
    "tools/build_aep_c2_evidence.py",
    "tools/freeze_aep_c2.py",
    "tools/run_aep_c2_qualification.py",
    "tools/replay_aep_c2_transport.py",
    "tests/test_aep_c2_control_plane.py",
    "planning/AEP-C2-CONTROL-BASELINE.json",
)
INCREMENTAL_SOURCE_ALLOWLIST = {"src/uclop/platform_reference_v2.py"}


def _path(value: Any) -> str:
    require(type(value) is str and value and "\\" not in value and not value.startswith("/"), "AEP_C2_PATH_INVALID")
    path = pathlib.PurePosixPath(value)
    require("." not in path.parts and ".." not in path.parts, "AEP_C2_PATH_INVALID")
    normalized = path.as_posix()
    require(normalized == value, "AEP_C2_PATH_NOT_CANONICAL")
    return normalized


def _kind(path: str) -> str:
    if path.startswith("src/"):
        return "SOURCE"
    if path.startswith("tests/"):
        return "COURT"
    if path.startswith("tools/"):
        return "TOOL"
    if path.startswith("spec/"):
        return "CONTRACT"
    if path.startswith("evidence/"):
        return "EVIDENCE"
    if path.startswith("planning/"):
        return "CONTROL_STATE"
    if "CLAIM" in path.upper() or "BOUNDARY" in path.upper():
        return "CLAIM"
    return "DOCUMENT"


def build_content_graph(workspace: pathlib.Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    files: list[dict[str, Any]] = []
    included: set[str] = set()
    for prefix in SCANNED_ROOTS:
        base = workspace / prefix
        if not base.exists():
            continue
        for path in sorted((item for item in base.rglob("*") if item.is_file()), key=lambda item: item.relative_to(workspace).as_posix()):
            relative = path.relative_to(workspace).as_posix()
            if relative in GRAPH_EXCLUSIONS or "__pycache__" in path.parts or ".pytest_cache" in path.parts or path.suffix.casefold() in {".pyc", ".pyo"}:
                continue
            data = path.read_bytes()
            files.append({"path": relative, "kind": _kind(relative), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
            included.add(relative)

    module_paths = {
        "uclop." + pathlib.PurePosixPath(row["path"]).stem: row["path"]
        for row in files if row["path"].startswith("src/uclop/") and row["path"].endswith(".py")
    }
    edges: set[tuple[str, str, str]] = set()
    for row in files:
        if not row["path"].endswith(".py"):
            continue
        try:
            tree = ast.parse((workspace / row["path"]).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level and row["path"].startswith(("src/uclop/", "tools/", "tests/")):
                    if node.module:
                        candidate = "src/uclop/" + node.module.split(".")[-1] + ".py"
                        if candidate in included:
                            edges.add((row["path"], candidate, "PYTHON_IMPORT"))
                elif node.module in module_paths:
                    edges.add((row["path"], module_paths[node.module], "PYTHON_IMPORT"))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in module_paths:
                        edges.add((row["path"], module_paths[alias.name], "PYTHON_IMPORT"))

    explicit_dependencies = {
        "evidence/aep-c2/AEP-C2-EVIDENCE-INDEX.json": ["tools/build_aep_c2_evidence.py", "tools/aep_c2_evidence_contract.py"],
        "evidence/aep-c2/PLATFORM-REFERENCE-V2.json": ["src/uclop/platform_reference_v2.py"],
        "evidence/aep-c2/PLATFORM-SNAPSHOT-V2.json": ["src/uclop/platform_kernel_v2.py"],
        "evidence/aep-c2/SUPERVISOR-CAPSULE.json": ["src/uclop/application_supervisor.py"],
        "evidence/aep-c2/PROTECTED-EXECUTION-CONTRACT.json": ["src/uclop/protected_execution_v2.py"],
        "evidence/aep-c2/BOUNDARY.json": ["docs/AEP-C2-TECHNICAL-BRIEF.md", "planning/AEP-C2-ROADMAP.json"],
    }
    for consumer, dependencies in explicit_dependencies.items():
        if consumer in included:
            for dependency in dependencies:
                if dependency in included:
                    edges.add((consumer, dependency, "DECLARED_BINDING"))

    edge_rows = [
        {"consumer": consumer, "depends_on": dependency, "relation": relation}
        for consumer, dependency, relation in sorted(edges)
    ]
    body = {
        "schema": "ucl.ucm.aep_c2_content_graph.v1",
        "files": files,
        "edges": edge_rows,
        "file_count": len(files),
        "edge_count": len(edge_rows),
        "kinds": sorted({row["kind"] for row in files}),
    }
    return {**body, "graph_root": root(body)}


def make_baseline_pin(*, graph: dict[str, Any]) -> dict[str, Any]:
    graph_body = {key: value for key, value in graph.items() if key != "graph_root"}
    require(graph.get("schema") == "ucl.ucm.aep_c2_content_graph.v1" and graph.get("graph_root") == root(graph_body), "AEP_C2_GRAPH_INVALID")
    body = {
        "schema": "ucl.ucm.aep_c2_baseline_pin.v1",
        "graph_root": graph["graph_root"],
        "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "predecessor_qualification_root": PREDECESSOR_QUALIFICATION_ROOT,
        "predecessor_transport_sha256": PREDECESSOR_TRANSPORT_SHA256,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "baseline_root": root(body)}


def verify_baseline_pin(value: Any, *, graph: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "graph_root", "predecessor_source_root", "predecessor_qualification_root",
        "predecessor_transport_sha256", "standing", "authority_effect", "baseline_root",
    }, "$.baseline")
    body = {key: item[key] for key in item if key != "baseline_root"}
    require(item["schema"] == "ucl.ucm.aep_c2_baseline_pin.v1" and item["baseline_root"] == root(body), "AEP_C2_BASELINE_ROOT_INVALID")
    require(item["graph_root"] == graph["graph_root"], "AEP_C2_BASELINE_GRAPH_MISMATCH")
    require(item["predecessor_source_root"] == PREDECESSOR_SOURCE_ROOT and item["predecessor_qualification_root"] == PREDECESSOR_QUALIFICATION_ROOT and item["predecessor_transport_sha256"] == PREDECESSOR_TRANSPORT_SHA256, "AEP_C2_BASELINE_PREDECESSOR_MISMATCH")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "AEP_C2_BASELINE_AUTHORITY_INVALID")
    return body


def _dependency_closure(graph: dict[str, Any], changed: set[str]) -> list[str]:
    reverse: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        reverse.setdefault(edge["depends_on"], set()).add(edge["consumer"])
    impacted = set(changed); frontier = list(changed)
    while frontier:
        dependency = frontier.pop()
        for consumer in reverse.get(dependency, set()):
            if consumer not in impacted:
                impacted.add(consumer); frontier.append(consumer)
    return sorted(impacted)


def plan_lane(
    *, changed_paths: list[str], circumstance: str, graph: dict[str, Any],
    baseline_pin: dict[str, Any] | None, frozen_candidate: bool = False,
) -> dict[str, Any]:
    require(type(changed_paths) is list, "AEP_C2_CHANGED_PATHS_INVALID")
    changed = sorted({_path(item) for item in changed_paths})
    graph_body = {key: value for key, value in graph.items() if key != "graph_root"}
    require(graph.get("schema") == "ucl.ucm.aep_c2_content_graph.v1" and graph.get("graph_root") == root(graph_body), "AEP_C2_GRAPH_INVALID")
    known_paths = {row["path"] for row in graph["files"]}
    circumstance_valid = type(circumstance) is str and circumstance == circumstance.strip().upper() and circumstance in KNOWN_CIRCUMSTANCES
    baseline_valid = False
    if baseline_pin is not None:
        try:
            verify_baseline_pin(baseline_pin, graph=graph); baseline_valid = True
        except Exception:
            baseline_valid = False
    unknown_impact = not circumstance_valid or (not changed and circumstance != "EXTERNAL_REVIEW") or any(path not in known_paths for path in changed)
    sensitive = any(
        path.casefold().startswith(tuple(prefix.casefold() for prefix in SENSITIVE_PREFIXES))
        or (path.casefold().startswith("src/") and path not in INCREMENTAL_SOURCE_ALLOWLIST)
        or path.casefold().startswith(("tools/", "tests/"))
        for path in changed
    )
    if circumstance == "EXTERNAL_REVIEW" and frozen_candidate and not changed and baseline_valid:
        lane, basis = "REVIEW", "EXACT_FROZEN_CANDIDATE"
    elif unknown_impact or not baseline_valid or circumstance in QUALIFICATION_CIRCUMSTANCES or sensitive:
        lane, basis = "QUALIFICATION", "UNKNOWN_SENSITIVE_OR_UNPINNED"
    elif changed and all(path in FAST_ALLOWLIST for path in changed) and circumstance == "DOCUMENTATION":
        lane, basis = "FAST", "EXPLICIT_DOCUMENT_ALLOWLIST"
    else:
        lane, basis = "INCREMENTAL", "CONTENT_GRAPH_IMPACT"
    impacted = _dependency_closure(graph, set(changed))
    selected_tests = sorted(path for path in impacted if path.startswith("tests/test_") and path.endswith(".py"))
    if lane == "INCREMENTAL" and not selected_tests:
        lane, basis = "QUALIFICATION", "NO_PROVEN_TEST_COVERAGE"
    selected_courts = {
        "FAST": ["AEP_C2_STATIC_CONTRACTS", "AEP_C2_DOCUMENT_LINKS"],
        "INCREMENTAL": selected_tests + ["AEP_C2_TARGETED_INVARIANTS"],
        "QUALIFICATION": ["AEP_C1_PRESERVATION", "AEP_C2_ALL_TESTS", "AEP_C2_ADVERSARIAL", "AEP_C2_GENERIC_RESEAL", "AEP_C2_EVIDENCE_CONTRACT", "AEP_C2_FREEZE"],
        "REVIEW": ["AEP_C2_CUSTODY", "AEP_C2_REVIEWER_TARGETS", "QUALIFICATION_ON_TRIGGER"],
    }[lane]
    input_rows = [row for row in graph["files"] if row["path"] in set(impacted)]
    dependency_root = root({"paths": input_rows, "courts": selected_courts})
    body = {
        "schema": "ucl.ucm.aep_c2_court_plan.v1",
        "changed_paths": changed,
        "circumstance": circumstance if type(circumstance) is str else "INVALID",
        "circumstance_valid": circumstance_valid,
        "graph_root": graph["graph_root"],
        "baseline_root": baseline_pin["baseline_root"] if baseline_valid else None,
        "lane": lane,
        "basis": basis,
        "unknown_impact": unknown_impact,
        "impacted_paths": impacted,
        "dependency_root": dependency_root,
        "selected_courts": selected_courts,
        "cache_policy": "DISABLED_REBUILD_FROM_SOURCE" if lane in {"QUALIFICATION", "REVIEW"} else "CONTENT_ADDRESSED_EPHEMERAL",
        "exact_test_identities_required": True,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "plan_root": root(body)}


def make_reuse_receipt(*, plan: dict[str, Any], court_results: dict[str, str]) -> dict[str, Any]:
    require(plan["lane"] in {"FAST", "INCREMENTAL"} and plan["cache_policy"] == "CONTENT_ADDRESSED_EPHEMERAL", "AEP_C2_REUSE_LANE_FORBIDDEN")
    require(set(court_results) == set(plan["selected_courts"]), "AEP_C2_REUSE_COURT_SET_INVALID")
    for value in court_results.values():
        require_root(value)
    body = {
        "schema": "ucl.ucm.aep_c2_reuse_receipt.v1",
        "plan_root": plan["plan_root"],
        "graph_root": plan["graph_root"],
        "dependency_root": plan["dependency_root"],
        "court_results": {key: court_results[key] for key in sorted(court_results)},
        "cache_scope": "CURRENT_PROCESS_ONLY",
        "prior_run_reads": 0,
        "status": "PASS",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "receipt_root": root(body)}


def verify_reuse_receipt(value: Any, *, plan: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "plan_root", "graph_root", "dependency_root", "court_results", "cache_scope",
        "prior_run_reads", "status", "standing", "authority_effect", "receipt_root",
    }, "$.reuse")
    body = {key: item[key] for key in item if key != "receipt_root"}
    require(item["schema"] == "ucl.ucm.aep_c2_reuse_receipt.v1" and item["receipt_root"] == root(body), "AEP_C2_REUSE_RECEIPT_ROOT_INVALID")
    require(plan["lane"] in {"FAST", "INCREMENTAL"} and plan["cache_policy"] == "CONTENT_ADDRESSED_EPHEMERAL", "AEP_C2_REUSE_LANE_FORBIDDEN")
    require(item["plan_root"] == plan["plan_root"] and item["graph_root"] == plan["graph_root"] and item["dependency_root"] == plan["dependency_root"], "AEP_C2_REUSE_CONTEXT_MISMATCH")
    require(set(item["court_results"]) == set(plan["selected_courts"]), "AEP_C2_REUSE_COURT_SET_INVALID")
    require(all(type(key) is str and require_root(value) for key, value in item["court_results"].items()), "AEP_C2_REUSE_COURT_ROOT_INVALID")
    require(item["cache_scope"] == "CURRENT_PROCESS_ONLY" and item["prior_run_reads"] == 0 and item["status"] == "PASS", "AEP_C2_REUSE_CACHE_POLICY_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "AEP_C2_REUSE_AUTHORITY_INVALID")
    return body


def schedule_courts(*, court_ids: list[str], measured_milliseconds: dict[str, int], workers: int) -> dict[str, Any]:
    require(court_ids == sorted(set(court_ids)) and court_ids, "AEP_C2_SCHEDULE_COURT_SET_INVALID")
    require(set(measured_milliseconds) == set(court_ids), "AEP_C2_SCHEDULE_RUNTIME_SET_INVALID")
    require(type(workers) is int and type(workers) is not bool and 1 <= workers <= 16, "AEP_C2_SCHEDULE_WORKERS_INVALID")
    require(all(type(value) is int and type(value) is not bool and value > 0 for value in measured_milliseconds.values()), "AEP_C2_SCHEDULE_RUNTIME_INVALID")
    groups: list[list[str]] = [[] for _ in range(workers)]; totals = [0] * workers
    for court_id in sorted(court_ids, key=lambda item: (-measured_milliseconds[item], item)):
        worker = min(range(workers), key=lambda index: (totals[index], index))
        groups[worker].append(court_id); totals[worker] += measured_milliseconds[court_id]
    body = {
        "schema": "ucl.ucm.aep_c2_court_schedule.v1",
        "court_ids": court_ids,
        "measured_milliseconds": {key: measured_milliseconds[key] for key in sorted(measured_milliseconds)},
        "workers": workers,
        "worker_groups": groups,
        "worker_totals_ms": totals,
        "estimated_wall_ms": max(totals),
        "test_identity_policy": "EXACT",
        "result_equivalence_required": True,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "schedule_root": root(body)}
