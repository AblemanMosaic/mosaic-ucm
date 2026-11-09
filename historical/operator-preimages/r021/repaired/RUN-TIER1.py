#!/usr/bin/env python3
"""Builder-authored, operator-runnable r021 dependency Tier 1 court."""
from __future__ import annotations

import argparse, hashlib, json, pathlib, sys, tempfile, zipfile

FIXED=(1980,1,1,0,0,0)
BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()

def verify_kit(root):
    m=json.loads((root/"KIT-MANIFEST.json").read_text(encoding="utf-8"));body={k:v for k,v in m.items() if k!="operator_kit_root"}
    if m.get("operator_kit_root")!=sha(canonical(body)):raise ValueError("KIT_MANIFEST_ROOT_INVALID")
    observed=[]
    for row in m["members"]:
        data=(root/row["path"]).read_bytes();observed.append({"path":row["path"],"sha256":sha(data),"bytes":len(data),"role":row["role"]})
    if observed!=m["members"]:raise ValueError("KIT_MEMBER_CUSTODY_INVALID")
    names=sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name!="KIT-MANIFEST.json")
    if names!=[row["path"] for row in m["members"]]:raise ValueError("KIT_CLOSED_SET_INVALID")
    return m

def evidence(out,result):
    report=(f"# UCM dependency r021 operator Tier 1\n\nStatus: **{result['status']}**  \nCases: {len(result['cases'])}  \nCourt root: `{result['court_root']}`\n").encode()
    payload={"TIER1-RESULT.json":canonical(result)+b"\n","REPORT.md":report,"RUN-TIER1.py":pathlib.Path(__file__).read_bytes()}
    rows=[{"path":n,"sha256":sha(d),"bytes":len(d)} for n,d in sorted(payload.items())]
    body={"schema":"mosaic.ucm.dependency-tier1-evidence-manifest.v0.1","members":rows,"member_count":len(rows),**BOUNDARY}
    payload["MANIFEST.json"]=canonical({**body,"manifest_root":sha(canonical(body))})+b"\n";out.mkdir(parents=True,exist_ok=True)
    path=out/f"UCM-DEPENDENCY-r021-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,data)
    return path

def fault_evidence(out,exc):
    body={"schema":"mosaic.ucm.dependency-tier1-fault.v0.1","revision":"r021","status":"HOLD_FOR_REPAIR","diagnostic":type(exc).__name__,"detail_sha256":sha(str(exc).encode()),"adversarial_cases_executed":0,**BOUNDARY}
    result={**body,"fault_root":sha(canonical(body))};report=(f"# UCM dependency r021 operator fault\n\nStatus: **HOLD_FOR_REPAIR**  \nDiagnostic: `{result['diagnostic']}`  \nFault root: `{result['fault_root']}`\n").encode()
    payload={"FAULT-RESULT.json":canonical(result)+b"\n","REPORT.md":report,"RUN-TIER1.py":pathlib.Path(__file__).read_bytes()};rows=[{"path":n,"sha256":sha(d),"bytes":len(d)} for n,d in sorted(payload.items())]
    manifest_body={"schema":"mosaic.ucm.dependency-tier1-fault-evidence-manifest.v0.1","members":rows,"member_count":len(rows),**BOUNDARY};payload["MANIFEST.json"]=canonical({**manifest_body,"manifest_root":sha(canonical(manifest_body))})+b"\n";out.mkdir(parents=True,exist_ok=True)
    path=out/f"UCM-DEPENDENCY-r021-TIER1-FAULT-{result['fault_root'][:16]}.zip"
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,data)
    return path,result

def main():
    p=argparse.ArgumentParser();p.add_argument("--kit-root",type=pathlib.Path,required=True);p.add_argument("--out-dir",type=pathlib.Path,required=True);p.add_argument("--custody-only",action="store_true");a=p.parse_args()
    kit=a.kit_root.resolve();manifest=verify_kit(kit)
    if a.custody_only:
        print(json.dumps({"status":"PASS","operator_kit_root":manifest["operator_kit_root"],"member_count":manifest["member_count"],"adversarial_cases_executed":0,**BOUNDARY},sort_keys=True));return 0
    cases=[]
    def case(cid,fn):
        try:ok=bool(fn());detail="PASS" if ok else "PREDICATE_FALSE"
        except Exception as exc:ok=False;detail=type(exc).__name__+":"+sha(str(exc).encode())
        cases.append({"case_id":cid,"status":"PASS" if ok else "FAIL","detail":detail});print(f"[case {len(cases):03d}] {cid}: {cases[-1]['status']}",flush=True)
    def refuses(fn,code):
        try:fn()
        except Exception as exc:return code in str(exc)
        return False
    with tempfile.TemporaryDirectory() as raw:
        temp=pathlib.Path(raw);runtime_root=temp/"runtime"
        with zipfile.ZipFile(kit/"UCM-v0.1-runtime.zip") as zf:zf.extractall(runtime_root)
        sys.path.insert(0,str(runtime_root/"src"))
        from uclop.canonical import root
        from ucm.dependency_graph import (apply_snapshot_delta,build_graph,build_portable_closure,
            build_producer_receipt,build_reuse_admission,build_snapshot,evaluate_graph,verify_graph,
            verify_portable_closure,verify_snapshot)
        from ucm.dependency_adapters import (build_c_dependency_envelope,build_storage_admission_indexes,
            capture_observation,prepare_courthouse_dependency_binding,project_effect_history)
        R=[root({"operator":i}) for i in range(12)]
        def node(n,kind="INPUT",deps=(),params=None,closure="COMPLETE"):
            return {"node_id":n,"kind":kind,"dependencies":[{"node_id":x,"edge_kind":k,"required":q} for x,k,q in deps],"parameters":params or {},"transform_id":kind,"transform_version":"v0.1","semantic_contract_root":R[0],"policy_root":R[1],"jurisdiction_root":R[2],"environment_root":R[3],"closure_coverage":closure,"evidence_grade":"DECLARED_INPUT" if kind=="INPUT" else "DETERMINISTIC_DERIVATION","pure":True}
        graph=build_graph(graph_id="operator",nodes=[node("input"),node("project","PROJECT",[("input","EXACT_BYTES",True)],{"field_path":["x"]})],adapter_id="TEST",adapter_version="v0.1",adapter_policy_root=R[4],schema_registry_root=R[5],trust_root=R[6],closure_claim="COMPLETE")
        snapshot=build_snapshot(graph=graph,snapshot_id="s",predecessor_snapshot_root=None,inputs=[{"node_id":"input","presence":{"present":True,"value":{"x":1}}}]);evaluation=evaluate_graph(graph=graph,snapshot=snapshot)
        case("CONTROL-KIT-CUSTODY",lambda:manifest["runtime_sha256"]==sha((kit/"UCM-v0.1-runtime.zip").read_bytes()))
        case("CONTROL-GRAPH",lambda:verify_graph(graph)["status"]=="PASS")
        case("CONTROL-SNAPSHOT",lambda:verify_snapshot(snapshot,graph)["status"]=="PASS")
        case("CONTROL-EVALUATION",lambda:evaluation["partitions"]["evaluated"]==["input","project"])
        bad=dict(graph);bad["graph_root"]=R[8];case("GRAPH-ROOT-SWAP",lambda:refuses(lambda:verify_graph(bad),"DEPENDENCY_GRAPH_ROOT_MISMATCH"))
        bad=dict(snapshot);bad["snapshot_root"]=R[8];case("SNAPSHOT-ROOT-SWAP",lambda:refuses(lambda:verify_snapshot(bad,graph),"DEPENDENCY_SNAPSHOT_ROOT_MISMATCH"))
        case("DELTA-STALE-HEAD",lambda:refuses(lambda:apply_snapshot_delta(graph=graph,predecessor=snapshot,expected_predecessor_root=R[8],delta_id="x",updates=[],snapshot_id="x"),"DEPENDENCY_PREDECESSOR_ROOT_MISMATCH"))
        receipt=build_producer_receipt(producer_root=R[7],graph=graph,snapshot=snapshot,evaluation=evaluation,execution_capsule_root=R[8],checker_root=R[9])
        case("REUSE-SELF-ROOT-REFUSED",lambda:refuses(lambda:build_reuse_admission(graph=graph,snapshot=snapshot,prior_graph=graph,prior_snapshot=snapshot,prior_evaluation=evaluation,expected_prior_evaluation_root=R[10],expected_producer_root=R[7],producer_receipt=receipt,consumer_trust_root=R[6],admitted_evidence_grades=["DETERMINISTIC_DERIVATION"],reuse_mode="VERIFIED_PURE_REUSE"),"DEPENDENCY_PRIOR_EVALUATION_UNEXPECTED"))
        declared=build_graph(graph_id="declared",nodes=[node("input")],adapter_id="TEST",adapter_version="v0.1",adapter_policy_root=R[4],schema_registry_root=R[5],trust_root=R[6],closure_claim="DECLARED");ds=build_snapshot(graph=declared,snapshot_id="d",predecessor_snapshot_root=None,inputs=[{"node_id":"input","presence":{"present":True,"value":1}}]);de=evaluate_graph(graph=declared,snapshot=ds)
        dr=build_producer_receipt(producer_root=R[7],graph=declared,snapshot=ds,evaluation=de,execution_capsule_root=R[8],checker_root=R[9]);da=build_reuse_admission(graph=declared,snapshot=ds,prior_graph=declared,prior_snapshot=ds,prior_evaluation=de,expected_prior_evaluation_root=de["evaluation_root"],expected_producer_root=R[7],producer_receipt=dr,consumer_trust_root=R[6],admitted_evidence_grades=["DECLARED_INPUT"],reuse_mode="VERIFIED_PURE_REUSE");dre=evaluate_graph(graph=declared,snapshot=ds,prior_evaluation=de,reuse_admission=da,mode="VERIFIED_PURE_REUSE")
        case("DECLARED-CLOSURE-NO-REUSE",lambda:not dre["partitions"]["reused"])
        missing=build_storage_admission_indexes(admission_root=R[0],invocation_root=R[1],result_root=R[2],content_root=R[3],bytes_available=False,retention_root=R[4]);case("MISSING-BYTES-NOT-REUSED",lambda:not missing["reusable"])
        incomplete=build_c_dependency_envelope(source_root=R[0],header_roots=[R[1]],generated_input_roots=[],compiler_root=R[2],flags_root=R[3],toolchain_root=R[4],environment_root=R[5],depfile_root=None,external_evidence_roots=[]);case("C-NO-DEPFILE-INCOMPLETE",lambda:not incomplete["reuse_eligible"])
        obs=capture_observation(request_root=R[0],result_root=R[1],observer_root=R[2],model_or_tool_root=R[3],mode="RECORDED_RETRIEVAL",observable_metadata={});case("RETRIEVAL-NOT-FRESH",lambda:not obs["fresh_execution"] and not obs["hidden_reasoning_observed"])
        uncertain=project_effect_history(operation_state={"state":"UNCERTAIN","state_root":R[0]},dependency_evaluation_root=evaluation["evaluation_root"]);case("UNCERTAIN-NEVER-RETRY",lambda:uncertain["reconciliation_required"] and not uncertain["automatic_retry_selected"])
        blocked_graph=build_graph(graph_id="blocked",nodes=[node("input")],adapter_id="TEST",adapter_version="v0.1",adapter_policy_root=R[4],schema_registry_root=R[5],trust_root=R[6],closure_claim="COMPLETE");blocked_snapshot=build_snapshot(graph=blocked_graph,snapshot_id="b",predecessor_snapshot_root=None,inputs=[{"node_id":"input","presence":{"present":False}}]);blocked_eval=evaluate_graph(graph=blocked_graph,snapshot=blocked_snapshot);binding=prepare_courthouse_dependency_binding(evaluation=blocked_eval,required_target_ids=["input"],workflow_request_root=R[0],acceptance_case_root=R[1],work_unit_root=R[2],native_validator_root=R[3]);case("BLOCKED-NEVER-COMPILES",lambda:binding["status"]=="BLOCKED_PREREQUISITE" and not binding["workflow_compiled"] and not binding["permit_created"])
        closure=build_portable_closure(profile="REPLAY",graph=graph,snapshot=snapshot,evaluation=evaluation,software_root=R[0],adapter_root=R[1],schema_roots=[R[2]],evidence_roots=[R[3]],members=[]);case("CONTROL-PORTABLE-CLOSURE",lambda:verify_portable_closure(closure)["status"]=="PASS")
        bad=dict(closure);bad["credentials_included"]=True;case("PORTABLE-CREDENTIALS-REFUSED",lambda:refuses(lambda:verify_portable_closure(bad),"DEPENDENCY_PORTABLE_CREDENTIALS_FORBIDDEN"))
    body={"schema":"mosaic.ucm.dependency-tier1-result.v0.1","revision":"r021","runtime_sha256":manifest["runtime_sha256"],"qualification_sha256":manifest["qualification_sha256"],"kit_manifest_root":manifest["operator_kit_root"],"cases":cases,"case_count":len(cases),"failed":sum(row["status"]!="PASS" for row in cases),**BOUNDARY};body["status"]="PASS" if body["failed"]==0 else "HOLD_FOR_REPAIR";result={**body,"court_root":sha(canonical(body))};path=evidence(a.out_dir.resolve(),result)
    print(json.dumps({"status":result["status"],"cases":len(cases),"failed":result["failed"],"court_root":result["court_root"],"evidence":str(path),"evidence_sha256":sha(path.read_bytes()),**BOUNDARY},sort_keys=True));return 0 if result["status"]=="PASS" else 3

if __name__=="__main__":
    try:raise SystemExit(main())
    except SystemExit:raise
    except Exception as exc:
        try:
            index=sys.argv.index("--out-dir");path,result=fault_evidence(pathlib.Path(sys.argv[index+1]).resolve(),exc)
            print(json.dumps({"status":"HOLD_FOR_REPAIR","diagnostic":result["diagnostic"],"detail_sha256":result["detail_sha256"],"fault_root":result["fault_root"],"evidence":str(path),"evidence_sha256":sha(path.read_bytes()),**BOUNDARY},sort_keys=True))
        except Exception:pass
        raise SystemExit(3)
