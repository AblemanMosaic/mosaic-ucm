#!/usr/bin/env python3
"""Builder-authored, operator-runnable r023 systemic repair court."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
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
    report = ("# UCM r023 systemic repair operator Tier 1\n\n"
              f"Status: **{result['status']}**  \nCases: {result['case_count']}  \n"
              f"Court root: `{result['court_root']}`\n").encode()
    payload = {"TIER1-RESULT.json": canonical(result) + b"\n",
               "REPORT.md": report, "RUN-TIER1.py": Path(__file__).read_bytes()}
    rows = [{"path": name, "sha256": sha(raw), "bytes": len(raw)}
            for name, raw in sorted(payload.items())]
    body = {"schema": "mosaic.ucm.systemic-repair-tier1-evidence-manifest.v0.1",
            "members": rows, "member_count": len(rows), **BOUNDARY}
    payload["MANIFEST.json"] = canonical(
        {**body, "manifest_root": sha(canonical(body))}) + b"\n"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"UCM-r023-SYSTEMIC-REPAIR-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
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
        work = Path(raw_temp); runtime = work / "runtime"; history = work / "history"
        with zipfile.ZipFile(kit / "UCM-v0.1-runtime.zip") as archive:
            archive.extractall(runtime)
        with zipfile.ZipFile(kit / "PROGRAM-HISTORY.zip") as archive:
            archive.extractall(history)
        sys.path.insert(0, str(runtime / "src"))
        manifest = verify_kit(kit)
        from uclop.canonical import Refusal, root
        from ucm.dependency_graph import (build_graph, build_producer_receipt,
            build_reuse_admission, build_snapshot, evaluate_graph)
        from ucm.program_history import verify_frozen_program_registry
        from ucm.ugel import (build_component_policy, build_guest_call,
            evaluate_reference_sim_add, validate_correspondence,
            validate_reference_result)
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
        case("CONTROL-KIT-CUSTODY", lambda: manifest["runtime_sha256"] == sha((kit / "UCM-v0.1-runtime.zip").read_bytes()))
        qualification = json.loads((kit / "UCM-v0.1-QUALIFICATION.json").read_text())
        case("CONTROL-QUALIFICATION", lambda: qualification["engineering_revision"] == "r023" and qualification["status"] == "PASS" and qualification["test_count"] == 411)

        verifier_spec = importlib.util.spec_from_file_location("ugel_source_verify", kit / "verify_ugel_source_archive.py")
        verifier = importlib.util.module_from_spec(verifier_spec); verifier_spec.loader.exec_module(verifier)
        archive_path = kit / "UGEL-BATCH-E-r001.zip"
        case("CONTROL-UGEL-SOURCE-CUSTODY", lambda: verifier.verify_archive(archive_path)["status"] == "PASS")

        registry = json.loads((history / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text())
        case("CONTROL-FROZEN-PROGRAM-HISTORY", lambda: verify_frozen_program_registry(source_root=history, registry=registry)["registry_root"] == registry["registry_root"])
        program = json.loads((runtime / "program/systemic-repair-r023/PROGRAM.json").read_text())
        case("CONTROL-R023-PROGRAM", lambda: program["engineering_revision"] == "r023" and len(program["acceptance_case_roots"]) == 5)

        R = [f"{i:x}" * 64 for i in range(1, 10)]
        node = {"node_id":"literal","kind":"LITERAL","dependencies":[],
                "parameters":{"value":{"ready":True}},"transform_id":"LITERAL",
                "transform_version":"v0.1","semantic_contract_root":R[0],
                "policy_root":R[1],"jurisdiction_root":R[2],"environment_root":R[3],
                "closure_coverage":"COMPLETE","evidence_grade":"DETERMINISTIC_DERIVATION","pure":True}
        graph = build_graph(graph_id="operator", nodes=[node], adapter_id="OPERATOR",
                            adapter_version="v0.1", adapter_policy_root=R[1],
                            schema_registry_root=R[4], trust_root=R[5], closure_claim="COMPLETE")
        snapshot = build_snapshot(graph=graph, snapshot_id="operator", inputs=[], predecessor_snapshot_root=None)
        prior = evaluate_graph(graph=graph, snapshot=snapshot, now_ns=20)
        receipt = build_producer_receipt(producer_root=R[0], graph=graph, snapshot=snapshot,
            evaluation=prior, execution_capsule_root=R[1], checker_root=R[2])
        admission = build_reuse_admission(graph=graph, snapshot=snapshot, prior_graph=graph,
            prior_snapshot=snapshot, prior_evaluation=prior,
            expected_prior_evaluation_root=prior["evaluation_root"], expected_producer_root=R[0],
            producer_receipt=receipt, consumer_trust_root=R[5],
            admitted_evidence_grades=["DETERMINISTIC_DERIVATION"], reuse_mode="VERIFIED_PURE_REUSE")
        common = dict(graph=graph, snapshot=snapshot, now_ns=20, prior_evaluation=prior,
            reuse_admission=admission, expected_prior_evaluation_root=prior["evaluation_root"],
            expected_producer_root=R[0], expected_producer_receipt_root=receipt["receipt_root"],
            expected_consumer_trust_root=R[5], mode="VERIFIED_PURE_REUSE")
        case("CONTROL-POINT-OF-USE-REUSE", lambda: evaluate_graph(**common)["status"] == "PASS")
        for case_id, field, code in (
            ("REUSE-PRIOR-ROOT-SWAP", "expected_prior_evaluation_root", "DEPENDENCY_PRIOR_EVALUATION_UNEXPECTED_AT_USE"),
            ("REUSE-PRODUCER-ROOT-SWAP", "expected_producer_root", "DEPENDENCY_ADMISSION_PRODUCER_UNEXPECTED_AT_USE"),
            ("REUSE-RECEIPT-ROOT-SWAP", "expected_producer_receipt_root", "DEPENDENCY_ADMISSION_RECEIPT_UNEXPECTED_AT_USE"),
            ("REUSE-TRUST-ROOT-SWAP", "expected_consumer_trust_root", "DEPENDENCY_ADMISSION_TRUST_UNEXPECTED_AT_USE"),
        ):
            changed = dict(common); changed[field] = R[8]
            case(case_id, lambda changed=changed, code=code: refuses(lambda: evaluate_graph(**changed), code))
        missing = dict(common); missing.pop("expected_producer_root")
        case("REUSE-MISSING-EXPECTED-ANCHOR", lambda: refuses(lambda: evaluate_graph(**missing), "DEPENDENCY_REUSE_EXPECTED_ANCHORS_REQUIRED"))

        frozen_member = history / registry["directories"][0]["directory"] / registry["directories"][0]["members"][0]["path"]
        original = frozen_member.read_bytes(); frozen_member.write_bytes(original + b"\n")
        case("FROZEN-PROGRAM-MUTATION", lambda: refuses(lambda: verify_frozen_program_registry(source_root=history, registry=registry), "FROZEN_PROGRAM_CUSTODY_MISMATCH"))
        frozen_member.write_bytes(original)
        mutated_archive = work / "mutated-ugel.zip"; shutil.copyfile(archive_path, mutated_archive)
        with mutated_archive.open("ab") as handle: handle.write(b"x")
        case("UGEL-SOURCE-ARCHIVE-TAMPER", lambda: refuses(lambda: verifier.verify_archive(mutated_archive), "UGEL_SOURCE_ARCHIVE_SHA256_MISMATCH"))

        policy = build_component_policy(component_sha256=R[0], contract_root=R[1],
            allowed_effects=["sim.add"], resource_ids=["calculator:primary"],
            allowed_actions=["RUN"], max_text_bytes=3)
        case("UGEL-TEXT-LIMIT", lambda: refuses(lambda: build_guest_call(policy=policy,
            action="RUN", operation_id="op:r023:text", effect_id="sim.add",
            resource_id="calculator:primary", parameters={"left":1,"right":2,"text":"four"},
            evidence_roots=[]), "UGEL_CALL_TEXT_LIMIT"))
        call = build_guest_call(policy=policy, action="RUN", operation_id="op:r023:result",
            effect_id="sim.add", resource_id="calculator:primary", parameters={"left":20,"right":22},
            evidence_roots=[])
        result = evaluate_reference_sim_add(guest_call=call, policy=policy)
        case("UGEL-RESULT-ROOT-TAMPER", lambda: refuses(lambda: validate_reference_result({**result,"output":{"sum":99}}), "UGEL_REFERENCE_RESULT_ROOT_INVALID"))
        correspondence_body = {"schema":"mosaic.ucm.ugel-correspondence.v0.1",
                               "operational_contract_root":R[0], "expected_result_root":result["result_root"]}
        correspondence = {**correspondence_body,"correspondence_root":root(correspondence_body)}
        case("UGEL-CORRESPONDENCE-ROOT-TAMPER", lambda: refuses(lambda: validate_correspondence({**correspondence,"expected_result_root":R[8]}), "UGEL_CORRESPONDENCE_INVALID"))

        provenance = json.loads((kit / "R022-OPERATOR-PROVENANCE.json").read_text())
        pass_row = next(row for row in provenance["operator_runs"] if row["status"] == "PASS")
        case("CONTROL-R022-OPERATOR-PASS-CUSTODY", lambda: pass_row["sha256"] == sha((kit / "R022-UGEL-TIER1-PASS-EVIDENCE.zip").read_bytes()) and pass_row["court_root"] == "9fb8e3b500795d9bf26ca384145ef552e7c6e110846389e1b3db62a7358df1c6")
        case("CONTROL-AUTHORITY-CEILING", lambda: all(row["status"] == "PASS" for row in cases) and BOUNDARY["authority_effect"] == "NONE")

    body = {"schema":"mosaic.ucm.systemic-repair-tier1-result.v0.1","revision":"r023",
            "runtime_sha256":manifest["runtime_sha256"],
            "qualification_sha256":manifest["qualification_sha256"],
            "operator_kit_root":manifest["operator_kit_root"],"cases":cases,
            "case_count":len(cases),"failed":sum(row["status"]!="PASS" for row in cases),**BOUNDARY}
    body["status"] = "PASS" if body["failed"] == 0 else "HOLD_FOR_REPAIR"
    result_record = {**body,"court_root":sha(canonical(body))}
    path = seal_evidence(args.out_dir.resolve(), result_record)
    print(json.dumps({"status":result_record["status"],"cases":len(cases),
        "failed":result_record["failed"],"court_root":result_record["court_root"],
        "evidence":str(path),"evidence_sha256":sha(path.read_bytes()),**BOUNDARY},sort_keys=True))
    return 0 if result_record["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
