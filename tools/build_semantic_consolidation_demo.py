"""Build the deterministic UCM semantic-consolidation demonstration."""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.semantic_consolidation import (
    build_judgment_packet,
    build_judgment_submission,
    compile_correspondence_program,
    discover_candidates,
    record_judgments,
    validate_discovery_policy,
)
from ucm.system import BOUNDARY


POLICY_PATH = ROOT / "policy-packs" / "SEMANTIC-CONSOLIDATION-CUSTODY-v0.1.json"
EXAMPLE_DIR = ROOT / "examples" / "consolidation" / "memory-vault-custody"
DIST_PATH = ROOT / "dist" / "UCM-SEMANTIC-CONSOLIDATION-CUSTODY-DEMO-C1.zip"
PLAN_DIR = ROOT / "integration" / "stage-i3" / "authoring" / "plans"
ARCHIVE_SCHEMA = "mosaic.ucm.semantic-consolidation-demo.v0.1"
ARCHIVE_ROLE = "UCM_SEMANTIC_CONSOLIDATION_DEMO"


def _policy() -> dict:
    family = {
        "family_id": "ARTIFACT_CUSTODY",
        "label": "Artifact custody, replay, and evidence access",
        "reference_application_id": "MOSAIC.MEMORY_VAULT",
        "roles": [
            {"role_id": "ARCHIVE_COMPOSE", "capability_tokens": ["ARCHIVE_COMPOSE"]},
            {"role_id": "ARCHIVE_REPLAY", "capability_tokens": ["ARCHIVE_REPLAY"]},
            {"role_id": "READ_EVIDENCE", "capability_tokens": ["READ_EVIDENCE"]},
            {"role_id": "VAULT_CUSTODY", "capability_tokens": ["VAULT_CUSTODY"]},
        ],
        "comparison_dimensions": [
            "INTENDED_MEANING",
            "INPUT_SCHEMA",
            "OUTPUT_SCHEMA",
            "DECISION_AND_REFUSAL",
            "EFFECT_AND_BUDGET",
            "AUTHORITY_AND_JURISDICTION",
            "RECOVERY_AND_UNCERTAINTY",
            "PRIVACY_AND_DISCLOSURE",
        ],
        "allowed_consolidation_forms": [
            "SHARED_CONTRACT",
            "SHARED_ADAPTER",
            "SHARED_SERVICE",
            "PRESERVE_SEPARATE",
        ],
    }
    body = {
        "schema": "mosaic.ucm.semantic-discovery-policy.v0.1",
        "policy_id": "SEMANTIC_CONSOLIDATION_CUSTODY_V0_1",
        "families": [family],
        **BOUNDARY,
    }
    return {**body, "policy_root": root(body)}


def _write(path: pathlib.Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def build() -> dict:
    policy = _policy()
    validate_discovery_policy(policy)
    plans = [strict_loads(path.read_bytes()) for path in sorted(PLAN_DIR.glob("*.json"))]
    discovery = discover_candidates(plans, policy)
    if (discovery["candidate_count"], discovery["comparison_pair_count"]) != (4, 13):
        raise RuntimeError("unexpected deterministic discovery census")
    packet = build_judgment_packet(discovery)
    decision_by_role = {
        "ARCHIVE_COMPOSE": (
            "PROVISIONAL_CANDIDATE",
            "Capability names and plan intent converge on archive construction, "
            "but container fidelity, versioning, and failure semantics still need correspondence evidence.",
        ),
        "ARCHIVE_REPLAY": (
            "NEEDS_EVIDENCE",
            "Replay suggests a shared role, but restore ordering, partial failure, "
            "and recovery custody are not established by the Stage I3 plans.",
        ),
        "READ_EVIDENCE": (
            "PROVISIONAL_CANDIDATE",
            "All members expose read-only evidence access; exact disclosure, "
            "normalization, and chain-continuity semantics still require human review and court evidence.",
        ),
        "VAULT_CUSTODY": (
            "NEEDS_EVIDENCE",
            "Custody language overlaps, while retention, retirement, identity, "
            "and jurisdiction responsibilities remain application-specific and unbound.",
        ),
    }
    candidate_by_root = {row["candidate_root"]: row for row in discovery["candidates"]}
    intent_rows = []
    for question in packet["questions"]:
        candidate = candidate_by_root[question["candidate_root"]]
        decision, rationale = decision_by_role[candidate["role_id"]]
        intent_rows.append({
            "judgment_id": question["judgment_id"],
            "decision": decision,
            "rationale": rationale,
            "evidence_roots": [candidate["candidate_root"], policy["policy_root"]],
            "human_confirmed": False,
        })
    intent = {
        "schema": "mosaic.ucm.semantic-judgment-intent.v0.1",
        "packet_root": packet["packet_root"],
        "decider_kind": "FSC_LLM_HYPOTHESIS",
        "decider_identity_root": root({
            "role": "UCM_PIPELINE_MODELING_HYPOTHESIS",
            "version": "0.1",
            "authority": "NONE",
        }),
        "judgments": intent_rows,
        **BOUNDARY,
    }
    submission = build_judgment_submission(packet, intent)
    register = record_judgments(packet, submission)
    program = compile_correspondence_program(discovery, register)
    if register["confirmed_count"] != 0 or program["ready_program_count"] != 0:
        raise RuntimeError("hypothesis crossed the human-confirmation boundary")
    report = {
        "schema": "mosaic.ucm.semantic-consolidation-demo-report.v0.1",
        "policy_root": policy["policy_root"],
        "discovery_root": discovery["discovery_root"],
        "packet_root": packet["packet_root"],
        "submission_root": submission["submission_root"],
        "register_root": register["register_root"],
        "consolidation_root": program["consolidation_root"],
        "application_count": len(plans),
        "candidate_count": discovery["candidate_count"],
        "comparison_pair_count": discovery["comparison_pair_count"],
        "cm1_obligation_count": sum(
            len(row["cm1_obligations"]) for row in program["programs"]),
        "human_confirmed_count": register["confirmed_count"],
        "ready_program_count": program["ready_program_count"],
        "result": "PROVISIONAL_HYBRID_DEMONSTRATION",
        "next_boundary": "HUMAN_JUDGMENT_THEN_CORRESPONDENCE_EVIDENCE",
        **BOUNDARY,
    }
    records = {
        "DISCOVERY-POLICY.json": policy,
        "DISCOVERY.json": discovery,
        "JUDGMENT-PACKET.json": packet,
        "LLM-HYPOTHESIS-INTENT.json": intent,
        "LLM-HYPOTHESIS-SUBMISSION.json": submission,
        "JUDGMENT-REGISTER.json": register,
        "CONSOLIDATION-PROGRAM.json": program,
        "DEMONSTRATION-REPORT.json": report,
    }
    for name, value in records.items():
        destination = POLICY_PATH if name == "DISCOVERY-POLICY.json" else EXAMPLE_DIR / name
        _write(destination, canonical_bytes(value))
    readme = """# Memory Vault custody semantic-consolidation demonstration

This demonstration runs the UCM hybrid consolidation pipeline over the seven
frozen Stage I3 application plans.

The deterministic discovery policy finds four candidate roles and thirteen
application-to-Memory-Vault comparison pairs. A modeling-system hypothesis
classifies two roles as provisional candidates and two as needing evidence.
No row is human-confirmed, so no program is ready for a correspondence court.

| Role | Applications | Pairs | Modeling disposition | Compiled status |
| --- | ---: | ---: | --- | --- |
| ARCHIVE_COMPOSE | 5 | 4 | PROVISIONAL_CANDIDATE | AWAITING_HUMAN_CONFIRMATION |
| ARCHIVE_REPLAY | 4 | 3 | NEEDS_EVIDENCE | DISCOVERY_EVIDENCE_INSUFFICIENT |
| READ_EVIDENCE | 5 | 4 | PROVISIONAL_CANDIDATE | AWAITING_HUMAN_CONFIRMATION |
| VAULT_CUSTODY | 3 | 2 | NEEDS_EVIDENCE | DISCOVERY_EVIDENCE_INSUFFICIENT |

The near-term gain is a precise denominator: thirteen pairwise questions and
104 explicit CM1 obligations replace a vague ecosystem-wide refactor. The
likely reusable boundary is a common custody/evidence contract plus adapters;
a shared effectful service remains only one CM2 option and is not preferred by
this result. The historical MOSAIC.2D_3D identity must be rebound to the World
Engine successor before any live campaign.

The output is intentionally non-authorizing. It proves reproducibility of the
discovery and compilation process; it does not prove semantic equivalence,
authorize composition, select a shared implementation, or execute an
application.

Next boundary: a human reviews JUDGMENT-PACKET.json and submits an exact
judgment intent. Confirmed candidates then receive CM1 obligations that must be
discharged by a correspondence court before any consolidation proposal.
"""
    _write(EXAMPLE_DIR / "README.md", readme.encode("utf-8"))
    payloads = {
        "policy/DISCOVERY-POLICY.json": canonical_bytes(policy),
        **{f"demo/{name}": canonical_bytes(value) for name, value in records.items()
           if name != "DISCOVERY-POLICY.json"},
        "demo/README.md": readme.encode("utf-8"),
        "software/semantic_consolidation.py":
            (ROOT / "src" / "ucm" / "semantic_consolidation.py").read_bytes(),
        "software/build_semantic_consolidation_demo.py":
            pathlib.Path(__file__).read_bytes(),
    }
    for path in sorted(PLAN_DIR.glob("*.json")):
        payloads[f"inputs/plans/{path.name}"] = path.read_bytes()
    first = deterministic_zip(payloads, schema=ARCHIVE_SCHEMA,
                              artifact_role=ARCHIVE_ROLE)
    second = deterministic_zip(payloads, schema=ARCHIVE_SCHEMA,
                               artifact_role=ARCHIVE_ROLE)
    if first != second:
        raise RuntimeError("demo archive is not deterministic")
    verify_deterministic_zip(first, expected_schema=ARCHIVE_SCHEMA,
                             expected_role=ARCHIVE_ROLE)
    _write(DIST_PATH, first)
    return {
        **report,
        "archive": str(DIST_PATH),
        "archive_sha256": hashlib.sha256(first).hexdigest(),
        "archive_bytes": len(first),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the UCM semantic-consolidation demonstration")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()
    result = build()
    if args.print_json:
        print(canonical_bytes(result).decode("utf-8"), end="")
    else:
        print(result["archive"])
        print(result["archive_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
