#!/usr/bin/env python3
"""Builder-authored, operator-runnable r029 collaboration-integrity court."""
from __future__ import annotations
import argparse, hashlib, inspect, json, sys, tempfile, zipfile
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
    report=("# UCM r029 collaboration-integrity operator Tier 1\n\n"
            f"Status: **{result['status']}**  \nCases: {result['case_count']}  \nCourt root: `{result['court_root']}`\n").encode()
    payload={"TIER1-RESULT.json":canonical(result)+b"\n","REPORT.md":report,"RUN-TIER1.py":Path(__file__).read_bytes()}
    rows=[{"path":n,"sha256":sha(r),"bytes":len(r)} for n,r in sorted(payload.items())]
    body={"schema":"mosaic.ucm.r029-tier1-evidence-manifest.v0.1","members":rows,"member_count":len(rows),**BOUNDARY}
    payload["MANIFEST.json"]=canonical({**body,"manifest_root":sha(canonical(body))})+b"\n"
    out.mkdir(parents=True,exist_ok=True);path=out/f"UCM-r029-COLLABORATION-INTEGRITY-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for name,raw in sorted(payload.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,raw)
    return path

def main():
    p=argparse.ArgumentParser();p.add_argument("--kit-root",type=Path,required=True);p.add_argument("--out-dir",type=Path,required=True);a=p.parse_args();kit=a.kit_root.resolve()
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td);runtime=temp/"runtime";cold=temp/"cold"
        with zipfile.ZipFile(kit/"UCM-v0.1-runtime.zip") as zf:zf.extractall(runtime)
        with zipfile.ZipFile(kit/"PIPPI-v0.1-adaptive-cold-boot.zip") as zf:zf.extractall(cold)
        sys.path.insert(0,str(runtime/"src"));manifest=verify_kit(kit)
        from uclop.canonical import canonical_bytes
        from ucm.identity import mosaic_id
        from ucm.pippi_constitution import (build_ccp_transition_binding,build_pipeline_model,
            build_signed_change_capsule,build_signed_publication_receipt,build_signed_retrieval_receipt,
            build_storage_locator,change_capsule_signing_body,publication_receipt_signing_body,
            retrieval_receipt_signing_body,validate_signed_change_capsule,validate_signed_publication_receipt)
        from ucm.pippi_credentials import seal_local_credential,write_local_credential
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
        case("CONTROL-QUALIFICATION",lambda:qualification["engineering_revision"]=="r029" and qualification["status"]=="PASS")
        private=Ed25519PrivateKey.from_private_bytes(bytes(range(32)));public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex();identity=mosaic_id(public)
        change=dict(base_root="1"*64,result_root="2"*64,changed_objects=[{"path":"src/x.py","before_sha256":"3"*64,"after_sha256":"4"*64,"semantic_role":"IMPLEMENTATION"}],acceptance_case_roots=["5"*64],standard_roots=["6"*64],policy_pack_roots=["7"*64],author_identity_root=identity,author_public_key_hex=public,dkn_namespace="mosaic.ucm.collaborator",dkn_epoch=1,revision="r029")
        signing=change_capsule_signing_body(**change);capsule=build_signed_change_capsule(signature_hex=private.sign(canonical_bytes(signing)).hex(),**change)
        case("CONTROL-KEY-BOUND-CHANGE",lambda:validate_signed_change_capsule(capsule)==capsule)
        wrong=deepcopy(change);wrong["author_identity_root"]="8"*64
        case("CHANGE-IDENTITY-KEY-SWAP",lambda:refuses(lambda:change_capsule_signing_body(**wrong),"PIPPI_CHANGE_AUTHOR_IDENTITY_KEY_MISMATCH"))
        artifact=temp/"artifact.bin";artifact.write_bytes(b"exact-r029-artifact");artifact_sha=sha(artifact.read_bytes())
        locator=build_storage_locator(provider_id="MEGA",locator="mega://folder/object",artifact_sha256=artifact_sha,provider_account_root="9"*64,credential_reference_root="a"*64)
        publication=dict(artifact_sha256=artifact_sha,state_root="b"*64,semantic_root="c"*64,metadata_root="d"*64,governance_root="e"*64,dkn_binding_root="f"*64,storage_locator=locator,publisher_identity_root=identity,publisher_public_key_hex=public,published_epoch=3)
        pub_signing=publication_receipt_signing_body(**publication);pub=build_signed_publication_receipt(signature_hex=private.sign(canonical_bytes(pub_signing)).hex(),**publication)
        case("CONTROL-KEY-BOUND-PUBLICATION",lambda:validate_signed_publication_receipt(pub)==pub)
        bad_pub=deepcopy(publication);bad_pub["publisher_identity_root"]="0"*64
        case("PUBLICATION-IDENTITY-KEY-SWAP",lambda:refuses(lambda:publication_receipt_signing_body(**bad_pub),"PIPPI_PUBLICATION_IDENTITY_KEY_MISMATCH"))
        retrieval=dict(publication_receipt=pub,retrieved_artifact_path=str(artifact),retriever_identity_root=identity,retriever_public_key_hex=public,retrieved_epoch=4)
        ret_signing=retrieval_receipt_signing_body(**retrieval);receipt=build_signed_retrieval_receipt(signature_hex=private.sign(canonical_bytes(ret_signing)).hex(),**retrieval)
        case("CONTROL-ACTUAL-BYTES-RETRIEVAL",lambda:receipt["signing_body"]["artifact_sha256"]==artifact_sha)
        artifact.write_bytes(b"mutated")
        case("RETRIEVAL-BYTE-MUTATION",lambda:refuses(lambda:retrieval_receipt_signing_body(**retrieval),"PIPPI_RETRIEVAL_ARTIFACT_HASH_MISMATCH"))
        evaluation=json.loads((kit/"CCP-CONTROL-EVALUATION.json").read_text())
        admitted=build_ccp_transition_binding(transition_id="PROPOSE_PUBLICATION",ccp_evaluation=evaluation)
        case("CONTROL-VALIDATED-CCP-EVALUATION",lambda:admitted["transition_ready"] and admitted["current_use_status"]=="ADMIT")
        forged=deepcopy(evaluation);forged["decision"]["decision"]="REFUSE"
        case("CCP-RESEALED-DECISION-LAUNDERING",lambda:refuses(lambda:build_ccp_transition_binding(transition_id="PROPOSE_PUBLICATION",ccp_evaluation=forged),"CCP_ADMISSIBILITY_DECISION_INVALID"))
        case("CCP-CALLER-LABEL-REMOVED",lambda:"current_use_status" not in inspect.signature(build_ccp_transition_binding).parameters)
        model=build_pipeline_model()
        case("PIPELINE-TERMINAL-STATE-EXACT",lambda:model["terminal_states"]==["PUBLISHED"] and any(row["from_state"]=="SEALED" for row in model["transitions"]))
        skill_root=runtime/"skill/ucm-pippi-mediated-agent";expected={f"SKILLS/ucm-pippi-mediated-agent/{p.relative_to(skill_root).as_posix()}" for p in skill_root.rglob("*") if p.is_file()};cold_names={p.relative_to(cold).as_posix() for p in cold.rglob("*") if p.is_file()}
        case("COLD-BOOT-SKILL-CLOSURE",lambda:expected and expected<=cold_names)
        case("CREDENTIAL-CALLER-RANDOMNESS-REMOVED",lambda:not {"salt","nonce"}.intersection(inspect.signature(seal_local_credential).parameters))
        target=temp/"credential.json";pending=target.with_name(target.name+".fixed.pending");pending.write_bytes(b"preexisting")
        import unittest.mock
        def pending_refusal():
            with unittest.mock.patch("ucm.pippi_credentials.secrets.token_hex",return_value="fixed"):
                try:write_local_credential(target,{"x":1})
                except FileExistsError:return pending.read_bytes()==b"preexisting"
            return False
        case("CREDENTIAL-EXCLUSIVE-PENDING",pending_refusal)
        registry={row["name"]:row["route"] for row in capability_registry()["surfaces"]}
        case("PUBLICATION-VERIFY-CLI-ABI",lambda:registry["VERIFY_SIGNED_STORAGE_PUBLICATION_RECEIPT"]=="pippi publication-receipt-verify" and all(registry[n]==f"pippi {c}" for n,c in ADAPTIVE_CLI_ROUTES.items()))
        case("CONTROL-AUTHORITY-CEILING",lambda:all(row["status"]=="PASS" for row in cases) and BOUNDARY["authority_effect"]=="NONE")
    body={"schema":"mosaic.ucm.r029-tier1-result.v0.1","revision":"r029","runtime_sha256":manifest["runtime_sha256"],"qualification_sha256":manifest["qualification_sha256"],"cases":cases,"case_count":len(cases),"failed":sum(row["status"]!="PASS" for row in cases),**BOUNDARY};body["status"]="PASS" if body["failed"]==0 else "HOLD_FOR_REPAIR";result={**body,"court_root":sha(canonical(body))};evidence=seal_evidence(a.out_dir.resolve(),result)
    print(json.dumps({"status":result["status"],"cases":len(cases),"failed":result["failed"],"court_root":result["court_root"],"evidence":str(evidence),"evidence_sha256":sha(evidence.read_bytes()),**BOUNDARY},sort_keys=True));return 0 if result["status"]=="PASS" else 3
if __name__=="__main__":raise SystemExit(main())
