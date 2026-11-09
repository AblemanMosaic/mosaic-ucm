#!/usr/bin/env python3
"""Builder-authored, operator-runnable r032 native-completion court."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

FIXED=(1980,1,1,0,0,0)
BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()

def rooted(value,field):
    return value.get(field)==sha(canonical({k:v for k,v in value.items() if k!=field}))

def verify_kit(root):
    manifest=json.loads((root/"KIT-MANIFEST.json").read_text(encoding="utf-8"))
    if not rooted(manifest,"operator_kit_root"): raise ValueError("KIT_ROOT_INVALID")
    expected={row["path"]:row for row in manifest["members"]}
    actual={path.relative_to(root).as_posix() for path in root.rglob("*")
            if path.is_file() and path.name!="KIT-MANIFEST.json"}
    if actual!=set(expected): raise ValueError("KIT_SET_INVALID")
    for name,row in expected.items():
        raw=(root/name).read_bytes()
        if len(raw)!=row["bytes"] or sha(raw)!=row["sha256"]:
            raise ValueError("KIT_MEMBER_INVALID:"+name)
    return manifest

def verify_runtime(path):
    with zipfile.ZipFile(path) as archive:
        manifest=json.loads(archive.read("MANIFEST.json"))
        if not rooted(manifest,"root"): raise ValueError("RUNTIME_ROOT_INVALID")
        rows={row["path"]:row for row in manifest["members"]}
        if set(archive.namelist())!={"MANIFEST.json",*rows}: raise ValueError("RUNTIME_SET_INVALID")
        for name,row in rows.items():
            raw=archive.read(name)
            if len(raw)!=row["bytes"] or sha(raw)!=row["sha256"]:
                raise ValueError("RUNTIME_MEMBER_INVALID:"+name)
    return manifest

def zip_evidence(path,members):
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in sorted(members.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;info.create_system=3;archive.writestr(info,raw)

def run_court(kit,out):
    manifest=verify_kit(kit);runtime_manifest=verify_runtime(kit/"UCM-v0.1-runtime.zip")
    cases=[]
    def case(case_id,action):
        try: action(); status="PASS"; diagnostic=None
        except Exception as error:
            status="FAIL"; diagnostic=type(error).__name__+":"+sha(str(error).encode())
        row={"case_id":case_id,"status":status,**BOUNDARY}
        if diagnostic: row["diagnostic"]=diagnostic
        cases.append(row);print(f"[case {len(cases):03d}] {case_id}: {status}",flush=True)

    # Scratch space is outside the extracted kit, so custody cannot be changed
    # merely by running the court.
    with tempfile.TemporaryDirectory(prefix="ucm-r032-native-court-") as raw:
        base=Path(raw);runtime=base/"runtime";runtime.mkdir()
        with zipfile.ZipFile(kit/"UCM-v0.1-runtime.zip") as archive: archive.extractall(runtime)
        sys.path.insert(0,str(runtime/"src"))
        from uclop.canonical import Refusal
        from ucm.native_core import (build_native_program,compile_native_core,
            detect_c17_compiler,execute_native_reference,lower_native_program,
            native_core_profile,verify_native_correspondence)

        corpus=[json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((runtime/"examples/native-core").glob("*.json"))]
        gate_program=next(row for row in corpus
                          if row["program_id"]=="ucm.gate.three_receipts")
        compiler=detect_c17_compiler()
        if not compiler["available"]: raise ValueError("NATIVE_C17_COMPILER_UNAVAILABLE")
        binary=base/("ucm-native.exe" if os.name=="nt" else "ucm-native")
        compile_native_core(source=runtime/"native/ucm_native_core.c",output=binary,compiler=compiler)
        correspondence=verify_native_correspondence(programs=corpus,binary=binary,work_dir=base/"corpus")

        def require(condition,code):
            if not condition: raise ValueError(code)

        case("CONTROL-KIT-CUSTODY",lambda:verify_kit(kit))
        case("CONTROL-QUALIFICATION",lambda:require(
            rooted(json.loads((kit/"UCM-v0.1-QUALIFICATION.json").read_text()),"root"),
            "QUALIFICATION_ROOT_INVALID"))
        case("CONTROL-R032-PROGRAM",lambda:require(
            rooted(json.loads((kit/"PROGRAM/PROGRAM.json").read_text()),"program_root"),
            "PROGRAM_ROOT_INVALID"))
        case("CONTROL-C-PREFLIGHT",lambda:require(
            json.loads((kit/"PROGRAM/C-PREFLIGHT.json").read_text())["decision"]=="READY_FOR_QUICK_CHECKS",
            "C_PREFLIGHT_NOT_READY"))
        case("CONTROL-R031-REPAIR-CUSTODY",lambda:require(
            sha((kit/"R031-USER-TIER1-PASS-EVIDENCE.zip").read_bytes())==
            "f24e8feaff3dd5916382e1e710637712b3261add48bd83ed8a7a00d9d9374099",
            "R031_EVIDENCE_PIN_MISMATCH"))
        def witness_control():
            rows=[json.loads((kit/name).read_text()) for name in
                  ("WINDOWS-NATIVE-CORE-WITNESS.json","WSL-NATIVE-CORE-WITNESS.json")]
            require(all(rooted(row,"witness_root") for row in rows),"WITNESS_ROOT_INVALID")
            require(rows[0]["result_set_root"]==rows[1]["result_set_root"],"WITNESS_DIVERGENCE")
        case("CONTROL-PLATFORM-WITNESSES",witness_control)
        case("CONTROL-NATIVE-CORRESPONDENCE",lambda:require(
            correspondence["all_correspond"] and correspondence["program_count"]==5,
            "NATIVE_CORRESPONDENCE_FAILED"))
        def mutation(old,new,code):
            projection=lower_native_program(gate_program).replace(old,new,1)
            require(projection!=lower_native_program(gate_program),code+"_FIXTURE_INVALID")
            path=base/(code+".ucln");path.write_bytes(projection)
            completed=subprocess.run([str(binary),str(path)],capture_output=True,text=True)
            require(completed.returncode!=0,code+"_ACCEPTED")
        case("PROJECTION-CODE-MUTATION",lambda:mutation(b"AND\n",b"OR\n","CODE_MUTATION"))
        case("PROJECTION-DENOMINATOR-SHRINK",lambda:mutation(
            b"INSTRUCTIONS\t6\n",b"INSTRUCTIONS\t5\n","DENOMINATOR_SHRINK"))
        case("PROJECTION-BODY-ROOT-SWAP",lambda:mutation(
            b"END\t6\t",b"END\t6\t"+b"0"*64+b"#","BODY_ROOT_SWAP"))
        def must_refuse(program,code):
            try: execute_native_reference(program)
            except Refusal: return
            raise ValueError(code)
        overflow=build_native_program(program_id="court.overflow",registers=[],max_steps=5,
            instructions=[{"op":"PUSH","arg":2**63-1},{"op":"PUSH","arg":1},{"op":"ADD"},{"op":"HALT"}],expected_result_i64=0)
        loop=build_native_program(program_id="court.loop",registers=[],max_steps=3,
            instructions=[{"op":"JMP","arg":0},{"op":"HALT"}],expected_result_i64=0)
        case("ARITHMETIC-OVERFLOW-REFUSED",lambda:must_refuse(overflow,"OVERFLOW_ACCEPTED"))
        case("STEP-BOUND-REFUSED",lambda:must_refuse(loop,"STEP_BOUND_ACCEPTED"))
        case("PYTHON-FALLBACK-PARITY",lambda:require(
            all(execute_native_reference(row)["status"]=="PASS" for row in corpus),
            "PYTHON_FALLBACK_FAILED"))
        case("CONTROL-AUTHORITY-CEILING",lambda:require(
            all(row["authority_effect"]=="NONE" and not row["real_a5"] and row["g0"]=="CLOSED"
                for row in cases),"AUTHORITY_CEILING_BREACH"))

    failed=sum(row["status"]!="PASS" for row in cases)
    body={"schema":"mosaic.ucm.r032-native-completion-tier1-result.v0.1",
          "status":"PASS" if failed==0 else "HOLD_FOR_REPAIR","cases":cases,
          "case_count":len(cases),"failed":failed,
          "subject_runtime_sha256":sha((kit/"UCM-v0.1-runtime.zip").read_bytes()),
          "subject_runtime_manifest_root":runtime_manifest["root"],
          "operator_kit_root":manifest["operator_kit_root"],**BOUNDARY}
    result={**body,"court_root":sha(canonical(body))}
    out.mkdir(parents=True,exist_ok=True)
    target=out/f"UCM-r032-NATIVE-COMPLETION-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
    zip_evidence(target,{"TIER1-RESULT.json":canonical(result)+b"\n",
        "REPORT.md":f"# UCM r032 native completion court\n\nStatus: {result['status']}\nCases: {len(cases)}\nFailed: {failed}\n".encode(),
        "RUN-TIER1.py":Path(__file__).read_bytes()})
    print(json.dumps({"status":result["status"],"cases":len(cases),"failed":failed,
        "court_root":result["court_root"],"evidence":str(target),
        "evidence_sha256":sha(target.read_bytes()),**BOUNDARY},sort_keys=True),flush=True)
    return 0 if failed==0 else 3

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--kit-root",type=Path,required=True)
    parser.add_argument("--out-dir",type=Path,required=True);args=parser.parse_args()
    try: return run_court(args.kit_root.resolve(),args.out_dir.resolve())
    except Exception as error:
        out=args.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
        body={"schema":"mosaic.ucm.r032-native-completion-tier1-fault.v0.1",
              "status":"HOLD_FOR_REPAIR","exception_type":type(error).__name__,
              "message_sha256":sha(str(error).encode()),**BOUNDARY}
        fault={**body,"fault_root":sha(canonical(body))}
        target=out/f"UCM-r032-NATIVE-COMPLETION-TIER1-FAULT-{fault['fault_root'][:16]}.zip"
        zip_evidence(target,{"FAULT.json":canonical(fault)+b"\n","RUN-TIER1.py":Path(__file__).read_bytes()})
        print(json.dumps({"status":"HOLD_FOR_REPAIR","evidence":str(target),
            "evidence_sha256":sha(target.read_bytes()),**BOUNDARY},sort_keys=True),flush=True)
        return 3

if __name__=="__main__": raise SystemExit(main())
