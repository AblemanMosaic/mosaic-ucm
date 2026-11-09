#!/usr/bin/env python3
"""Builder-authored, operator-runnable r028 constitutional-atlas court."""
from __future__ import annotations
import argparse, hashlib, json, sys, tempfile, zipfile
from copy import deepcopy
from pathlib import Path

FIXED=(1980,1,1,0,0,0)
BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()

def verify_kit(root):
    manifest=json.loads((root/"KIT-MANIFEST.json").read_text(encoding="utf-8"))
    from ucm.pippi_reviews import validate_operator_kit_contract
    validate_operator_kit_contract(manifest)
    for row in manifest["members"]:
        raw=(root/row["path"]).read_bytes()
        if sha(raw)!=row["sha256"] or len(raw)!=row["bytes"]:raise ValueError("KIT_MEMBER_CUSTODY_INVALID")
    names=sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name!="KIT-MANIFEST.json")
    if names!=[row["path"] for row in manifest["members"]]:raise ValueError("KIT_CLOSED_SET_INVALID")
    return manifest

def seal_evidence(out,result):
    report=("# UCM r028 constitutional-atlas operator Tier 1\n\n"
            f"Status: **{result['status']}**  \nCases: {result['case_count']}  \nCourt root: `{result['court_root']}`\n").encode()
    payload={"TIER1-RESULT.json":canonical(result)+b"\n","REPORT.md":report,"RUN-TIER1.py":Path(__file__).read_bytes()}
    rows=[{"path":n,"sha256":sha(r),"bytes":len(r)} for n,r in sorted(payload.items())]
    body={"schema":"mosaic.ucm.r028-tier1-evidence-manifest.v0.1","members":rows,"member_count":len(rows),**BOUNDARY}
    payload["MANIFEST.json"]=canonical({**body,"manifest_root":sha(canonical(body))})+b"\n"
    out.mkdir(parents=True,exist_ok=True);path=out/f"UCM-r028-CONSTITUTIONAL-ATLAS-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for name,raw in sorted(payload.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,raw)
    return path

def main():
    p=argparse.ArgumentParser();p.add_argument("--kit-root",type=Path,required=True);p.add_argument("--out-dir",type=Path,required=True);a=p.parse_args();kit=a.kit_root.resolve()
    with tempfile.TemporaryDirectory() as td:
        runtime=Path(td)/"runtime";cold=Path(td)/"cold"
        with zipfile.ZipFile(kit/"UCM-v0.1-runtime.zip") as zf:zf.extractall(runtime)
        with zipfile.ZipFile(kit/"PIPPI-v0.1-adaptive-cold-boot.zip") as zf:zf.extractall(cold)
        sys.path.insert(0,str(runtime/"src"));manifest=verify_kit(kit)
        from uclop.canonical import root
        from ucm.pippi_constitution import (build_constitutional_standards_atlas,build_pipeline_model,
            validate_constitutional_standards_atlas,validate_pipeline_model,explain_context_selection,
            build_ccp_transition_binding,build_credential_reference,credential_broker_policy,
            build_storage_locator,change_capsule_signing_body,build_signed_change_capsule,
            validate_signed_change_capsule)
        from ucm.pippi_adaptive import ADAPTIVE_CLI_ROUTES
        from ucm.system import capability_registry
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        cases=[]
        def case(cid,predicate):
            try:ok=bool(predicate());detail="PASS" if ok else "PREDICATE_FALSE"
            except Exception as exc:ok=False;detail=type(exc).__name__+":"+sha(str(exc).encode())
            cases.append({"case_id":cid,"status":"PASS" if ok else "FAIL","detail":detail});print(f"[case {len(cases):03d}] {cid}: {cases[-1]['status']}",flush=True)
        def refuses(call,code):
            try:call()
            except Exception as exc:return code in str(exc)
            return False
        qualification=json.loads((kit/"UCM-v0.1-QUALIFICATION.json").read_text())
        case("CONTROL-KIT-CUSTODY",lambda:manifest["runtime_sha256"]==sha((kit/"UCM-v0.1-runtime.zip").read_bytes()))
        case("CONTROL-QUALIFICATION",lambda:qualification["engineering_revision"]=="r028" and qualification["status"]=="PASS")
        atlas=build_constitutional_standards_atlas();model=build_pipeline_model()
        case("CONTROL-ATLAS",lambda:validate_constitutional_standards_atlas(atlas)==atlas and atlas["rule_count"]==14)
        case("CONTROL-PIPELINE",lambda:validate_pipeline_model(model)==model and model["transition_count"]==10)
        tampered=deepcopy(atlas);tampered["rules"]=tampered["rules"][:-1];tampered["atlas_root"]=root({k:v for k,v in tampered.items() if k!="atlas_root"})
        case("ATLAS-DENOMINATOR-SHRINK",lambda:refuses(lambda:validate_constitutional_standards_atlas(tampered),"PIPPI_STANDARDS_ATLAS_INVALID"))
        laundered=deepcopy(atlas);laundered["co_projections"][0]["identity_equivalence_claimed"]=True;laundered["atlas_root"]=root({k:v for k,v in laundered.items() if k!="atlas_root"})
        case("CO-PROJECTION-IDENTITY-LAUNDERING",lambda:refuses(lambda:validate_constitutional_standards_atlas(laundered),"PIPPI_STANDARDS_ATLAS_INVALID"))
        changed=deepcopy(model);changed["transitions"][4]["automatic_authority_grant"]=True;changed["pipeline_model_root"]=root({k:v for k,v in changed.items() if k!="pipeline_model_root"})
        case("PIPELINE-AUTHORITY-LAUNDERING",lambda:refuses(lambda:validate_pipeline_model(changed),"PIPPI_PIPELINE_MODEL_INVALID"))
        held=build_ccp_transition_binding(transition_id="PREPARE_DISPATCH",subject_root="1"*64,jurisdiction_profile_root="2"*64,evidence_snapshot_root="3"*64,current_use_decision_root="4"*64,current_use_status="DEFER")
        case("CCP-BYPASS-REFUSED",lambda:held["status"]=="HELD_BY_CURRENT_USE_ADMISSIBILITY" and not held["transition_ready"])
        explanation=explain_context_selection(scenario="CODING",requested_rule_ids=["VERSION_POLICY"],variables={"revision":"r028"})
        case("CONTROL-CONTEXT-REASON-PATHS",lambda:all(row["reason"] in {"SCENARIO_REQUIRED","EXPLICIT_REQUEST"} for row in explanation["reason_paths"]))
        case("CONTEXT-UNKNOWN-RULE",lambda:refuses(lambda:explain_context_selection(scenario="CODING",requested_rule_ids=["MISSING"],variables={}),"PIPPI_CONTEXT_RULE_INVALID"))
        policy=credential_broker_policy();ref=build_credential_reference(provider_id="GITHUB",account_identity="AblemanMosaic",scopes=["CONTENTS_WRITE"],secret_handle="pippi-credential://github/main",storage_policy_root=policy["credential_broker_policy_root"],expires_at_epoch=None)
        case("CONTROL-CREDENTIAL-REFERENCE",lambda:not ref["portable"] and not ref["secret_material_present"])
        case("CREDENTIAL-IN-LOCATOR-REFUSED",lambda:refuses(lambda:build_storage_locator(provider_id="MEGA",locator="mega://x?token=secret",artifact_sha256="1"*64,provider_account_root="2"*64,credential_reference_root=ref["credential_reference_root"]),"PIPPI_STORAGE_LOCATOR_CONTAINS_CREDENTIAL"))
        private=Ed25519PrivateKey.from_private_bytes(bytes(range(32)));public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
        fields=dict(base_root="1"*64,result_root="2"*64,changed_objects=[{"path":"src/x.py","before_sha256":"3"*64,"after_sha256":"4"*64,"semantic_role":"IMPLEMENTATION"}],acceptance_case_roots=["5"*64],standard_roots=["6"*64],policy_pack_roots=["7"*64],author_identity_root="8"*64,author_public_key_hex=public,dkn_namespace="mosaic.ucm.collaborator",dkn_epoch=1,revision="r028")
        signing=change_capsule_signing_body(**fields);capsule=build_signed_change_capsule(signature_hex=private.sign(canonical(signing)).hex(),**fields)
        case("CONTROL-SIGNED-CHANGE",lambda:validate_signed_change_capsule(capsule)==capsule)
        bad=deepcopy(capsule);bad["signing_body"]["result_root"]="9"*64
        case("CHANGE-SIGNATURE-SWAP",lambda:refuses(lambda:validate_signed_change_capsule(bad),"PIPPI_CHANGE_SIGNATURE_INVALID"))
        wrong=dict(fields);wrong["stable_nonce"]="governance"
        case("DKN-NONCE-SWAP",lambda:refuses(lambda:change_capsule_signing_body(**wrong),"PIPPI_CHANGE_STABLE_NONCE_INVALID"))
        registry={row["name"]:row["route"] for row in capability_registry()["surfaces"]}
        case("CONTROL-CLI-ABI-PARITY",lambda:all(registry[name]==f"pippi {command}" for name,command in ADAPTIVE_CLI_ROUTES.items()))
        case("CONTROL-COLD-BOOT-ATLAS",lambda:(cold/"PIPPI/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json").read_bytes()==(runtime/"spec/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json").read_bytes())
        case("CONTROL-COLD-BOOT-PIPELINE",lambda:(cold/"PIPPI/PIPPI-PIPELINE-MODEL.json").read_bytes()==(runtime/"spec/PIPPI-PIPELINE-MODEL.json").read_bytes())
        case("CONTROL-AUTHORITY-CEILING",lambda:all(row["status"]=="PASS" for row in cases) and BOUNDARY["authority_effect"]=="NONE")
    body={"schema":"mosaic.ucm.r028-tier1-result.v0.1","revision":"r028","runtime_sha256":manifest["runtime_sha256"],"qualification_sha256":manifest["qualification_sha256"],"cases":cases,"case_count":len(cases),"failed":sum(row["status"]!="PASS" for row in cases),**BOUNDARY};body["status"]="PASS" if body["failed"]==0 else "HOLD_FOR_REPAIR";result={**body,"court_root":sha(canonical(body))};evidence=seal_evidence(a.out_dir.resolve(),result)
    print(json.dumps({"status":result["status"],"cases":len(cases),"failed":result["failed"],"court_root":result["court_root"],"evidence":str(evidence),"evidence_sha256":sha(evidence.read_bytes()),**BOUNDARY},sort_keys=True));return 0 if result["status"]=="PASS" else 3
if __name__=="__main__":raise SystemExit(main())
