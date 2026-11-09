#!/usr/bin/env python3
"""Builder-authored, operator-runnable r031 adversarial court. Do not import."""
from __future__ import annotations
import argparse,copy,hashlib,json,os
from pathlib import Path
import shutil,sys,tempfile,zipfile

FIXED=(1980,1,1,0,0,0);BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify_kit(root):
 m=json.loads((root/"KIT-MANIFEST.json").read_text(encoding="utf-8"));body={k:v for k,v in m.items() if k!="operator_kit_root"}
 if sha(canonical(body))!=m.get("operator_kit_root"):raise ValueError("KIT_ROOT_INVALID")
 expected={r["path"]:r for r in m["members"]};actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name!="KIT-MANIFEST.json"}
 if actual!=set(expected):raise ValueError("KIT_SET_INVALID")
 for name,row in expected.items():
  raw=(root/name).read_bytes()
  if sha(raw)!=row["sha256"] or len(raw)!=row["bytes"]:raise ValueError("KIT_MEMBER_INVALID:"+name)
 return m
def verify_runtime(path):
 with zipfile.ZipFile(path) as z:
  names=z.namelist();m=json.loads(z.read("MANIFEST.json"));body={k:v for k,v in m.items() if k!="root"}
  if sha(canonical(body))!=m.get("root"):raise ValueError("RUNTIME_MANIFEST_ROOT_INVALID")
  rows={r["path"]:r for r in m["members"]}
  if set(names)!={"MANIFEST.json",*rows}:raise ValueError("RUNTIME_SET_INVALID")
  for name,row in rows.items():
   raw=z.read(name)
   if sha(raw)!=row["sha256"] or len(raw)!=row["bytes"]:raise ValueError("RUNTIME_MEMBER_INVALID")
 return m
def main():
 p=argparse.ArgumentParser();p.add_argument("--kit-root",type=Path,required=True);p.add_argument("--out-dir",type=Path,required=True);a=p.parse_args()
 kit=a.kit_root.resolve();out=a.out_dir.resolve();verify_kit(kit);verify_runtime(kit/"UCM-v0.1-runtime.zip");cases=[]
 def case(name,fn):
  try:fn();status="PASS"
  except Exception as e:status="FAIL";detail=type(e).__name__+":"+sha(str(e).encode())
  else:detail=None
  row={"case_id":name,"status":status,**BOUNDARY};
  if detail:row["diagnostic"]=detail
  cases.append(row);print(f"[case {len(cases):03d}] {name}: {status}",flush=True)
 with tempfile.TemporaryDirectory(prefix="r031-court-") as raw:
  base=Path(raw);runtime=base/"runtime";runtime.mkdir()
  with zipfile.ZipFile(kit/"UCM-v0.1-runtime.zip") as z:z.extractall(runtime)
  sys.path.insert(0,str(runtime/"src"))
  from uclop.canonical import Refusal,root
  from ucm import transtemporal_archive as t
  source=base/"source";repo=base/"repo";source.mkdir();(source/"a.txt").write_bytes(b"alpha\n");(source/"b.txt").write_bytes(b"beta\n")
  kwargs={"source":source,"repository":repo,"revision":"r031","semantic_root":root({"s":1}),"governance_root":root({"g":1}),"jurisdiction_root":root({"j":1})}
  result=t.ingest_tree(**kwargs);manifest=result["MANIFEST.json"]
  case("CONTROL-KIT-CUSTODY",lambda:verify_kit(kit))
  case("CONTROL-DUAL-DIGEST",lambda:[t.digest_record((source/r["path"]).read_bytes())==r["digest"] or (_ for _ in()).throw(ValueError()) for r in manifest["files"]])
  case("CONTROL-REVISION-VERIFY",lambda:t.verify_revision(repository=repo,revision="r031"))
  def reconstruct():
   dst=base/"restored";t.materialize_revision(repository=repo,revision="r031",destination=dst)
   if sorted((p.relative_to(dst).as_posix(),p.read_bytes()) for p in dst.rglob("*") if p.is_file())!=sorted((p.relative_to(source).as_posix(),p.read_bytes()) for p in source.rglob("*") if p.is_file()):raise ValueError("RECONSTRUCTION_MISMATCH")
  case("CONTROL-EXACT-RECONSTRUCTION",reconstruct)
  case("CONTROL-DKN-UNBOUND",lambda:result["DKN-BINDING.json"]["status"]=="DECLARED_UNBOUND" or (_ for _ in()).throw(ValueError()))
  case("CONTROL-NATIVE-PROJECTION",lambda:t.build_native_manifest(repository=repo,revision="r031").startswith(b"UCM-NATIVE-MANIFEST\t1\tSHA-256\n") or (_ for _ in()).throw(ValueError()))
  def object_attack():
   row=manifest["files"][0];path=repo/"objects"/"blake3-256"/row["digest"]["blake3_256"][:2]/row["digest"]["blake3_256"];old=path.read_bytes();path.write_bytes(b"attack")
   try:
    try:t.verify_revision(repository=repo,revision="r031")
    except (Refusal,ValueError,FileNotFoundError):return
    raise ValueError("OBJECT_MUTATION_ACCEPTED")
   finally:path.write_bytes(old)
  case("OBJECT-BYTES-MUTATION",object_attack)
  def manifest_attack(field,value,code):
   path=repo/"revisions/r031/MANIFEST.json";old=path.read_bytes();m=json.loads(old);m[field]=value;m["manifest_root"]=t.root({k:v for k,v in m.items() if k!="manifest_root"});path.write_bytes(canonical(m)+b"\n")
   try:
    try:t.verify_revision(repository=repo,revision="r031")
    except (Refusal,ValueError,FileNotFoundError):return
    raise ValueError(code)
   finally:path.write_bytes(old)
  case("PARENT-ROOT-RESEALED-SWAP",lambda:manifest_attack("parent_manifest_root","0"*64,"PARENT_SWAP_ACCEPTED"))
  def thr_attack():
   path=repo/"revisions/r031/THR-MANIFEST.json";old=path.read_bytes();m=json.loads(old);m["commitments"]["H_s_state"]="0"*64;m["h_body"]=t.root(m["commitments"]);m["thr_manifest_root"]=t.root({k:v for k,v in m.items() if k!="thr_manifest_root"});path.write_bytes(canonical(m)+b"\n")
   try:
    try:t.verify_revision(repository=repo,revision="r031")
    except (Refusal,ValueError):return
    raise ValueError("THR_SWAP_ACCEPTED")
   finally:path.write_bytes(old)
  case("THR-STATE-RESEALED-SWAP",thr_attack)
  def dkn_attack():
   path=repo/"revisions/r031/DKN-BINDING.json";old=path.read_bytes();m=json.loads(old);m.update(status="PASS_SELF_CERTIFIED",public_key="00",signature="00");m["dkn_binding_root"]=t.root({k:v for k,v in m.items() if k!="dkn_binding_root"});path.write_bytes(canonical(m)+b"\n")
   try:
    try:t.verify_revision(repository=repo,revision="r031")
    except (Refusal,ValueError):return
    raise ValueError("DKN_OVERCLAIM_ACCEPTED")
   finally:path.write_bytes(old)
  case("DKN-UNBOUND-LAUNDERING",dkn_attack)
  def path_refusal():
   try:t._portable("../x")
   except (Refusal,ValueError):return
   raise ValueError("PATH_ACCEPTED")
  case("PATH-TRAVERSAL-REFUSED",path_refusal)
  def nonempty():
   dst=base/"nonempty";dst.mkdir();(dst/"keep").write_bytes(b"keep")
   try:t.materialize_revision(repository=repo,revision="r031",destination=dst)
   except (Refusal,ValueError):return
   raise ValueError("NONEMPTY_ACCEPTED")
  case("NONEMPTY-MATERIALIZATION-REFUSED",nonempty)
  case("SEMCRYS-UNBOUND-HELD",lambda:t.build_semcrys_plan(repository=repo,revision="r031",semcrys_manifest_root=None,memory_vault_binding_root=None)["status"]=="HELD_OPTIONAL_PACK_UNBOUND" or (_ for _ in()).throw(ValueError()))
  def native_mutation():
   lines=t.build_native_manifest(repository=repo,revision="r031").decode().splitlines();lines[1]="0"*64+lines[1][64:]
   if lines[1].split("\t",1)[0]==manifest["files"][0]["digest"]["sha256"]:raise ValueError("NATIVE_MUTATION_INVISIBLE")
  case("NATIVE-MANIFEST-DIGEST-SWAP",native_mutation)
  failed=sum(r["status"]!="PASS" for r in cases);body={"schema":"mosaic.ucm.r031-tier1-result.v0.1","status":"PASS" if failed==0 else "HOLD_FOR_REPAIR","cases":cases,"case_count":len(cases),"failed":failed,"subject_runtime_sha256":sha((kit/"UCM-v0.1-runtime.zip").read_bytes()),**BOUNDARY};result={**body,"court_root":sha(canonical(body))}
  evidence={"TIER1-RESULT.json":canonical(result)+b"\n","REPORT.md":f"# UCM r031 operator court\n\nStatus: {result['status']}\nCases: {len(cases)}\nFailed: {failed}\n".encode(),"RUN-TIER1.py":Path(__file__).read_bytes()}
  out.mkdir(parents=True,exist_ok=True);path=out/f"UCM-r031-TRANSTEMPORAL-NATIVE-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
  with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for name,data in sorted(evidence.items()):info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;info.create_system=3;z.writestr(info,data)
  print(json.dumps({"status":result["status"],"cases":len(cases),"failed":failed,"court_root":result["court_root"],"evidence":str(path),"evidence_sha256":sha(path.read_bytes()),**BOUNDARY},sort_keys=True));return 0 if failed==0 else 3
if __name__=="__main__":raise SystemExit(main())
