"""Content-addressed incremental hotfix planning and validation for UCM/AMCAS."""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Sequence
from uclop.canonical import canonical_bytes,root
from .content_graph import build_graph

BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
PLAN_SCHEMA="mosaic.ucm.incremental-hotfix-plan.v0.1"
RESULT_SCHEMA="mosaic.ucm.incremental-hotfix-validation.v0.1"
CACHE_SCHEMA="mosaic.ucm.incremental-reuse-record.v0.1"
CRITICAL_PREFIXES=(
 "src/ucm/system.py","src/ucm/capabilities.py","src/ucm/content_graph.py",
 "src/ucm/incremental_hotfix.py","src/ucm/correction_transaction.py",
 "src/uclop/","src/uclsh/","tools/run_","tools/build_","tools/prepare_release",
 "spec/ABI-STABILITY.json","spec/ucm-system-registry.json","spec/product-profiles/",
)
class HotfixRefusal(RuntimeError):
 def __init__(self,code,detail=""):self.code,self.detail=code,detail;super().__init__(code+(":"+detail if detail else ""))
def _hex(v):return type(v) is str and len(v)==64 and all(c in "0123456789abcdef" for c in v)
def _path(v):
 if type(v) is not str or not v or "\\" in v:raise HotfixRefusal("HOTFIX_PATH_INVALID",str(v))
 p=PurePosixPath(v)
 if p.is_absolute() or any(x in ("",".","..") for x in p.parts):raise HotfixRefusal("HOTFIX_PATH_INVALID",v)
 return p.as_posix()
def _load(value):
 if isinstance(value,(str,Path)):return json.loads(Path(value).read_text("utf-8"))
 return value
def _progress(path:Path|None,phase,state,**fields):
 e={"schema":"mosaic.ucm.nonsemantic-progress.v0.1","phase":phase,"state":state,"nonsemantic":True,"time_unix_ns":time.time_ns(),**fields}
 if path:
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open("ab") as f:f.write(canonical_bytes(e)+b"\n");f.flush()
 print(json.dumps(e,sort_keys=True,separators=(",",":")),flush=True)
 return e
def cache_key(*,unit_root,dependency_roots,compiler_root,contract_root,policy_pack_roots,toolchain_root,environment_root,configuration_root):
 body={"schema":"mosaic.ucm.incremental-cache-key.v0.1","unit_root":unit_root,"dependency_roots":sorted(dependency_roots),"compiler_root":compiler_root,"contract_root":contract_root,"policy_pack_roots":sorted(policy_pack_roots),"toolchain_root":toolchain_root,"environment_root":environment_root,"configuration_root":configuration_root}
 for k,v in body.items():
  if k=="schema":continue
  if isinstance(v,list):
   if not all(_hex(x) for x in v):raise HotfixRefusal("HOTFIX_CACHE_KEY_ROOT_INVALID",k)
  elif not _hex(v):raise HotfixRefusal("HOTFIX_CACHE_KEY_ROOT_INVALID",k)
 return root(body)
def _catalog(catalog):
 value=_load(catalog)
 if type(value) is not list:raise HotfixRefusal("HOTFIX_TEST_CATALOG_INVALID")
 rows=[]
 for row in value:
  if type(row) is not dict or set(row)!={"test_id","covers","always"}:raise HotfixRefusal("HOTFIX_TEST_CATALOG_ROW_INVALID")
  if type(row["test_id"]) is not str or type(row["always"]) is not bool or type(row["covers"]) is not list:raise HotfixRefusal("HOTFIX_TEST_CATALOG_ROW_INVALID")
  rows.append({"test_id":row["test_id"],"covers":sorted({_path(x) for x in row["covers"]}),"always":row["always"]})
 if len({x["test_id"] for x in rows})!=len(rows):raise HotfixRefusal("HOTFIX_TEST_CATALOG_DUPLICATE")
 return sorted(rows,key=lambda x:x["test_id"])
def _cache(records):
 value=_load(records) if records is not None else []
 if type(value) is not list:raise HotfixRefusal("HOTFIX_CACHE_RECORDS_INVALID")
 out={}
 for row in value:
  if type(row) is not dict or row.get("schema")!=CACHE_SCHEMA or not _hex(row.get("cache_key")) or not _hex(row.get("result_root")) or row.get("status")!="PASS":raise HotfixRefusal("HOTFIX_CACHE_RECORD_INVALID")
  if row["cache_key"] in out:raise HotfixRefusal("HOTFIX_CACHE_RECORD_DUPLICATE")
  out[row["cache_key"]]=row
 return out
def build_hotfix_plan(*,workspace,changed_paths,test_catalog,cache_records,compiler_root,contract_root,policy_pack_roots,toolchain_root,environment_root,configuration_root,progress_path=None):
 workspace=Path(workspace).resolve();progress=Path(progress_path) if progress_path else None
 changed=sorted({_path(x) for x in changed_paths});_progress(progress,"inventory","start",changed_count=len(changed))
 graph=build_graph(workspace);nodes={x["path"]:x for x in graph["nodes"]};unknown=sorted(set(changed)-set(nodes))
 _progress(progress,"impact","start",graph_root=graph["graph_root"])
 affected=set(changed)&set(nodes);front=list(affected)
 by_hash={x["sha256"]:x["path"] for x in graph["nodes"]}
 reverse={}
 for e in graph["edges"]:
  for resolved in e["resolved_paths"]:reverse.setdefault(resolved,set()).add(e["from"])
 while front:
  item=front.pop()
  for dependent in reverse.get(item,set()):
   if dependent not in affected:affected.add(dependent);front.append(dependent)
 critical=sorted(x for x in changed if any(x==p or x.startswith(p) for p in CRITICAL_PREFIXES))
 units=sorted(x for x in affected if nodes[x]["kind"] in {"SOURCE","CONTRACT","TOOL"})
 catalog=_catalog(test_catalog);selected=[];covered=set()
 for row in catalog:
  hits=sorted({p for p in affected for prefix in row["covers"] if p==prefix or p.startswith(prefix)})
  if row["always"] or hits:selected.append({"test_id":row["test_id"],"reason":"ALWAYS" if row["always"] else "AFFECTED_CLOSURE","covered_paths":hits});covered.update(hits)
 uncovered=sorted(x for x in units if x not in covered)
 cache=_cache(cache_records);reuse=[];compile_units=[]
 roots={"compiler_root":compiler_root,"contract_root":contract_root,"policy_pack_roots":sorted(policy_pack_roots),"toolchain_root":toolchain_root,"environment_root":environment_root,"configuration_root":configuration_root}
 for unit in units:
  node=nodes[unit];deps=sorted({nodes[x]["sha256"] for x in reverse.get(unit,set()) if x in nodes})
  key=cache_key(unit_root=node["sha256"],dependency_roots=deps,**roots)
  if key in cache:
   rr=cache[key];core={"schema":"mosaic.ucm.proof-of-reuse.v0.1","path":unit,"unit_root":node["sha256"],"cache_key":key,"prior_result_root":rr["result_root"],"unchanged_dependency_roots":deps,**roots,**BOUNDARY};reuse.append({**core,"reuse_root":root(core)})
  else:compile_units.append({"path":unit,"unit_root":node["sha256"],"dependency_roots":deps,"cache_key":key})
 escalation=bool(unknown or critical or uncovered)
 body={"schema":PLAN_SCHEMA,"workspace_graph_root":graph["graph_root"],"changed_paths":changed,"affected_paths":sorted(affected),"unknown_paths":unknown,"critical_paths":critical,"compilation_units":compile_units,"reuse_receipts":reuse,"selected_tests":selected,"uncovered_units":uncovered,"development_lane":"FULL_QUALIFICATION" if escalation else "INCREMENTAL","cache_reuse_allowed":not bool(critical),"full_qualification_required_for_release":True,"release_qualified":False,"roots":roots,**BOUNDARY}
 plan={**body,"plan_root":root(body)}
 _progress(progress,"impact","complete",affected=len(affected),unknown=len(unknown),critical=len(critical));_progress(progress,"cache","complete",hits=len(reuse),misses=len(compile_units));_progress(progress,"test_selection","complete",selected=len(selected),uncovered=len(uncovered),development_lane=body["development_lane"])
 return plan
def validate_hotfix_result(*,plan,compilation_results,test_results,progress_path=None):
 plan=_load(plan);progress=Path(progress_path) if progress_path else None
 if type(plan) is not dict or plan.get("schema")!=PLAN_SCHEMA or plan.get("plan_root")!=root({k:v for k,v in plan.items() if k!="plan_root"}):raise HotfixRefusal("HOTFIX_PLAN_INVALID")
 _progress(progress,"validation","start",plan_root=plan["plan_root"])
 cr=_load(compilation_results);tr=_load(test_results)
 expected_units={x["path"]:x for x in plan["compilation_units"]};expected_tests={x["test_id"] for x in plan["selected_tests"]}
 if type(cr) is not list or {x.get("path") for x in cr}!=set(expected_units):raise HotfixRefusal("HOTFIX_COMPILATION_DENOMINATOR_MISMATCH")
 if type(tr) is not list or {x.get("test_id") for x in tr}!=expected_tests:raise HotfixRefusal("HOTFIX_TEST_DENOMINATOR_MISMATCH")
 for row in cr:
  unit=expected_units[row["path"]]
  if set(row)!={"path","unit_root","cache_key","status","result_root"} or row["unit_root"]!=unit["unit_root"] or row["cache_key"]!=unit["cache_key"] or row["status"]!="PASS" or not _hex(row["result_root"]):raise HotfixRefusal("HOTFIX_COMPILATION_RESULT_INVALID",row.get("path",""))
 for row in tr:
  if set(row)!={"test_id","status","result_root"} or row["status"]!="PASS" or not _hex(row["result_root"]):raise HotfixRefusal("HOTFIX_TEST_RESULT_INVALID",row.get("test_id",""))
 developmental="FULL_QUALIFICATION_REQUIRED" if plan["development_lane"]=="FULL_QUALIFICATION" else "INCREMENTAL_PASS"
 body={"schema":RESULT_SCHEMA,"plan_root":plan["plan_root"],"workspace_graph_root":plan["workspace_graph_root"],"changed_paths":plan["changed_paths"],"compilation_result_roots":sorted(x["result_root"] for x in cr),"test_result_roots":sorted(x["result_root"] for x in tr),"reuse_roots":sorted(x["reuse_root"] for x in plan["reuse_receipts"]),"development_status":developmental,"full_qualification_required_for_release":True,"release_qualified":False,**BOUNDARY}
 result={**body,"validation_root":root(body)};_progress(progress,"validation","complete",development_status=developmental,validation_root=result["validation_root"]);return result

def build_bound_hotfix_plan(*,transaction_dir,test_catalog,cache_records,compiler_root,contract_root,policy_pack_roots,toolchain_root,environment_root,configuration_root,progress_path=None):
 from .correction_transaction import inventory as correction_inventory, status as correction_status
 tx=Path(transaction_dir).resolve();summary=correction_status(tx);s=summary["transaction"]
 if s["state"]!="SEALED":raise HotfixRefusal("HOTFIX_CORRECTION_NOT_SEALED",s["state"])
 patch=json.loads(__import__("zipfile").ZipFile(tx/"PATCH.zip").read("PATCH.json"))
 core={k:v for k,v in patch.items() if k!="patch_root"}
 if patch.get("patch_root")!=root(core) or patch["patch_root"]!=s["patch_root"]:raise HotfixRefusal("HOTFIX_CORRECTION_PATCH_INVALID")
 workspace=Path(s["source_path"])
 observed=correction_inventory(workspace,patch["excludes"])
 if observed["source_root"]!=patch["post_source_root"] or observed["source_root"]!=s["post_source_root"]:raise HotfixRefusal("HOTFIX_CORRECTION_POST_ROOT_MISMATCH")
 plan=build_hotfix_plan(workspace=workspace,changed_paths=[x["path"] for x in patch["changes"]],test_catalog=test_catalog,cache_records=cache_records,compiler_root=compiler_root,contract_root=contract_root,policy_pack_roots=policy_pack_roots,toolchain_root=toolchain_root,environment_root=environment_root,configuration_root=configuration_root,progress_path=progress_path)
 body={k:v for k,v in plan.items() if k!="plan_root"};body.update({"correction_transaction_id":s["transaction_id"],"correction_patch_root":s["patch_root"],"pre_source_root":s["pre_source_root"],"candidate_source_root":s["post_source_root"]})
 return {**body,"plan_root":root(body)}

def execute_hotfix_plan(*,plan,workspace,python_executable=None,progress_path=None):
 import os,subprocess,sys
 plan=_load(plan);workspace=Path(workspace).resolve();progress=Path(progress_path) if progress_path else None
 if type(plan) is not dict or plan.get("schema")!=PLAN_SCHEMA or plan.get("plan_root")!=root({k:v for k,v in plan.items() if k!="plan_root"}):raise HotfixRefusal("HOTFIX_PLAN_INVALID")
 graph=build_graph(workspace)
 if graph["graph_root"]!=plan["workspace_graph_root"]:raise HotfixRefusal("HOTFIX_WORKSPACE_GRAPH_MISMATCH")
 compile_results=[];_progress(progress,"partial_compilation","start",total=len(plan["compilation_units"]))
 for index,unit in enumerate(plan["compilation_units"],1):
  path=workspace/unit["path"];raw=path.read_bytes()
  if __import__("hashlib").sha256(raw).hexdigest()!=unit["unit_root"]:raise HotfixRefusal("HOTFIX_COMPILATION_UNIT_ROOT_MISMATCH",unit["path"])
  try:
   if path.suffix==".py":compile(raw,unit["path"],"exec",dont_inherit=True)
   status="PASS"
  except (SyntaxError,ValueError,TypeError):status="FAIL"
  body={"schema":"mosaic.ucm.incremental-compilation-result.v0.1","path":unit["path"],"unit_root":unit["unit_root"],"cache_key":unit["cache_key"],"status":status}
  row={"path":unit["path"],"unit_root":unit["unit_root"],"cache_key":unit["cache_key"],"status":status,"result_root":root(body)};compile_results.append(row);_progress(progress,"partial_compilation","progress",completed=index,total=len(plan["compilation_units"]),unit_path=unit["path"],status=status)
 env=dict(os.environ);env["PYTHONDONTWRITEBYTECODE"]="1";src=str(workspace/"src");env["PYTHONPATH"]=src+(os.pathsep+env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
 test_results=[];_progress(progress,"targeted_tests","start",total=len(plan["selected_tests"]))
 for index,item in enumerate(plan["selected_tests"],1):
  run=subprocess.run([python_executable or sys.executable,"-m","unittest",item["test_id"]],cwd=workspace,env=env,capture_output=True)
  status="PASS" if run.returncode==0 else "FAIL";body={"schema":"mosaic.ucm.incremental-test-result.v0.1","test_id":item["test_id"],"status":status,"exit_code":run.returncode,"stdout_sha256":__import__("hashlib").sha256(run.stdout).hexdigest(),"stderr_sha256":__import__("hashlib").sha256(run.stderr).hexdigest()}
  test_results.append({"test_id":item["test_id"],"status":status,"result_root":root(body)});_progress(progress,"targeted_tests","progress",completed=index,total=len(plan["selected_tests"]),test_id=item["test_id"],status=status)
 _progress(progress,"execution","complete",compilation_failures=sum(x["status"]!="PASS" for x in compile_results),test_failures=sum(x["status"]!="PASS" for x in test_results))
 return {"compilation_results":compile_results,"test_results":test_results}
