#!/usr/bin/env python3
"""Freeze the c3 review candidate after operator Tier 1 and qualification pass."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def build(source,evidence,predecessor,out):
    p=subprocess.run([sys.executable,str(ROOT/"tools/build_stage4_c3_review_handoff.py"),"--qualification-source",str(source),"--operator-evidence",str(evidence),"--predecessor-handoff",str(predecessor),"--out",str(out)],capture_output=True,text=True)
    if p.returncode: raise SystemExit(p.stderr or p.stdout)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--qualification-source",type=Path,required=True); ap.add_argument("--operator-evidence",type=Path,required=True); ap.add_argument("--predecessor-handoff",type=Path,required=True); ap.add_argument("--out-dir",type=Path,required=True); a=ap.parse_args()
    if a.out_dir.exists(): raise SystemExit("STAGE_I4_C3_FREEZE_DESTINATION_EXISTS")
    with tempfile.TemporaryDirectory(prefix="UCM-I4-C3-FREEZE-") as f:
        first=Path(f)/"a.zip"; second=Path(f)/"b.zip"; build(a.qualification_source,a.operator_evidence,a.predecessor_handoff,first); build(a.qualification_source,a.operator_evidence,a.predecessor_handoff,second)
        if first.read_bytes()!=second.read_bytes(): raise SystemExit("STAGE_I4_C3_HANDOFF_NONDETERMINISTIC")
        a.out_dir.mkdir(parents=True); handoff=a.out_dir/"UCL-UCM-AMCAS-STAGE-I4-C3-INDEPENDENT-REVIEW-HANDOFF.zip"; shutil.copyfile(first,handoff)
    body={"schema":"mosaic.ucm.amcas-stage-i4-c3-freeze-receipt.v0.1","subject":"UCM-AMCAS Stage I4 c3 consolidated successor","review_handoff_sha256":sha(handoff),"qualification_source_sha256":sha(a.qualification_source),"operator_evidence_sha256":sha(a.operator_evidence),"predecessor_handoff_sha256":sha(a.predecessor_handoff),"deterministic_rebuild_equal":True,"application_contact_authorized":False,"shadow_execution_authorized":False,"composition_authorized":False,**BOUNDARY}; receipt={**body,"receipt_root":root(body)}; (a.out_dir/"STAGE-I4-C3-FREEZE-RECEIPT.json").write_bytes(canonical_bytes(receipt))
    boundary={"schema":"codex.exact-artifact-boundary.v1","runner_required_paths":[handoff.name,"STAGE-I4-C3-FREEZE-RECEIPT.json"],"external_exact_dependencies":[{"path":a.predecessor_handoff.name,"sha256":sha(a.predecessor_handoff)}],"review_handoff_sha256":sha(handoff),"receipt_root":receipt["receipt_root"],**BOUNDARY}; (a.out_dir/"EXACT-ARTIFACT-BOUNDARY.json").write_bytes(canonical_bytes(boundary)); (a.out_dir/"START-HERE.md").write_text("# Stage I4 c3 independent review\n\nUse the handoff with the externally supplied predecessor named in the exact boundary. Run VERIFY.py from inside the handoff, then follow the joint work order. No application contact or authority grant is permitted.\n",encoding="utf-8",newline="\n")
    print(json.dumps({"status":"PASS","review_handoff_sha256":sha(handoff),"receipt_root":receipt["receipt_root"],"directory":str(a.out_dir),**BOUNDARY},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
