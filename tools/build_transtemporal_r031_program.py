#!/usr/bin/env python3
"""Build the acceptance-bound UCM r031 transtemporal/native program."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"program/transtemporal-native-r031"
BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
PREDECESSOR_SOURCE_ROOT="7ada98546cbd1330eeaca3f01125a3e428d047a427fc5cd34ba395acf52b5e07"
FILES=("README.md","docs/TRANSTEMPORAL-ARCHIVE-AND-NATIVE-VERIFICATION.md","native/ucm_archive_verify.c",
       "src/ucm/transtemporal_archive.py","src/ucm/pippi_cli.py","src/ucm/system.py","src/ucm/capabilities.py",
       "tests/test_transtemporal_archive.py","tools/run_r031_native_study.py",
       "tools/build_r031_transtemporal_history.py","tools/build_r031_review_transport.py",
       "docs/R31-REVIEW-WORK-ORDER.md",
       "operator/transtemporal-native-r031/KIT-DECLARATION.json","operator/transtemporal-native-r031/RUN-TIER1.py",
       "tools/build_transtemporal_r031_operator_kit.py")
CASES=(
 ("R31-01","Constitutional computing is the primary public orientation",
  "tests.test_transtemporal_archive.TranstemporalArchiveTests.test_readme_leads_with_constitutional_substrate_and_native_scope"),
 ("R31-02","Two revisions deduplicate and reconstruct exact bytes with stable integer identities",
  "tests.test_transtemporal_archive.TranstemporalArchiveTests.test_two_revisions_deduplicate_reconstruct_and_keep_integer_ids"),
 ("R31-03","Tampered objects refuse and DKN remains unbound without key ceremony",
  "tests.test_transtemporal_archive.TranstemporalArchiveTests.test_tampered_object_refuses_and_dkn_stays_unbound"),
 ("R31-04","SemCrys and Memory Vault remain optional non-effecting realizations",
  "tests.test_transtemporal_archive.TranstemporalArchiveTests.test_semcrys_is_optional_and_never_claims_an_effect"),
 ("R31-05","The read-only archive verifier is identical through the public ABI",
  "tests.test_transtemporal_archive.TranstemporalArchiveTests.test_read_only_public_abi_matches_direct_verification"),
 ("R31-06","The operator court is builder-authored, unexecuted, and reserved for the user",
  "tests.test_transtemporal_archive.TranstemporalArchiveTests.test_operator_runner_is_builder_authored_and_unexecuted"),
)
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def seal(body,field):return {**body,field:hashlib.sha256(canonical(body)).hexdigest()}
def build():
 rows=[{"path":p,"sha256":hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),"bytes":(ROOT/p).stat().st_size} for p in FILES]
 denominator=seal({"schema":"mosaic.ucm.r031-source-denominator.v0.1","predecessor_source_root":PREDECESSOR_SOURCE_ROOT,
                   "members":rows,"member_count":len(rows),**BOUNDARY},"source_denominator_root")
 payload={"SOURCE-DENOMINATOR.json":denominator};reqs=[];cases=[];sels=[]
 for identifier,title,check in CASES:
  req=seal({"schema":"mosaic.ucm.r031-requirement.v0.1","requirement_id":identifier,"title":title,
            "source_denominator_root":denominator["source_denominator_root"],"program_rule":"ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT",**BOUNDARY},"requirement_root")
  case=seal({"schema":"mosaic.ucm.pippi-acceptance-case.v0.1","acceptance_case_id":identifier,
             "requirement_root":req["requirement_root"],"subject_root":PREDECESSOR_SOURCE_ROOT,
             "verification_surface":check,"expected_result_code":"PASS","current_status":"UNMET",**BOUNDARY},"acceptance_case_root")
  sel=seal({"schema":"mosaic.ucm.pippi-work-selection.v0.1","acceptance_case_root":case["acceptance_case_root"],
            "work_class":"DIRECT_ACCEPTANCE_CLOSURE","direct_closure_check_id":check,
            "infrastructure_block_root":None,"selection_basis":"DIRECT_CASE_CLOSURE",
            "implementation_effect_authorized":False,**BOUNDARY},"work_selection_root")
  payload[f"{identifier}-REQUIREMENT.json"]=req;payload[f"{identifier}-ACCEPTANCE-CASE.json"]=case;payload[f"{identifier}-WORK-SELECTION.json"]=sel
  reqs.append(req["requirement_root"]);cases.append(case["acceptance_case_root"]);sels.append(sel["work_selection_root"])
 program=seal({"schema":"mosaic.ucm.r031-transtemporal-native-program.v0.1","program_id":"UCM_R031_TRANSTEMPORAL_NATIVE",
  "version":"v0.1","engineering_revision":"r031","predecessor_revision":"r030","predecessor_source_root":PREDECESSOR_SOURCE_ROOT,
  "source_denominator_root":denominator["source_denominator_root"],"requirement_roots":reqs,"acceptance_case_roots":cases,
  "work_selection_roots":sels,"required_portability_legs":["WINDOWS_NATIVE","WSL_NATIVE"],
  "operator_tier1_status":"NOT_RUN","publication_authorized":False,**BOUNDARY},"program_root")
 payload["PROGRAM.json"]=program;return payload
def main():
 p=argparse.ArgumentParser();p.add_argument("--check",action="store_true");a=p.parse_args();payload=build()
 if a.check:
  for name,value in payload.items():
   if not (OUT/name).is_file() or (OUT/name).read_bytes()!=canonical(value)+b"\n":raise SystemExit("R031_PROGRAM_DRIFT:"+name)
 else:
  OUT.mkdir(parents=True,exist_ok=True)
  for name,value in payload.items():(OUT/name).write_bytes(canonical(value)+b"\n")
 print(json.dumps({"status":"PASS","program_root":payload["PROGRAM.json"]["program_root"],"records":len(payload)},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
