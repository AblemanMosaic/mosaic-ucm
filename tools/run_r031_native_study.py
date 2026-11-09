#!/usr/bin/env python3
"""Build and measure the bounded r031 native verification slice."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from uclop.canonical import canonical_bytes,root  # noqa:E402
from ucm.transtemporal_archive import (build_native_manifest,ingest_tree,
    materialize_revision,verify_revision)  # noqa:E402

BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}

def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);parser.add_argument("--iterations",type=int,default=32)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    compiler=shutil.which("gcc")
    if compiler is None: raise SystemExit("NATIVE_C_COMPILER_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="ucm-r031-native-",dir=out) as raw:
        base=Path(raw);source=base/"source";archive=base/"archive";restored=base/"restored";source.mkdir()
        # A deterministic mixed-size fixture makes interpreter overhead visible
        # without pretending to benchmark a complete application workload.
        for index in range(256):
            (source/f"F{index:06d}.bin").write_bytes(hashlib.sha256(str(index).encode()).digest()*(index%17+1))
        ingest=ingest_tree(source=source,repository=archive,revision="r031",
            semantic_root=root({"fixture":"native-study"}),governance_root=root({"policy":"r031"}),
            jurisdiction_root=root({"jurisdiction":"information-only"}))
        materialize_revision(repository=archive,revision="r031",destination=restored)
        manifest=base/"NATIVE-MANIFEST.tsv";manifest.write_bytes(build_native_manifest(repository=archive,revision="r031"))
        executable=base/("ucm-archive-verify.exe" if os.name=="nt" else "ucm-archive-verify")
        compile_result=subprocess.run([compiler,"-std=c11","-O2","-Wall","-Wextra","-Werror",
            str(ROOT/"native/ucm_archive_verify.c"),"-o",str(executable)],capture_output=True,text=True)
        if compile_result.returncode: sys.stderr.write(compile_result.stderr);raise SystemExit("NATIVE_C_BUILD_FAILED")
        native_start=time.perf_counter_ns();native_output=None
        for _ in range(args.iterations):
            run=subprocess.run([str(executable),str(manifest),str(restored)],capture_output=True,text=True)
            if run.returncode: sys.stderr.write(run.stderr);raise SystemExit("NATIVE_C_VERIFY_FAILED")
            native_output=json.loads(run.stdout)
        native_ns=time.perf_counter_ns()-native_start
        python_start=time.perf_counter_ns()
        for _ in range(args.iterations): verify_revision(repository=archive,revision="r031")
        python_ns=time.perf_counter_ns()-python_start
        body={"schema":"mosaic.ucm.r031-native-study.v0.1","status":"PASS","scope":"BOUNDED_SHA256_COMPATIBILITY_PROJECTION",
            "compiler":Path(compiler).name,"iterations":args.iterations,"files":native_output["checked"],
            "native_elapsed_ns":native_ns,"reference_elapsed_ns":python_ns,
            "native_to_reference_ratio_ppm":native_ns*1_000_000//python_ns,
            "manifest_sha256":hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "revision_manifest_root":ingest["MANIFEST.json"]["manifest_root"],
            "nonclaims":["NOT_FULL_UCM_EQUIVALENCE","NOT_BLAKE3_VERIFICATION","NOT_AUTHORITY"],**BOUNDARY}
        record={**body,"study_root":root(body)}
        (out/"R031-NATIVE-STUDY.json").write_bytes(canonical_bytes(record)+b"\n")
        print(json.dumps(record,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
