"""Run a deterministic, no-effect Pippi reference campaign with live progress."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.pippi import (build_constitutional_exception, build_human_projection,
    build_model_draft, build_pippi_context, build_pippi_decision, build_turn_envelope)
from ucm.pippi_runtime import PippiCampaign, validate_pippi_campaign_workspace
from ucm.progress import Progress


def h(label: str) -> str:
    return root({"reference_label": label})


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def run(out: Path, progress_path: Path | None = None) -> dict:
    if out.exists():
        raise ValueError("PIPPI_REFERENCE_OUTPUT_EXISTS")
    progress = Progress(progress_path)
    progress.emit("PHASE_START", phase="CONTEXT")
    context = build_pippi_context(session_root=h("reference-session"),
        subject_root=h("reference-subject"), policy_roots=[h("development-policy")],
        capability_registry_root=h("capability-registry"), profile_root=h("authoring-profile"),
        jurisdiction_root=h("unbound-jurisdiction"), retained_context_roots=[],
        mediated_channels=["MODEL_DRAFT", "MODEL_INPUT", "TOOL_PROPOSAL", "VISIBLE_OUTPUT"])
    campaign = PippiCampaign.create(out / "campaign", context)
    progress.emit("PHASE_PASS", phase="CONTEXT", integration_mode=context["integration_mode"])

    progress.emit("PHASE_START", phase="DRAFT_AND_POLICY")
    draft = build_model_draft(turn_id="REFERENCE.TURN.1", context=context,
        text="The repair is prepared. Workspace writing remains held until a declared effect contract exists.",
        proposals=[
            {"proposal_id": "P.TEXT", "kind": "TEXT", "payload_root": h("visible-text"),
             "effect_class": "NONE"},
            {"proposal_id": "P.WRITE", "kind": "TOOL_CALL", "payload_root": h("write-request"),
             "effect_class": "WRITE_WORKSPACE"},
        ])
    decision = build_pippi_decision(draft=draft, policy_evaluation_roots=[h("policy-evaluation")],
        proposal_dispositions=[
            {"proposal_id": "P.TEXT", "declared": False, "effectful": False,
             "decision": "PASS", "reason_codes": [], "contract_root": None},
            {"proposal_id": "P.WRITE", "declared": False, "effectful": True,
             "decision": "HELD", "reason_codes": ["CONSTITUTIONAL_GAP"], "contract_root": None},
        ], semantic_resolution_root=None, semantic_status="NOT_REQUIRED")
    projection = build_human_projection(draft=draft, decision=decision, view="READING")
    exception = build_constitutional_exception(draft_root=draft["draft_root"],
        proposal_id="P.WRITE", missing_rule_id="EFFECT.WRITE_WORKSPACE",
        requested_decision="BIND_OR_REFUSE",
        affected_obligation_ids=["PIPPI.UNDECLARED_EFFECT_HELD"])
    progress.emit("PHASE_PASS", phase="DRAFT_AND_POLICY", decision=decision["status"])

    progress.emit("PHASE_START", phase="JOURNAL")
    turn = build_turn_envelope(sequence=1, previous_turn_root=None, context=context,
        draft=draft, decision=decision, projection=projection,
        tool_proposal_roots=[h("write-request")], dispatch_receipt_roots=[], tool_result_roots=[])
    campaign.record_turn(context=context, draft=draft, decision=decision,
                         projection=projection, turn=turn, event_id="reference-turn-1")
    campaign.record_exception(exception, event_id="reference-exception-1")
    progress.emit("PHASE_PASS", phase="JOURNAL", turn_root=turn["turn_root"])

    progress.emit("PHASE_START", phase="OBSERVATORY")
    state = campaign.observatory()
    human = campaign.project("HUMAN")
    agent = campaign.project("AGENT")
    verification = validate_pippi_campaign_workspace(out / "campaign")
    for name, value in (("CONTEXT", context), ("DRAFT", draft), ("DECISION", decision),
                        ("PROJECTION", projection), ("EXCEPTION", exception), ("TURN", turn),
                        ("OBSERVATORY", state), ("HUMAN-VIEW", human),
                        ("AGENT-VIEW", agent), ("VERIFICATION", verification)):
        write(out / "records" / f"{name}.json", value)
    progress.emit("PHASE_PASS", phase="OBSERVATORY", status=state["status"])

    body = {"schema": "mosaic.ucm.pippi-reference-campaign-receipt.v0.1",
        "context_root": context["context_root"], "turn_root": turn["turn_root"],
        "decision_root": decision["decision_root"], "exception_root": exception["exception_root"],
        "observatory_state_root": state["observatory_state_root"],
        "verification_root": verification["verification_root"],
        "effect_dispatch_count": 0, "status": "PASS_HELD_UNDECLARED_EFFECT", **BOUNDARY}
    receipt = {**body, "receipt_root": root(body)}
    write(out / "REFERENCE-CAMPAIGN-RECEIPT.json", receipt)
    progress.emit("PHASE_PASS", phase="COMPLETE", receipt_root=receipt["receipt_root"])
    progress.write_summary(total=5, status="PASS")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the no-effect Pippi reference campaign")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--progress", type=Path)
    args = parser.parse_args()
    print(canonical_bytes(run(args.out, args.progress)).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
