#!/usr/bin/env python3
"""Operator-executed Tier 1 court for the exact P/PPI r018 adaptive release."""
from __future__ import annotations

import argparse, hashlib, json, os, pathlib, subprocess, sys, tempfile, zipfile

FIXED=(1980,1,1,0,0,0)
BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def rooted(body,field):return {**body,field:sha(canonical(body))}

def verify_kit(root:pathlib.Path):
    manifest=json.loads((root/"KIT-MANIFEST.json").read_text(encoding="utf-8"))
    body={k:v for k,v in manifest.items() if k!="manifest_root"}
    if manifest.get("manifest_root")!=sha(canonical(body)):raise ValueError("KIT_MANIFEST_ROOT_INVALID")
    observed=[]
    for row in manifest["members"]:
        data=(root/row["path"]).read_bytes();observed.append({"path":row["path"],"sha256":sha(data),"bytes":len(data)})
    if observed!=manifest["members"]:raise ValueError("KIT_MEMBER_CUSTODY_INVALID")
    names=sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name!="KIT-MANIFEST.json")
    if names!=[row["path"] for row in manifest["members"]]:raise ValueError("KIT_CLOSED_SET_INVALID")
    return manifest

def write_evidence(out:pathlib.Path,result:dict):
    report=("# P/PPI r018 adaptive operator Tier 1\n\n"
            f"Status: **{result['status']}**  \nCases: {result['case_count']}  \n"
            f"Court root: `{result['court_root']}`\n").encode()
    payload={"TIER1-RESULT.json":canonical(result)+b"\n","REPORT.md":report,
             "RUN-TIER1.py":pathlib.Path(__file__).read_bytes()}
    rows=[{"path":n,"sha256":sha(d),"bytes":len(d)} for n,d in sorted(payload.items())]
    manifest_body={"schema":"mosaic.ucm.pippi-adaptive-tier1-evidence-manifest.v0.1",
        "members":rows,"member_count":len(rows),**BOUNDARY}
    payload["MANIFEST.json"]=canonical(rooted(manifest_body,"manifest_root"))+b"\n"
    out.mkdir(parents=True,exist_ok=True)
    path=out/f"PIPPI-r018-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,data)
    return path

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--kit-root",type=pathlib.Path,required=True)
    parser.add_argument("--out-dir",type=pathlib.Path,required=True);args=parser.parse_args()
    kit=args.kit_root.resolve();manifest=verify_kit(kit)
    runtime=kit/"UCM-v0.1-runtime.zip";cold=kit/"PIPPI-v0.1-adaptive-cold-boot.zip"
    cases=[]
    def case(case_id,fn):
        try: ok=bool(fn());detail="PASS" if ok else "PREDICATE_FALSE"
        except Exception as exc:ok=False;detail=type(exc).__name__+":"+sha(str(exc).encode())
        row={"case_id":case_id,"status":"PASS" if ok else "FAIL","detail":detail}
        cases.append(row);print(f"[case {len(cases):03d}] {case_id}: {row['status']}",flush=True)
    def refuses(fn,code):
        try:fn()
        except Exception as exc:return code in str(exc)
        return False
    with tempfile.TemporaryDirectory() as raw:
        temp=pathlib.Path(raw);runtime_root=temp/"runtime"
        with zipfile.ZipFile(runtime) as zf:zf.extractall(runtime_root)
        sys.path.insert(0,str(runtime_root/"src"))
        from uclop.canonical import root
        from ucm.pippi_adaptive import (build_project_capsule,build_turn_report,interface_conformance,
            mediation_library,negotiate_host_mode,pippi_shell_completion,prepare_turn,reconcile_turn,
            validate_turn_opening,validate_turn_report,verify_project_capsule)
        from ucm.pippi_global import build_project
        from ucm.pippi_packs import (PackStore, build_install_plan, default_pack_inventory,
            explain_project_portability, pack_registry, transition_pack_inventory,
            verify_bundled_optional_pack_manifests)
        from ucm.pippi_installer import probe_installer
        R=[str(i)*64 for i in range(1,6)]
        project=build_project(project_id="operator",title="Operator court",workspace=str(temp/"workspace"),
            github_url=None,application_command=["pippi","dashboard"],
            verification_command=["pippi","interface-doctor"],revision="r018")
        local=negotiate_host_mode(host_id="operator",requested_mode="EXECUTABLE_LOCAL",
            capability_ids=["ARTIFACT_EXCHANGE","FILESYSTEM_READ","PROCESS_EXECUTION"],adapter_root=None)
        web=negotiate_host_mode(host_id="web",requested_mode="ARTIFACT_MEDIATED_WEB",
            capability_ids=["ARTIFACT_EXCHANGE"],adapter_root=None)
        opening=prepare_turn(project=project,host_profile=local,sequence=1,previous_turn_root=None,
            scenario="OPERATOR_REVIEW",requested_rule_ids=["UGK_CLAIM_DISCIPLINE","VERSION_POLICY"],
            acceptance_case_roots=[R[0]],journal_head=R[1])
        report=build_turn_report(opening=opening,summary="Operator review record.",changed_paths=[],
            artifact_roots=[R[2]],evidence_roots=[R[3]],unresolved_items=[],
            next_action="Preserve evidence.",claim_class="EXECUTION_EVIDENCE")
        reconciliation=reconcile_turn(opening=opening,report=report,
            current_project_root=project["project_root"],current_journal_head=R[1])
        library=mediation_library()
        capsule=build_project_capsule(profile="WORK_CAPSULE",project=project,host_profile=local,
            ucm_root=R[0],ugk_root=R[1],mediation_library_root=library["mediation_library_root"],
            journal_head=R[2],turn_root=opening["turn_opening_root"],public_identity_roots=[R[3]],
            members=[{"path":"BOOT/START-HERE.md","sha256":R[4],"bytes":1,"role":"ORIENTATION"}])
        case("CONTROL-KIT-CUSTODY",lambda:manifest["runtime_sha256"]==sha(runtime.read_bytes()))
        case("CONTROL-MEDIATION-LIBRARY",lambda:len(library["rules"])>=12)
        case("CONTROL-LOCAL-HOST",lambda:local["status"]=="PASS")
        case("CONTROL-WEB-HOST",lambda:web["status"]=="PASS")
        case("CONTROL-TURN-OPENING",lambda:validate_turn_opening(opening)==opening)
        case("CONTROL-TURN-REPORT",lambda:validate_turn_report(report)==report)
        case("CONTROL-RECONCILIATION",lambda:reconciliation["state"]=="RECONCILED")
        case("CONTROL-CAPSULE",lambda:verify_project_capsule(capsule)["status"]=="PASS")
        case("CONTROL-INTERFACE",lambda:interface_conformance()["status"]=="PASS")
        case("CONTROL-COMPLETION",lambda:"turn-prepare" in pippi_shell_completion("powershell")["commands"])
        native_caps=["ARTIFACT_EXCHANGE","TOOL_INTERPOSITION","VISIBLE_OUTPUT_INTERPOSITION"]
        case("NATIVE-SELF-ATTESTATION-REFUSED",lambda:negotiate_host_mode(host_id="native",
            requested_mode="NATIVE_ENFORCED",capability_ids=native_caps,adapter_root=R[0])["status"]
            =="REFUSED_NATIVE_ENFORCEMENT_UNSUBSTANTIATED")
        bad=dict(opening);bad["project_root"]=R[4]
        case("OPENING-PROJECT-SWAP",lambda:refuses(lambda:validate_turn_opening(bad),"PIPPI_TURN_OPENING_INVALID"))
        case("OPENING-UNKNOWN-RULE",lambda:refuses(lambda:prepare_turn(project=project,host_profile=local,
            sequence=1,previous_turn_root=None,scenario="X",requested_rule_ids=["UNKNOWN"],
            acceptance_case_roots=[R[0]],journal_head=None),"PIPPI_CONTEXT_RULE_INVALID"))
        bad_report=dict(report);bad_report["opening_root"]=R[4]
        case("REPORT-OPENING-SWAP",lambda:refuses(lambda:validate_turn_report(bad_report),"PIPPI_TURN_REPORT_INVALID"))
        case("RECONCILE-STALE-JOURNAL",lambda:refuses(lambda:reconcile_turn(opening=opening,report=report,
            current_project_root=project["project_root"],current_journal_head=R[4]),"PIPPI_JOURNAL_CHANGED_DURING_TURN"))
        case("RECONCILE-PROJECT-SWAP",lambda:refuses(lambda:reconcile_turn(opening=opening,report=report,
            current_project_root=R[4],current_journal_head=R[1]),"PIPPI_PROJECT_CHANGED_DURING_TURN"))
        bad_capsule=dict(capsule);bad_capsule["private_material_present"]=True
        case("CAPSULE-PRIVATE-MATERIAL",lambda:refuses(lambda:verify_project_capsule(bad_capsule),"PIPPI_CAPSULE_INVALID"))
        bad_capsule2=dict(capsule);bad_capsule2["ugk_root"]=R[4]
        case("CAPSULE-UGK-SWAP",lambda:refuses(lambda:verify_project_capsule(bad_capsule2),"PIPPI_CAPSULE_INVALID"))
        verify_script=temp/"VERIFY.py"
        with zipfile.ZipFile(cold) as zf:verify_script.write_bytes(zf.read("VERIFY.py"))
        checked=subprocess.run([sys.executable,str(verify_script),str(cold)],capture_output=True,text=True)
        case("CONTROL-COLD-BOOT",lambda:checked.returncode==0 and json.loads(checked.stdout)["status"]=="PASS")
        tampered=temp/"tampered.zip";data=bytearray(cold.read_bytes());data[-7]^=1;tampered.write_bytes(data)
        rejected=subprocess.run([sys.executable,str(verify_script),str(tampered)],capture_output=True,text=True)
        case("COLD-BOOT-TAMPER",lambda:rejected.returncode!=0)
        inventory=default_pack_inventory()
        recommended=build_install_plan(profile="RECOMMENDED_LOCAL",inventory=inventory)
        temporal=build_install_plan(profile="TRANSTEMPORAL_PROJECT",inventory=inventory)
        case("CONTROL-PACK-REGISTRY",lambda:len(pack_registry()["packs"])==9)
        case("CONTROL-RECOMMENDED-PLAN",lambda:recommended["status"]=="READY" and not recommended["plan_performs_effects"])
        case("CONTROL-OPTIONAL-HOLDS",lambda:temporal["status"]=="HELD" and not temporal["plan_performs_effects"])
        case("PACK-REMOTE-EFFECT-HELD",lambda:build_install_plan(profile="TRANSTEMPORAL_PROJECT",
            inventory=inventory,allow_remote_downloads=True)["explicit_user_authorization_required"] is True)
        case("PACK-HEAD-MISMATCH",lambda:refuses(lambda:PackStore(temp/"pack-store").record(
            expected_inventory_root="0"*64,pack_id="SEMCRYS_CORE",state="INSTALLED_UNBOUND",
            installed_root="1"*64,binding_root=None,evidence_roots=["2"*64]),"PIPPI_PACK_INVENTORY_HEAD_MISMATCH"))
        case("PACK-EVIDENCE-REQUIRED",lambda:refuses(lambda:transition_pack_inventory(inventory=inventory,
            pack_id="SEMCRYS_CORE",state="INSTALLED_UNBOUND",installed_root="1"*64,
            binding_root=None,evidence_roots=[]),"PIPPI_PACK_VERIFICATION_EVIDENCE_REQUIRED"))
        case("PACK-PORTABILITY-PRESERVES-REQUIREMENTS",lambda:explain_project_portability(
            required_packs=["MEMORY_VAULT_ADAPTER"],inventory=inventory)["status"]=="NEEDS_PACKS")
        case("CONTROL-OPTIONAL-MANIFEST-PINS",lambda:verify_bundled_optional_pack_manifests(runtime_root)["status"]=="PASS")
        installer=probe_installer(temp/"installer")
        case("CONTROL-HEADLESS-INSTALLER",lambda:installer["status"]=="PASS" and installer["rainbow_sun"]=="VERIFIED_ASSET")
    court_body={"schema":"mosaic.ucm.pippi-adaptive-tier1-result.v0.1",
        "revision":"r018","runtime_sha256":sha(runtime.read_bytes()),"cold_boot_sha256":sha(cold.read_bytes()),
        "kit_manifest_root":manifest["manifest_root"],"cases":cases,"case_count":len(cases),
        "failed":sum(row["status"]!="PASS" for row in cases),**BOUNDARY}
    result=rooted(court_body,"court_root");result["status"]="PASS" if result["failed"]==0 else "HOLD_FOR_REPAIR"
    # Re-root after adding the terminal status.
    body={k:v for k,v in result.items() if k!="court_root"};result["court_root"]=sha(canonical(body))
    evidence=write_evidence(args.out_dir.resolve(),result)
    print(json.dumps({"status":result["status"],"cases":result["case_count"],"failed":result["failed"],
        "court_root":result["court_root"],"evidence":str(evidence),"evidence_sha256":sha(evidence.read_bytes()),**BOUNDARY},sort_keys=True))
    return 0 if result["status"]=="PASS" else 3

if __name__=="__main__":raise SystemExit(main())
