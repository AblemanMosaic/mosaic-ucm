"""Prove exact headless behavior equivalence between full and ablated Mosaic UI."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .ablate import verify_slice
from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .probe import load_subject


WITNESS_SCHEMA = "mosaic.ui.ablation-equivalence-witness.v0.1"
RECEIPT_SCHEMA = "mosaic.ui.ablation-equivalence-receipt.v0.1"


class EquivalenceRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}")


WORKER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from mosaic_ui.headless import HeadlessUI, replay
from mosaic_ui.model import UIRefusal
data = json.load(sys.stdin)
payload, docket, layouts = data["payload"], data["docket"], data.get("layouts")
plans = {} if layouts is None else {(p["width"], p["height"]): {k: tuple(v) for k, v in p["rects"].items()} for p in layouts["plans"]}
rows = []
for scenario in docket["scenarios"]:
    viewports = scenario.get("viewports") or ([] if layouts is None else [{"width": p["width"], "height": p["height"]} for p in layouts["plans"]])
    if not viewports:
        raise ValueError("scenario has no viewport and no external layout plan")
    for viewport in viewports:
        width, height = viewport["width"], viewport["height"]
        plan = plans.get((width, height))
        provider = None if plan is None else lambda _w, _h, plan=plan: plan
        events = scenario.get("events", [])
        replay_result = replay(payload, provider, events)
        runtime = HeadlessUI(payload, provider)
        for event in events:
            try:
                runtime.apply(event)
            except UIRefusal:
                pass
        rows.append({
            "scenario_id": scenario["id"], "viewport": viewport,
            "replay": replay_result, "projection": runtime.project(width, height).as_dict(),
        })
result = {"rows": rows, "authority_effect": "NONE"}
print(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
'''


def _run(runtime_root: Path, payload: dict[str, Any], docket: dict[str, Any], layouts: dict[str, Any]) -> dict[str, Any]:
    value = {"payload": payload, "docket": docket, "layouts": layouts}
    run = subprocess.run(
        [sys.executable, "-B", "-I", "-c", WORKER, str(runtime_root)],
        input=json.dumps(value, ensure_ascii=True), capture_output=True, text=True, timeout=120,
    )
    if run.returncode != 0:
        raise EquivalenceRefusal("EQUIVALENCE_RUNTIME_REFUSED", run.stderr[-2000:])
    result = json.loads(run.stdout)
    result["commitment"] = commitment("MOSAIC.UI.ABLATION_EQUIVALENCE_EXECUTION.v0.1", result)
    return result


def run_equivalence(
    generated_dir: Path,
    docket_path: Path,
    layouts_path: Path | None,
    slice_archive: Path,
    output_dir: Path,
    full_runtime_root: Path | None = None,
) -> tuple[dict[str, Any], int]:
    payload, subject = load_subject(generated_dir.resolve())
    docket = read_json(docket_path)
    layouts = read_json(layouts_path) if layouts_path is not None else None
    if not isinstance(docket, dict) or not isinstance(docket.get("scenarios"), list):
        raise EquivalenceRefusal("EQUIVALENCE_DOCKET_REFUSED")
    if layouts is not None and (not isinstance(layouts, dict) or not isinstance(layouts.get("plans"), list)):
        raise EquivalenceRefusal("EQUIVALENCE_LAYOUTS_REFUSED")
    verification = verify_slice(slice_archive.resolve())
    source_root = (full_runtime_root or Path(__file__).resolve().parent.parent).resolve()
    full_result = _run(source_root, payload, docket, layouts)
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-equivalence-") as raw:
        with zipfile.ZipFile(slice_archive) as archive:
            archive.extractall(raw)
        slice_result = _run(Path(raw), payload, docket, layouts)
    equivalent = canonical_bytes(full_result["rows"]) == canonical_bytes(slice_result["rows"])
    witness = {
        "schema": WITNESS_SCHEMA,
        "subject": subject,
        "slice_verification": verification,
        "docket_root": commitment("MOSAIC.UI.PROBE_DOCKET.v0.1", docket),
        "layouts_root": commitment("MOSAIC.UI.PROBE_LAYOUTS.v0.1", layouts) if layouts is not None else None,
        "layout_mode": "EXTERNAL_FIXTURE" if layouts is not None else "DETERMINISTIC_TREE_LAYOUT",
        "full_execution": full_result,
        "slice_execution": slice_result,
        "exact_equivalence": equivalent,
        "scenario_projection_count": len(full_result["rows"]),
        "disposition": "PASS_LOCAL_CANDIDATE" if equivalent else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "HEADLESS_EQUIVALENCE_DOES_NOT_ESTABLISH_NATIVE_HOST_EQUIVALENCE_OR_AUTHORITY",
    }
    witness["witness_commitment"] = commitment("MOSAIC.UI.ABLATION_EQUIVALENCE_WITNESS.v0.1", witness)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "witness_commitment": witness["witness_commitment"],
        "profile_root": verification["profile_root"],
        "generated_root": subject["generated_root"],
        "scenario_projection_count": witness["scenario_projection_count"],
        "exact_equivalence": equivalent,
        "disposition": witness["disposition"],
        "authority_effect": "NONE",
    }
    receipt["receipt_commitment"] = commitment("MOSAIC.UI.ABLATION_EQUIVALENCE_RECEIPT.v0.1", receipt)
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(output_dir / "ablation-equivalence-witness.json", canonical_bytes(witness) + b"\n")
    atomic_write(output_dir / "ablation-equivalence-receipt.json", canonical_bytes(receipt) + b"\n")
    return receipt, 0 if equivalent else 32


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generated", type=Path)
    parser.add_argument("--docket", type=Path, required=True)
    parser.add_argument("--layouts", type=Path)
    parser.add_argument("--slice", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--full-runtime-root", type=Path)
    args = parser.parse_args(argv)
    try:
        receipt, code = run_equivalence(
            args.generated, args.docket, args.layouts, args.slice, args.output, args.full_runtime_root,
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return code
    except (EquivalenceRefusal, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "schema": "mosaic.ui.ablation-equivalence-refusal.v0.1",
            "disposition": "REFUSE", "refusal_code": getattr(exc, "code", "EQUIVALENCE_INPUT_REFUSED"),
            "detail": getattr(exc, "detail", str(exc)), "authority_effect": "NONE",
        }, indent=2, sort_keys=True))
        return 32


if __name__ == "__main__":
    raise SystemExit(main())
