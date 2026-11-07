#!/usr/bin/env python3
"""Build the deterministic adaptive-orchestration P/PPI cold boot."""
from __future__ import annotations

import argparse, hashlib, io, json, pathlib, sys, zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
FIXED=(1980,1,1,0,0,0)
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(1,str(ROOT/"tools"))
from release_common import ENGINEERING_REVISION
from ucm.release_certification import build_embedded_metadata


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()


def add(rows,path,source):rows[path]=source.read_bytes()


def build(runtime:pathlib.Path, output:pathlib.Path, project_capsule:pathlib.Path|None=None):
    runtime_raw=runtime.read_bytes();rows={}
    add(rows,"BOOT/START-HERE.md",ROOT/"portable/BOOT/START-HERE.md")
    rows["UCM/UCM-v0.1-runtime.zip"]=runtime_raw
    add(rows,"UGK/README.md",ROOT/"vendor/ugk-adaptive-profile/README.md")
    add(rows,"UGK/UGK-ADAPTIVE-PROFILE.json",ROOT/"vendor/ugk-adaptive-profile/UGK-ADAPTIVE-PROFILE.json")
    add(rows,"PIPPI/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json",ROOT/"spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json")
    add(rows,"PIPPI/PIPPI-CAPABILITY-SURFACE-REGISTRY.json",ROOT/"spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json")
    add(rows,"PIPPI/PIPPI-MEDIATION-LIBRARY.json",ROOT/"spec/PIPPI-MEDIATION-LIBRARY.json")
    add(rows,"PIPPI/PIPPI-ADAPTIVE-COLD-BOOT.md",ROOT/"docs/PIPPI-ADAPTIVE-COLD-BOOT.md")
    for suffix in ("bash","zsh","fish","ps1"):
        add(rows,f"PIPPI/completions/pippi.{suffix}",ROOT/f"completions/pippi.{suffix}")
        add(rows,f"PIPPI/completions/pippi.{suffix}.json",ROOT/f"completions/pippi.{suffix}.json")
    add(rows,"SKILLS/ucm-pippi-mediated-agent/SKILL.md",ROOT/"skill/ucm-pippi-mediated-agent/SKILL.md")
    add(rows,"RETURN/README.md",ROOT/"portable/RETURN/README.md")
    add(rows,"VERIFY.py",ROOT/"tools/verify_pippi_cold_boot.py")
    if project_capsule is not None:add(rows,"PROJECT/PROJECT-CAPSULE.json",project_capsule)
    ugk=json.loads(rows["UGK/UGK-ADAPTIVE-PROFILE.json"])
    contract=json.loads(rows["PIPPI/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json"])
    meta_body={"schema":"mosaic.ucm.pippi-adaptive-cold-boot.v0.1","version":"v0.1","revision":ENGINEERING_REVISION,
        "runtime_sha256":sha(runtime_raw),"ugk_profile_root":ugk["ugk_profile_root"],
        "cold_boot_contract_root":contract["cold_boot_contract_root"],
        "project_capsule_sha256":sha(project_capsule.read_bytes()) if project_capsule else None,
        "host_modes":["EXECUTABLE_LOCAL","ARTIFACT_MEDIATED_WEB"],
        "native_enforced_available":False,"standing":"INFORMATION_ONLY","authority_effect":"NONE",
        "real_a5":False,"g0":"CLOSED"}
    rows["BOOT/COLD-BOOT.json"]=canonical({**meta_body,"cold_boot_root":sha(canonical(meta_body))})+b"\n"
    with zipfile.ZipFile(io.BytesIO(runtime_raw)) as runtime_zip:
        runtime_thr=json.loads(runtime_zip.read("META/THR-MANIFEST.json"))
    certification=build_embedded_metadata(payload_rows=sorted(rows.items()),
        artifact="PIPPI_ADAPTIVE_COLD_BOOT",completeness="PORTABLE_ADAPTIVE_SYSTEM",
        version="v0.1",engineering_revision=ENGINEERING_REVISION,
        source_manifest_root=runtime_thr["admissibility"]["source_manifest_root"],
        release_identity_root=runtime_thr["admissibility"]["release_identity_root"],
        public_namespace="mosaic.ucm.v0.1")
    rows.update(certification)
    ordered=sorted(rows.items());members=[{"path":name,"sha256":sha(raw),"bytes":len(raw)} for name,raw in ordered]
    mf_body={"schema":"mosaic.ucm.pippi-cold-boot-manifest.v0.1","members":members,
             "member_count":len(members),"standing":"INFORMATION_ONLY","authority_effect":"NONE",
             "real_a5":False,"g0":"CLOSED"}
    ordered=[("MANIFEST.json",canonical({**mf_body,"manifest_root":sha(canonical(mf_body))})+b"\n"),*ordered]
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for name,raw in ordered:
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,raw)
    return {"status":"PASS","path":str(output),"sha256":sha(output.read_bytes()),
            "bytes":output.stat().st_size,"members":len(members),"standing":"INFORMATION_ONLY",
            "authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}


def main():
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True);p.add_argument("--project-capsule",type=pathlib.Path)
    a=p.parse_args();print(json.dumps(build(a.runtime.resolve(),a.output.resolve(),a.project_capsule),sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
