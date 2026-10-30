#!/usr/bin/env python3
"""Seal the complete c4 operator folder as one portable archive."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
SCHEMA="mosaic.ucm.amcas-stage-i4-c4-operator-delivery.v0.1"; ROLE="UCM_AMCAS_STAGE_I4_C4_OPERATOR_DELIVERY"
def main():
    p=argparse.ArgumentParser(); p.add_argument("--directory",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    if not a.directory.is_dir() or a.out.exists(): raise SystemExit("C4_OPERATOR_DELIVERY_BOUNDARY_INVALID")
    payloads={path.relative_to(a.directory).as_posix():path.read_bytes() for path in sorted(a.directory.rglob("*")) if path.is_file()}
    required={"BOOTSTRAP-STAGE-I4-C4.py","EXACT-ARTIFACT-BOUNDARY.json","RUN-STAGE-I4-C4-TIER1.cmd","START-HERE.md","UCL-UCM-AMCAS-STAGE-I4-C4-OPERATOR-KIT.zip"}
    if set(payloads)!=required: raise SystemExit("C4_OPERATOR_DELIVERY_FILE_SET_INVALID")
    raw=deterministic_zip(payloads,schema=SCHEMA,artifact_role=ROLE); manifest=verify_deterministic_zip(raw,expected_schema=SCHEMA,expected_role=ROLE)
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_bytes(raw)
    print(json.dumps({"status":"PASS","path":str(a.out),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"members":len(manifest["files"]),"manifest_root":manifest["manifest_root"],"execution":"NOT_PERFORMED_BY_BUILDER",**BOUNDARY},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
