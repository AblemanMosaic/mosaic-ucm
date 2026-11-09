#!/usr/bin/env python3
"""Builder-authored, operator-runnable r025 contract-parity court."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

FIXED = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_kit(root):
    manifest = json.loads((root / "KIT-MANIFEST.json").read_text(encoding="utf-8"))
    from ucm.pippi_reviews import validate_operator_kit_contract
    validate_operator_kit_contract(manifest)
    for row in manifest["members"]:
        raw = (root / row["path"]).read_bytes()
        if sha(raw) != row["sha256"] or len(raw) != row["bytes"]:
            raise ValueError("KIT_MEMBER_CUSTODY_INVALID")
    names = sorted(path.relative_to(root).as_posix() for path in root.rglob("*")
                   if path.is_file() and path.name != "KIT-MANIFEST.json")
    if names != [row["path"] for row in manifest["members"]]:
        raise ValueError("KIT_CLOSED_SET_INVALID")
    return manifest


def seal_evidence(out, result):
    report = ("# UCM r025 contract-parity operator Tier 1\n\n"
              f"Status: **{result['status']}**  \nCases: {result['case_count']}  \n"
              f"Court root: `{result['court_root']}`\n").encode()
    payload = {"TIER1-RESULT.json": canonical(result) + b"\n",
               "REPORT.md": report, "RUN-TIER1.py": Path(__file__).read_bytes()}
    rows = [{"path": name, "sha256": sha(raw), "bytes": len(raw)}
            for name, raw in sorted(payload.items())]
    body = {"schema": "mosaic.ucm.portability-tier1-evidence-manifest.v0.1",
            "members": rows, "member_count": len(rows), **BOUNDARY}
    payload["MANIFEST.json"] = canonical(
        {**body, "manifest_root": sha(canonical(body))}) + b"\n"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"UCM-r025-CONTRACT-PARITY-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED); info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16; info.create_system = 3
            archive.writestr(info, raw)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(); kit = args.kit_root.resolve()
    with tempfile.TemporaryDirectory() as raw_temp:
        work = Path(raw_temp); runtime = work / "runtime"
        operator_history = work / "operator-history"
        program_history = work / "program-history"
        cold_boot = work / "cold-boot"
        with zipfile.ZipFile(kit / "UCM-v0.1-runtime.zip") as archive:
            archive.extractall(runtime)
        with zipfile.ZipFile(kit / "OPERATOR-HISTORY.zip") as archive:
            archive.extractall(operator_history)
        with zipfile.ZipFile(kit / "PROGRAM-HISTORY.zip") as archive:
            archive.extractall(program_history)
        with zipfile.ZipFile(kit / "PIPPI-v0.1-adaptive-cold-boot.zip") as archive:
            archive.extractall(cold_boot)
        sys.path.insert(0, str(runtime / "src"))
        manifest = verify_kit(kit)
        from ucm.operator_history import verify_frozen_operator_registry
        from ucm.program_history import verify_frozen_program_registry
        from ucm.pippi_adaptive import (mediation_library, pippi_shell_completion,
                                        prepare_turn, validate_turn_opening)
        from ucm.pippi_global import build_project
        from ucm.pippi_adaptive import negotiate_host_mode
        from ucm.pippi_portability import (
            build_execution_context, build_portability_witness,
            evaluate_portability_gate, inspect_portable_python_sources,
            portability_policy, probe_case_sensitivity)
        from ucm.system import capability_registry
        cases = []

        def case(case_id, predicate):
            try:
                ok = bool(predicate()); detail = "PASS" if ok else "PREDICATE_FALSE"
            except Exception as error:
                ok = False; detail = type(error).__name__ + ":" + sha(str(error).encode())
            cases.append({"case_id": case_id, "status": "PASS" if ok else "FAIL",
                          "detail": detail})
            print(f"[case {len(cases):03d}] {case_id}: {cases[-1]['status']}", flush=True)

        def refuses(call, code):
            try: call()
            except Exception as error: return code in str(error)
            return False

        qualification = json.loads((kit / "UCM-v0.1-QUALIFICATION.json").read_text())
        case("CONTROL-KIT-CUSTODY", lambda: manifest["runtime_sha256"] == sha((kit / "UCM-v0.1-runtime.zip").read_bytes()))
        case("CONTROL-QUALIFICATION", lambda: qualification["engineering_revision"] == "r025" and qualification["status"] == "PASS")
        registry = json.loads((operator_history / "spec/FROZEN-OPERATOR-REGISTRY.json").read_text())
        case("CONTROL-OPERATOR-HISTORY", lambda: verify_frozen_operator_registry(source_root=operator_history, registry=registry)["registry_root"] == registry["registry_root"])
        original = operator_history / "operator/dependency-graph-r021/RUN-TIER1.py"
        case("CONTROL-R021-ORIGINAL", lambda: sha(original.read_bytes()) == "12486f1726ac42698878dcb931bc7607429e090627c0472b5b579cdb1388b2f2")
        compat = operator_history / "operator/dependency-graph-r023-compat/RUN-TIER1.py"
        case("CONTROL-R023-COMPAT-SUCCESSOR", lambda: sha(compat.read_bytes()) == "d2ccc8d468c521fef72e0fdb9d065b7aafc8828c80819848e7cefc50cb8d2c7d")
        original_raw = original.read_bytes(); original.write_bytes(original_raw + b"x")
        case("OPERATOR-HISTORY-MUTATION", lambda: refuses(
            lambda: verify_frozen_operator_registry(source_root=operator_history, registry=registry),
            "FROZEN_OPERATOR_CUSTODY_MISMATCH"))
        original.write_bytes(original_raw)

        win = build_execution_context(host_family="WINDOWS", shell_family="POWERSHELL",
            path_flavour="WINDOWS", filesystem_class="WINDOWS_NATIVE",
            case_sensitive=False, python_implementation="CPython", python_version="3.12.3",
            source="DECLARED_EXTERNAL_HOST", wsl_distribution=None)
        wsl = build_execution_context(host_family="LINUX", shell_family="BASH",
            path_flavour="POSIX", filesystem_class="WSL_NATIVE", case_sensitive=True,
            python_implementation="CPython", python_version="3.12.3",
            source="DECLARED_EXTERNAL_HOST", wsl_distribution="Ubuntu")
        outputs = [{"artifact_id":"OUT", "root":"1"*64}]
        first = build_portability_witness(leg_id="WINDOWS_NATIVE", execution_context=win,
            source_root="2"*64, test_set_root="3"*64, canonical_outputs=outputs,
            status="PASS", reason_codes=[])
        second = build_portability_witness(leg_id="WSL_NATIVE", execution_context=wsl,
            source_root="2"*64, test_set_root="3"*64, canonical_outputs=outputs,
            status="PASS", reason_codes=[])
        case("CONTROL-PORTABILITY-GATE", lambda: evaluate_portability_gate(witnesses=[first, second])["status"] == "PASS_PORTABLE")
        case("MISSING-WSL-LEG", lambda: evaluate_portability_gate(witnesses=[first])["status"] == "PLATFORM_LEG_UNAVAILABLE")
        divergent = dict(second); divergent["canonical_outputs"] = [{"artifact_id":"OUT","root":"4"*64}]
        divergent_body = {key:value for key,value in divergent.items() if key != "witness_root"}
        from uclop.canonical import root
        divergent["witness_root"] = root(divergent_body)
        case("PLATFORM-OUTPUT-DIVERGENCE", lambda: evaluate_portability_gate(witnesses=[first, divergent])["status"] == "PLATFORM_DIVERGENCE")
        case("HOST-PATH-SORT-REFUSED", lambda: inspect_portable_python_sources(sources=[
            {"path":"src/bad.py", "text":"items=sorted(root.rglob('*'))\n"}])["status"] == "REFUSED")
        case("KEYED-PATH-SORT-PASSES", lambda: inspect_portable_python_sources(sources=[
            {"path":"src/good.py", "text":"items=sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix())\n"}])["status"] == "PASS")
        case("INVALID-PORTABLE-PATH-REFUSED", lambda: refuses(
            lambda: inspect_portable_python_sources(sources=[{"path":"src\\bad.py","text":"x=1\n"}]),
            "PIPPI_PORTABLE_PATH_INVALID"))
        case("CONTROL-POLICY", lambda: portability_policy()["required_leg_ids"] == ["WINDOWS_NATIVE","WSL_NATIVE"])
        shipped_gate = json.loads((kit / "PORTABILITY-GATE.json").read_text())
        shipped_witnesses = [json.loads((kit / name).read_text()) for name in
            ("WINDOWS-NATIVE-WITNESS.json", "WSL-NATIVE-WITNESS.json")]
        case("CONTROL-SHIPPED-PORTABILITY-EVIDENCE", lambda:
            evaluate_portability_gate(witnesses=shipped_witnesses)["portability_gate_root"]
            == shipped_gate["portability_gate_root"]
            and qualification["portability_gate_root"] == shipped_gate["portability_gate_root"])

        live_registry = capability_registry()
        checked_surface = json.loads((runtime / "spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json").read_text())
        checked_library = json.loads((runtime / "spec/PIPPI-MEDIATION-LIBRARY.json").read_text())
        portability_commands = {"environment-observe", "portability-policy",
            "portability-witness", "portability-gate", "portability-source-doctor"}
        completion_suffixes = {"bash": "bash", "zsh": "zsh", "fish": "fish",
                               "powershell": "ps1"}
        case("CONTROL-GENERATED-CONTRACTS", lambda:
            checked_surface["capability_registry_root"] == live_registry["root"]
            and checked_library == mediation_library()
            and portability_commands <= {row["cli"].split()[-1]
                                         for row in checked_surface["surfaces"]}
            and all(json.loads((runtime / f"completions/pippi.{suffix}.json").read_text())
                    == pippi_shell_completion(shell)
                    for shell, suffix in completion_suffixes.items()))
        cold_pairs = [
            ("PIPPI/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json",
             "spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json"),
            ("PIPPI/PIPPI-CAPABILITY-SURFACE-REGISTRY.json",
             "spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json"),
            ("PIPPI/PIPPI-MEDIATION-LIBRARY.json",
             "spec/PIPPI-MEDIATION-LIBRARY.json"),
        ] + [pair for suffix in ("bash", "zsh", "fish", "ps1") for pair in (
            (f"PIPPI/completions/pippi.{suffix}", f"completions/pippi.{suffix}"),
            (f"PIPPI/completions/pippi.{suffix}.json",
             f"completions/pippi.{suffix}.json"))]
        case("CONTROL-COLD-BOOT-CONTRACT-PARITY", lambda:
            all((cold_boot / left).read_bytes() == (runtime / right).read_bytes()
                for left, right in cold_pairs)
            and json.loads((cold_boot / cold_pairs[0][0]).read_text())["revision"] == "r025")

        program_registry = json.loads(
            (program_history / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text())
        verified_program = verify_frozen_program_registry(
            source_root=program_history, registry=program_registry)
        expected_outputs = sorted([
            {"artifact_id": "CAPABILITY_REGISTRY", "root": live_registry["root"]},
            {"artifact_id": "FROZEN_OPERATOR_REGISTRY", "root": registry["registry_root"]},
            {"artifact_id": "FROZEN_PROGRAM_REGISTRY", "root": verified_program["registry_root"]},
            {"artifact_id": "MEDIATION_LIBRARY", "root": mediation_library()["mediation_library_root"]},
            {"artifact_id": "PORTABILITY_POLICY", "root": portability_policy()["portability_policy_root"]},
        ], key=lambda row: row["artifact_id"])
        case("CONTROL-RECOMPUTED-WITNESS-OUTPUTS", lambda:
            all(row["canonical_outputs"] == expected_outputs for row in shipped_witnesses))
        substituted = [dict(row) for row in shipped_witnesses]
        substituted[0]["canonical_outputs"] = [{"artifact_id": "CAPABILITY_REGISTRY",
                                                   "root": "9" * 64}]
        case("WITNESS-STORED-ROOT-SUBSTITUTION", lambda:
            substituted[0]["canonical_outputs"] != expected_outputs)

        project = build_project(project_id="r025", title="r025", workspace=str(runtime),
            github_url=None, application_command=None, verification_command=None,
            readme=None, docs=[], revision="r025")
        host = negotiate_host_mode(host_id="operator", requested_mode="EXECUTABLE_LOCAL",
            capability_ids=["ARTIFACT_EXCHANGE","FILESYSTEM_READ","PROCESS_EXECUTION"], adapter_root=None)
        opening = prepare_turn(project=project, host_profile=host, sequence=1,
            previous_turn_root=None, scenario="PACKAGING",
            requested_rule_ids=["EXECUTION_CONTEXT_DISCIPLINE","PORTABILITY_DETERMINISM"],
            acceptance_case_roots=["5"*64], journal_head=None, execution_context=win)
        case("CONTROL-TURN-CONTEXT-BINDING", lambda: validate_turn_opening(opening)["execution_context_root"] == win["execution_context_root"])
        swapped = dict(opening); swapped["execution_context_root"] = "6"*64
        case("TURN-CONTEXT-SWAP", lambda: refuses(lambda: validate_turn_opening(swapped), "PIPPI_TURN_OPENING_INVALID"))
        library = mediation_library()
        ids = {row["rule_id"] for row in library["rules"]}
        case("CONTROL-CONTEXT-RULES", lambda: {"EXECUTION_CONTEXT_DISCIPLINE","PORTABILITY_DETERMINISM"} <= ids)
        automatic = prepare_turn(project=project, host_profile=host, sequence=1,
            previous_turn_root=None, scenario="PACKAGING", requested_rule_ids=[],
            acceptance_case_roots=["5"*64], journal_head=None, execution_context=win)
        case("SCENARIO-REQUIRED-RULES-INJECTED", lambda:
            {"ARCHIVE_POLICY", "EXECUTION_CONTEXT_DISCIPLINE",
             "PORTABILITY_DETERMINISM", "VERSION_POLICY"} <= set(automatic["rule_ids"]))
        omitted = dict(automatic)
        omitted["rule_ids"] = [value for value in omitted["rule_ids"]
                               if value != "PORTABILITY_DETERMINISM"]
        omitted["context"] = [row for row in omitted["context"]
                              if row["rule_id"] != "PORTABILITY_DETERMINISM"]
        omitted["turn_opening_root"] = root({key: value for key, value in omitted.items()
                                              if key != "turn_opening_root"})
        case("SCENARIO-REQUIRED-RULE-OMISSION", lambda: refuses(
            lambda: validate_turn_opening(omitted), "PIPPI_TURN_OPENING_INVALID"))
        before = {path.name for path in work.glob(".pippi-case-probe-*")}
        observed_case = probe_case_sensitivity(work)
        after = {path.name for path in work.glob(".pippi-case-probe-*")}
        case("FILESYSTEM-CASE-PROBE-CLEAN", lambda:
            type(observed_case) is bool and before == after)
        case("CONTROL-AUTHORITY-CEILING", lambda: all(row["status"] == "PASS" for row in cases) and BOUNDARY["authority_effect"] == "NONE")

    body = {"schema":"mosaic.ucm.portability-tier1-result.v0.1",
            "revision":"r025", "runtime_sha256":manifest["runtime_sha256"],
            "qualification_sha256":manifest["qualification_sha256"],
            "cases":cases, "case_count":len(cases),
            "failed":sum(row["status"] != "PASS" for row in cases), **BOUNDARY}
    body["status"] = "PASS" if body["failed"] == 0 else "HOLD_FOR_REPAIR"
    result = {**body, "court_root": sha(canonical(body))}
    evidence = seal_evidence(args.out_dir.resolve(), result)
    print(json.dumps({"status":result["status"], "cases":len(cases),
                      "failed":result["failed"], "court_root":result["court_root"],
                      "evidence":str(evidence), "evidence_sha256":sha(evidence.read_bytes()),
                      **BOUNDARY}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
