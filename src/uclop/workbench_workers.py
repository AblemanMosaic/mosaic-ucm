"""Bounded trusted workers. This module is not an operating-system sandbox.

Only externally pinned, trusted test source may execute. Hostile candidate code
requires the separate UNBOUND_EXTERNAL OS-sandbox adapter.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time
import unicodedata
from typing import Any

from .canonical import Refusal, canonical_bytes, exact_keys, require, require_root, root, strict_loads
from .custody import CustodyProvider, public_key_root, verify_asymmetric


BINDINGS = ("project_root", "source_root", "registry_root", "policy_root", "charter_root", "jurisdiction_root", "grant_root")
OPERATIONS = ("INSPECT_ARTIFACTS", "RUN_TESTS", "PREPARE_CANDIDATE")
RECEIPT_DOMAIN = "UCL_UCM_WORKBENCH_WORKER_RECEIPT_V1"
OBSERVATION_DOMAIN = "UCL_UCM_WORKBENCH_WORKER_OBSERVATION_V1"
RECONCILIATION_DOMAIN = "UCL_UCM_WORKBENCH_NO_EXECUTION_V1"
MAX_FILE_BYTES = 8 * 1024 * 1024
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_MODULE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$")
_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {f"{p}{i}" for p in ("COM", "LPT") for i in range(1, 10)}


# A fixed runner records identities and actual outcomes. Caller data never
# becomes source text, argv fragments, a shell command, or a result assertion.
TRUSTED_RUNNER = r'''import contextlib, hashlib, importlib, io, json, pathlib, sys, unittest
source = pathlib.Path(sys.argv[1]); modules = json.loads(sys.argv[2]); result_path = pathlib.Path(sys.argv[3])
sys.dont_write_bytecode = True
sys.path[:0] = [str(source / "src"), str(source)]
captured_out = io.StringIO(); captured_err = io.StringIO()
class Result(unittest.TestResult):
    def __init__(self):
        super().__init__(); self.ids=[]; self.outcomes=[]
    def startTest(self, test):
        super().startTest(test); self.ids.append(test.id())
    def addSuccess(self, test):
        super().addSuccess(test); self.outcomes.append({"id":test.id(),"outcome":"PASS"})
    def addFailure(self, test, err):
        super().addFailure(test,err); self.outcomes.append({"id":test.id(),"outcome":"FAIL"})
    def addError(self, test, err):
        super().addError(test,err); self.outcomes.append({"id":test.id(),"outcome":"ERROR"})
    def addSkip(self, test, reason):
        super().addSkip(test,reason); self.outcomes.append({"id":test.id(),"outcome":"SKIP"})
    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test,err); self.outcomes.append({"id":test.id(),"outcome":"EXPECTED_FAILURE"})
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.outcomes.append({"id":test.id(),"outcome":"UNEXPECTED_SUCCESS"})
result = Result(); loaded=[]; load_error=None
try:
    with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
        suite=unittest.TestSuite()
        for name in modules:
            module=importlib.import_module(name)
            loaded.append({"module":name,"sha256":hashlib.sha256(pathlib.Path(module.__file__).read_bytes()).hexdigest()})
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
        suite.run(result)
except BaseException as error:
    load_error=type(error).__name__
body={"schema":"ucl.ucm.workbench_test_measurement.v1","modules":loaded,"test_ids":sorted(result.ids),"outcomes":sorted(result.outcomes,key=lambda x:(x["id"],x["outcome"])),"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses),"load_error":load_error}
result_path.write_text(json.dumps(body,sort_keys=True,separators=(",",":")),encoding="utf-8")
sys.stdout.write(captured_out.getvalue()); sys.stderr.write(captured_err.getvalue())
sys.exit(0 if load_error is None and result.wasSuccessful() and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses else 1)
'''
RUNNER_ROOT = hashlib.sha256(TRUSTED_RUNNER.encode("utf-8")).hexdigest()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _id(value: Any) -> str:
    require(type(value) is str and bool(_ID.fullmatch(value)), "WORKER_ID_INVALID")
    return value


def _relative(value: Any) -> str:
    require(type(value) is str and value and unicodedata.normalize("NFC", value) == value, "WORKER_PATH_INVALID")
    require("\\" not in value and ":" not in value and "\x00" not in value and not value.startswith("/"), "WORKER_PATH_INVALID")
    parts = value.split("/")
    require(all(part not in {"", ".", ".."} and part[-1] not in {" ", "."} and part.split(".")[0].upper() not in _RESERVED for part in parts), "WORKER_PATH_INVALID")
    require(PurePosixPath(value).as_posix() == value, "WORKER_PATH_INVALID")
    return value


def _contained(base: Path, relative: str) -> Path:
    require(not base.is_symlink(), "WORKER_SYMLINK_FORBIDDEN")
    current = base
    for part in _relative(relative).split("/"):
        current = current / part
        require(not current.is_symlink(), "WORKER_SYMLINK_FORBIDDEN")
        if current.exists():
            require(not bool(getattr(current.stat(), "st_file_attributes", 0) & 0x400), "WORKER_REPARSE_FORBIDDEN")
    require(current.resolve().is_relative_to(base.resolve()), "WORKER_PATH_ESCAPE")
    return current


def _source_path(value: Any) -> str:
    name = _relative(value)
    require(all(part.casefold() != "__pycache__" for part in name.split("/")) and not name.casefold().endswith((".pyc", ".pyo")), "WORKER_BYTECODE_FORBIDDEN")
    return name


def snapshot_source(directory: str | Path) -> dict[str, Any]:
    """Hash the entire exact tree: no invisible files and no ignored directories."""
    base = Path(directory)
    require(base.is_dir() and not base.is_symlink(), "WORKER_SOURCE_DIRECTORY_INVALID")
    files = []; seen: dict[str, str] = {}; total = 0
    try:
        paths = sorted(base.rglob("*"), key=lambda p: p.relative_to(base).as_posix())
    except (FileNotFoundError, NotADirectoryError, OSError) as error:
        raise Refusal("WORKER_SOURCE_CHANGED") from error
    for path in paths:
        try:
            name = _source_path(path.relative_to(base).as_posix()); _contained(base, name)
            require(name.casefold() not in seen, "WORKER_PATH_COLLISION")
            seen[name.casefold()] = name
            mode = path.lstat().st_mode
            require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), "WORKER_SPECIAL_FILE_FORBIDDEN")
            if stat.S_ISDIR(mode):
                continue
            initial = path.stat(); size = initial.st_size; total += size
            require(size <= MAX_FILE_BYTES and total <= 512 * MAX_FILE_BYTES and len(files) < 20000, "WORKER_SOURCE_BUDGET_EXCEEDED")
            raw = path.read_bytes(); require(len(raw) == size, "WORKER_SOURCE_CHANGED")
            # Re-stat after reading so a same-path replacement cannot silently
            # become part of a supposedly atomic snapshot.
            final = path.stat()
            require((final.st_size, final.st_dev, final.st_ino, final.st_mtime_ns)
                    == (initial.st_size, initial.st_dev, initial.st_ino, initial.st_mtime_ns),
                    "WORKER_SOURCE_CHANGED")
            files.append({"path": name, "sha256": _sha(raw), "bytes": len(raw)})
        except Refusal:
            raise
        except (FileNotFoundError, NotADirectoryError, OSError) as error:
            raise Refusal("WORKER_SOURCE_CHANGED") from error
    body = {"schema": "ucl.ucm.workbench_source_snapshot.v1", "files": files, "file_count": len(files)}
    return {**body, "source_root": root(body)}


def _snapshot(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "files", "file_count", "source_root"})
    require(item["schema"] == "ucl.ucm.workbench_source_snapshot.v1" and type(item["files"]) is list and type(item["file_count"]) is int and item["file_count"] == len(item["files"]), "WORKER_SOURCE_MANIFEST_INVALID")
    names = []; collisions = set()
    for row in item["files"]:
        exact_keys(row, {"path", "sha256", "bytes"}); names.append(_source_path(row["path"])); require_root(row["sha256"])
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_FILE_BYTES, "WORKER_SOURCE_MANIFEST_INVALID")
        for index in range(1, len(names[-1].split("/")) + 1):
            partial = "/".join(names[-1].split("/")[:index]); folded = partial.casefold()
            # Aliased parents are rejected by the actual tree snapshot too.
            require(not any(other.casefold() == folded and other != partial for other in collisions), "WORKER_PATH_COLLISION")
            collisions.add(partial)
    require(names == sorted(names) and len(set(name.casefold() for name in names)) == len(names), "WORKER_SOURCE_MANIFEST_INVALID")
    file_names = set(names)
    require(all("/".join(name.split("/")[:index]) not in file_names for name in names for index in range(1, len(name.split("/")))), "WORKER_PATH_COLLISION")
    body = {key: item[key] for key in item if key != "source_root"}
    require(item["source_root"] == root(body), "WORKER_SOURCE_ROOT_INVALID")
    return deepcopy(item)


def _payload_shape(operation: str, payload: Any) -> None:
    require(type(payload) is dict, "WORKER_PAYLOAD_INVALID")
    if operation == "INSPECT_ARTIFACTS":
        exact_keys(payload, {"paths"}); values = payload["paths"]
        require(type(values) is list and 0 < len(values) <= 10000 and all(type(value) is str for value in values), "WORKER_READSET_INVALID")
        require(values == sorted(values) and len(set(values)) == len(values), "WORKER_READSET_INVALID")
        for value in values: _relative(value)
    elif operation == "RUN_TESTS":
        require(set(payload) in ({"modules"}, {"modules", "candidate_operation_id", "candidate_source_root", "candidate_receipt_root"}),
                "WORKER_PAYLOAD_INVALID")
        if "candidate_operation_id" in payload:
            _relative(payload["candidate_operation_id"]); require_root(payload["candidate_source_root"]); require_root(payload["candidate_receipt_root"])
        values = payload["modules"]
        require(type(values) is list and 0 < len(values) <= 128 and all(type(value) is str and _MODULE.fullmatch(value) for value in values), "WORKER_TEST_MODULE_SET_INVALID")
        require(values == sorted(values) and len(set(values)) == len(values), "WORKER_TEST_MODULE_SET_INVALID")
    else:
        exact_keys(payload, {"changes"}); values = payload["changes"]
        require(type(values) is list and 0 < len(values) <= 100, "WORKER_CHANGES_INVALID")
        for value in values:
            exact_keys(value, {"path", "original_sha256", "replacement_base64"}); _source_path(value["path"])
            if value["original_sha256"] is not None: require_root(value["original_sha256"])
            require(value["replacement_base64"] is None or type(value["replacement_base64"]) is str, "WORKER_REPLACEMENT_INVALID")


def make_worker_request(*, operation: str, operation_id: str, task_id: str, attempt_id: str, generation: int, tenant_id: str,
                        project_root: str, source_root: str, registry_root: str, policy_root: str, charter_root: str,
                        jurisdiction_root: str, grant_root: str, payload: dict[str, Any]) -> dict[str, Any]:
    require(operation in OPERATIONS, "WORKER_OPERATION_FORBIDDEN")
    require(type(generation) is int and generation > 0, "WORKER_GENERATION_INVALID")
    _payload_shape(operation, payload)
    _relative(operation_id)
    body = {"schema": "ucl.ucm.workbench_worker_request.v1", "operation": operation, "operation_id": _id(operation_id), "task_id": _id(task_id), "attempt_id": _id(attempt_id), "generation": generation, "tenant_id": _id(tenant_id),
            "project_root": require_root(project_root), "source_root": require_root(source_root), "registry_root": require_root(registry_root), "policy_root": require_root(policy_root), "charter_root": require_root(charter_root), "jurisdiction_root": require_root(jurisdiction_root), "grant_root": require_root(grant_root), "payload": deepcopy(payload)}
    canonical_bytes(body)
    return {**body, "request_root": root(body)}


def verify_worker_request(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "operation", "operation_id", "task_id", "attempt_id", "generation", "tenant_id", "payload", "request_root", *BINDINGS})
    rebuilt = make_worker_request(**{key: item[key] for key in item if key not in {"schema", "request_root"}})
    require(item == rebuilt, "WORKER_REQUEST_ROOT_INVALID")
    return deepcopy(item)


def _changes(payload: Any, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    exact_keys(payload, {"changes"}); require(type(payload["changes"]) is list and 0 < len(payload["changes"]) <= 100, "WORKER_CHANGES_INVALID")
    rows = {row["path"]: row for row in snapshot["files"]}; result = []
    for change in payload["changes"]:
        exact_keys(change, {"path", "original_sha256", "replacement_base64"}); name = _source_path(change["path"])
        expected = rows[name]["sha256"] if name in rows else None
        require(change["original_sha256"] == expected, "WORKER_ORIGINAL_BYTES_MISMATCH")
        encoded = change["replacement_base64"]
        if encoded is None:
            require(expected is not None, "WORKER_DELETE_MISSING_FILE")
            data = None
        else:
            require(type(encoded) is str and len(encoded) <= MAX_FILE_BYTES * 2, "WORKER_REPLACEMENT_INVALID")
            try:
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as error:
                raise Refusal("WORKER_REPLACEMENT_INVALID") from error
            require(len(data) <= MAX_FILE_BYTES and base64.b64encode(data).decode("ascii") == encoded, "WORKER_REPLACEMENT_INVALID")
        result.append({"path": name, "original_sha256": expected, "replacement_sha256": None if data is None else _sha(data), "replacement_bytes": None if data is None else len(data)})
    require([row["path"] for row in result] == sorted(row["path"] for row in result) and len({row["path"].casefold() for row in result}) == len(result), "WORKER_CHANGES_ORDER_INVALID")
    return result


def _test_status(measurement: Any, expected_modules: list[dict[str, Any]], expected_ids: list[str], exit_code: int | None, input_stable: bool) -> tuple[str, str]:
    exact_keys(measurement, {"schema", "modules", "test_ids", "outcomes", "tests_run", "failures", "errors", "skips", "expected_failures", "unexpected_successes", "load_error"})
    require(measurement["schema"] == "ucl.ucm.workbench_test_measurement.v1", "WORKER_TEST_MEASUREMENT_INVALID")
    require(exit_code is None or type(exit_code) is int, "WORKER_TEST_EXIT_CODE_INVALID")
    require(measurement["load_error"] is None or type(measurement["load_error"]) is str, "WORKER_TEST_MEASUREMENT_INVALID")
    for field in ("tests_run", "failures", "errors", "skips", "expected_failures", "unexpected_successes"):
        require(type(measurement[field]) is int and measurement[field] >= 0, "WORKER_TEST_COUNT_INVALID")
    require(type(measurement["test_ids"]) is list and all(type(value) is str for value in measurement["test_ids"]) and type(measurement["outcomes"]) is list, "WORKER_TEST_MEASUREMENT_INVALID")
    for row in measurement["outcomes"]:
        exact_keys(row, {"id", "outcome"}); require(row["outcome"] in {"PASS", "FAIL", "ERROR", "SKIP", "EXPECTED_FAILURE", "UNEXPECTED_SUCCESS"} and type(row["id"]) is str, "WORKER_TEST_MEASUREMENT_INVALID")
    if not input_stable:
        return "FAIL", "WORKER_INPUT_DRIFT"
    if measurement["load_error"] is not None:
        return "FAIL", "WORKER_TEST_LOAD_FAILED"
    if measurement["modules"] != expected_modules or measurement["test_ids"] != expected_ids or len(expected_ids) == 0 or measurement["tests_run"] != len(expected_ids):
        return "FAIL", "WORKER_TEST_IDENTITY_MISMATCH"
    if measurement["failures"]:
        return "FAIL", "WORKER_TEST_FAILURES"
    if measurement["errors"]:
        return "FAIL", "WORKER_TEST_ERRORS"
    if measurement["skips"] or measurement["expected_failures"] or measurement["unexpected_successes"]:
        return "FAIL", "WORKER_TEST_REQUIRED_SKIPS"
    if measurement["outcomes"] != [{"id": value, "outcome": "PASS"} for value in expected_ids]:
        return "FAIL", "WORKER_TEST_OUTCOMES_INVALID"
    return ("PASS", "OK") if exit_code == 0 else ("FAIL", "WORKER_TEST_PROCESS_FAILED")


def _dispatch_payload(request: dict[str, Any], manifest: dict[str, Any], policy: dict[str, Any]) -> None:
    """Shared admission check: execution and receipt verification have one rule."""
    _payload_shape(request["operation"], request["payload"])
    rows = {row["path"]: row for row in manifest["files"]}; ceiling = policy["maximum_artifact_bytes"]
    if request["operation"] == "INSPECT_ARTIFACTS":
        for name in request["payload"]["paths"]:
            require(name in rows, "WORKER_READSET_UNKNOWN")
            require(rows[name]["bytes"] <= ceiling, "WORKER_ARTIFACT_BUDGET_EXCEEDED")
    elif request["operation"] == "RUN_TESTS":
        require(all(module in policy["trusted_tests"] for module in request["payload"]["modules"]), "WORKER_TEST_MODULE_UNTRUSTED")
        for module in request["payload"]["modules"]:
            pin = exact_keys(policy["trusted_tests"][module], {"path", "sha256", "test_ids"})
            require(pin["path"] in rows and pin["sha256"] == rows[pin["path"]]["sha256"], "WORKER_TEST_MODULE_PIN_INVALID")
            require(rows[pin["path"]]["bytes"] <= ceiling, "WORKER_ARTIFACT_BUDGET_EXCEEDED")
    else:
        changes = _changes(request["payload"], manifest)
        require(all(row["bytes"] <= ceiling for row in manifest["files"]), "WORKER_ARTIFACT_BUDGET_EXCEEDED")
        require(all(row["replacement_bytes"] is None or row["replacement_bytes"] <= ceiling for row in changes), "WORKER_ARTIFACT_BUDGET_EXCEEDED")


class BoundedWorker:
    """A trusted local worker with immutable bindings and durable no-blind-retry custody.

    Binding roots/issuer/allowlists must come from the independently verified
    orientation and grant. Supplying these pins is not itself an authority grant.
    """

    def __init__(self, *, source_directory: str | Path, source_manifest: dict[str, Any], output_directory: str | Path,
                 bindings: dict[str, str], tenant_id: str, provider: CustodyProvider, signing_handle: str,
                 expected_issuer: dict[str, Any], trusted_tests: dict[str, dict[str, Any]],
                 allowed_operations: tuple[str, ...] = OPERATIONS, maximum_test_seconds: int = 60,
                 maximum_artifact_bytes: int = MAX_FILE_BYTES) -> None:
        for directory in (Path(source_directory).absolute(), Path(output_directory).absolute()):
            for ancestor in (directory, *directory.parents):
                require(not ancestor.is_symlink(), "WORKER_SYMLINK_FORBIDDEN")
                if ancestor.exists():
                    require(not bool(getattr(ancestor.stat(), "st_file_attributes", 0) & 0x400), "WORKER_REPARSE_FORBIDDEN")
        self.source = Path(source_directory).resolve(); self.output = Path(output_directory).resolve()
        self.manifest = _snapshot(source_manifest)
        require(type(bindings) is dict and set(bindings) == set(BINDINGS), "WORKER_BINDINGS_REQUIRED")
        self.bindings = {key: require_root(bindings[key]) for key in BINDINGS}; self.tenant_id = _id(tenant_id)
        require(self.bindings["source_root"] == self.manifest["source_root"], "WORKER_SOURCE_BINDING_MISMATCH")
        require(not self.output.is_relative_to(self.source) and not self.source.is_relative_to(self.output), "WORKER_OUTPUT_SCOPE_INVALID")
        require(not Path(output_directory).is_symlink(), "WORKER_SYMLINK_FORBIDDEN")
        self.output.mkdir(parents=True, exist_ok=True)
        self.provider = provider; self.handle = signing_handle
        self.issuer = deepcopy(expected_issuer)
        require(provider.identity(signing_handle) == self.issuer and self.issuer["key_root"] == public_key_root(self.issuer["public_key_hex"]), "WORKER_ISSUER_MISMATCH")
        require(self.issuer["role"] in {"WITNESS", "NODE"}, "WORKER_ISSUER_ROLE_INVALID")
        require(type(allowed_operations) in {list, tuple} and allowed_operations and set(allowed_operations).issubset(OPERATIONS) and len(set(allowed_operations)) == len(allowed_operations), "WORKER_OPERATION_SET_INVALID")
        self.allowed_operations = tuple(sorted(allowed_operations))
        require(type(maximum_test_seconds) is int and 1 <= maximum_test_seconds <= 3600, "WORKER_TEST_TIMEOUT_INVALID")
        self.maximum_test_seconds = maximum_test_seconds
        require(type(maximum_artifact_bytes) is int and 1 <= maximum_artifact_bytes <= MAX_FILE_BYTES, "WORKER_ARTIFACT_BUDGET_INVALID")
        self.maximum_artifact_bytes = maximum_artifact_bytes
        self.trusted_tests = deepcopy(trusted_tests); source_rows = {row["path"]: row for row in self.manifest["files"]}
        require(type(trusted_tests) is dict, "WORKER_TRUSTED_TESTS_INVALID")
        for module, pin in self.trusted_tests.items():
            require(type(module) is str and bool(_MODULE.fullmatch(module)), "WORKER_TEST_MODULE_INVALID")
            exact_keys(pin, {"path", "sha256", "test_ids"}); name = _relative(pin["path"])
            require(name == module.replace(".", "/") + ".py" and name in source_rows and pin["sha256"] == source_rows[name]["sha256"], "WORKER_TEST_MODULE_PIN_INVALID")
            ids = pin["test_ids"]
            require(type(ids) is list and ids and ids == sorted(ids) and len(set(ids)) == len(ids) and all(type(value) is str and value.startswith(module + ".") for value in ids), "WORKER_TEST_IDENTITIES_INVALID")
        policy = {"schema": "ucl.ucm.workbench_worker_policy.v1", "bindings": self.bindings, "tenant_id": self.tenant_id, "issuer_root": self.issuer["key_root"], "implementation_root": _sha(Path(__file__).read_bytes()), "runner_root": RUNNER_ROOT, "trusted_tests": self.trusted_tests, "allowed_operations": list(self.allowed_operations), "maximum_test_seconds": maximum_test_seconds, "maximum_artifact_bytes": maximum_artifact_bytes, "sandbox": "UNBOUND_EXTERNAL", "execution_scope": "TRUSTED_PINNED_CODE_ONLY"}
        self.worker_root = root(policy); self.policy = policy
        require(snapshot_source(self.source) == self.manifest, "WORKER_SOURCE_CHANGED")

    def _validate(self, request: Any) -> dict[str, Any]:
        item = verify_worker_request(request)
        require(item["tenant_id"] == self.tenant_id, "WORKER_TENANT_MISMATCH")
        for key in BINDINGS:
            require(item[key] == self.bindings[key], "WORKER_BINDING_MISMATCH", "$", key)
        require(item["operation"] in self.allowed_operations, "WORKER_OPERATION_FORBIDDEN")
        _dispatch_payload(item, self.manifest, self.policy)
        return item

    def inspect_attempt(self, request: Any) -> dict[str, Any]:
        item = self._validate(request); folder = _contained(self.output, item["operation_id"])
        claim_path = _contained(self.output, item["operation_id"] + ".claim.json")
        if not claim_path.exists() and not folder.exists():
            return {"status": "NOT_STARTED", "request_root": item["request_root"], "retry_permitted": True}
        require(claim_path.is_file(), "WORKER_CUSTODY_CLAIM_MISSING")
        claim = strict_loads(claim_path.read_bytes())
        if type(claim) is dict and claim.get("disposition") == "EXECUTION_CLAIMED":
            require(claim == {"schema": "ucl.ucm.workbench.operation_claim.v1",
                              "request_root": item["request_root"],
                              "disposition": "EXECUTION_CLAIMED"},
                    "WORKER_IDEMPOTENCY_CONFLICT")
            if not folder.exists():
                return {"status": "PENDING_RECONCILIATION", "request_root": item["request_root"],
                        "retry_permitted": False, "observed_outputs": {"claim": claim}}
        else:
            body = _signature(claim, RECONCILIATION_DOMAIN, self.issuer)
            require(body == {"schema": "ucl.ucm.workbench.no_execution.v1",
                             "request_root": item["request_root"], "status": "NOT_EXECUTED",
                             "standing": "INFORMATION_ONLY", "authority_effect": "NONE"},
                    "WORKER_IDEMPOTENCY_CONFLICT")
            require(not folder.exists(), "WORKER_CUSTODY_CONFLICT")
            return {"status": "CANCELLED", "request_root": item["request_root"],
                    "retry_permitted": False, "attestation": claim}
        require(folder.is_dir(), "WORKER_CUSTODY_PATH_INVALID")
        request_path = _contained(folder, "REQUEST.json")
        require(request_path.is_file() and strict_loads(request_path.read_bytes()) == item, "WORKER_IDEMPOTENCY_CONFLICT")
        result_path = _contained(folder, "RESULT.json")
        if result_path.is_file():
            result = strict_loads(result_path.read_bytes())
            verify_worker_result(result, expected_request=item, expected_issuer=self.issuer, expected_worker_root=self.worker_root, expected_policy=self.policy)
            require(snapshot_source(self.source) == self.manifest, "WORKER_SOURCE_CHANGED")
            if item["operation"] == "PREPARE_CANDIDATE":
                candidate = _contained(folder, "candidate")
                require(snapshot_source(candidate) == result["evidence"]["result"]["candidate_manifest"], "WORKER_CANDIDATE_OUTPUT_DRIFT")
            return {"status": "COMPLETE", "request_root": item["request_root"], "retry_permitted": False, "result": result}
        # Observation never executes a second process or repeats a partial edit.
        files = snapshot_source(folder)
        return {"status": "PENDING_RECONCILIATION", "request_root": item["request_root"], "retry_permitted": False, "observed_outputs": files}

    def preflight(self, request: Any) -> dict[str, Any]:
        """Validate exact dispatch inputs before the manager marks an attempt in flight."""
        item = self._validate(request)
        require(snapshot_source(self.source) == self.manifest, "WORKER_SOURCE_CHANGED")
        if item["operation"] == "RUN_TESTS" and "candidate_operation_id" in item["payload"]:
            self._test_execution_source(item)
        prior = self.inspect_attempt(item)
        require(prior["status"] not in {"PENDING_RECONCILIATION", "CANCELLED"},
                "WORKER_RECONCILIATION_REQUIRED")
        body = {"schema": "ucl.ucm.workbench_worker_preflight.v1", "request_root": item["request_root"], "worker_root": self.worker_root, "source_root": self.manifest["source_root"], "status": "READY" if prior["status"] == "NOT_STARTED" else "ALREADY_COMPLETE", "authority_effect": "NONE"}
        return {**body, "preflight_root": root(body)}

    def attest_not_executed(self, request: Any) -> dict[str, Any]:
        """Atomically and durably cancel one exact request before attesting it."""
        item = self._validate(request)
        observed = self.inspect_attempt(item)
        if observed["status"] == "CANCELLED":
            return deepcopy(observed["attestation"])
        require(observed == {"status": "NOT_STARTED", "request_root": item["request_root"],
                             "retry_permitted": True}, "WORKER_NO_EXECUTION_ATTESTATION_REFUSED")
        body = {"schema": "ucl.ucm.workbench.no_execution.v1",
                "request_root": item["request_root"], "status": "NOT_EXECUTED",
                "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        attestation = self.provider.sign(self.handle, RECONCILIATION_DOMAIN, body)
        claim_path = _contained(self.output, item["operation_id"] + ".claim.json")
        try:
            with claim_path.open("xb") as stream:
                stream.write(canonical_bytes(attestation)); stream.flush(); os.fsync(stream.fileno())
        except FileExistsError as error:
            concurrent = self.inspect_attempt(item)
            if concurrent["status"] == "CANCELLED":
                return deepcopy(concurrent["attestation"])
            raise Refusal("WORKER_NO_EXECUTION_ATTESTATION_REFUSED") from error
        return attestation

    def execute(self, request: Any) -> dict[str, Any]:
        item = self._validate(request); prior = self.inspect_attempt(item)
        if prior["status"] == "COMPLETE":
            return deepcopy(prior["result"])
        require(prior["status"] != "CANCELLED", "WORKER_ATTEMPT_CANCELLED")
        require(prior["status"] == "NOT_STARTED", "WORKER_RECONCILIATION_REQUIRED")
        require(snapshot_source(self.source) == self.manifest, "WORKER_SOURCE_CHANGED")
        claim = {"schema": "ucl.ucm.workbench.operation_claim.v1",
                 "request_root": item["request_root"], "disposition": "EXECUTION_CLAIMED"}
        claim_path = _contained(self.output, item["operation_id"] + ".claim.json")
        try:
            with claim_path.open("xb") as stream:
                stream.write(canonical_bytes(claim)); stream.flush(); os.fsync(stream.fileno())
        except FileExistsError as error:
            concurrent = self.inspect_attempt(item)
            if concurrent["status"] == "COMPLETE":
                return deepcopy(concurrent["result"])
            if concurrent["status"] == "CANCELLED":
                raise Refusal("WORKER_ATTEMPT_CANCELLED") from error
            raise Refusal("WORKER_CONCURRENT_ATTEMPT") from error
        folder = _contained(self.output, item["operation_id"])
        try:
            folder.mkdir(exist_ok=False)
        except FileExistsError as error:
            raise Refusal("WORKER_CONCURRENT_ATTEMPT") from error
        (folder / "REQUEST.json").write_bytes(canonical_bytes(item))
        evidence, observation = self._perform(item, folder)
        body = _receipt_body(item, evidence, self.worker_root)
        signed = self.provider.sign(self.handle, RECEIPT_DOMAIN, body)
        observed = {"schema": "ucl.ucm.workbench_worker_observation.v1", "request_root": item["request_root"], "receipt_root": root(signed), **observation}
        result = {"receipt": signed, "evidence": evidence, "observation": observed, "observation_receipt": self.provider.sign(self.handle, OBSERVATION_DOMAIN, observed)}
        verify_worker_result(result, expected_request=item, expected_issuer=self.issuer, expected_worker_root=self.worker_root, expected_policy=self.policy)
        temporary = folder / "RESULT.pending.json"; temporary.write_bytes(canonical_bytes(result)); temporary.replace(folder / "RESULT.json")
        return result

    def _test_execution_source(self, request: dict[str, Any]) -> tuple[Path, dict[str, Any], str | None]:
        if "candidate_operation_id" not in request["payload"]:
            return self.source, self.manifest, None
        prepared_folder = _contained(self.output, request["payload"]["candidate_operation_id"])
        require(prepared_folder.is_dir(), "WORKER_CANDIDATE_PROVENANCE_INVALID")
        request_path = _contained(prepared_folder, "REQUEST.json")
        result_path = _contained(prepared_folder, "RESULT.json")
        require(request_path.is_file() and result_path.is_file(),
                "WORKER_CANDIDATE_PROVENANCE_INVALID")
        prepared_request = strict_loads(request_path.read_bytes())
        require(prepared_request["operation"] == "PREPARE_CANDIDATE", "WORKER_CANDIDATE_PROVENANCE_INVALID")
        prepared_result = strict_loads(result_path.read_bytes())
        verify_worker_result(prepared_result, expected_request=prepared_request,
                             expected_issuer=self.issuer, expected_worker_root=self.worker_root,
                             expected_policy=self.policy)
        manifest = _snapshot(prepared_result["evidence"]["result"]["candidate_manifest"])
        require(manifest["source_root"] == request["payload"]["candidate_source_root"],
                "WORKER_CANDIDATE_SOURCE_MISMATCH")
        source = _contained(prepared_folder,
                            prepared_result["evidence"]["result"]["candidate_relative_path"])
        require(snapshot_source(source) == manifest, "WORKER_CANDIDATE_OUTPUT_DRIFT")
        rows = {row["path"]: row for row in manifest["files"]}
        for module in request["payload"]["modules"]:
            pin = self.trusted_tests[module]
            require(rows.get(pin["path"], {}).get("sha256") == pin["sha256"],
                    "WORKER_CANDIDATE_TEST_MODULE_CHANGED")
        receipt_root = root(prepared_result["receipt"])
        require(receipt_root == request["payload"]["candidate_receipt_root"],
                "WORKER_CANDIDATE_RECEIPT_MISMATCH")
        return source, manifest, receipt_root

    def _perform(self, request: dict[str, Any], folder: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        operation = request["operation"]; observation: dict[str, Any] = {"process": None, "elapsed_nanoseconds": 0}
        evidence: dict[str, Any] = {"schema": "ucl.ucm.workbench_worker_evidence.v1", "operation": operation, "request_root": request["request_root"], "source_manifest": self.manifest, "source_unchanged": True, "policy": self.policy, "result": {}}
        if operation == "INSPECT_ARTIFACTS":
            rows = {row["path"]: row for row in self.manifest["files"]}
            inspected = []
            for name in request["payload"]["paths"]:
                raw = _contained(self.source, name).read_bytes()
                require(_sha(raw) == rows[name]["sha256"] and len(raw) == rows[name]["bytes"], "WORKER_SOURCE_CHANGED")
                inspected.append(deepcopy(rows[name]))
            evidence["result"] = {"inspected": inspected, "readset_root": root(inspected)}
        elif operation == "PREPARE_CANDIDATE":
            changes = _changes(request["payload"], self.manifest); candidate = folder / "candidate"; candidate.mkdir()
            for row in self.manifest["files"]:
                original = _contained(self.source, row["path"]).read_bytes(); require(_sha(original) == row["sha256"], "WORKER_SOURCE_CHANGED")
                target = _contained(candidate, row["path"]); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(original)
            for change in request["payload"]["changes"]:
                target = _contained(candidate, change["path"])
                if change["replacement_base64"] is None:
                    target.unlink()
                else:
                    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(base64.b64decode(change["replacement_base64"], validate=True))
            evidence["result"] = {"changes": changes, "candidate_manifest": snapshot_source(candidate), "candidate_relative_path": "candidate", "canonical_source_modified": False}
        else:
            modules = request["payload"]["modules"]
            execution_source, execution_manifest, candidate_receipt_root = self._test_execution_source(request)
            run_directory = folder / "run"; run_directory.mkdir()
            result_path = folder / "MEASUREMENT.json"
            argv = [sys.executable, "-I", "-B", "-c", TRUSTED_RUNNER, str(execution_source), json.dumps(modules, separators=(",", ":")), str(result_path)]
            started = time.monotonic_ns(); exit_code = None; stdout = b""; stderr = b""; process_error = None
            environment = {key: value for key, value in os.environ.items() if key.upper() not in {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT"}}
            environment["PYTHONHASHSEED"] = "0"; environment["PYTHONDONTWRITEBYTECODE"] = "1"
            try:
                completed = subprocess.run(argv, cwd=run_directory, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=self.maximum_test_seconds, shell=False, check=False)
                exit_code = completed.returncode; stdout = completed.stdout; stderr = completed.stderr
            except subprocess.TimeoutExpired as error:
                process_error = "TIMEOUT"; stdout = error.stdout or b""; stderr = error.stderr or b""
            except OSError as error:
                process_error = type(error).__name__
            observation = {"elapsed_nanoseconds": time.monotonic_ns() - started, "process": {"argv": argv, "cwd": str(run_directory), "python_version": sys.version, "python_executable_sha256": _sha(Path(sys.executable).read_bytes()), "exit_code": exit_code, "stdout_base64": base64.b64encode(stdout).decode("ascii"), "stderr_base64": base64.b64encode(stderr).decode("ascii"), "stdout_sha256": _sha(stdout), "stderr_sha256": _sha(stderr), "process_error": process_error}}
            measurement = strict_loads(result_path.read_bytes()) if result_path.is_file() else None
            expected_modules = [{"module": module, "sha256": self.trusted_tests[module]["sha256"]} for module in modules]
            expected_ids = sorted(value for module in modules for value in self.trusted_tests[module]["test_ids"])
            evidence["result"] = {"runner_root": RUNNER_ROOT, "expected_modules": expected_modules,
                "expected_test_ids": expected_ids, "measurement": measurement, "exit_code": exit_code,
                "process_error": process_error, "execution_source_manifest": execution_manifest,
                "execution_source_unchanged": snapshot_source(execution_source) == execution_manifest,
                "candidate_receipt_root": candidate_receipt_root,
                "invocation": {"runner_root": RUNNER_ROOT, "isolation_flags": ["-I", "-B"],
                    "modules": modules, "source_root": execution_manifest["source_root"],
                    "shell": False, "fresh_process": True, "sandbox": "UNBOUND_EXTERNAL"}}
        evidence["source_unchanged"] = snapshot_source(self.source) == self.manifest
        return evidence, observation


def _derive(request: dict[str, Any], evidence: Any) -> tuple[str, str, list[str]]:
    exact_keys(evidence, {"schema", "operation", "request_root", "source_manifest", "source_unchanged", "policy", "result"})
    require(evidence["schema"] == "ucl.ucm.workbench_worker_evidence.v1" and evidence["operation"] == request["operation"] and evidence["request_root"] == request["request_root"], "WORKER_EVIDENCE_BINDING_MISMATCH")
    source = _snapshot(evidence["source_manifest"]); require(source["source_root"] == request["source_root"], "WORKER_SOURCE_BINDING_MISMATCH")
    require(type(evidence["source_unchanged"]) is bool, "WORKER_EVIDENCE_INVALID")
    result = evidence["result"]; operation = request["operation"]
    effects = ["LOCAL_DISPOSABLE_WORKSPACE", "READ_WORKSPACE"]  # custody records are real local writes
    if operation == "INSPECT_ARTIFACTS":
        exact_keys(result, {"inspected", "readset_root"}); known = {row["path"]: row for row in source["files"]}
        require(result["inspected"] == [known[value] for value in request["payload"]["paths"]] and result["readset_root"] == root(result["inspected"]), "WORKER_READSET_MISMATCH")
    elif operation == "PREPARE_CANDIDATE":
        exact_keys(result, {"changes", "candidate_manifest", "candidate_relative_path", "canonical_source_modified"})
        changes = _changes(request["payload"], source); require(result["changes"] == changes, "WORKER_CHANGES_MISMATCH")
        expected = {row["path"]: deepcopy(row) for row in source["files"]}
        for change in changes:
            if change["replacement_sha256"] is None:
                expected.pop(change["path"])
            else:
                expected[change["path"]] = {"path": change["path"], "sha256": change["replacement_sha256"], "bytes": change["replacement_bytes"]}
        candidate = _snapshot(result["candidate_manifest"])
        require(candidate["files"] == [expected[key] for key in sorted(expected)] and result["candidate_relative_path"] == "candidate" and result["canonical_source_modified"] is False, "WORKER_CANDIDATE_MISMATCH")
    else:
        exact_keys(result, {"runner_root", "expected_modules", "expected_test_ids", "measurement", "exit_code", "process_error",
                            "execution_source_manifest", "execution_source_unchanged", "candidate_receipt_root", "invocation"})
        policy = evidence["policy"]; modules = request["payload"]["modules"]
        execution_source = _snapshot(result["execution_source_manifest"])
        expected_execution_root = request["payload"].get("candidate_source_root", request["source_root"])
        expected_candidate_receipt = None
        if "candidate_source_root" in request["payload"]:
            require_root(result["candidate_receipt_root"])
            expected_candidate_receipt = request["payload"]["candidate_receipt_root"]
        require(execution_source["source_root"] == expected_execution_root
                and result["candidate_receipt_root"] == expected_candidate_receipt
                and type(result["execution_source_unchanged"]) is bool,
                "WORKER_EXECUTION_SOURCE_INVALID")
        expected_modules = [{"module": module, "sha256": policy["trusted_tests"][module]["sha256"]} for module in modules]
        expected_ids = sorted(value for module in modules for value in policy["trusted_tests"][module]["test_ids"])
        require(result["expected_modules"] == expected_modules and result["expected_test_ids"] == expected_ids and result["runner_root"] == RUNNER_ROOT, "WORKER_TEST_POLICY_MISMATCH")
        require(result["invocation"] == {"runner_root": RUNNER_ROOT, "isolation_flags": ["-I", "-B"], "modules": modules, "source_root": execution_source["source_root"], "shell": False, "fresh_process": True, "sandbox": "UNBOUND_EXTERNAL"}, "WORKER_INVOCATION_INVALID")
        effects.append("LOCAL_TRUSTED_PROCESS")
        if result["process_error"] is not None:
            return "FAIL", "WORKER_TEST_PROCESS_FAILED", effects
        if result["measurement"] is None:
            return "FAIL", "WORKER_TEST_MEASUREMENT_MISSING", effects
        status, diagnostic = _test_status(result["measurement"], expected_modules, expected_ids, result["exit_code"], evidence["source_unchanged"] and result["execution_source_unchanged"])
        return status, diagnostic, effects
    return ("PASS", "OK", effects) if evidence["source_unchanged"] else ("FAIL", "WORKER_INPUT_DRIFT", effects)


def _receipt_body(request: dict[str, Any], evidence: Any, worker_root: str) -> dict[str, Any]:
    status, diagnostic, effects = _derive(request, evidence)
    return {"schema": "ucl.ucm.workbench_worker_receipt.v1", **{key: request[key] for key in ("operation", "operation_id", "task_id", "attempt_id", "generation", "tenant_id", *BINDINGS)}, "request_root": request["request_root"], "worker_root": require_root(worker_root), "evidence_root": root(evidence), "status": status, "diagnostic": diagnostic, "effects_observed": sorted(effects), "standing": "INFORMATION_ONLY", "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}


def _signature(record: Any, domain: str, issuer: dict[str, Any]) -> dict[str, Any]:
    exact_keys(record, {"body", "body_root", "signature", "key_root", "signature_algorithm"})
    require(type(record["signature"]) is str and type(record["body"]) is dict, "WORKER_SIGNATURE_INVALID")
    try:
        return verify_asymmetric(record, domain, expected_key_root=issuer["key_root"], public_key_hex=issuer["public_key_hex"])
    except (TypeError, UnicodeError) as error:
        raise Refusal("WORKER_SIGNATURE_INVALID") from error


def verify_worker_result(value: Any, *, expected_request: dict[str, Any], expected_issuer: dict[str, Any], expected_worker_root: str, expected_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate exact evidence and independent issuer; a stored PASS is never trusted."""
    item = exact_keys(value, {"receipt", "evidence", "observation", "observation_receipt"}); request = verify_worker_request(expected_request)
    body = _signature(item["receipt"], RECEIPT_DOMAIN, expected_issuer)
    exact_keys(item["evidence"], {"schema", "operation", "request_root", "source_manifest", "source_unchanged", "policy", "result"})
    policy = exact_keys(item["evidence"]["policy"], {"schema", "bindings", "tenant_id", "issuer_root", "implementation_root", "runner_root", "trusted_tests", "allowed_operations", "maximum_test_seconds", "maximum_artifact_bytes", "sandbox", "execution_scope"})
    require(policy["schema"] == "ucl.ucm.workbench_worker_policy.v1" and policy["implementation_root"] == _sha(Path(__file__).read_bytes()) and policy["sandbox"] == "UNBOUND_EXTERNAL" and policy["execution_scope"] == "TRUSTED_PINNED_CODE_ONLY", "WORKER_IMPLEMENTATION_PIN_MISMATCH")
    require(type(policy["maximum_artifact_bytes"]) is int and 1 <= policy["maximum_artifact_bytes"] <= MAX_FILE_BYTES and type(policy["maximum_test_seconds"]) is int and 1 <= policy["maximum_test_seconds"] <= 3600, "WORKER_POLICY_BUDGET_INVALID")
    require(root(policy) == require_root(expected_worker_root), "WORKER_POLICY_PIN_MISMATCH")
    if expected_policy is not None:
        require(policy == expected_policy, "WORKER_POLICY_PIN_MISMATCH")
    require(policy["issuer_root"] == expected_issuer["key_root"] and policy["tenant_id"] == request["tenant_id"] and policy["bindings"] == {key: request[key] for key in BINDINGS} and request["operation"] in policy["allowed_operations"] and policy["runner_root"] == RUNNER_ROOT, "WORKER_POLICY_BINDING_MISMATCH")
    _dispatch_payload(request, _snapshot(item["evidence"]["source_manifest"]), policy)
    require(body == _receipt_body(request, item["evidence"], expected_worker_root), "WORKER_RECEIPT_DERIVATION_MISMATCH")
    observation = item["observation"]
    exact_keys(observation, {"schema", "request_root", "receipt_root", "process", "elapsed_nanoseconds"})
    require(observation["schema"] == "ucl.ucm.workbench_worker_observation.v1" and observation["request_root"] == request["request_root"] and observation["receipt_root"] == root(item["receipt"]), "WORKER_OBSERVATION_BINDING_MISMATCH")
    observed = _signature(item["observation_receipt"], OBSERVATION_DOMAIN, expected_issuer)
    require(observed == observation and type(observation["elapsed_nanoseconds"]) is int and observation["elapsed_nanoseconds"] >= 0, "WORKER_OBSERVATION_INVALID")
    if request["operation"] == "RUN_TESTS":
        process = exact_keys(observation["process"], {"argv", "cwd", "python_version", "python_executable_sha256", "exit_code", "stdout_base64", "stderr_base64", "stdout_sha256", "stderr_sha256", "process_error"})
        require_root(process["python_executable_sha256"])
        for stream in ("stdout", "stderr"):
            try:
                decoded = base64.b64decode(process[stream + "_base64"], validate=True)
            except (ValueError, TypeError) as error:
                raise Refusal("WORKER_OBSERVATION_INVALID") from error
            require(_sha(decoded) == process[stream + "_sha256"], "WORKER_OBSERVATION_INVALID")
        argv = process["argv"]
        require(type(argv) is list and len(argv) == 8 and all(type(value) is str for value in argv) and argv[1:5] == ["-I", "-B", "-c", TRUSTED_RUNNER], "WORKER_PROCESS_INVOCATION_MISMATCH")
        require(strict_loads(argv[6]) == request["payload"]["modules"], "WORKER_PROCESS_INVOCATION_MISMATCH")
        require(process["exit_code"] == item["evidence"]["result"]["exit_code"] and process["process_error"] == item["evidence"]["result"]["process_error"], "WORKER_PROCESS_OBSERVATION_MISMATCH")
    else:
        require(observation["process"] is None and observation["elapsed_nanoseconds"] == 0, "WORKER_OBSERVATION_INVALID")
    return deepcopy(body)
