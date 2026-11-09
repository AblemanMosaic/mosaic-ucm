"""Unified command surface for Mosaic UI authoring, execution, probing, and release."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, read_json
from .model import UIRefusal, validate_tree


def _emit(value: Any, output: Path | None = None) -> None:
    data = json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if output is not None:
        atomic_write(output.resolve(), data.encode("utf-8"))
    print(data, end="")


def _payload(generated: Path | None) -> dict[str, Any]:
    if generated is None:
        from .pilot import build_payload

        return build_payload()
    from .ablate import load_subject

    return load_subject(generated.resolve())[0]


def _command_validate(args: argparse.Namespace) -> dict[str, Any]:
    from mosaic_ui_std.lifecycle import validate_lifecycle

    application = read_json(args.application.resolve())
    tree = validate_tree(application["tree"], set(application.get("declared_operation_ids", ())))
    lifecycle = validate_lifecycle(application)
    return {
        "schema": "mosaic.ui.cli-validation.v0.1", "tree": tree, "lifecycle": lifecycle,
        "disposition": "PASS_LOCAL_CANDIDATE", "authority_effect": "NONE",
    }


def _command_layout(args: argparse.Namespace) -> dict[str, Any]:
    from .layout import witness

    payload = _payload(args.generated)
    return witness(payload["application"]["tree"], args.width, args.height, active_view=args.view)


def _command_pilot(args: argparse.Namespace) -> dict[str, Any]:
    if args.native:
        if args.screenshot is None:
            raise UIRefusal("PILOT_NATIVE_SCREENSHOT_REQUIRED", "")
        from .pilot_native import run_native_pilot

        return run_native_pilot(args.screenshot.resolve(), width=args.width, height=args.height)
    from .pilot import pilot_witness

    return pilot_witness(args.width, args.height)


def _command_protocol(args: argparse.Namespace) -> dict[str, Any]:
    from .realizer import conformance_witness, create_realizer

    realizer = create_realizer(args.realizer, _payload(args.generated))
    try:
        return conformance_witness(realizer, viewports=((args.width, args.height), (800, 600)))
    finally:
        realizer.close()


def _command_review(args: argparse.Namespace) -> dict[str, Any]:
    from .signature_review import run_signature_review
    from .signature_review_host import list_scenarios

    if args.list_scenarios:
        return list_scenarios(args.composition)

    return run_signature_review(
        args.composition, theme_id=args.theme, density_id=args.density,
        width=args.width, height=args.height, capture=args.capture.resolve() if args.capture else None,
        review_mode=args.mode, realizer=args.realizer, scenario=args.scenario,
        export_root=args.export_root.resolve() if args.export_root else None,
        record=args.record.resolve() if args.record else None, subject_id=args.subject,
    )


def _command_review_resize(args: argparse.Namespace) -> dict[str, Any]:
    from .native_review_workbench import run_native_review_resize_witness

    return run_native_review_resize_witness(
        args.output_dir.resolve(), subject_id=args.subject,
        theme_id=args.theme, density_id=args.density,
    )


def _command_slice(args: argparse.Namespace) -> dict[str, Any]:
    from .ablate import build_slice

    return build_slice(
        args.generated.resolve(), args.output_dir.resolve(), tuple(args.realizer or ["HEADLESS"]),
        tuple(args.theme), tuple(args.retain_kind), include_pathways=tuple(args.pathway),
        signature_profile=args.signature_profile, densities=tuple(args.density),
        v02_themes=tuple(args.v02_theme),
    )


def _command_verify_slice(args: argparse.Namespace) -> dict[str, Any]:
    from .ablate import verify_slice

    return verify_slice(args.archive.resolve(), args.receipt.resolve() if args.receipt else None)


def _command_release(args: argparse.Namespace) -> dict[str, Any]:
    from .release import build_release

    return build_release(args.source.resolve(), args.output_dir.resolve(), run_native=args.native,
                         browser_engines=tuple(args.browser_engine),
                         upgrade_from_wheel=args.upgrade_from_wheel.resolve())


def _command_browser_engines(args: argparse.Namespace) -> dict[str, Any]:
    from .browser_engine_acceptance import run_browser_engine_acceptance

    return run_browser_engine_acceptance(tuple(args.engine), args.output_dir.resolve(),
                                         width=args.width, height=args.height)


def _command_session_backup(args: argparse.Namespace) -> dict[str, Any]:
    from .session_custody import backup_session_database

    return backup_session_database(args.database.resolve(), args.backup.resolve())


def _command_session_verify(args: argparse.Namespace) -> dict[str, Any]:
    from .session_custody import verify_session_backup

    return verify_session_backup(args.backup.resolve())


def _command_package(args: argparse.Namespace) -> dict[str, Any]:
    from .adoption import build_from_manifest

    return build_from_manifest(args.manifest.resolve(), args.output_dir.resolve())


def _command_consumer_lifecycle(args: argparse.Namespace) -> dict[str, Any]:
    from .consumer_lifecycle import run_consumer_lifecycle

    return run_consumer_lifecycle(
        args.baseline_wheel.resolve(), args.candidate_wheel.resolve(), args.output_dir.resolve(),
    )


def _command_visual(args: argparse.Namespace) -> dict[str, Any]:
    from .visual_certification import build_matrix, record_baseline, verify_baseline

    if args.record:
        return record_baseline(args.baseline.resolve())
    result = verify_baseline(args.baseline.resolve())
    if args.artifacts:
        result = {**result, "matrix": build_matrix(args.artifacts.resolve())}
    return result


def _command_visual_v02(args: argparse.Namespace) -> dict[str, Any]:
    from .visual_certification_v02 import record_baseline_v02, verify_baseline_v02

    return record_baseline_v02(args.baseline.resolve()) if args.record else verify_baseline_v02(args.baseline.resolve())


def _command_theme_v02(args: argparse.Namespace) -> dict[str, Any]:
    from mosaic_ui_std.theme_v02 import (
        THEMES_V02_DIR, list_themes_v02, load_theme_v02, theme_v02_commitment, verify_font_assets,
    )

    theme_ids = list_themes_v02() if args.theme in {None, "all"} else [args.theme]
    themes = []
    for theme_id in theme_ids:
        theme = load_theme_v02(THEMES_V02_DIR / f"{theme_id}.json")
        themes.append({"theme_id": theme_id, "label": theme["label"], "scheme": theme["scheme"],
                       "commitment": theme_v02_commitment(theme)})
    font_failures = verify_font_assets()
    return {"schema": "mosaic.ui.theme-v02-witness.v0.1", "themes": themes,
            "font_failures": font_failures,
            "disposition": "PASS_LOCAL_CANDIDATE" if themes and not font_failures else "REFUSE",
            "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE"}


def _command_export_pack(args: argparse.Namespace) -> dict[str, Any]:
    from .review_library import export_pack

    return export_pack(args.pack, args.theme, args.output_dir.resolve())


def _command_gate_repeat(args: argparse.Namespace) -> dict[str, Any]:
    from .evidence_gates import gate_repeat

    return gate_repeat(include_measurement=not args.deterministic_only, only=args.only or None)


def _command_review_court(args: argparse.Namespace) -> dict[str, Any]:
    from .review_courts import run_review_headless_court

    return run_review_headless_court(args.pack, args.themes, args.plan)


def _command_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    from .performance import run_performance_gate

    return run_performance_gate(args.policy.resolve())


def _command_accessibility(_args: argparse.Namespace) -> dict[str, Any]:
    from .accessibility import accessibility_witness

    return accessibility_witness()


def _command_review_ontology(args: argparse.Namespace) -> dict[str, Any]:
    from .review_ontology import build_review_ontology, review_ontology_witness

    return review_ontology_witness() if args.witness else build_review_ontology()


def _command_signature_visual(args: argparse.Namespace) -> dict[str, Any]:
    from mosaic_ui_std.visual_profile import load_signature_visual_profile, signature_visual_witness

    return signature_visual_witness() if args.witness else load_signature_visual_profile()


def _command_review_session(args: argparse.Namespace) -> dict[str, Any]:
    from .review_session import ReviewSession

    session = ReviewSession(realizer=args.realizer, subject_id=args.subject)
    session.set_mode(args.mode)
    if args.view:
        session.select_view(args.view)
    for raw in args.condition:
        if "=" not in raw:
            raise UIRefusal("REVIEW_SESSION_CONDITION_REFUSED", raw)
        condition_id, value = raw.split("=", 1)
        session.set_condition(condition_id, value)
    if args.disposition:
        session.set_disposition(args.disposition, note=args.note)
    elif args.note:
        session.set_note(args.note)
    if args.specimen_value is not None:
        try:
            specimen_value = json.loads(args.specimen_value)
        except json.JSONDecodeError:
            specimen_value = args.specimen_value
        session.set_specimen_value(specimen_value)
    if args.next:
        session.move(1, unresolved_only=args.mode == "GUIDED_REVIEW")
    return session.snapshot() if args.snapshot else session.state()


def _command_review_audit(args: argparse.Namespace) -> dict[str, Any]:
    from .review_experience_audit import review_experience_audit

    return review_experience_audit()


def _command_review_specimens(args: argparse.Namespace) -> dict[str, Any]:
    from .review_ontology import build_review_ontology
    from .review_specimens import run_specimen_headless_witness, validate_specimen_catalog

    ontology = build_review_ontology()
    return run_specimen_headless_witness(ontology) if args.headless else validate_specimen_catalog(ontology)


def _command_orient(args: argparse.Namespace) -> dict[str, Any]:
    from .orient import orientation_witness

    return orientation_witness(args.source.resolve() if args.source else None)


def _command_doctor(_args: argparse.Namespace) -> dict[str, Any]:
    from .orient import doctor_witness

    return doctor_witness()


def _command_public_contract(_args: argparse.Namespace) -> dict[str, Any]:
    from .public_contract import public_contract_witness

    return public_contract_witness()


def _command_play_evidence(_args: argparse.Namespace) -> dict[str, Any]:
    from .play import play_evidence_witness

    return play_evidence_witness()


def _command_spatial_evidence(_args: argparse.Namespace) -> dict[str, Any]:
    from .spatial import spatial_evidence_witness

    return spatial_evidence_witness()


def _command_play_adapter_matrix(_args: argparse.Namespace) -> dict[str, Any]:
    from .play_adapters import adapter_candidate_matrix

    return adapter_candidate_matrix()


def _command_play_adapters(args: argparse.Namespace) -> dict[str, Any]:
    from .play_adapters import play_adapter_witness

    return play_adapter_witness(args.output_dir.resolve())


def _command_play_runtime(args: argparse.Namespace) -> dict[str, Any]:
    from .play_runtime_qualification import play_runtime_qualification_witness

    return play_runtime_qualification_witness(args.chromium_executable.resolve(), args.output_dir.resolve())


def _command_second_host(args: argparse.Namespace) -> dict[str, Any]:
    from .release_acceptance import run_second_host_acceptance

    return run_second_host_acceptance(args.release_dir.resolve(), args.receipt.resolve())


def _command_sign(args: argparse.Namespace) -> dict[str, Any]:
    from .release_acceptance import create_signature_envelope

    return create_signature_envelope(args.request.resolve(), args.private_key.resolve(), args.public_key.resolve(),
                                     args.signer_id, args.envelope.resolve())


def _command_verify_signature(args: argparse.Namespace) -> dict[str, Any]:
    from .release_acceptance import verify_signature_envelope

    return verify_signature_envelope(args.request.resolve(), args.envelope.resolve())


def _command_human_review_template(args: argparse.Namespace) -> dict[str, Any]:
    from .human_review import make_human_review_template

    return make_human_review_template(args.request.resolve(), args.receipt.resolve())


def _command_verify_human_review(args: argparse.Namespace) -> dict[str, Any]:
    from .human_review import verify_human_review_receipt

    return verify_human_review_receipt(args.request.resolve(), args.receipt.resolve())


def _command_finalize(args: argparse.Namespace) -> dict[str, Any]:
    from .release_acceptance import finalize_release

    return finalize_release(args.release_dir.resolve(), args.signature.resolve(),
                            args.second_host.resolve(), args.human_review.resolve(), args.output_dir.resolve())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mosaic-ui", description="Mosaic UI governed toolchain")
    parser.add_argument("--output", type=Path, help="Also write the command receipt as JSON")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="Validate an application semantic tree and lifecycle")
    validate.add_argument("application", type=Path)
    validate.set_defaults(run=_command_validate)

    layout = commands.add_parser("layout", help="Compile deterministic layout and emit a witness")
    layout.add_argument("--generated", type=Path)
    layout.add_argument("--width", type=int, default=1280)
    layout.add_argument("--height", type=int, default=800)
    layout.add_argument("--view")
    layout.set_defaults(run=_command_layout)

    pilot = commands.add_parser("pilot", help="Run the release-console pilot and emit evidence")
    pilot.add_argument("--width", type=int, default=1280)
    pilot.add_argument("--height", type=int, default=800)
    pilot.add_argument("--native", action="store_true")
    pilot.add_argument("--screenshot", type=Path)
    pilot.set_defaults(run=_command_pilot)

    protocol = commands.add_parser("protocol", help="Run portable realizer protocol conformance")
    protocol.add_argument("--generated", type=Path)
    protocol.add_argument("--realizer", choices=("HEADLESS", "BROWSER"), default="HEADLESS")
    protocol.add_argument("--width", type=int, default=1280)
    protocol.add_argument("--height", type=int, default=800)
    protocol.set_defaults(run=_command_protocol)

    review = commands.add_parser("review", help="Run functional or conformance Mosaic Signature review")
    review.add_argument("--realizer", choices=("WIN32", "HEADLESS"), default="WIN32")
    review.add_argument("--mode", choices=("functional", "conformance"), default="functional")
    review.add_argument("--composition", choices=("operational-dashboard", "data-workspace", "settings-workflow"),
                        default="operational-dashboard")
    review.add_argument("--theme", choices=("signature-dark", "signature-light", "high-contrast-dark"),
                        default="signature-dark")
    review.add_argument("--density", choices=("comfortable", "compact"), default="comfortable")
    review.add_argument("--width", type=int, default=1280)
    review.add_argument("--height", type=int, default=800)
    review.add_argument("--capture", type=Path)
    review.add_argument("--scenario")
    review.add_argument("--export-root", type=Path)
    review.add_argument("--record", type=Path)
    review.add_argument("--subject", help="Initial ontology subject ID for interactive Win32 review")
    review.add_argument("--list-scenarios", action="store_true")
    review.set_defaults(run=_command_review)

    review_resize = commands.add_parser(
        "review-resize", help="Capture a governed Win32 wide/compact/narrow resize witness",
    )
    review_resize.add_argument("output_dir", type=Path)
    review_resize.add_argument("--theme", choices=("signature-dark", "signature-light", "high-contrast-dark"),
                               default="signature-dark")
    review_resize.add_argument("--density", choices=("comfortable", "compact"), default="comfortable")
    review_resize.add_argument("--subject", default="component.button")
    review_resize.set_defaults(run=_command_review_resize)

    workbench = commands.add_parser("workbench", help="Run the local live builder workbench")
    workbench.add_argument("--host", default="127.0.0.1")
    workbench.add_argument("--port", type=int, default=0)
    workbench.add_argument("--pack")
    workbench.add_argument("--theme")
    workbench.set_defaults(run=None)

    browser = commands.add_parser("browser", help="Serve a governed browser realization on loopback")
    browser.add_argument("--host", default="127.0.0.1")
    browser.add_argument("--port", type=int, default=0)
    browser.add_argument("--width", type=int, default=1280)
    browser.add_argument("--height", type=int, default=800)
    browser.add_argument("--sufficiency", action="store_true")
    browser.set_defaults(run=None)

    slice_cmd = commands.add_parser("slice", help="Build an application-bound runtime slice")
    slice_cmd.add_argument("generated", type=Path)
    slice_cmd.add_argument("output_dir", type=Path)
    slice_cmd.add_argument("--realizer", action="append", choices=("HEADLESS", "BROWSER", "WIN32"))
    slice_cmd.add_argument("--theme", action="append", default=[])
    slice_cmd.add_argument("--signature-profile")
    slice_cmd.add_argument("--density", action="append", default=[])
    slice_cmd.add_argument("--v02-theme", action="append", default=[])
    slice_cmd.add_argument("--retain-kind", action="append", default=[])
    slice_cmd.add_argument("--pathway", action="append", default=[])
    slice_cmd.set_defaults(run=_command_slice)

    verify = commands.add_parser("verify-slice", help="Verify a runtime slice and receipt")
    verify.add_argument("archive", type=Path)
    verify.add_argument("--receipt", type=Path)
    verify.set_defaults(run=_command_verify_slice)

    release = commands.add_parser("release", help="Build and attest a release candidate")
    release.add_argument("source", type=Path, nargs="?", default=Path.cwd())
    release.add_argument("output_dir", type=Path)
    release.add_argument("--native", action="store_true")
    release.add_argument("--browser-engine", action="append", default=[],
                         help="Explicit ID=browser executable; repeat twice or more")
    release.add_argument("--upgrade-from-wheel", type=Path, required=True,
                         help="Exact prior-version wheel used for installed-consumer upgrade and recovery")
    release.set_defaults(run=_command_release)

    browser_engines = commands.add_parser("browser-engines", help="Probe explicit installed browser engines")
    browser_engines.add_argument("output_dir", type=Path)
    browser_engines.add_argument("--engine", action="append", required=True,
                                 help="Explicit ID=browser executable; repeat twice or more")
    browser_engines.add_argument("--width", type=int, default=676)
    browser_engines.add_argument("--height", type=int, default=600)
    browser_engines.set_defaults(run=_command_browser_engines)

    session_backup = commands.add_parser("session-backup", help="Create a consistent governed session database backup")
    session_backup.add_argument("database", type=Path)
    session_backup.add_argument("backup", type=Path)
    session_backup.set_defaults(run=_command_session_backup)

    session_verify = commands.add_parser("session-verify", help="Verify a standalone governed session database backup")
    session_verify.add_argument("backup", type=Path)
    session_verify.set_defaults(run=_command_session_verify)

    package = commands.add_parser("package", help="Build an application-bound package from a manifest")
    package.add_argument("manifest", type=Path)
    package.add_argument("output_dir", type=Path)
    package.set_defaults(run=_command_package)

    consumer_lifecycle = commands.add_parser(
        "consumer-lifecycle",
        help="Exercise installed-wheel application build, upgrade, backup, restore, and failure recovery",
    )
    consumer_lifecycle.add_argument("baseline_wheel", type=Path)
    consumer_lifecycle.add_argument("candidate_wheel", type=Path)
    consumer_lifecycle.add_argument("output_dir", type=Path)
    consumer_lifecycle.set_defaults(run=_command_consumer_lifecycle)

    visual = commands.add_parser("visual-certify", help="Verify or record the governed visual baseline")
    visual.add_argument("--baseline", type=Path, default=Path(__file__).resolve().parent / "source" / "visual-baseline.json")
    visual.add_argument("--record", action="store_true")
    visual.add_argument("--artifacts", type=Path)
    visual.set_defaults(run=_command_visual)

    visual_v02 = commands.add_parser("visual-certify-v02", help="Verify or record the sampled v0.2 theme baseline")
    visual_v02.add_argument("--baseline", type=Path,
                            default=Path(__file__).resolve().parent / "source" / "visual-baseline-v02.json")
    visual_v02.add_argument("--record", action="store_true")
    visual_v02.set_defaults(run=_command_visual_v02)

    theme_v02 = commands.add_parser("theme-v02", help="Validate governed v0.2 themes and owned font assets")
    theme_v02.add_argument("--theme", help="Theme id or 'all'", default="all")
    theme_v02.set_defaults(run=_command_theme_v02)

    export_pack = commands.add_parser("export-pack", help="Export a deterministic review pack and manifest")
    export_pack.add_argument("output_dir", type=Path)
    export_pack.add_argument("--pack", default="g2-stage")
    export_pack.add_argument("--theme", default="signature-dark")
    export_pack.set_defaults(run=_command_export_pack)

    gate_repeat = commands.add_parser("gate-repeat", help="Repeat registered evidence gates in independent processes")
    gate_repeat.add_argument("--only", action="append", default=[])
    gate_repeat.add_argument("--deterministic-only", action="store_true")
    gate_repeat.set_defaults(run=_command_gate_repeat)

    review_court = commands.add_parser("review-court", help="Court a review pack with Mosaic HeadlessUI evidence")
    review_court.add_argument("--pack", default="g2-stage")
    review_court.add_argument("--themes", action="append", default=None,
                              help="Theme id; repeat, or pass 'all'")
    review_court.add_argument("--plan", choices=("auto", "exhaustive", "pairwise", "strength3"), default="auto")
    review_court.set_defaults(run=_command_review_court)

    benchmark = commands.add_parser("benchmark", help="Measure governed performance envelopes")
    benchmark.add_argument(
        "--policy", type=Path,
        default=Path(__file__).resolve().parent / "source" / "performance-policy.json",
    )
    benchmark.set_defaults(run=_command_benchmark)

    accessibility = commands.add_parser("accessibility", help="Audit deterministic semantic and browser accessibility")
    accessibility.set_defaults(run=_command_accessibility)

    review_ontology = commands.add_parser(
        "review-ontology", help="Emit the shared human and agent UI review ontology",
    )
    review_ontology.add_argument("--witness", action="store_true", help="Emit the compact coverage witness")
    review_ontology.set_defaults(run=_command_review_ontology)

    signature_visual = commands.add_parser(
        "signature-visual", help="Emit the governed Mosaic Signature professional visual profile",
    )
    signature_visual.add_argument("--witness", action="store_true", help="Emit its compact evidence witness")
    signature_visual.set_defaults(run=_command_signature_visual)

    review_session = commands.add_parser(
        "review-session", help="Project a deterministic agent-readable UI review session",
    )
    review_session.add_argument("--realizer", choices=("HEADLESS", "BROWSER", "WIN32"), default="HEADLESS")
    review_session.add_argument("--subject", default="component.button")
    review_session.add_argument("--mode", choices=("EXPLORE", "GUIDED_REVIEW", "CHANGES"),
                                default="GUIDED_REVIEW")
    review_session.add_argument("--view", choices=("anatomy", "accessibility", "tokens", "parity",
                                                    "evidence", "delivery", "lifecycle"))
    review_session.add_argument("--condition", action="append", default=[], metavar="ID=VALUE")
    review_session.add_argument("--disposition", choices=("APPROVED", "ISSUE", "DEFERRED"))
    review_session.add_argument("--note")
    review_session.add_argument("--next", action="store_true", help="Advance to the next review subject")
    review_session.add_argument("--snapshot", action="store_true", help="Emit the full event-bound snapshot")
    review_session.add_argument("--specimen-value", help="Exercise the specimen value without changing simulated state")
    review_session.set_defaults(run=_command_review_session)

    review_specimens = commands.add_parser(
        "review-specimens", help="Validate or headlessly exercise all 45 shared review specimens",
    )
    review_specimens.add_argument("--headless", action="store_true", help="Run all specimen states and scenarios")
    review_specimens.set_defaults(run=_command_review_specimens)

    review_audit = commands.add_parser(
        "review-audit", help="Probe review scoping and the governed headless runtime",
    )
    review_audit.set_defaults(run=_command_review_audit)

    orient = commands.add_parser("orient", help="Emit deterministic cold-boot system orientation")
    orient.add_argument("--source", type=Path)
    orient.set_defaults(run=_command_orient)

    doctor = commands.add_parser("doctor", help="Report local runtime and realizer capabilities")
    doctor.set_defaults(run=_command_doctor)

    public_contract = commands.add_parser(
        "public-contract", help="Verify the frozen 25-kind Mosaic UI 1.0-RC1 public contract",
    )
    public_contract.set_defaults(run=_command_public_contract)

    play_evidence = commands.add_parser(
        "play-evidence", help="Run the engine-neutral Mosaic Play 2D prototype witness",
    )
    play_evidence.set_defaults(run=_command_play_evidence)

    spatial_evidence = commands.add_parser(
        "spatial-evidence", help="Run the engine-neutral Mosaic Spatial 3D prototype witness",
    )
    spatial_evidence.set_defaults(run=_command_spatial_evidence)

    play_adapter_matrix = commands.add_parser(
        "play-adapter-matrix", help="Evaluate bounded Mosaic Play adapter candidates",
    )
    play_adapter_matrix.set_defaults(run=_command_play_adapter_matrix)

    play_adapters = commands.add_parser(
        "play-adapters", help="Build two selected Mosaic Play artifacts and cross-adapter evidence",
    )
    play_adapters.add_argument("output_dir", type=Path)
    play_adapters.set_defaults(run=_command_play_adapters)

    play_runtime = commands.add_parser(
        "play-runtime", help="Qualify one explicit installed Chromium runtime for Mosaic Play",
    )
    play_runtime.add_argument("output_dir", type=Path)
    play_runtime.add_argument("--chromium-executable", type=Path, required=True)
    play_runtime.set_defaults(run=_command_play_runtime)

    second_host = commands.add_parser("second-host", help="Run clean installed-package acceptance on another host")
    second_host.add_argument("release_dir", type=Path)
    second_host.add_argument("receipt", type=Path)
    second_host.set_defaults(run=_command_second_host)

    sign = commands.add_parser("sign", help="Create an Ed25519 signature envelope for a release request")
    sign.add_argument("request", type=Path)
    sign.add_argument("private_key", type=Path)
    sign.add_argument("public_key", type=Path)
    sign.add_argument("signer_id")
    sign.add_argument("envelope", type=Path)
    sign.set_defaults(run=_command_sign)

    signature = commands.add_parser("verify-signature", help="Cryptographically verify a release signature envelope")
    signature.add_argument("request", type=Path)
    signature.add_argument("envelope", type=Path)
    signature.set_defaults(run=_command_verify_signature)

    human_review_template = commands.add_parser(
        "human-review-template", help="Create a candidate-bound template for five human review lanes",
    )
    human_review_template.add_argument("request", type=Path)
    human_review_template.add_argument("receipt", type=Path)
    human_review_template.set_defaults(run=_command_human_review_template)

    verify_human_review = commands.add_parser(
        "verify-human-review", help="Verify candidate-bound human review dispositions and evidence refs",
    )
    verify_human_review.add_argument("request", type=Path)
    verify_human_review.add_argument("receipt", type=Path)
    verify_human_review.set_defaults(run=_command_verify_human_review)

    finalize = commands.add_parser("finalize", help="Bind external signature and second-host evidence")
    finalize.add_argument("release_dir", type=Path)
    finalize.add_argument("signature", type=Path)
    finalize.add_argument("second_host", type=Path)
    finalize.add_argument("human_review", type=Path)
    finalize.add_argument("output_dir", type=Path)
    finalize.set_defaults(run=_command_finalize)
    for command_parser in (validate, layout, pilot, protocol, review, review_resize, slice_cmd, verify, release, browser_engines,
                           session_backup, session_verify, package, consumer_lifecycle, visual, visual_v02, theme_v02, export_pack,
                           gate_repeat, review_court, benchmark, accessibility, review_ontology,
                           signature_visual, review_session, review_specimens, review_audit,
                           orient, doctor, public_contract, play_evidence, spatial_evidence, play_adapter_matrix, play_adapters,
                           play_runtime,
                           second_host, sign, signature, human_review_template, verify_human_review, finalize):
        command_parser.add_argument(
            "--output", type=Path, default=argparse.SUPPRESS,
            help="Also write the command receipt as JSON (accepted before or after the subcommand)",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "workbench":
        from .workbench import main as workbench_main

        forwarded = ["--host", args.host, "--port", str(args.port)]
        if args.pack is not None:
            forwarded.extend(["--pack", args.pack])
        if args.theme is not None:
            forwarded.extend(["--theme", args.theme])
        return workbench_main(forwarded)
    if args.command == "browser":
        from .browser_realizer import create_browser_server
        from .pilot import build_payload
        from .sufficiency import build_sufficiency_payload

        payload = build_sufficiency_payload() if args.sufficiency else build_payload()
        server, _ = create_browser_server(payload, args.host, args.port, width=args.width, height=args.height)
        print(json.dumps({"schema": "mosaic.ui.browser-server.v0.1",
                          "url": f"http://{args.host}:{server.server_port}/", "authority_effect": "NONE"}), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    try:
        result = args.run(args)
        _emit(result, args.output)
        return 0 if result.get("disposition", result.get("status", "PASS")) not in {"REFUSE", "FAIL"} else 32
    except (UIRefusal, OSError, ValueError, json.JSONDecodeError) as exc:
        refusal = {
            "schema": "mosaic.ui.cli-refusal.v0.1", "disposition": "REFUSE",
            "refusal_code": getattr(exc, "code", "CLI_INPUT_OR_EXECUTION_REFUSED"),
            "detail": getattr(exc, "detail", str(exc)), "authority_effect": "NONE",
        }
        _emit(refusal, args.output)
        return 32


if __name__ == "__main__":
    raise SystemExit(main())
