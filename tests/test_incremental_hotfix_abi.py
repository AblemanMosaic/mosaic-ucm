import tempfile,unittest
from pathlib import Path
from ucm.capabilities import invoke
from ucm.correction_transaction import begin,build_patch,seal
class IncrementalHotfixAbiTests(unittest.TestCase):
 def test_authoring_profile_plans_from_sealed_correction(self):
  with tempfile.TemporaryDirectory() as raw:
   base=Path(raw);w=base/"w";tx=base/"tx";(w/"docs").mkdir(parents=True);(w/"docs"/"x.md").write_text("x\n",encoding="utf-8");replacement=base/"new.md";replacement.write_text("y\n",encoding="utf-8")
   begin(w,tx,"abi-hotfix");patch=base/"patch.zip";build_patch(tx,patch,[("docs/x.md",replacement)]);seal(tx,patch)
   roots=dict(compiler_root="1"*64,contract_root="2"*64,policy_pack_roots=["3"*64],toolchain_root="4"*64,environment_root="5"*64,configuration_root="6"*64)
   payload={"transaction_dir":str(tx),"test_catalog":[{"test_id":"DOC","covers":["docs/"],"always":False}],"cache_records":[],**roots}
   plan=invoke({"schema":"mosaic.ucm.request.v0.1","surface":"PLAN_INCREMENTAL_HOTFIX","payload":payload,"request_id":"plan"})["result"]
   self.assertEqual(plan["development_lane"],"INCREMENTAL");self.assertEqual(plan["correction_patch_root"],seal.__module__ and __import__("json").loads(__import__("zipfile").ZipFile(patch).read("PATCH.json"))["patch_root"])
   result=invoke({"schema":"mosaic.ucm.request.v0.1","surface":"VALIDATE_INCREMENTAL_HOTFIX","payload":{"plan":plan,"compilation_results":[],"test_results":[{"test_id":"DOC","status":"PASS","result_root":"7"*64}]},"request_id":"validate"})["result"]
   self.assertEqual(result["development_status"],"INCREMENTAL_PASS");self.assertFalse(result["release_qualified"])
if __name__=="__main__":unittest.main()
