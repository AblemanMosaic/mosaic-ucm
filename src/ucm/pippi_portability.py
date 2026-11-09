"""Observed execution context and cross-platform correspondence for P/PPI.

The records in this module keep platform facts separate from canonical product
outputs.  A Windows receipt and a WSL receipt are expected to differ as
execution evidence; the portability gate compares only the exact source, test
denominator, policy, and declared canonical outputs.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import os
from pathlib import Path, PurePosixPath
import platform
import secrets
import sys
from typing import Any

from uclop.canonical import exact_keys, require, root

from .amcas import BOUNDARY


HOST_FAMILIES = ("WINDOWS", "LINUX", "MACOS", "OTHER")
SHELL_FAMILIES = ("POWERSHELL", "CMD", "BASH", "ZSH", "FISH", "UNKNOWN")
FILESYSTEM_CLASSES = (
    "WINDOWS_NATIVE", "WSL_NATIVE", "WSL_MOUNTED_WINDOWS",
    "POSIX_NATIVE", "OTHER",
)
REQUIRED_LEGS = ("WINDOWS_NATIVE", "WSL_NATIVE")
TEXT_POLICY = {
    "source_encoding": "UTF-8_NO_BOM",
    "governed_source_newline": "LF",
    "windows_launcher_newline": "CRLF",
    "canonical_json": "UTF-8_NO_BOM_SORTED_KEYS_COMPACT_NO_TRAILING_NEWLINE",
}


def _root_value(value: Any, code: str) -> str:
    require(type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value), code)
    return value


def portable_relative_path(value: str) -> str:
    """Return one canonical relative POSIX path or refuse."""
    require(type(value) is str and bool(value) and "\\" not in value,
            "PIPPI_PORTABLE_PATH_INVALID")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts
            and value == path.as_posix(), "PIPPI_PORTABLE_PATH_INVALID")
    return value


def portable_path_key(path: Path, base: Path) -> str:
    """Platform-neutral key for deterministic filesystem ordering."""
    return path.relative_to(base).as_posix()


def build_execution_context(*, host_family: str, shell_family: str,
                            path_flavour: str, filesystem_class: str,
                            case_sensitive: bool, python_implementation: str,
                            python_version: str, source: str,
                            wsl_distribution: str | None,
                            case_sensitivity_source: str | None = None) -> dict[str, Any]:
    require(host_family in HOST_FAMILIES, "PIPPI_HOST_FAMILY_INVALID")
    require(shell_family in SHELL_FAMILIES, "PIPPI_SHELL_FAMILY_INVALID")
    require(path_flavour in {"WINDOWS", "POSIX"},
            "PIPPI_PATH_FLAVOUR_INVALID")
    require(filesystem_class in FILESYSTEM_CLASSES,
            "PIPPI_FILESYSTEM_CLASS_INVALID")
    require(type(case_sensitive) is bool,
            "PIPPI_CASE_POLICY_INVALID")
    require(type(python_implementation) is str and python_implementation,
            "PIPPI_PYTHON_IMPLEMENTATION_INVALID")
    require(type(python_version) is str and python_version,
            "PIPPI_PYTHON_VERSION_INVALID")
    require(source in {"OBSERVED_LOCAL_PROCESS", "DECLARED_EXTERNAL_HOST"},
            "PIPPI_CONTEXT_SOURCE_INVALID")
    expected_case_source = ("PROBED_CURRENT_FILESYSTEM" if source == "OBSERVED_LOCAL_PROCESS"
                            else "DECLARED_BY_CALLER")
    if case_sensitivity_source is None:
        case_sensitivity_source = expected_case_source
    require(case_sensitivity_source == expected_case_source,
            "PIPPI_CASE_POLICY_SOURCE_INVALID")
    require(wsl_distribution is None or
            (type(wsl_distribution) is str and bool(wsl_distribution)),
            "PIPPI_WSL_DISTRIBUTION_INVALID")
    if filesystem_class.startswith("WSL_"):
        require(host_family == "LINUX" and wsl_distribution is not None,
                "PIPPI_WSL_CONTEXT_INVALID")
    else:
        require(wsl_distribution is None, "PIPPI_WSL_CONTEXT_INVALID")
    body = {
        "schema": "mosaic.ucm.pippi-execution-context.v0.1",
        "host_family": host_family, "shell_family": shell_family,
        "path_flavour": path_flavour,
        "filesystem_class": filesystem_class,
        "case_sensitive": case_sensitive,
        "case_sensitivity_source": case_sensitivity_source,
        "python_implementation": python_implementation,
        "python_version": python_version,
        "wsl_distribution": wsl_distribution,
        "text_policy": deepcopy(TEXT_POLICY),
        "source": source,
        "context_is_evidence_not_authority": True,
        **BOUNDARY,
    }
    return {**body, "execution_context_root": root(body)}


def probe_case_sensitivity(directory: Path) -> bool:
    """Probe the filesystem containing *directory* and remove all probe bytes."""
    require(directory.is_dir(), "PIPPI_CASE_SENSITIVITY_PROBE_ROOT_INVALID")
    name = ".pippi-case-probe-" + secrets.token_hex(12).casefold()
    probe = directory / name
    alternate = directory / name.upper()
    try:
        with probe.open("xb") as stream:
            stream.write(b"pippi-case-sensitivity-probe\n")
        return not alternate.exists()
    except OSError as error:
        raise ValueError("PIPPI_CASE_SENSITIVITY_PROBE_FAILED") from error
    finally:
        try:
            probe.unlink(missing_ok=True)
        except OSError as error:
            raise ValueError("PIPPI_CASE_SENSITIVITY_PROBE_CLEANUP_FAILED") from error


def observe_execution_context(*, shell_family: str) -> dict[str, Any]:
    """Observe only facts available to the current local process."""
    if sys.platform == "win32":
        host = "WINDOWS"; flavour = "WINDOWS"
        filesystem = "WINDOWS_NATIVE"; distro = None
    elif sys.platform.startswith("linux"):
        host = "LINUX"; flavour = "POSIX"; distro = os.environ.get("WSL_DISTRO_NAME")
        if distro:
            filesystem = ("WSL_MOUNTED_WINDOWS"
                          if Path.cwd().as_posix().startswith("/mnt/")
                          else "WSL_NATIVE")
        else:
            filesystem = "POSIX_NATIVE"
    elif sys.platform == "darwin":
        host = "MACOS"; flavour = "POSIX"
        filesystem = "POSIX_NATIVE"; distro = None
    else:
        host = "OTHER"; flavour = "POSIX"
        filesystem = "OTHER"; distro = None
    case_sensitive = probe_case_sensitivity(Path.cwd())
    return build_execution_context(
        host_family=host, shell_family=shell_family,
        path_flavour=flavour, filesystem_class=filesystem,
        case_sensitive=case_sensitive,
        python_implementation=platform.python_implementation(),
        python_version=platform.python_version(),
        source="OBSERVED_LOCAL_PROCESS", wsl_distribution=distro)


def validate_execution_context(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "host_family", "shell_family", "path_flavour",
        "filesystem_class", "case_sensitive", "case_sensitivity_source",
        "python_implementation",
        "python_version", "wsl_distribution", "text_policy", "source",
        "context_is_evidence_not_authority", "standing", "authority_effect",
        "real_a5", "g0", "execution_context_root",
    })
    expected = build_execution_context(
        host_family=item["host_family"], shell_family=item["shell_family"],
        path_flavour=item["path_flavour"],
        filesystem_class=item["filesystem_class"],
        case_sensitive=item["case_sensitive"],
        python_implementation=item["python_implementation"],
        python_version=item["python_version"], source=item["source"],
        wsl_distribution=item["wsl_distribution"],
        case_sensitivity_source=item["case_sensitivity_source"])
    require(item == expected, "PIPPI_EXECUTION_CONTEXT_INVALID")
    return deepcopy(item)


def portability_policy() -> dict[str, Any]:
    body = {
        "schema": "mosaic.ucm.pippi-portability-policy.v0.1",
        "required_leg_ids": list(REQUIRED_LEGS),
        "canonical_path_order": "RELATIVE_POSIX_CODEPOINT",
        "text_policy": deepcopy(TEXT_POLICY),
        "wsl_linux_leg_requires_native_filesystem": True,
        "case_sensitivity_observation": "PROBE_CURRENT_FILESYSTEM_AND_CLEAN",
        "compare_full_execution_receipts": False,
        "compare_source_and_test_denominator": True,
        "compare_recomputed_canonical_outputs": True,
        "native_leg_outputs_recomputed_from_exact_source": True,
        "portable_claim_requires_all_legs": True,
        **BOUNDARY,
    }
    return {**body, "portability_policy_root": root(body)}


def build_portability_witness(*, leg_id: str, execution_context: dict[str, Any],
                              source_root: str, test_set_root: str,
                              canonical_outputs: list[dict[str, str]],
                              status: str,
                              reason_codes: list[str]) -> dict[str, Any]:
    require(leg_id in REQUIRED_LEGS, "PIPPI_PORTABILITY_LEG_INVALID")
    context = validate_execution_context(execution_context)
    require(context["filesystem_class"] == leg_id,
            "PIPPI_PORTABILITY_CONTEXT_LEG_MISMATCH")
    _root_value(source_root, "PIPPI_PORTABILITY_SOURCE_ROOT_INVALID")
    _root_value(test_set_root, "PIPPI_PORTABILITY_TEST_ROOT_INVALID")
    require(status in {"PASS", "UNAVAILABLE", "FAIL"},
            "PIPPI_PORTABILITY_STATUS_INVALID")
    require(type(reason_codes) is list
            and reason_codes == sorted(set(reason_codes))
            and all(type(code) is str and code for code in reason_codes),
            "PIPPI_PORTABILITY_REASON_CODES_INVALID")
    require((status == "PASS") == (not reason_codes),
            "PIPPI_PORTABILITY_STATUS_INVALID")
    outputs = []
    for raw in canonical_outputs:
        row = exact_keys(raw, {"artifact_id", "root"})
        require(type(row["artifact_id"]) is str and row["artifact_id"],
                "PIPPI_PORTABILITY_OUTPUT_INVALID")
        _root_value(row["root"], "PIPPI_PORTABILITY_OUTPUT_INVALID")
        outputs.append(deepcopy(row))
    require(outputs == sorted(outputs, key=lambda row: row["artifact_id"])
            and len({row["artifact_id"] for row in outputs}) == len(outputs),
            "PIPPI_PORTABILITY_OUTPUTS_INVALID")
    body = {
        "schema": "mosaic.ucm.pippi-portability-witness.v0.1",
        "leg_id": leg_id,
        "execution_context_root": context["execution_context_root"],
        "source_root": source_root, "test_set_root": test_set_root,
        "portability_policy_root": portability_policy()["portability_policy_root"],
        "canonical_outputs": outputs, "status": status,
        "reason_codes": reason_codes,
        "receipt_is_platform_specific": True,
        **BOUNDARY,
    }
    return {**body, "witness_root": root(body)}


def evaluate_portability_gate(*, witnesses: list[dict[str, Any]]) -> dict[str, Any]:
    require(type(witnesses) is list, "PIPPI_PORTABILITY_WITNESSES_INVALID")
    rows = []
    for witness in witnesses:
        item = exact_keys(witness, {
            "schema", "leg_id", "execution_context_root", "source_root",
            "test_set_root", "portability_policy_root", "canonical_outputs",
            "status", "reason_codes", "receipt_is_platform_specific",
            "standing", "authority_effect", "real_a5", "g0", "witness_root",
        })
        require(item["leg_id"] in REQUIRED_LEGS,
                "PIPPI_PORTABILITY_LEG_INVALID")
        require(item["portability_policy_root"]
                == portability_policy()["portability_policy_root"],
                "PIPPI_PORTABILITY_POLICY_MISMATCH")
        require(item["receipt_is_platform_specific"] is True,
                "PIPPI_PORTABILITY_RECEIPT_CLASS_INVALID")
        require(item["status"] in {"PASS", "UNAVAILABLE", "FAIL"}
                and type(item["reason_codes"]) is list
                and item["reason_codes"] == sorted(set(item["reason_codes"]))
                and ((item["status"] == "PASS") == (not item["reason_codes"])),
                "PIPPI_PORTABILITY_STATUS_INVALID")
        for field in ("execution_context_root", "source_root", "test_set_root",
                      "portability_policy_root"):
            _root_value(item[field], "PIPPI_PORTABILITY_WITNESS_INVALID")
        _root_value(item["witness_root"], "PIPPI_PORTABILITY_WITNESS_INVALID")
        body = {key: deepcopy(value) for key, value in item.items()
                if key != "witness_root"}
        require(item["witness_root"] == root(body),
                "PIPPI_PORTABILITY_WITNESS_INVALID")
        rows.append(deepcopy(item))
    require([row["leg_id"] for row in rows]
            == sorted(set(row["leg_id"] for row in rows)),
            "PIPPI_PORTABILITY_WITNESS_DENOMINATOR_INVALID")
    by_leg = {row["leg_id"]: row for row in rows}
    missing = sorted(set(REQUIRED_LEGS) - set(by_leg))
    non_pass = sorted(row["leg_id"] for row in rows if row["status"] != "PASS")
    differences = []
    if not missing and not non_pass:
        baseline = rows[0]
        for field in ("source_root", "test_set_root", "portability_policy_root",
                      "canonical_outputs"):
            if any(row[field] != baseline[field] for row in rows[1:]):
                differences.append(field)
    if missing or non_pass:
        status = "PLATFORM_LEG_UNAVAILABLE"
    elif differences:
        status = "PLATFORM_DIVERGENCE"
    else:
        status = "PASS_PORTABLE"
    body = {
        "schema": "mosaic.ucm.pippi-portability-gate.v0.1",
        "required_leg_ids": list(REQUIRED_LEGS),
        "witness_roots": [row["witness_root"] for row in rows],
        "missing_leg_ids": missing, "non_pass_leg_ids": non_pass,
        "differing_fields": differences, "status": status,
        "portable_claim_allowed": status == "PASS_PORTABLE",
        **BOUNDARY,
    }
    return {**body, "portability_gate_root": root(body)}


class _PathSortVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.lines: list[int] = []

    @staticmethod
    def _contains_path_iterator(node: ast.AST) -> bool:
        return any(isinstance(child, ast.Call)
                   and isinstance(child.func, ast.Attribute)
                   and child.func.attr in {"glob", "rglob", "iterdir"}
                   for child in ast.walk(node))

    @staticmethod
    def _projects_to_portable_scalar(node: ast.AST) -> bool:
        if isinstance(node, (ast.GeneratorExp, ast.ListComp)):
            value = node.elt
            if isinstance(value, ast.Attribute) and value.attr in {"name", "stem", "suffix"}:
                return True
            if (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                    and value.func.attr == "as_posix"):
                return True
        return False

    def visit_Call(self, node: ast.Call) -> None:
        if (isinstance(node.func, ast.Name) and node.func.id == "sorted"
                and node.args and self._contains_path_iterator(node.args[0])
                and not self._projects_to_portable_scalar(node.args[0])
                and not any(keyword.arg == "key" for keyword in node.keywords)):
            self.lines.append(node.lineno)
        self.generic_visit(node)


def inspect_portable_python_sources(*,
                                    sources: list[dict[str, str]]) -> dict[str, Any]:
    require(type(sources) is list, "PIPPI_PORTABLE_SOURCES_INVALID")
    findings = []
    paths = []
    for raw in sources:
        row = exact_keys(raw, {"path", "text"})
        path = portable_relative_path(row["path"])
        require(path.endswith(".py") and type(row["text"]) is str,
                "PIPPI_PORTABLE_SOURCE_INVALID")
        try:
            tree = ast.parse(row["text"], filename=path)
        except SyntaxError as error:
            findings.append({"path": path, "line": error.lineno or 0,
                             "code": "PYTHON_SYNTAX_INVALID"})
        else:
            visitor = _PathSortVisitor(); visitor.visit(tree)
            findings.extend({"path": path, "line": line,
                             "code": "HOST_FLAVOURED_PATH_SORT"}
                            for line in visitor.lines)
        paths.append(path)
    require(paths == sorted(set(paths)), "PIPPI_PORTABLE_SOURCES_INVALID")
    findings = sorted(findings, key=lambda row: (row["path"], row["line"], row["code"]))
    body = {
        "schema": "mosaic.ucm.pippi-portable-source-inspection.v0.1",
        "source_paths": paths, "findings": findings,
        "finding_count": len(findings),
        "status": "PASS" if not findings else "REFUSED",
        "policy_root": portability_policy()["portability_policy_root"],
        **BOUNDARY,
    }
    return {**body, "inspection_root": root(body)}
