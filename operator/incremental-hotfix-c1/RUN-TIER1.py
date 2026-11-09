from __future__ import annotations
import argparse,hashlib,json,sys,tempfile,zipfile
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument("--subject",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.subject/"src"))
 from ucm.correction_transaction import begin,build_patch,seal
 from ucm.incremental_hotfix import HotfixRefusal,build_bound_hotfix_plan,build_hotfix_plan,cache_key,validate_hotfix_result,CACHE_SCHEMA
 cases=[]
 def case(name,fn):
  try:ok=bool(fn());detail="PASS" if ok else "FALSE"
  except Exception as e:ok=False;detail=type(e).__name__+":"+str(e)
  row={"case_id":name,"status":"PASS" if ok else "FAIL","detail":detail};cases.append(row);print(f"[case {len(cases):03d}] {name}: {row['status']}",flush=True)
 roots=dict(compiler_root="1"*64,contract_root="2"*64,policy_pack_roots=["3"*64],toolchain_root="4"*64,environment_root="5"*64,configuration_root="6"*64)
 with tempfile.TemporaryDirectory() as raw:
  b=Path(raw);w=b/"w";tx=b/"tx";(w/"docs").mkdir(parents=True);(w/"docs"/"x.md").write_text("a\n");n=b/"new";n.write_text("b\n");begin(w,tx,"tier1");z=b/"p.zip";build_patch(tx,z,[("docs/x.md",n)]);seal(tx,z);cat=[{"test_id":"DOC","covers":["docs/"],"always":False}];plan=build_bound_hotfix_plan(transaction_dir=tx,test_catalog=cat,cache_records=[],**roots)
  case("SEALED-CORRECTION-BINDING",lambda:plan["changed_paths"]==["docs/x.md"] and bool(plan["correction_patch_root"]))
  case("RELEASE-CEILING",lambda:not plan["release_qualified"] and plan["full_qualification_required_for_release"])
  def unsealed():
   s=b/"s";u=b/"u";s.mkdir();(s/"x").write_text("x");begin(s,u,"u")
   try:build_bound_hotfix_plan(transaction_dir=u,test_catalog=[],cache_records=[],**roots);return False
   except HotfixRefusal as e:return e.code=="HOTFIX_CORRECTION_NOT_SEALED"
  case("UNSEALED-REFUSED",unsealed)
  def omitted():
   try:validate_hotfix_result(plan=plan,compilation_results=[],test_results=[]);return False
   except HotfixRefusal as e:return e.code=="HOTFIX_TEST_DENOMINATOR_MISMATCH"
  case("OMITTED-TEST-REFUSED",omitted)
  def tamper():
   x=dict(plan);x["release_qualified"]=True
   try:validate_hotfix_result(plan=x,compilation_results=[],test_results=[]);return False
   except HotfixRefusal as e:return e.code=="HOTFIX_PLAN_INVALID"
  case("PLAN-TAMPER-REFUSED",tamper)
  case("PROGRESS-NOT-EVIDENCE",lambda:"progress" not in json.dumps(plan).lower())
  def critical():
   q=b/"critical";(q/"src"/"ucm").mkdir(parents=True);(q/"src"/"ucm"/"system.py").write_text("X=1");x=build_hotfix_plan(workspace=q,changed_paths=["src/ucm/system.py"],test_catalog=[{"test_id":"S","covers":["src/ucm/system.py"],"always":False}],cache_records=[],**roots);return x["development_lane"]=="FULL_QUALIFICATION"
  case("CONTROL-PLANE-ESCALATES",critical)
  def stale():
   q=b/"cache";(q/"src").mkdir(parents=True);f=q/"src"/"x.py";f.write_text("X=1");u=hashlib.sha256(f.read_bytes()).hexdigest();wrong=dict(roots);wrong["environment_root"]="9"*64;k=cache_key(unit_root=u,dependency_roots=[],**wrong);record={"schema":CACHE_SCHEMA,"cache_key":k,"result_root":"8"*64,"status":"PASS"};x=build_hotfix_plan(workspace=q,changed_paths=["src/x.py"],test_catalog=[{"test_id":"X","covers":["src/"],"always":False}],cache_records=[record],**roots);return not x["reuse_receipts"]
  case("STALE-CACHE-NOT-REUSED",stale)
  case("EXACT-RESULT-VALIDATES",lambda:validate_hotfix_result(plan=plan,compilation_results=[],test_results=[{"test_id":"DOC","status":"PASS","result_root":"7"*64}])["development_status"]=="INCREMENTAL_PASS")
 status="PASS" if all(x["status"]=="PASS" for x in cases) else "HOLD_FOR_REPAIR";body={"schema":"mosaic.ucm.incremental-hotfix-tier1.v0.1","cases":cases,"case_count":len(cases),"status":status,"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"};body["court_root"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest();a.out.mkdir(parents=True,exist_ok=True);members={"TIER1-RESULT.json":json.dumps(body,sort_keys=True,separators=(",",":")).encode()+b"\n","REPORT.md":f"# Incremental hotfix Tier 1\n\nStatus: {status}\n\nCases: {len(cases)}\n".encode()};out=a.out/"UCM-INCREMENTAL-HOTFIX-C1-TIER1-EVIDENCE.zip"
 with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
  for name in sorted(members):
   i=zipfile.ZipInfo(name,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,members[name])
 print(json.dumps({"status":status,"evidence":str(out),"court_root":body["court_root"]},sort_keys=True));return 0 if status=="PASS" else 20
if __name__=="__main__":raise SystemExit(main())
