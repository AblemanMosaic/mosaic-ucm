"""Exact optional CMBA binding of Pippi's common observable turn record.

The supplied CMBA generic evaluator checks commitments.  It does not interpret
Pippi policy, verify reported activity, grant a permit, or assert native-host
interposition.  The older CMBA r033 native-turn adapter keeps its own contract.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import csv
import hashlib
import importlib
import io
from pathlib import Path, PurePosixPath
import sys
import threading
from typing import Any
import zipfile
import zipimport

from uclop.canonical import Refusal, canonical_bytes, require, root

from .pippi_global import BOUNDARY


CMBA_SOURCE_SHA256 = "620f4987533198337306e577e8c8c6cca74bc63685947cab1e37c0907782f230"
CMBA_WHEEL_SHA256 = "fad457fd7a8fe4598da1280fbca90881cfc5e48a5dd410ab9c784ffcb19c70ca"
CMBA_WHEEL_RELATIVE_PATH = "vendor/optional-packs/cmba/cmba_core-0.1.0a7-py3-none-any.whl"
CMBA_PROFILE_ID = "cmba.generic"
_IMPORT_LOCK = threading.RLock()
_PACKAGES = ("cmba_core", "cmba_agent", "cmba_workbench")
_SELECTED_MODULES = ("cmba_core", "cmba_core.bindings", "cmba_core.codec",
                     "cmba_core.evaluation", "cmba_core.registry")


def _wheel_path() -> Path:
    return Path(__file__).resolve().parents[2] / CMBA_WHEEL_RELATIVE_PATH


def _verified_wheel(expected_wheel_sha256: str) -> tuple[Path, dict[str, str], str]:
    require(type(expected_wheel_sha256) is str
            and expected_wheel_sha256 == CMBA_WHEEL_SHA256,
            "PIPPI_CMBA_EXPECTED_WHEEL_PIN_REQUIRED")
    path = _wheel_path()
    require(path.is_file(), "PIPPI_CMBA_WHEEL_UNAVAILABLE")
    try:
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected_wheel_sha256,
                "PIPPI_CMBA_WHEEL_PIN_MISMATCH")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            require(len(names) == len(set(names)) and names,
                    "PIPPI_CMBA_WHEEL_MEMBERS_INVALID")
            members = {}
            for name in names:
                part = PurePosixPath(name)
                require(name == part.as_posix() and not part.is_absolute()
                        and ".." not in part.parts and "\\" not in name
                        and not name.endswith("/"),
                        "PIPPI_CMBA_WHEEL_MEMBERS_INVALID")
                members[name] = archive.read(name)
        record_name = "cmba_core-0.1.0a7.dist-info/RECORD"
        require(record_name in members, "PIPPI_CMBA_WHEEL_RECORD_MISSING")
        records = list(csv.reader(io.StringIO(members[record_name].decode("utf-8"))))
        require(all(len(row) == 3 for row in records)
                and len(records) == len(members)
                and len({row[0] for row in records}) == len(records)
                and {row[0] for row in records} == set(members),
                "PIPPI_CMBA_WHEEL_RECORD_INVALID")
        for name, digest, size in records:
            if name == record_name:
                require(digest == "" and size == "", "PIPPI_CMBA_WHEEL_RECORD_INVALID")
            else:
                encoded = base64.urlsafe_b64encode(
                    hashlib.sha256(members[name]).digest()).rstrip(b"=").decode("ascii")
                require(digest == "sha256=" + encoded and size == str(len(members[name])),
                        "PIPPI_CMBA_WHEEL_RECORD_INVALID")
        hashes = {name: hashlib.sha256(value).hexdigest()
                  for name, value in sorted(members.items())}
        return path.resolve(), hashes, root(hashes)
    except Refusal:
        raise
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, csv.Error) as error:
        raise Refusal("PIPPI_CMBA_WHEEL_INVALID", detail=type(error).__name__) from error


def _module_origin(module: Any, path: Path, hashes: dict[str, str]) -> str:
    loader = getattr(module, "__loader__", None)
    archive = getattr(loader, "archive", None)
    spec = getattr(module, "__spec__", None)
    origin = getattr(spec, "origin", None)
    require(isinstance(loader, zipimport.zipimporter)
            and getattr(spec, "loader", None) is loader
            and type(archive) is str and Path(archive).resolve() == path
            and type(origin) is str and origin == getattr(module, "__file__", None),
            "PIPPI_CMBA_MODULE_ORIGIN_MISMATCH")
    prefix = str(path).replace("\\", "/") + "/"
    normalized = origin.replace("\\", "/")
    require(normalized.startswith(prefix), "PIPPI_CMBA_MODULE_ORIGIN_MISMATCH")
    member = normalized[len(prefix):]
    require(member in hashes, "PIPPI_CMBA_MODULE_ORIGIN_MISMATCH")
    return member


def _verify_preloaded(path: Path, hashes: dict[str, str]) -> None:
    for name, module in list(sys.modules.items()):
        if any(name == prefix or name.startswith(prefix + ".") for prefix in _PACKAGES):
            require(module is not None, "PIPPI_CMBA_MODULE_ORIGIN_MISMATCH")
            _module_origin(module, path, hashes)


def _load_cmba(expected_wheel_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    with _IMPORT_LOCK:
        path, hashes, members_root = _verified_wheel(expected_wheel_sha256)
        _verify_preloaded(path, hashes)
        entry = str(path)
        importlib.invalidate_caches()
        sys.path.insert(0, entry)
        try:
            modules = {name: importlib.import_module(name) for name in _SELECTED_MODULES}
        except (ImportError, OSError, ValueError) as error:
            raise Refusal("PIPPI_CMBA_LOAD_FAILED", detail=type(error).__name__) from error
        finally:
            # Restore exactly the temporary search entry; retain package origins.
            if sys.path and sys.path[0] == entry:
                sys.path.pop(0)
            elif entry in sys.path:
                sys.path.remove(entry)
        # Verify the artifact again after import. The local package must remain
        # immutable throughout loading; origin checks do not attest host runtime.
        post_path, post_hashes, post_root = _verified_wheel(expected_wheel_sha256)
        require((post_path, post_hashes, post_root) == (path, hashes, members_root),
                "PIPPI_CMBA_WHEEL_CHANGED_DURING_LOAD")
        _verify_preloaded(path, hashes)
        origins = [{"module": name, "member": _module_origin(modules[name], path, hashes),
                    "sha256": hashes[_module_origin(modules[name], path, hashes)]}
                   for name in _SELECTED_MODULES]
        identity = {"artifact": CMBA_WHEEL_RELATIVE_PATH,
                    "wheel_sha256": expected_wheel_sha256,
                    "source_archive_sha256": CMBA_SOURCE_SHA256,
                    "source_binding": "EXACT_SUPPLIED_CANDIDATE_DECLARATION",
                    "wheel_members_root": members_root,
                    "wheel_member_count": len(hashes), "loaded_origins": origins,
                    "load_boundary": "EXACT_WHEEL_NO_INSTALL_NO_NETWORK",
                    "runtime_integrity": "HOST_TRUST_ASSUMPTION",
                    "artifact_mutation_during_load": "FORBIDDEN"}
        return modules, identity


def discover_cmba_binding() -> dict[str, Any]:
    """Inspect optional artifact availability without importing its code."""
    available = _wheel_path().is_file()
    observation = "NOT_PRESENT"
    if available:
        _verified_wheel(CMBA_WHEEL_SHA256)
        observation = "EXACT_WHEEL_VERIFIED"
    body = {"schema": "mosaic.ucm.pippi-cmba-binding.v0.1",
            "status": "AVAILABLE" if available else "UNAVAILABLE_OPTIONAL_PACK",
            "artifact_observation": observation,
            "wheel_artifact": CMBA_WHEEL_RELATIVE_PATH,
            "expected_wheel_sha256": CMBA_WHEEL_SHA256,
            "source_archive_sha256": CMBA_SOURCE_SHA256,
            "profile_id": CMBA_PROFILE_ID,
            "mapping": "UCM_COMMON_TURN_AS_TYPED_NONCRITICAL_DIMENSIONS",
            "claim_ceiling": "COMMITMENT_STRUCTURE_AND_EXACT_VALUES_ONLY",
            "native_adapter_inventory": [{
                "module": "cmba_core.profiles.pippi", "function": "project_native_turn",
                "scope": "PINNED_UCM_R033_NO_NATIVE_TOOLS",
                "availability": "SEPARATE_EXISTING_CMBA_API",
                "r034_compatibility": "NOT_CLAIMED"}],
            "core_turn_records_require_cmba": False,
            "effect_authorized": False, "policy_truth": "NOT_ESTABLISHED", **BOUNDARY}
    return {**body, "binding_descriptor_root": root(body)}


def build_cmba_turn_assessment(*, opening: dict[str, Any], report: dict[str, Any],
                               turn_record: dict[str, Any],
                               expected_wheel_sha256: str) -> dict[str, Any]:
    """Revalidate UCM records, then invoke the exact supplied CMBA evaluator."""
    from .pippi_turn_record import validate_turn_record

    turn = validate_turn_record(turn_record, opening=opening, report=report)
    modules, identity = _load_cmba(expected_wheel_sha256)
    bindings = modules["cmba_core.bindings"]
    evaluator = modules["cmba_core.evaluation"]
    registry = modules["cmba_core.registry"]
    contract = registry.contract(CMBA_PROFILE_ID)
    profile = bindings.profile_reference(contract)
    values = {"ucm.common-turn": deepcopy(turn), "ucm.opening": deepcopy(opening),
              "ucm.report": deepcopy(report)}
    schemas = {"ucm.common-turn": "mosaic.ucm.pippi-turn-record.v0.1",
               "ucm.opening": opening["schema"], "ucm.report": report["schema"]}
    try:
        dimensions = [bindings.dimension(name, "observable-record", schemas[name], value,
                                         critical=False)
                      for name, value in sorted(values.items())]
        native_roots = {"turn_record_root": turn["turn_record_root"],
                        "turn_opening_root": opening["turn_opening_root"],
                        "turn_report_root": report["turn_report_root"]}
        relations = [bindings.relation("ucm-" + name.replace("_", "-"),
                                       "references-native-root",
                                       bindings.reference("mosaic.ucm.native-root", digest))
                     for name, digest in sorted(native_roots.items())]
        binding = bindings.bind(profile, dimensions, relations=relations)
        inspection = bindings.inspect(binding, values, expected_root=binding["binding_root"])
        context = {"schema": "cmba.evaluation-context.v0.1-i1",
                   "expected_binding_root": binding["binding_root"],
                   "policy": {"profile": profile, "required_checks": sorted(contract["predicates"])},
                   "authority_snapshot": {"authority_effect": "NONE", "recognition": "NOT_ESTABLISHED"},
                   "evidence_snapshot": [],
                   "time": {"epoch": 0, "clock_source": "deterministic-structural-assessment"}}
        receipt = evaluator.evaluate(binding, values, context)
        replay = evaluator.replay(receipt, binding, values, context)
        require(receipt["body"]["result"]["status"] == "MATCH_FOR_SUPPLIED_EVIDENCE",
                "PIPPI_CMBA_STRUCTURAL_ASSESSMENT_INCOMPLETE")
    except Refusal:
        raise
    except ValueError as error:
        code = getattr(error, "code", "CMBA_EVALUATION_REFUSED")
        raise Refusal("PIPPI_CMBA_EVALUATOR_REFUSED", detail=str(code)) from error
    body = {"schema": "mosaic.ucm.pippi-cmba-turn-assessment.v0.1",
            "outcome": "STRUCTURAL_BINDING_VALID", "native_roots": native_roots,
            "cmba_identity": identity, "cmba_profile": profile,
            "cmba_binding": binding, "cmba_values": values,
            "cmba_inspection": inspection, "cmba_context": context,
            "cmba_receipt": receipt, "cmba_replay": replay,
            "assurance": "DECLARED_NOT_VERIFIED",
            "claim_ceiling": "COMMITMENT_STRUCTURE_AND_EXACT_VALUES_ONLY",
            "policy_truth": "NOT_ESTABLISHED", "reported_activity": "NOT_INDEPENDENTLY_OBSERVED",
            "host_interposition": "NOT_ESTABLISHED", "effect_authorized": False,
            "current_use_admissibility": "NOT_EVALUATED", **BOUNDARY}
    return {**body, "assessment_root": root(body)}


def validate_cmba_turn_assessment(value: dict[str, Any], *, opening: dict[str, Any],
                                  report: dict[str, Any], turn_record: dict[str, Any],
                                  expected_wheel_sha256: str) -> dict[str, Any]:
    expected = build_cmba_turn_assessment(opening=opening, report=report,
        turn_record=turn_record, expected_wheel_sha256=expected_wheel_sha256)
    require(canonical_bytes(value) == canonical_bytes(expected), "PIPPI_CMBA_ASSESSMENT_MISMATCH")
    return deepcopy(expected)
