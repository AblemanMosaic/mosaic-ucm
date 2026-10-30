#!/usr/bin/env python3
"""Slim agentic-adaptation entry point used beside an exact UCM core."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
ALLOWED = {
    "orient", "capabilities", "validate-realization", "check-realization",
    "select-realization", "validate-amcas", "compile-amcas", "campaign-init",
    "campaign-status", "campaign-challenge", "campaign-authenticate",
    "operation-plan", "operation-witness", "operation-diagnostic",
    "requirement-disposition", "campaign-export", "build-integration-kit",
    "verify-integration-archive", "campaign-import-report", "campaign-plan",
    "integration-bind-subject", "integration-check-control-planes",
    "integration-correspondence-court", "integration-verify-stage1",
    "integration-upgrade-stage1", "portfolio-init", "portfolio-record-intake",
    "portfolio-record-instruction", "portfolio-import-stage1",
    "portfolio-import-stage2", "portfolio-status", "portfolio-campaign-preflight",
    "portfolio-composition-template", "portfolio-composition-preflight",
    "portfolio-issue-stage3-instructions", "portfolio-import-stage3-plan",
    "stage3-validate-plan", "stage4-derive-eligibility",
    "stage4-validate-run-contract", "stage4-validate-observation",
    "stage4-c3-derive-eligibility", "stage4-c3-build-run-contract",
    "stage4-c3-build-terminal-refusal",
}


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def verify_core(core: Path) -> dict:
    core = core.resolve()
    contract_path = Path(__file__).resolve().with_name("SIDECAR-CONTRACT.json")
    registry_path = core / "spec" / "ucm-system-registry.json"
    tool = core / "tools" / "ucm.py"
    if not contract_path.is_file() or not registry_path.is_file() or not tool.is_file():
        raise ValueError("ADAPT_UCM_CORE_INCOMPLETE")
    contract = json.loads(contract_path.read_bytes())
    contract_body = {key: value for key, value in contract.items()
                     if key != "contract_root"}
    if contract.get("contract_root") != hashlib.sha256(canonical(contract_body)).hexdigest():
        raise ValueError("ADAPT_SIDECAR_CONTRACT_INVALID")
    expected_system = contract.get("required_ucm_system_registry_root")
    expected_capabilities = contract.get("required_ucm_capability_registry_root")
    registry = json.loads(registry_path.read_bytes())
    body = {key: value for key, value in registry.items() if key != "root"}
    observed = hashlib.sha256(canonical(body)).hexdigest()
    if registry.get("root") != observed or observed != expected_system:
        raise ValueError("ADAPT_UCM_SYSTEM_REGISTRY_MISMATCH")
    if registry.get("capability_registry_root") != expected_capabilities:
        raise ValueError("ADAPT_UCM_CAPABILITY_REGISTRY_MISMATCH")
    if {key: registry.get(key) for key in BOUNDARY} != BOUNDARY:
        raise ValueError("ADAPT_UCM_AUTHORITY_CEILING_MISMATCH")
    return {"status": "PASS", "ucm_root": str(core),
            "system_registry_root": observed,
            "capability_registry_root": expected_capabilities, **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser(description="UCM-AMCAS agentic adaptation sidecar")
    parser.add_argument("--ucm-root", type=Path, required=True)
    parser.add_argument("command", choices=["sidecar-orient", "verify-core", "ucm"])
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        core = verify_core(args.ucm_root)
        if args.command == "verify-core":
            result = core
        elif args.command == "sidecar-orient":
            result = {"status": "PASS", "role": "AGENTIC_ADAPTATION_SIDECAR",
                      "next": ["verify-core", "ucm orient", "ucm capabilities",
                               "ucm validate-amcas", "ucm compile-amcas"],
                      "stage_order": ["SUBJECT", "CONTROL_PLANES", "AMCAS", "SHADOW",
                                      "STAGE_I1", "STAGE_I2", "CORRESPONDENCE",
                                      "STAGE_I3_PLANNING"],
                      "proof_rule": "JOURNAL_AND_BOUND_RECEIPTS_ONLY",
                      "ucm": core, **BOUNDARY}
        else:
            if not args.arguments or args.arguments[0] not in ALLOWED:
                raise ValueError("ADAPT_UCM_COMMAND_NOT_ALLOWED")
            started = time.monotonic()
            try:
                print(json.dumps({"progress": "START", "command": args.arguments[0]}),
                      file=sys.stderr, flush=True)
            except (OSError, UnicodeError):
                pass
            completed = subprocess.run(
                [sys.executable, "-B", str(Path(core["ucm_root"]) / "tools" / "ucm.py"),
                 *args.arguments], check=False)
            try:
                print(json.dumps({"progress": "COMPLETE", "command": args.arguments[0],
                                  "exit_code": completed.returncode,
                                  "elapsed_ms": round((time.monotonic() - started) * 1000)}),
                      file=sys.stderr, flush=True)
            except (OSError, UnicodeError):
                pass
            return completed.returncode
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "REFUSED", "diagnostic": str(error), **BOUNDARY},
                         sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
