#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
def sha(v): return hashlib.sha256(v).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--qualification-source",type=Path,required=True); ap.add_argument("--operator-evidence",type=Path,required=True); ap.add_argument("--predecessor-handoff",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); a=ap.parse_args()
    source=a.qualification_source.read_bytes(); evidence=a.operator_evidence.read_bytes(); pred=a.predecessor_handoff.read_bytes(); contract=(ROOT/"spec/STAGE-I4-C3-CONTRACT.json").read_bytes()
    ledger=(ROOT/"review/STAGE-I4-C3-REPAIR-LEDGER.json").read_bytes(); completion=(ROOT/"review/STAGE-I4-C3-COMPLETION-AUDIT.json").read_bytes(); work_order=(ROOT/"review/STAGE-I4-C3-INDEPENDENT-REVIEW-WORK-ORDER.md").read_bytes(); native_source=(ROOT/"vendor/aok-headless-runner/NATIVE-RUNNER-BINDING-SOURCE.json").read_bytes()
    r5_dir=ROOT/"predecessors/stage-i4-c2-r5-passive-review"; r5_payload={}; r5_rows=[]
    for path in sorted(r5_dir.iterdir(),key=lambda item:item.name):
        if not path.is_file(): raise SystemExit("STAGE_I4_C3_R5_REVIEW_SET_INVALID")
        raw=path.read_bytes(); name=f"review/r5-passive/{path.name}"; r5_payload[name]=raw
        r5_rows.append({"path":name,"bytes":len(raw),"sha256":sha(raw)})
    if len(r5_rows)!=9: raise SystemExit("STAGE_I4_C3_R5_REVIEW_SET_INVALID")
    body={"schema":"mosaic.ucm.amcas-stage-i4-c3-review-boundary.v0.1","qualification_source_sha256":sha(source),"operator_evidence_sha256":sha(evidence),"predecessor_handoff_sha256":sha(pred),"r5_passive_review_files":r5_rows,"r5_passive_review_root":root(r5_rows),"semantic_contract_sha256":sha(contract),"repair_ledger_sha256":sha(ledger),"completion_audit_sha256":sha(completion),"work_order_sha256":sha(work_order),"native_runner_binding_source_sha256":sha(native_source),**BOUNDARY}; boundary={**body,"boundary_root":root(body)}
    payload={"REVIEW-BOUNDARY.json":canonical_bytes(boundary),"qualification/QUALIFICATION-SOURCE.zip":source,"qualification/OPERATOR-EVIDENCE.zip":evidence,"review/REPAIR-LEDGER.json":ledger,"review/COMPLETION-AUDIT.json":completion,"review/WORK-ORDER.md":work_order,"spec/STAGE-I4-C3-CONTRACT.json":contract,"vendor/NATIVE-RUNNER-BINDING-SOURCE.json":native_source,"VERIFY.py":(ROOT/"review/stage4-c3/VERIFY.py").read_bytes(),**r5_payload}
    raw=deterministic_zip(payload,schema="mosaic.ucm.amcas-stage-i4-c3-review-handoff.v0.1",artifact_role="INDEPENDENT_REVIEW_HANDOFF"); verify_deterministic_zip(raw,expected_schema="mosaic.ucm.amcas-stage-i4-c3-review-handoff.v0.1",expected_role="INDEPENDENT_REVIEW_HANDOFF")
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_bytes(raw)
    verified=subprocess.run([sys.executable,str(ROOT/"review/stage4-c3/VERIFY.py"),str(a.out),"--expected-sha256",sha(raw),"--predecessor",str(a.predecessor_handoff)],capture_output=True,text=True)
    if verified.returncode: raise SystemExit("STAGE_I4_C3_EXTERNAL_VERIFY_FAILED:"+verified.stderr)
    print(json.dumps({"status":"PASS","handoff_sha256":sha(raw),"boundary_root":boundary["boundary_root"],"external_verifier":json.loads(verified.stdout),**BOUNDARY},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
