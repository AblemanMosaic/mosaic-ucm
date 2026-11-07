#!/usr/bin/env python3
"""Generate the checked-in P/PPI adaptive contracts from executable registries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "tools"))

from uclop.canonical import canonical_bytes, root
from release_common import ENGINEERING_REVISION
from ucm.pippi_adaptive import (ADAPTIVE_CLI_ROUTES, CAPSULE_PROFILES,
                                HOST_MODES, mediation_library,
                                pippi_shell_completion)
from ucm.system import BOUNDARY, capability_registry


def records():
    registry = capability_registry()
    owned_systems = {"PIPPI_MEDIATION", "PROCESS_GOVERNANCE",
                     "AGENT_WORKBENCH", "PORTABLE_BOOTSTRAP"}
    pippi = [row for row in registry["surfaces"]
             if row["system"] in owned_systems
             or row["name"] in ADAPTIVE_CLI_ROUTES]
    by_name = {row["name"]: row for row in pippi}
    missing = sorted(set(ADAPTIVE_CLI_ROUTES) - set(by_name))
    mismatched = sorted(name for name, command in ADAPTIVE_CLI_ROUTES.items()
                        if name in by_name
                        and by_name[name]["route"] != f"pippi {command}")
    if missing:
        raise ValueError("PIPPI_ADAPTIVE_SURFACE_MISSING:" + ",".join(missing))
    if mismatched:
        raise ValueError("PIPPI_ADAPTIVE_ROUTE_MISMATCH:" + ",".join(mismatched))
    surface_body = {"schema":"mosaic.ucm.pippi-capability-surface-registry.v0.1",
        "capability_registry_root":registry["root"], "surfaces":pippi,
        "rules":["ONE_REGISTRY_GENERATES_ABI_CLI_DOCS_AND_ADAPTERS",
                 "UNKNOWN_SURFACE_REFUSES", "PROFILES_ATTENUATE_ONLY",
                 "EFFECTS_REQUIRE_GOVERNED_GATEWAY"], **BOUNDARY}
    surface = {**surface_body, "surface_registry_root":root(surface_body)}
    ugk_body = {"schema":"mosaic.ucm.ugk-adaptive-profile.v0.1",
        "profile_id":"UGK_ADAPTIVE_CONTEXT", "runtime_status":"EXTERNAL_CANONICAL_RELEASE_NOT_EMBEDDED",
        "practices":[
            {"id":"FGA", "requirement":"EVERY_GOVERNED_TRANSITION_NAMES_PREDECESSOR_RULE_SUCCESSOR_AND_RECEIPT"},
            {"id":"THREE_HASH_RULE", "commitments":["STATE","MEANING","GOVERNANCE_ADMISSIBILITY","JURISDICTION_LOCALITY","RECEIPT_IDENTITY","WHOLE_BODY"]},
            {"id":"IEL", "requirement":"VALIDATE_BEFORE_MUTATE_CORRUPT_IS_NOT_MISSING_ATOMIC_STAGE_NO_UNCERTAIN_REDISPATCH"},
            {"id":"CK", "requirement":"CONSTITUTIONAL_CONTEXT_REMAINS_PORTABLE_ACROSS_HOSTS"},
            {"id":"CGP", "requirement":"CAPABILITY_EVIDENCE_AND_POSTURE_ARE_EXPLICIT"},
            {"id":"CLAIM_DISCIPLINE", "classes":["DESIGN","IMPLEMENTATION","EXECUTION_EVIDENCE","CONFORMANCE","DEPLOYMENT"]}],
        "canonical_runtime_required_for":["NATIVE_ENFORCED","FULL_REFERENCE","UGK_RECEIPT_CERTIFICATION"],
        "profile_does_not_grant_authority":True, **BOUNDARY}
    ugk = {**ugk_body, "ugk_profile_root":root(ugk_body)}
    library = mediation_library()
    cold_body = {"schema":"mosaic.ucm.pippi-adaptive-cold-boot-contract.v0.1",
        "version":"v0.1", "revision":ENGINEERING_REVISION, "host_modes":list(HOST_MODES),
        "profiles":list(CAPSULE_PROFILES), "capability_registry_root":registry["root"],
        "pippi_surface_registry_root":surface["surface_registry_root"],
        "mediation_library_root":library["mediation_library_root"],
        "ugk_profile_root":ugk["ugk_profile_root"],
        "required_directories":["BOOT","UCM","UGK","PIPPI","SKILLS","PROJECT","META","RETURN"],
        "secret_policy":"PUBLIC_MATERIAL_AND_OPAQUE_PROVIDER_REFERENCES_ONLY",
        "native_orchestration_status":"DEFERRED_FUTURE_REALIZATION",
        "web_execution_claim":"NEVER_INFERRED_FROM_ARTIFACT_ACCESS", **BOUNDARY}
    cold = {**cold_body, "cold_boot_contract_root":root(cold_body)}
    result = {
        ROOT / "spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json": surface,
        ROOT / "spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json": cold,
        ROOT / "vendor/ugk-adaptive-profile/UGK-ADAPTIVE-PROFILE.json": ugk,
        ROOT / "spec/PIPPI-MEDIATION-LIBRARY.json": library,
    }
    suffixes = {"bash":"bash", "zsh":"zsh", "fish":"fish", "powershell":"ps1"}
    for shell, suffix in suffixes.items():
        completion = pippi_shell_completion(shell)
        result[ROOT / f"completions/pippi.{suffix}.json"] = completion
        result[ROOT / f"completions/pippi.{suffix}"] = completion["script"]
    return result


def main():
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write",action="store_true");group.add_argument("--check",action="store_true")
    args=parser.parse_args(); failures=[]
    for path,value in records().items():
        raw=((value.rstrip("\n").encode("utf-8") if isinstance(value,str)
             else canonical_bytes(value))+b"\n")
        if args.write:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        elif not path.is_file() or path.read_bytes()!=raw:
            failures.append(path.relative_to(ROOT).as_posix())
    print(json.dumps({"status":"PASS" if not failures else "REFUSED",
                      "mismatches":failures,"records":len(records()),**BOUNDARY},sort_keys=True))
    return 0 if not failures else 3


if __name__=="__main__":raise SystemExit(main())
