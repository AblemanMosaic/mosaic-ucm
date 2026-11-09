#!/usr/bin/env python3
"""Builder-authored, operator-runnable r022 UGEL boundary court."""
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
    report = ("# UCM UGEL r022 operator Tier 1\n\n"
              f"Status: **{result['status']}**  \nCases: {result['case_count']}  \n"
              f"Court root: `{result['court_root']}`\n").encode()
    payload = {"TIER1-RESULT.json": canonical(result) + b"\n",
               "REPORT.md": report, "RUN-TIER1.py": Path(__file__).read_bytes()}
    rows = [{"path": name, "sha256": sha(raw), "bytes": len(raw)}
            for name, raw in sorted(payload.items())]
    body = {"schema": "mosaic.ucm.ugel-tier1-evidence-manifest.v0.1",
            "members": rows, "member_count": len(rows), **BOUNDARY}
    payload["MANIFEST.json"] = canonical(
        {**body, "manifest_root": sha(canonical(body))}) + b"\n"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"UCM-UGEL-r022-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
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
    args = parser.parse_args()
    kit = args.kit_root.resolve()
    with tempfile.TemporaryDirectory() as raw_temp:
        runtime = Path(raw_temp) / "runtime"
        with zipfile.ZipFile(kit / "UCM-v0.1-runtime.zip") as archive:
            archive.extractall(runtime)
        sys.path.insert(0, str(runtime / "src"))
        manifest = verify_kit(kit)
        from uclop.canonical import root
        from ucm.pippi_packs import (build_install_plan, default_pack_inventory,
                                     pack_registry)
        from ucm.ugel import (UGEL_SOURCE_ARCHIVE_SHA256, UGEL_SOURCE_ROOT,
            build_component_policy, build_executor_binding, build_guest_call,
            evaluate_reference_sim_add, executor_pack_registry, ugel_root)
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
        evidence = [root({"custody": UGEL_SOURCE_ARCHIVE_SHA256})]
        binding = build_executor_binding(
            executor_public_key_hex="72" * 32,
            source_archive_sha256=UGEL_SOURCE_ARCHIVE_SHA256,
            source_root=UGEL_SOURCE_ROOT, evidence_roots=evidence)
        policy = build_component_policy(
            component_sha256=root({"component": "operator"}),
            contract_root=root({"contract": "operator"}), allowed_effects=["sim.add"],
            resource_ids=["calculator:primary"], allowed_actions=["RUN"],
            max_text_bytes=0)
        call = build_guest_call(
            policy=policy, action="RUN", operation_id="op:ugel:r022:operator",
            effect_id="sim.add", resource_id="calculator:primary",
            parameters={"left": 20, "right": 22}, evidence_roots=evidence)
        result = evaluate_reference_sim_add(guest_call=call, policy=policy)
        registry = executor_pack_registry()
        case("CONTROL-KIT-CUSTODY", lambda: manifest["runtime_sha256"] == sha((kit / "UCM-v0.1-runtime.zip").read_bytes()))
        case("CONTROL-EXECUTOR-REGISTRY", lambda: registry["native_wasi_runtime_status"] == "NOT_BOUND" and not registry["executor_selected_by_ucm"])
        case("CONTROL-EXACT-UGEL-PINS", lambda: binding["source_archive_sha256"] == UGEL_SOURCE_ARCHIVE_SHA256 and binding["source_root"] == UGEL_SOURCE_ROOT)
        case("CONTROL-DOMAIN-SEPARATION", lambda: ugel_root({"x": 1}) != root({"x": 1}))
        case("CONTROL-SIM-ADD", lambda: result["output"]["sum"] == 42)
        case("SOURCE-ARCHIVE-PIN-SWAP", lambda: refuses(lambda: build_executor_binding(executor_public_key_hex="72"*32, source_archive_sha256="0"*64, source_root=UGEL_SOURCE_ROOT, evidence_roots=evidence), "UGEL_SOURCE_ARCHIVE_PIN_MISMATCH"))
        case("SOURCE-ROOT-SWAP", lambda: refuses(lambda: build_executor_binding(executor_public_key_hex="72"*32, source_archive_sha256=UGEL_SOURCE_ARCHIVE_SHA256, source_root="0"*64, evidence_roots=evidence), "UGEL_SOURCE_ROOT_MISMATCH"))
        case("BINDING-EVIDENCE-EMPTY", lambda: refuses(lambda: build_executor_binding(executor_public_key_hex="72"*32, source_archive_sha256=UGEL_SOURCE_ARCHIVE_SHA256, source_root=UGEL_SOURCE_ROOT, evidence_roots=[]), "UGEL_BINDING_EVIDENCE_INVALID"))
        case("UNSUPPORTED-EFFECT-REFUSED", lambda: refuses(lambda: build_component_policy(component_sha256=root({"c":1}), contract_root=root({"p":1}), allowed_effects=["fs.create"], resource_ids=["r"], allowed_actions=["RUN"], max_text_bytes=0), "UGEL_POLICY_EFFECTS_INVALID"))
        case("CALL-RESOURCE-OUTSIDE-POLICY", lambda: refuses(lambda: build_guest_call(policy=policy, action="RUN", operation_id="op:x", effect_id="sim.add", resource_id="calculator:other", parameters={"left":1,"right":2}, evidence_roots=evidence), "UGEL_RESOURCE_NOT_ALLOWED"))
        case("CALL-EFFECT-OUTSIDE-POLICY", lambda: refuses(lambda: build_guest_call(policy=policy, action="RUN", operation_id="op:x", effect_id="sim.echo", resource_id="calculator:primary", parameters={"text":"x"}, evidence_roots=evidence), "UGEL_EFFECT_NOT_ALLOWED"))
        case("CALL-PARAMETER-SHAPE-REFUSED", lambda: refuses(lambda: evaluate_reference_sim_add(guest_call=build_guest_call(policy=policy, action="RUN", operation_id="op:x", effect_id="sim.add", resource_id="calculator:primary", parameters={"left":1}, evidence_roots=evidence), policy=policy), "REQUIRED_FIELD_MISSING"))
        packs = pack_registry()
        pack_ids = [row["pack_id"] for row in packs["packs"]]
        case("CONTROL-OPTIONAL-PACK", lambda: "UGEL_EXECUTOR" in pack_ids and "UGEL_EXECUTOR" not in packs["profiles"]["RECOMMENDED_LOCAL"])
        plan = build_install_plan(profile="RECOMMENDED_LOCAL",
                                  inventory=default_pack_inventory(),
                                  requested_packs=["UGEL_EXECUTOR"],
                                  allow_remote_downloads=False)
        case("OPTIONAL-PACK-UNBOUND-HELD", lambda: plan["status"] == "HELD" and any(row["pack_id"] == "UGEL_EXECUTOR" for row in plan["holds"]))
        qualification = json.loads((kit / "UCM-v0.1-QUALIFICATION.json").read_text())
        case("QUALIFICATION-NAMES-ACCEPTANCE", lambda: any(item.endswith("test_sim_add_crosses_pippi_gateway_receipts_and_dependency_evidence") for item in qualification["test_ids"]))
    body = {"schema": "mosaic.ucm.ugel-tier1-result.v0.1", "revision": "r022",
            "runtime_sha256": manifest["runtime_sha256"],
            "qualification_sha256": manifest["qualification_sha256"],
            "operator_kit_root": manifest["operator_kit_root"],
            "cases": cases, "case_count": len(cases),
            "failed": sum(row["status"] != "PASS" for row in cases), **BOUNDARY}
    body["status"] = "PASS" if body["failed"] == 0 else "HOLD_FOR_REPAIR"
    result_record = {**body, "court_root": sha(canonical(body))}
    path = seal_evidence(args.out_dir.resolve(), result_record)
    print(json.dumps({"status": result_record["status"], "cases": len(cases),
                      "failed": result_record["failed"],
                      "court_root": result_record["court_root"],
                      "evidence": str(path), "evidence_sha256": sha(path.read_bytes()),
                      **BOUNDARY}, sort_keys=True))
    return 0 if result_record["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
