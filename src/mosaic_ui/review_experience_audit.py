"""Deterministic intelligent-scoping and runtime audit for the review workbench."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .canonical import atomic_write, canonical_bytes, commitment
from .model import UIRefusal
from .realizer import conformance_witness, create_realizer
from .review_ontology import build_review_ontology
from .review_session import ReviewSession
from .sufficiency import build_sufficiency_payload
from mosaic_ui_std.visual_profile import signature_visual_witness


def review_experience_audit(
    output: Path | None = None, *, reporter: Callable[[str, float], None] | None = None,
) -> dict[str, Any]:
    """Probe review scope across every subject and the governed HEADLESS runtime."""
    report = reporter or (lambda _message, _percent: None)
    ontology = build_review_ontology()
    all_states = tuple(next(item for item in ontology["conditions"]
                            if item["condition_id"] == "state")["options"])
    failures: list[dict[str, str]] = []
    checks = 0
    state_pairs = 0

    def check(case_id: str, passed: bool, detail: str = "") -> None:
        nonlocal checks
        checks += 1
        if not passed:
            failures.append({"case_id": case_id, "detail": detail})

    report("Validating the 45-subject review ontology...", 18)
    for subject in ontology["subjects"]:
        subject_id = subject["subject_id"]
        session = ReviewSession(ontology, subject_id=subject_id)
        applicable = session.applicable_states()
        check(f"{subject_id}:STATE_SET", bool(applicable) and set(applicable) <= set(all_states),
              ",".join(applicable))
        for state in all_states:
            state_pairs += 1
            if state in applicable:
                try:
                    session.set_condition("state", state)
                    check(f"{subject_id}:{state}", session.conditions["state"] == state)
                except UIRefusal as exc:
                    check(f"{subject_id}:{state}", False, exc.code)
            else:
                try:
                    session.set_condition("state", state)
                except UIRefusal as exc:
                    check(f"{subject_id}:{state}", exc.code == "REVIEW_SESSION_STATE_NOT_APPLICABLE",
                          exc.code)
                else:
                    check(f"{subject_id}:{state}", False, "inapplicable state accepted")

        session.set_condition("state", applicable[0])
        before = dict(session.conditions)
        interactive = bool(subject.get("metadata", {}).get("interactive"))
        try:
            session.record_interaction("AUDIT")
        except UIRefusal as exc:
            check(f"{subject_id}:INTERACTION_SCOPE", not interactive and
                  exc.code == "REVIEW_SESSION_ACTION_NOT_APPLICABLE", exc.code)
        else:
            check(f"{subject_id}:INTERACTION_SCOPE", interactive and session.conditions == before)

        if interactive and "DISABLED" in applicable:
            session.set_condition("state", "DISABLED")
            try:
                session.record_interaction("AUDIT_DISABLED")
            except UIRefusal as exc:
                check(f"{subject_id}:DISABLED_INTERACTION", exc.code == "REVIEW_SESSION_ACTION_NOT_APPLICABLE",
                      exc.code)
            else:
                check(f"{subject_id}:DISABLED_INTERACTION", False, "disabled interaction accepted")

    report("Checking mode, action, and navigation scoping...", 42)
    explore = ReviewSession(ontology)
    explore.set_mode("EXPLORE")
    for intent, action in (
        ("SET_NOTE", lambda: explore.set_note("not applicable")),
        ("SET_DISPOSITION", lambda: explore.set_disposition("APPROVED")),
    ):
        try:
            action()
        except UIRefusal as exc:
            check(f"EXPLORE:{intent}", exc.code == "REVIEW_SESSION_ACTION_NOT_APPLICABLE", exc.code)
        else:
            check(f"EXPLORE:{intent}", False, "action accepted")
    check("EXPLORE:ACTION_SCOPE", not explore.action_scope()["review_note_enabled"] and
          not explore.action_scope()["disposition_enabled"])

    changes = ReviewSession(ontology)
    changes.set_disposition("APPROVED")
    first_changed = changes.subject_id
    changes.move(1)
    changes.set_disposition("ISSUE")
    second_changed = changes.subject_id
    changes.set_mode("CHANGES")
    changes.select_subject(first_changed)
    changes.dispatch({"intent": "NEXT"})
    check("CHANGES:NAVIGATION_SCOPE", changes.subject_id == second_changed and
          changes.action_scope()["navigation_scope"] == "CHANGED")

    report("Probing browser and native session projections...", 58)
    from .native_review_workbench import NativeReviewModel
    from .workbench import WorkbenchSession

    browser = WorkbenchSession()
    browser_before = browser.review_state()["event_count"]
    browser_after = browser.review_action({"intent": "INTERACT", "value": "AUDIT_BROWSER"})
    check("BROWSER:SESSION_PROJECTION", browser_after["event_count"] == browser_before + 1 and
          browser_after["last_event"]["intent"] == "INTERACT")

    native = NativeReviewModel(ontology, subject_id="component.button")
    native_before = native.state()["event_count"]
    native.record_interaction("AUDIT_NATIVE")
    native_after = native.state()
    check("WIN32:SESSION_PROJECTION", native_after["event_count"] == native_before + 1 and
          native_after["action_scope"] == browser_after["action_scope"])

    report("Running the Mosaic HEADLESS realizer conformance probe...", 76)
    realizer = create_realizer("HEADLESS", build_sufficiency_payload())
    try:
        runtime_witness = conformance_witness(
            realizer,
            viewports=((1280, 800), (800, 600)),
            events=({"intent": "SELECT", "node_id": "suff.tree", "value": "Releases"},),
        )
    finally:
        realizer.close()
    check("HEADLESS:RUNTIME_CONFORMANCE", runtime_witness["disposition"] == "PASS_LOCAL_CANDIDATE",
          str(runtime_witness["failure_count"]))
    check("HEADLESS:RUNTIME_TRANSITION",
          runtime_witness["transitions"][0]["state"]["values"]["suff.tree"] == "Releases")

    report("Binding the review-experience receipt...", 94)
    visual_witness = signature_visual_witness()
    check("SIGNATURE:VISUAL_PROFILE", visual_witness["disposition"] == "PASS_LOCAL_CANDIDATE",
          str(visual_witness["failure_count"]))
    value = {
        "schema": "mosaic.ui.review-experience-audit.v0.1",
        "ontology_commitment": ontology["commitment"],
        "coverage": {
            "group_count": len(ontology["groups"]),
            "subject_count": len(ontology["subjects"]),
            "component_count": len([item for item in ontology["subjects"]
                                    if item["subject_type"] == "COMPONENT"]),
            "state_pair_count": state_pairs,
            "check_count": checks,
        },
        "surface_probes": {
            "agent": "ReviewSession",
            "browser": "WorkbenchSession.review_action",
            "native": "NativeReviewModel",
            "shared_action_scope_keys": sorted(native_after["action_scope"]),
        },
        "runtime_witness": runtime_witness,
        "visual_system_witness": visual_witness,
        "failure_count": len(failures),
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "LOCAL_CONTRACT_AND_HEADLESS_RUNTIME_PROBES_DO_NOT_ESTABLISH_BROAD_HUMAN_USABILITY_OR_EXTERNAL_HOST_CERTIFICATION",
    }
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_EXPERIENCE_AUDIT.v0.1", value)
    if output is not None:
        atomic_write(output.resolve(), canonical_bytes(value) + b"\n")
    report("Review runtime ready.", 100)
    return value


__all__ = ["review_experience_audit"]
