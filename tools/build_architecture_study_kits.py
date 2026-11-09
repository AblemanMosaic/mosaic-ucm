"""Build isolated, deterministic run kits for the architecture study.

This packages exact inputs. It does not invoke a model, score a result, or make a
benefit claim.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.evaluation import (build_run_roster, validate_execution_context_registration,
                            validate_study_protocol)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path):
    return strict_loads(path.read_bytes())


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_run_kits(workspace: Path, output: Path,
                   execution_context: dict | None = None) -> dict:
    protocol = validate_study_protocol(_load(workspace / "evaluation" / "ARCHITECTURE-COMPLIANCE-STUDY.json"))
    if execution_context is None:
        raise ValueError("STUDY_EXECUTION_CONTEXT_REGISTRATION_REQUIRED")
    registered = validate_execution_context_registration(protocol, execution_context)
    roster = build_run_roster(protocol)
    task_dir = workspace / "evaluation" / "tasks" / "reference-data-client"
    task = _load(task_dir / "TASK.json")
    contexts = _load(task_dir / "ARM-CONTEXTS.json")
    oversight = _load(workspace / "evaluation" / "HUMAN-OVERSIGHT-POLICY.json")
    subject_raw = (task_dir / "SUBJECT.zip").read_bytes()
    follow_on_raw = (task_dir / "FOLLOW-ON-TASK.md").read_bytes()
    if _sha(follow_on_raw) != protocol["follow_on_task_root"]:
        raise SystemExit("STUDY_FOLLOW_ON_TASK_PIN_MISMATCH")
    verify_deterministic_zip(subject_raw,
        expected_schema="mosaic.ucm.architecture-study-subject-archive.v0.1",
        expected_role="ARCHITECTURE_STUDY_SUBJECT")
    if _sha(subject_raw) != task["subject_archive_sha256"]:
        raise SystemExit("STUDY_SUBJECT_ARCHIVE_PIN_MISMATCH")
    if task["task_root"] != next(row["task_root"] for row in protocol["tasks"]
                                  if row["task_id"] == task["task_id"]):
        raise SystemExit("STUDY_TASK_PROTOCOL_MISMATCH")
    contexts_by_arm = {row["arm_id"]: row for row in contexts["arms"]}
    output.mkdir(parents=True, exist_ok=True)
    inventory_rows = []
    for run in roster["runs"]:
        arm = contexts_by_arm[run["arm_id"]]
        if arm["context_root"] != next(row["context_root"] for row in protocol["arms"]
                                        if row["arm_id"] == run["arm_id"]):
            raise SystemExit("STUDY_ARM_CONTEXT_MISMATCH")
        oversight_root = next(row["human_oversight_policy_root"]
            for row in protocol["arms"] if row["arm_id"] == run["arm_id"])
        if arm["treatment_contract_root"] != next(
                row["treatment_contract_root"] for row in protocol["arms"]
                if row["arm_id"] == run["arm_id"]):
            raise SystemExit("STUDY_TREATMENT_CONTRACT_MISMATCH")
        assignment_body = {
            "schema": "mosaic.ucm.architecture-study-assignment.v0.2",
            "run_id": run["run_id"], "task_root": run["task_root"],
            "repetition": run["repetition"],
            "condition_context_root": arm["context_root"],
            "human_oversight_policy_root": oversight_root,
            "treatment_contract_root": arm["treatment_contract_root"],
            "context_registration_root": registered["registration_root"],
            "follow_on_task_root": protocol["follow_on_task_root"],
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED",
        }
        assignment = {**assignment_body, "assignment_root": root(assignment_body)}
        condition = {"schema": "mosaic.ucm.architecture-study-condition.v0.2",
                     "context": arm["context"], "context_root": arm["context_root"],
                     "treatment": arm["treatment"],
                     "treatment_contract_root": arm["treatment_contract_root"]}
        output_template = {
            "schema": "mosaic.ucm.architecture-study-raw-run-output.v0.3",
            "run_id": run["run_id"], "task_root": run["task_root"],
            "model_id_root": registered["model_id_root"],
            "model_settings_root": registered["model_settings_root"],
            "executor_session_root": "<64-lowercase-hex>",
            "environment_root": registered["environment_root"],
            "toolchain_root": registered["toolchain_root"],
            "execution_context_root": "<derive-from-five-context-roots>",
            "output_root": "<64-lowercase-hex>",
            "actions_root": "<64-lowercase-hex>",
            "tests_root": "<64-lowercase-hex>",
            "follow_on_result_root": "<64-lowercase-hex>",
            "context_registration_root": registered["registration_root"],
            "elapsed_seconds": 0, "notes": [],
            "output_record_root": "<derive-after-completion>",
        }
        readme = ("UCM architecture-compliance study executor kit\n"
                  f"Run ID: {run['run_id']}\n"
                  "This kit intentionally omits the arm label, other conditions, and scoring rubric.\n"
                  "Record the exact model settings, unique executor session, environment, and toolchain roots.\n"
                  "Do not infer authority or a study conclusion from this package.\n").encode("utf-8")
        payloads = {
            "ASSIGNMENT.json": canonical_bytes(assignment),
            "TASK.json": canonical_bytes(task),
            "SUBJECT.zip": subject_raw,
            "TASK-PROMPT.md": (task_dir / "TASK-PROMPT.md").read_bytes(),
            "CONDITION-CONTEXT.json": canonical_bytes(condition),
            "HUMAN-OVERSIGHT-POLICY.json": canonical_bytes(oversight),
            "EXECUTION-CONTEXT-REGISTRATION.json": canonical_bytes(registered),
            "FOLLOW-ON-TASK.md": follow_on_raw,
            "RUN-OUTPUT.template.json": canonical_bytes(output_template),
            "README.txt": readme,
            "VERIFY.py": (workspace / "VERIFY.py").read_bytes(),
        }
        if run["arm_id"] in {"CONVENTIONAL_ENFORCEMENT", "UCM_GOVERNED"}:
            payloads["ARCHITECTURE-CONTRACT.json"] = (
                task_dir / "ARCHITECTURE-CONTRACT.json").read_bytes()
        if run["arm_id"] == "UCM_GOVERNED":
            payloads["UCM-ARCHITECTURE-POLICY-PACK.json"] = (
                workspace / "policy-packs" / "ARCHITECTURE-FIDELITY-v0.1.json").read_bytes()
            payloads["UCM-EFFECT-POLICY-PACK.json"] = (
                workspace / "policy-packs" / "THREE-GATE-EFFECTS-v0.1.json").read_bytes()
        raw = deterministic_zip(payloads,
            schema="mosaic.ucm.architecture-study-run-kit.v0.1",
            artifact_role="ARCHITECTURE_STUDY_RUN_KIT")
        name = f"RUN-{run['run_id']}.zip"
        (output / name).write_bytes(raw)
        inventory_rows.append({"run_id": run["run_id"], "task_id": run["task_id"],
            "arm_id": run["arm_id"], "repetition": run["repetition"],
            "archive": name, "bytes": len(raw), "sha256": _sha(raw)})
    inventory_body = {"schema": "mosaic.ucm.architecture-study-kit-inventory.v0.2",
        "study_root": protocol["study_root"], "roster_root": roster["roster_root"],
        "context_registration_root": registered["registration_root"],
        "follow_on_task_root": protocol["follow_on_task_root"],
        "denominator": roster["denominator"], "runs": inventory_rows,
        "status": "READY_NOT_EXECUTED", "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED",
        "non_claims": ["NO_MODEL_EXECUTION", "NO_STUDY_RESULT", "NO_BENEFIT_CLAIM"]}
    inventory = {**inventory_body, "inventory_root": root(inventory_body)}
    inventory_raw = canonical_bytes(inventory)
    roster_raw = canonical_bytes(roster)
    (output / "STUDY-KIT-INVENTORY.json").write_bytes(inventory_raw)
    (output / "STUDY-ROSTER.json").write_bytes(roster_raw)
    package_payloads = {
        "STUDY-KIT-INVENTORY.json": inventory_raw,
        "STUDY-ROSTER.json": roster_raw,
        "STUDY-PROTOCOL.json": canonical_bytes(protocol),
        "ARM-CONTEXTS.json": canonical_bytes(contexts),
        "SCORING-RUBRIC.json": (task_dir / "SCORING-RUBRIC.json").read_bytes(),
        "ARCHITECTURE-CONTRACT.json": (task_dir / "ARCHITECTURE-CONTRACT.json").read_bytes(),
        "HUMAN-OVERSIGHT-POLICY.json": canonical_bytes(oversight),
        "EXECUTION-CONTEXT-REGISTRATION.json": canonical_bytes(registered),
        "FOLLOW-ON-TASK.md": follow_on_raw,
        "VERIFY.py": (workspace / "VERIFY.py").read_bytes(),
        "README.txt": ("UCM architecture-compliance study C3 run kits\n"
                       "Six isolated registered runs; no model execution or result.\n"
                       "Verify this package and each nested kit before assignment.\n"
                       "Give an executor only its nested run kit; retain coordinator files separately.\n").encode("ascii"),
    }
    for row in inventory_rows:
        package_payloads["runs/" + row["archive"]] = (output / row["archive"]).read_bytes()
    package = deterministic_zip(package_payloads,
        schema="mosaic.ucm.architecture-study-package.v0.1",
        artifact_role="ARCHITECTURE_STUDY_PACKAGE")
    (output / "UCM-ARCHITECTURE-STUDY-C3-RUN-KITS.zip").write_bytes(package)
    return inventory


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-context", type=Path, required=True,
                        help="pre-registered exact model/settings/environment/toolchain roots")
    args = parser.parse_args()
    print(canonical_bytes(build_run_kits(args.workspace.resolve(), args.output.resolve(),
        _load(args.execution_context.resolve()))).decode())
