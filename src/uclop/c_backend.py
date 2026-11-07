from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from typing import Any

from .canonical import require, root
from .eligibility import validate_problem


PROFILE = {
    "schema": "ucl.op.restricted_c_profile.v1",
    "language": "C11_BOUNDED_SUBSET",
    "forbidden_tokens": ["malloc", "calloc", "realloc", "free", "goto", "setjmp", "longjmp", "asm", "__asm", "system("],
    "dynamic_allocation": False,
    "recursion": False,
    "integer_model": "SIGNED_32_WITH_GENERATOR_RANGE_PROOF",
    "effects": ["STDOUT_RESULT_ONLY_IN_DISPOSABLE_HARNESS"],
}
PROFILE["profile_root"] = root(PROFILE)


def validate_c_source(source: Any) -> str:
    require(type(source) is str and source, "C_SOURCE_INVALID")
    require(source.startswith("/* UCL_OP_GENERATED_RESTRICTED_C_V2 */\n"), "C_PROFILE_GENERATOR_MARKER_REQUIRED")
    for token in PROFILE["forbidden_tokens"]:
        require(token not in source, "C_PROFILE_FORBIDDEN_TOKEN", detail=token)
    require("#include <stdio.h>" in source and "#include <stdint.h>" in source, "C_PROFILE_HEADER_SET_INVALID")
    require("int main(void)" in source, "C_PROFILE_ENTRYPOINT_INVALID")
    definitions = re.findall(r"(?m)^\s*(?:static\s+)?(?:int|int32_t|uint8_t|void)\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{", source)
    require(definitions == ["main"], "C_PROFILE_FUNCTION_SET_INVALID")
    return source


def generate_eligibility_c(problem_value: dict[str, Any]) -> dict[str, Any]:
    problem = validate_problem(problem_value)
    nodes = {name: index for index, name in enumerate(problem["nodes"])}
    required = set(problem["required_labels"])
    edges = [(nodes[e["from"]], nodes[e["to"]]) for e in sorted(problem["edges"], key=lambda row: row["id"]) if required <= set(e["labels"])]
    require(len(problem["nodes"]) <= 4096 and len(edges) <= 16384, "C_PROFILE_GRAPH_BOUND_EXHAUSTED")
    edge_rows = ",\n  ".join(f"{{{source},{target}}}" for source, target in edges) or "{0,0}"
    source = f'''/* UCL_OP_GENERATED_RESTRICTED_C_V2 */\n#include <stdio.h>\n#include <stdint.h>\n\ntypedef struct {{ int32_t from; int32_t to; }} Edge;\nstatic const Edge EDGES[{max(1, len(edges))}] = {{\n  {edge_rows}\n}};\n\nint main(void) {{\n  uint8_t seen[{len(nodes)}] = {{0}};\n  int32_t queue[{len(nodes)}] = {{0}};\n  int32_t head = 0, tail = 0, visits = 0;\n  queue[tail++] = {nodes[problem['source']]};\n  seen[{nodes[problem['source']]}] = 1;\n  while (head < tail) {{\n    int32_t node = queue[head++];\n    visits += 1;\n    if (visits > {problem['max_visits']}) {{ puts("REFUSED:ELIGIBILITY_VISIT_BOUND_EXHAUSTED"); return 2; }}\n    if (node == {nodes[problem['target']]}) {{ puts("ELIGIBLE"); return 0; }}\n    for (int32_t i = 0; i < {len(edges)}; ++i) {{\n      if (EDGES[i].from == node && !seen[EDGES[i].to]) {{\n        seen[EDGES[i].to] = 1; queue[tail++] = EDGES[i].to;\n      }}\n    }}\n  }}\n  puts("INELIGIBLE"); return 0;\n}}\n'''
    validate_c_source(source)
    body = {"schema": "ucl.op.c_realization.v1", "problem": problem, "problem_root": root(problem), "profile_root": PROFILE["profile_root"], "source": source, "expected": "UNRESOLVED_UNTIL_REFERENCE", "effect": "DISPOSABLE_HARNESS_ONLY"}
    return {**body, "realization_root": root(body)}


def detect_toolchain() -> dict[str, Any]:
    required = os.environ.get("UCL_NATIVE_COMPILER")
    for name in ((required,) if required else ("gcc", "clang", "cc")):
        path = shutil.which(name)
        if path:
            completed = subprocess.run([path, "--version"], capture_output=True, text=True)
            first = (completed.stdout or completed.stderr).splitlines()[0] if completed.returncode == 0 else "unknown"
            return {"available": True, "kind": name, "path": path, "version": first, "selection": "EXPLICIT_ENV_PIN" if required else "DETERMINISTIC_PRIORITY"}
    return {"available": False, "kind": required, "path": None, "version": None, "selection": "EXPLICIT_ENV_PIN" if required else "DETERMINISTIC_PRIORITY"}


def compile_and_run(realization: dict[str, Any], *, work_root: pathlib.Path | None = None) -> dict[str, Any]:
    require(type(realization) is dict and realization.get("schema") == "ucl.op.c_realization.v1", "C_REALIZATION_INVALID")
    require(realization.get("realization_root") == root({key: value for key, value in realization.items() if key != "realization_root"}), "C_REALIZATION_ROOT_MISMATCH")
    validate_c_source(realization.get("source"))
    # The executable profile is generator-closed.  A source string cannot
    # acquire standing merely by passing lexical scans: it must be the exact
    # deterministic realization regenerated from the bound problem.
    problem = validate_problem(realization.get("problem"))
    expected_realization = generate_eligibility_c(problem)
    executable_fields = set(expected_realization) - {"realization_root"}
    require(
        set(realization) <= executable_fields | {"realization_root", "obligation_carriers"},
        "C_REALIZATION_FIELD_SET_INVALID",
    )
    require(
        all(realization.get(field) == expected_realization[field] for field in executable_fields),
        "C_REALIZATION_NOT_EXACT_GENERATOR_OUTPUT",
    )
    toolchain = detect_toolchain()
    if not toolchain["available"]:
        return {"schema": "ucl.op.native_result.v1", "status": "UNSUPPORTED_TOOLCHAIN", "toolchain": toolchain, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    owned = work_root is None
    temporary = tempfile.TemporaryDirectory(prefix="uclop-native-") if owned else None
    root_path = pathlib.Path(temporary.name if temporary else work_root)
    root_path.mkdir(parents=True, exist_ok=True)
    source_path = root_path / "candidate.c"
    binary_path = root_path / ("candidate.exe" if __import__("os").name == "nt" else "candidate")
    source_path.write_text(realization["source"], encoding="utf-8", newline="\n")
    command = [toolchain["path"], "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", str(source_path), "-o", str(binary_path)]
    compiled = subprocess.run(command, cwd=root_path, capture_output=True, text=True, timeout=30)
    if compiled.returncode != 0:
        result = {"schema": "ucl.op.native_result.v1", "status": "COMPILE_REFUSED", "toolchain": toolchain, "exit_code": compiled.returncode, "stderr": compiled.stderr[-4000:], "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    else:
        executed = subprocess.run([str(binary_path)], cwd=root_path, capture_output=True, text=True, timeout=10)
        result = {"schema": "ucl.op.native_result.v1", "status": "PASS" if executed.returncode == 0 else "RUN_REFUSED", "toolchain": toolchain, "exit_code": executed.returncode, "stdout": executed.stdout.strip(), "stderr": executed.stderr[-4000:], "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    result["result_root"] = root(result)
    if temporary:
        temporary.cleanup()
    return result
