import hashlib,json,tempfile,unittest
from pathlib import Path
from uclop.canonical import root
from ucm.incremental_hotfix import CACHE_SCHEMA,build_hotfix_plan,cache_key,validate_hotfix_result

H="1"*64
class IncrementalHotfixTests(unittest.TestCase):
 def fixture(self,base):
  w=base/"workspace";(w/"docs").mkdir(parents=True);(w/"src"/"app").mkdir(parents=True);(w/"tests").mkdir()
  (w/"docs"/"guide.md").write_text("guide\n",encoding="utf-8")
  (w/"src"/"app"/"model.py").write_text("VALUE=1\n",encoding="utf-8")
  (w/"tests"/"test_model.py").write_text("pass\n",encoding="utf-8")
  return w
 def roots(self):return dict(compiler_root="1"*64,contract_root="2"*64,policy_pack_roots=["3"*64],toolchain_root="4"*64,environment_root="5"*64,configuration_root="6"*64)
 def test_document_hotfix_is_incremental_and_never_release_qualified(self):
  with tempfile.TemporaryDirectory() as raw:
   b=Path(raw);w=self.fixture(b);catalog=[{"test_id":"DOC-CHECK","covers":["docs/"],"always":False}]
   plan=build_hotfix_plan(workspace=w,changed_paths=["docs/guide.md"],test_catalog=catalog,cache_records=[],progress_path=b/"progress.jsonl",**self.roots())
   self.assertEqual(plan["development_lane"],"INCREMENTAL");self.assertTrue(plan["full_qualification_required_for_release"]);self.assertFalse(plan["release_qualified"])
   result=validate_hotfix_result(plan=plan,compilation_results=[],test_results=[{"test_id":"DOC-CHECK","status":"PASS","result_root":"7"*64}],progress_path=b/"progress.jsonl")
   self.assertEqual(result["development_status"],"INCREMENTAL_PASS");self.assertFalse(result["release_qualified"])
   events=[json.loads(x) for x in (b/"progress.jsonl").read_text("utf-8").splitlines()];self.assertTrue(all(x["nonsemantic"] for x in events))
 def test_exact_cache_record_produces_proof_of_reuse(self):
  with tempfile.TemporaryDirectory() as raw:
   b=Path(raw);w=self.fixture(b);unit=w/"src"/"app"/"model.py";u=hashlib.sha256(unit.read_bytes()).hexdigest();k=cache_key(unit_root=u,dependency_roots=[],**self.roots())
   cache=[{"schema":CACHE_SCHEMA,"cache_key":k,"result_root":"8"*64,"status":"PASS"}]
   catalog=[{"test_id":"MODEL","covers":["src/app/"],"always":False}]
   plan=build_hotfix_plan(workspace=w,changed_paths=["src/app/model.py"],test_catalog=catalog,cache_records=cache,**self.roots())
   self.assertEqual(len(plan["reuse_receipts"]),1);self.assertEqual(plan["compilation_units"],[])
   result=validate_hotfix_result(plan=plan,compilation_results=[],test_results=[{"test_id":"MODEL","status":"PASS","result_root":"9"*64}])
   self.assertEqual(result["development_status"],"INCREMENTAL_PASS")
 def test_control_plane_change_escalates_development_lane(self):
  with tempfile.TemporaryDirectory() as raw:
   b=Path(raw);w=self.fixture(b);(w/"src"/"ucm").mkdir();(w/"src"/"ucm"/"system.py").write_text("X=1\n",encoding="utf-8")
   plan=build_hotfix_plan(workspace=w,changed_paths=["src/ucm/system.py"],test_catalog=[{"test_id":"SYSTEM","covers":["src/ucm/system.py"],"always":False}],cache_records=[],**self.roots())
   self.assertEqual(plan["development_lane"],"FULL_QUALIFICATION");self.assertIn("src/ucm/system.py",plan["critical_paths"])
 def test_executor_compiles_affected_unit_and_runs_selected_test(self):
  from ucm.incremental_hotfix import execute_hotfix_plan
  with tempfile.TemporaryDirectory() as raw:
   b=Path(raw);w=self.fixture(b);(w/"tests"/"__init__.py").write_text("",encoding="utf-8");(w/"tests"/"test_sample.py").write_text("import unittest\nfrom app import model\nclass Sample(unittest.TestCase):\n def test_ok(self): self.assertEqual(model.VALUE,1)\n",encoding="utf-8");(w/"src"/"app"/"__init__.py").write_text("",encoding="utf-8")
   plan=build_hotfix_plan(workspace=w,changed_paths=["src/app/model.py"],test_catalog=[{"test_id":"tests.test_sample.Sample.test_ok","covers":["src/app/"],"always":False}],cache_records=[],**self.roots())
   execution=execute_hotfix_plan(plan=plan,workspace=w,progress_path=b/"progress.jsonl")
   self.assertTrue(all(x["status"]=="PASS" for x in execution["compilation_results"]));self.assertEqual(execution["test_results"][0]["status"],"PASS")
if __name__=="__main__":unittest.main()
