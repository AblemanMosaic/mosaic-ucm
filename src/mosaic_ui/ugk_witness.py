"""Consumer-owned UGK HeadlessRunner witness adapter for Mosaic probe outputs."""
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .model import UIRefusal
from .probe import load_subject, run_probe


class UGKWitnessRefusal(UIRefusal):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_runner(ugk_root: Path) -> tuple[Any, Any, Any, dict]:
    release = ugk_root / "RELEASE.txt"
    runner_module = ugk_root / "ugk" / "cgp" / "runner" / "__init__.py"
    if not release.is_file() or not runner_module.is_file():
        raise UGKWitnessRefusal("UGK_RELEASE_ROOT_REFUSED", str(ugk_root))
    existing = sys.modules.get("ugk")
    if existing is not None and not str(getattr(existing, "__file__", "")).startswith(str(ugk_root)):
        raise UGKWitnessRefusal("UGK_MODULE_IDENTITY_CONFLICT", str(getattr(existing, "__file__", "")))
    sys.path.insert(0, str(ugk_root))
    module = importlib.import_module("ugk.cgp.runner")
    identity = {
        "release_root": str(ugk_root.resolve()),
        "release_txt_sha256": _sha256(release),
        "runner_module_sha256": _sha256(runner_module),
        "declared_release": "ugk-v0.2.0-r178-CONSTITUTIONAL-RELEASE",
    }
    return module.HeadlessRunner, module.CGPRunner, module.EvidenceArtifact, identity


def _result_dict(value: Any) -> dict:
    return dataclasses.asdict(value) if dataclasses.is_dataclass(value) else dict(value)


def run_ugk_witness(
    generated_dir: Path,
    docket_path: Path,
    layout_path: Path,
    output_dir: Path,
    ugk_root: Path,
    evidence_paths: tuple[Path, ...] = (),
) -> tuple[dict, int]:
    HeadlessRunner, CGPRunner, EvidenceArtifact, ugk_identity = _load_runner(ugk_root.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    probe_output = output_dir / "mosaic-probe"
    state: dict[str, Any] = {}

    def subject_integrity(kernel: Any) -> None:
        _, subject = load_subject(generated_dir)
        state["subject"] = subject
        kernel.execute(
            op="crp_evidence",
            authority="headless_runner",
            parameters={
                "instrument": "mosaic_ui.subject_integrity",
                "subject_commitment": subject["commitment"],
                "generated_root": subject["generated_root"],
                "authority_effect": "NONE",
            },
        )

    def probe_suite(kernel: Any) -> None:
        receipt, code = run_probe(generated_dir, docket_path, layout_path, probe_output)
        state["probe_receipt"] = receipt
        if code != 0:
            raise AssertionError(f"Mosaic probe refused with code {code}")
        kernel.execute(
            op="crp_evidence",
            authority="headless_runner",
            parameters={
                "instrument": "mosaic_ui.probe_suite",
                "probe_receipt_commitment": receipt["receipt_commitment"],
                "witness_commitment": receipt["witness_commitment"],
                "passed": receipt["passed"],
                "failed": receipt["failed"],
                "authority_effect": "NONE",
            },
        )

    scenarios: list[Any] = [subject_integrity, probe_suite]
    scenario_specs = [
        ("MOSAIC-UI-SUBJECT-INTEGRITY", "subject-integrity"),
        ("MOSAIC-UI-PROBE-SUITE", "scenario-sweep"),
    ]
    supplemental: list[dict[str, Any]] = []
    domains = {
        "mosaic.ui.visual-regression-receipt.v0.1": ("receipt_commitment", "MOSAIC.UI.VISUAL_REGRESSION_RECEIPT.v0.1"),
        "mosaic.ui.win32-catalog-choice-witness.v0.1": ("commitment", "MOSAIC.UI.WIN32_CATALOG_CHOICE_WITNESS.v0.1"),
        "mosaic.ui.semantic-demo-witness.v0.1": ("commitment", "MOSAIC.UI.SEMANTIC_DEMO_WITNESS.v0.1"),
        "mosaic.ui.native-conformance-witness.v0.1": ("commitment", "MOSAIC.UI.NATIVE_CONFORMANCE_WITNESS.v0.1"),
        "mosaic.ui.win32-25-kind-sufficiency-witness.v0.1": (
            "commitment", "MOSAIC.UI.WIN32_25_KIND_SUFFICIENCY.v0.1",
        ),
        "mosaic.ui.browser-engine-acceptance.v0.1": (
            "commitment", "MOSAIC.UI.BROWSER_ENGINE_ACCEPTANCE.v0.1",
        ),
        "mosaic.ui.browser-session-custody-evidence.v0.1": (
            "commitment", "MOSAIC.UI.BROWSER_SESSION_CUSTODY_EVIDENCE.v0.1",
        ),
        "mosaic.ui.signature-profile-witness.v0.1": (
            "commitment", "MOSAIC.UI.SIGNATURE_PROFILE_WITNESS.v0.1",
        ),
        "mosaic.ui.win32-signature-profile-witness.v0.1": (
            "commitment", "MOSAIC.UI.WIN32_SIGNATURE_PROFILE_WITNESS.v0.1",
        ),
        "mosaic.ui.ablation-receipt.v0.1": ("receipt_commitment", "MOSAIC.UI.ABLATION_RECEIPT.v0.1"),
        "mosaic.ui.ablation-equivalence-receipt.v0.1": (
            "receipt_commitment", "MOSAIC.UI.ABLATION_EQUIVALENCE_RECEIPT.v0.1",
        ),
        "mosaic.ui.application-build-receipt.v0.1": (
            "commitment", "MOSAIC.UI.APPLICATION_BUILD_RECEIPT.v0.1",
        ),
        "mosaic.ui.visual-pixel-witness.v0.1": (
            "commitment", "MOSAIC.UI.VISUAL_PIXEL_WITNESS.v0.1",
        ),
        "mosaic.ui.release-receipt.v0.1": (
            "receipt_commitment", "MOSAIC.UI.RELEASE_RECEIPT.v0.1",
        ),
        "mosaic.ui.performance-evidence.v0.1": (
            "commitment", "MOSAIC.UI.PERFORMANCE_EVIDENCE.v0.1",
        ),
        "mosaic.ui.architecture-readiness-evidence.v0.1": (
            "commitment", "MOSAIC.UI.ARCHITECTURE_READINESS_EVIDENCE.v0.1",
        ),
        "mosaic.ui.review-experience-audit.v0.1": (
            "commitment", "MOSAIC.UI.REVIEW_EXPERIENCE_AUDIT.v0.1",
        ),
        "mosaic.ui.review-headless-runner-witness.v0.1": (
            "commitment", "MOSAIC.UI.REVIEW_HEADLESS_RUNNER_WITNESS.v0.1",
        ),
        "mosaic.ui.signature-visual-witness.v0.1": (
            "commitment", "MOSAIC.UI.SIGNATURE_VISUAL_WITNESS.v0.1",
        ),
    }
    for index, evidence_path in enumerate(evidence_paths, 1):
        evidence_path = evidence_path.resolve()
        evidence = read_json(evidence_path)
        if not isinstance(evidence, dict) or evidence.get("schema") not in domains:
            raise UGKWitnessRefusal("UGK_SUPPLEMENTAL_EVIDENCE_SCHEMA_REFUSED", str(evidence_path))
        field, domain = domains[evidence["schema"]]
        body = copy.deepcopy(evidence)
        observed = body.pop(field, None)
        if observed != commitment(domain, body):
            raise UGKWitnessRefusal("UGK_SUPPLEMENTAL_EVIDENCE_COMMITMENT_REFUSED", str(evidence_path))
        if evidence.get("authority_effect") != "NONE" or evidence.get("disposition") != "PASS_LOCAL_CANDIDATE":
            raise UGKWitnessRefusal("UGK_SUPPLEMENTAL_EVIDENCE_DISPOSITION_REFUSED", str(evidence_path))
        descriptor = {
            "schema": evidence["schema"], "evidence_commitment": observed,
            "file_sha256": _sha256(evidence_path), "file_name": evidence_path.name,
        }
        supplemental.append(descriptor)

        def supplemental_scenario(kernel: Any, descriptor=descriptor) -> None:
            kernel.execute(
                op="crp_evidence", authority="headless_runner",
                parameters={"instrument": "mosaic_ui.supplemental_evidence", **descriptor,
                            "authority_effect": "NONE"},
            )

        supplemental_scenario.__name__ = f"supplemental_evidence_{index}"
        scenarios.append(supplemental_scenario)
        scenario_specs.append((f"MOSAIC-UI-SUPPLEMENTAL-{index}", evidence["schema"]))

    runner = HeadlessRunner(authority="headless_runner")
    protocol_conformant = isinstance(runner, CGPRunner)
    profile = runner.make_epistemic_profile("mosaic-ui-consumer-witness", ["gate_admit", "crp_evidence"])
    batch = runner.run_batch(scenarios, profile=profile)
    scenario_results = [_result_dict(item) for item in batch.scenario_results]
    artifacts = []
    for (invariant, evidence_class), result in zip(scenario_specs, batch.scenario_results):
        artifact = EvidenceArtifact(
            invariant=invariant,
            verdict="PROVEN" if result.passed else "FAIL",
            evidence_class=evidence_class,
            details=f"UGK receipt_delta={result.receipt_delta}; anomaly_score={result.anomaly_score}",
            scenario_result=result,
        )
        artifacts.append(_result_dict(artifact))

    passed = protocol_conformant and all(item.passed for item in batch.scenario_results)
    witness = {
        "schema": "mosaic.ui.ugk-headless-witness.v0.1",
        "ugk": ugk_identity,
        "runner": {
            "canonical_import": "ugk.cgp.runner.HeadlessRunner",
            "protocol_conformant": protocol_conformant,
            "pattern": "A_SCENARIO_EXECUTION_CHECKPOINT_RECEIPTS",
        },
        "subject": state.get("subject"),
        "mosaic_probe_receipt": state.get("probe_receipt"),
        "supplemental_evidence": supplemental,
        "scenario_results": scenario_results,
        "evidence_artifacts": artifacts,
        "receipt_observability": {
            "receipt_delta": batch.total_receipt_delta,
            "checkpoint_hashes": list(batch.checkpoint_hashes),
            "final_stream_hash": batch.final_stream_hash,
            "stream_hash_verified": runner.verify_stream_hash(),
        },
        "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "standing_effect": "NONE",
        "authority_effect": "NONE",
        "native_evs_runtime_claimed": False,
        "native_cop_runtime_claimed": False,
        "claim_boundary": "CONSUMER_OWNED_EVS_COP_SHAPED_WITNESS_OVER_UGK_RUNNER_NOT_KERNEL_NATIVE_EVS_OR_COP",
        "nonclaims": [
            "CONSTITUTIONAL_ADMISSION_NOT_CLAIMED",
            "UGK_NATIVE_EVS_RUNTIME_NOT_CLAIMED",
            "UGK_NATIVE_COP_RUNTIME_NOT_CLAIMED",
            "HOST_DESKTOP_BEHAVIOR_NOT_ESTABLISHED_BY_HEADLESS_RUN",
        ],
    }
    witness["witness_commitment"] = commitment("MOSAIC.UI.UGK_HEADLESS_WITNESS.v0.1", witness)
    receipt = {
        "schema": "mosaic.ui.ugk-headless-witness-receipt.v0.1",
        "witness_commitment": witness["witness_commitment"],
        "generated_root": (state.get("subject") or {}).get("generated_root"),
        "ugk_release_txt_sha256": ugk_identity["release_txt_sha256"],
        "scenario_count": len(scenario_results),
        "passed": sum(1 for item in batch.scenario_results if item.passed),
        "failed": sum(1 for item in batch.scenario_results if not item.passed),
        "final_stream_hash": batch.final_stream_hash,
        "disposition": witness["disposition"],
        "authority_effect": "NONE",
    }
    receipt["receipt_commitment"] = commitment("MOSAIC.UI.UGK_HEADLESS_WITNESS_RECEIPT.v0.1", receipt)
    atomic_write(output_dir / "ugk-headless-witness.json", canonical_bytes(witness) + b"\n")
    atomic_write(output_dir / "ugk-headless-witness-receipt.json", canonical_bytes(receipt) + b"\n")
    return receipt, 0 if passed else 32


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Mosaic evidence through the canonical UGK HeadlessRunner.")
    parser.add_argument("generated", type=Path)
    parser.add_argument("--docket", type=Path, required=True)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ugk-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, action="append", default=[],
                        help="Committed PASS visual/native/semantic evidence to add as UGK scenarios")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt, code = run_ugk_witness(
            args.generated.resolve(), args.docket.resolve(), args.layouts.resolve(),
            args.output.resolve(), args.ugk_root.resolve(), tuple(path.resolve() for path in args.evidence),
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return code
    except (UGKWitnessRefusal, UIRefusal, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "schema": "mosaic.ui.ugk-headless-witness-refusal.v0.1",
            "disposition": "REFUSE",
            "refusal_code": getattr(exc, "code", "UGK_WITNESS_INPUT_OR_IO_REFUSED"),
            "detail": getattr(exc, "detail", str(exc)),
            "effects_performed": [],
            "authority_effect": "NONE",
        }, indent=2, sort_keys=True))
        return 32


if __name__ == "__main__":
    raise SystemExit(main())
