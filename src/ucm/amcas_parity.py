"""Canonical AMCAS registry, UCM coverage, compiler, diff, and parity court.

The module is deliberately non-authorizing.  AMCAS defines application
semantics; UCM records how those semantics are implemented and where explicit
migration or adapter work remains.  No registry or court result grants an
effect, application admission, or semantic equivalence.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY, SCHEMA as AMCAS_SCHEMA, compile_contract, validate_contract
from .profiles import PROFILE_DEFINITIONS, profile_registry
from .system import SYSTEMS, capability_registry

REGISTRY_SCHEMA = "mosaic.amcas.element-registry.v0.1"
COVERAGE_SCHEMA = "mosaic.ucm.amcas-coverage-registry.v0.1"
PROGRAM_SCHEMA = "mosaic.ucm.amcas-baseline-program.v0.1"
DIFF_SCHEMA = "mosaic.ucm.amcas-semantic-diff.v0.1"
COURT_SCHEMA = "mosaic.ucm.amcas-parity-court-result.v0.1"
PROFILE_SET_SCHEMA = "mosaic.ucm.application-profile-set.v0.1"
OBSERVATORY_SCHEMA = "mosaic.ucm.amcas-portfolio-observatory.v0.1"

PREDECESSOR_STAGE_I3_PROFILE_ROOTS = {
    "MOSAIC.2D_3D": "88ae21eab0fee0d509b5ca58aa32836c942286b517e6c2443b468f606c7d9787",
    "MOSAIC.AAC": "fd9b0b758b828cd846a89e2b74937f17d3c2d43955ea96930e02143aef01da3f",
    "MOSAIC.FIELD_MODELER": "87fc9f120e8ddaf5da3e0b0cb2409cf3b726c1b08a0c7f213dd8157e9697262c",
    "MOSAIC.MEDIA_CENTER": "817e19011a8896bce9ce5ffa7c30738f949d0081e0a1031b67d54e4d90b4853b",
    "MOSAIC.MEMORY_VAULT": "828c7ddf963b0498486d9b045d3a06cba7f5c3940d1b7197f8d8f6dd336e70f5",
    "MOSAIC.MESSENGER_CRYSTAL": "9bf389ff1f16e0b20c87dcdbe5e1248dfdf6646b1a7c6d418b1f4dd3402ba697",
    "MOSAIC.READER": "353ed3db2d8e2d8253d52c119c240d8acd591912ee8b6a62d3acd775b6a7c2fe",
}

CANONICAL_STAGE_I3_PROFILE_ROOTS = {
    "MOSAIC.2D_3D": "cdf47bd10c80e8a08bf736cb050808798e5ee51a8101f3795097cd0dcdcb432c",
    "MOSAIC.AAC": "452752ca050c996349894dbe5624c0ff40cda5bf79d9911f3c83616e5373a46b",
    "MOSAIC.FIELD_MODELER": "bfad232ccaab4fa56cbf597f1fc055bda257d85fe5132f09eaa7a217f013a85f",
    "MOSAIC.MEDIA_CENTER": "c62b9bb918d18e536a971088743f9aa99498da34fcb04b63020524c29decd9f0",
    "MOSAIC.MEMORY_VAULT": "6cb89adeb4bd6032f59def03e11dc10fc6a1fc048ae4f3e2d61622eb1ebda3d9",
    "MOSAIC.MESSENGER_CRYSTAL": "6b69ef78d5bc35752f8b0d7a846cc2c8e77786b172e3b942c9befbccda6a4195",
    "MOSAIC.READER": "f806b1214bd0abdb1c9ec6236b875e923d38b58c8a95dac49927cc49d5831f3e",
}


def build_profile_baseline_migration() -> dict[str, Any]:
    rows = []
    for application_id in sorted(CANONICAL_STAGE_I3_PROFILE_ROOTS):
        body = {"application_id": application_id,
                "predecessor_profile_set_root": PREDECESSOR_STAGE_I3_PROFILE_ROOTS[application_id],
                "successor_profile_set_root": CANONICAL_STAGE_I3_PROFILE_ROOTS[application_id],
                "reason": "CAPABILITY_REGISTRY_EXTENDED_WITH_PORTABILITY_DETERMINISM_SURFACES",
                "semantic_change": False,
                "native_authority_preserved": True}
        rows.append({**body, "migration_row_root": root(body)})
    body = {"schema": "mosaic.ucm.amcas-profile-baseline-migration.v0.1",
            "rows": rows, "row_count": len(rows), **BOUNDARY}
    return {**body, "migration_root": root(body)}

CLASSIFICATIONS = {
    "CORE_REQUIRED", "PROFILE_REQUIRED", "APPLICATION_LOCAL",
    "EXPERIMENTAL", "DEPRECATED",
}
COVERAGE_STATUSES = {
    "IMPLEMENTED", "PARTIAL", "APPLICATION_ADAPTER_REQUIRED",
    "UNIMPLEMENTED", "INCOMPATIBLE", "DEPRECATED",
}

_ELEMENT_DEFINITIONS = (
    ("APPLICATION_CONTRACT", "Application Constitution", "CORE_REQUIRED",
     "Application identity, CM1 requirements, CM2 preferences, boundaries, and acceptance."),
    ("IDENTITY_JURISDICTION", "Identity and Jurisdiction", "CORE_REQUIRED",
     "MosaicID, DKN namespace, THR locality, session identity, and delegation requirements."),
    ("CAPABILITY_EFFECT", "Capability and Effect Model", "CORE_REQUIRED",
     "Typed capabilities, effect classes, budgets, ceilings, and native executor ownership."),
    ("WORKFLOW_THREE_GATE", "Workflow and Three-Gate Operations", "CORE_REQUIRED",
     "Intent, G1 Sentinel, external execution, G2 Witness, G3 Diagnostic, and uncertainty."),
    ("ARTIFACT_CUSTODY", "Artifact Custody", "CORE_REQUIRED",
     "Content-addressed objects, manifests, atomic staging, freshness, rollback, and replay."),
    ("INTEGRATION_JOURNAL", "Constitutional Journal", "CORE_REQUIRED",
     "Append-only events, expected-head custody, portable continuation, and inclusion proofs."),
    ("REALIZATION_SELECTION", "Realization Space", "CORE_REQUIRED",
     "CM1 admissibility, CM2 comparison, deterministic selection, lowering, and explanation."),
    ("EVIDENCE_VERIFICATION", "Evidence and Verification", "CORE_REQUIRED",
     "Typed external evidence, verifier identity, source binding, tests, proofs, and receipts."),
    ("CORRESPONDENCE_COURT", "Correspondence Courts", "PROFILE_REQUIRED",
     "Exact behavioral comparison obligations without implied semantic equivalence."),
    ("POLICY_PACKS", "Policy Packs", "PROFILE_REQUIRED",
     "Versioned, hash-pinned reusable requirements and explicit conflict detection."),
    ("SEMANTIC_GRAPH", "Semantic and Project Graph", "PROFILE_REQUIRED",
     "Identity, lineage, dependency, derivation, impact, and projection relations."),
    ("DEPENDENCY_EVIDENCE_GRAPH", "Dependency and Evidence Graph", "CORE_REQUIRED",
     "Typed dependency closure, immutable snapshots, derivation receipts, current-use validity, admitted reuse, impact, and portable reconstruction."),
    ("PRESENTATION_ABI", "Presentation and Interaction ABI", "APPLICATION_LOCAL",
     "Semantic views and interaction intents projected into GUI, TUI, native, and headless forms."),
    ("AGENT_ABI", "Agent Runtime ABI", "PROFILE_REQUIRED",
     "Orient, bind, validate, compile, plan, gate, inspect, and journal-export operations."),
    ("TEST_REPAIR_CONTROL", "Test and Repair Control", "CORE_REQUIRED",
     "Fixed denominators, impact surfaces, qualification lanes, evidence, and nonsemantic progress."),
    ("LIFECYCLE_MIGRATION", "Lifecycle and Migration", "CORE_REQUIRED",
     "Version compatibility, repair deltas, supersession, deprecation, and journal continuity."),
    ("PRIVACY_DISCLOSURE", "Privacy and Disclosure", "APPLICATION_LOCAL",
     "Disclosure constraints, redaction commitments, private state boundaries, and evidence views."),
    ("PORTABLE_BOOTSTRAP", "Portable Bootstrap", "PROFILE_REQUIRED",
     "Offline closure, deterministic profiles, staging, verification, and cold-start recovery."),
    ("FEDERATION_CONTINUITY", "Federation and Continuity", "PROFILE_REQUIRED",
     "Peer identity, replay protection, retirement, migration, and cross-session continuity."),
    ("NATIVE_PROOF", "Native Deductive Proof", "PROFILE_REQUIRED",
     "Bounded proof obligations and independently rechecked certificates."),
    ("PORTFOLIO_OBSERVABILITY", "Portfolio Observability", "PROFILE_REQUIRED",
     "Read-only application coverage, freshness, migration, and consolidation state."),
    ("DEVELOPMENT_STANDARDS", "Development Standards Plane", "CORE_REQUIRED",
     "Fixed-denominator development obligations, contextual triggers, evidence lineage, and dispositions."),
    ("PIPPI_MEDIATION", "Pippi Mediation Boundary", "PROFILE_REQUIRED",
     "Rooted model drafts, proposal policy, human projections, constitutional exceptions, and observable-turn journals."),
    ("SEMANTIC_PASSAGE", "Semantic Passage Protocol", "EXPERIMENTAL",
     "Exact-text spans, qualified integer senses, bounded clarification, and pinned external semantic providers."),
    ("CONSTITUTIONAL_LAUNCH", "Constitutional Launcher", "APPLICATION_LOCAL",
     "Shared startup identity, readiness, presentation, three-gate observations, and uncertain-outcome reconciliation."),
    ("BEHAVIORAL_HARNESS", "Behavioral Harness", "PROFILE_REQUIRED",
     "Controlled transition scenarios with declared controls, write sets, and external-executor receipts."),
)

_SYSTEM_TO_ELEMENT = {
    "CONSTITUTIONAL_CORE": "APPLICATION_CONTRACT",
    "UCL_LANGUAGE": "NATIVE_PROOF",
    "TESSERA_COMPILATION": "NATIVE_PROOF",
    "NATIVE_PROOF": "NATIVE_PROOF",
    "REALIZATION_SPACE": "REALIZATION_SELECTION",
    "COURT_EXECUTION": "CORRESPONDENCE_COURT",
    "QUALIFICATION_CONTROL": "TEST_REPAIR_CONTROL",
    "CUSTODY_FEDERATION": "FEDERATION_CONTINUITY",
    "AGENT_WORKBENCH": "AGENT_ABI",
    "PROJECT_INTELLIGENCE": "SEMANTIC_GRAPH",
    "DEPENDENCY_EVIDENCE_GRAPH": "DEPENDENCY_EVIDENCE_GRAPH",
    "AUTONOMOUS_PROJECT_MANAGER": "LIFECYCLE_MIGRATION",
    "PORTABLE_BOOTSTRAP": "PORTABLE_BOOTSTRAP",
    "APPLICATION_GATEWAY": "PRESENTATION_ABI",
    "AMCAS_INTEGRATION": "APPLICATION_CONTRACT",
    "IDENTITY_SESSION": "IDENTITY_JURISDICTION",
    "INTEGRATION_JOURNAL": "INTEGRATION_JOURNAL",
    "INTEGRATION_PORTFOLIO": "PORTFOLIO_OBSERVABILITY",
    "POINT_OF_USE_ADMISSIBILITY": "EVIDENCE_VERIFICATION",
    "OPERATIONAL_GATEWAY": "WORKFLOW_THREE_GATE",
    "GOVERNED_EXECUTION_LAYER": "CAPABILITY_EFFECT",
    "CONSTITUTIONAL_INTEGRATION": "CAPABILITY_EFFECT",
    "DEVELOPMENT_STANDARDS": "DEVELOPMENT_STANDARDS",
    "PIPPI_MEDIATION": "PIPPI_MEDIATION",
    "PROCESS_GOVERNANCE": "LIFECYCLE_MIGRATION",
    "C_CODING_PREFLIGHT": "TEST_REPAIR_CONTROL",
    "SEMANTIC_PASSAGE": "SEMANTIC_PASSAGE",
    "CONSTITUTIONAL_LAUNCH": "CONSTITUTIONAL_LAUNCH",
    "BEHAVIORAL_HARNESS": "BEHAVIORAL_HARNESS",
}

_ELEMENT_IMPLEMENTATION_SYSTEMS = {
    "APPLICATION_CONTRACT": ["AMCAS_INTEGRATION", "CONSTITUTIONAL_CORE"],
    "IDENTITY_JURISDICTION": ["IDENTITY_SESSION", "CONSTITUTIONAL_CORE"],
    "CAPABILITY_EFFECT": ["CONSTITUTIONAL_INTEGRATION", "CONSTITUTIONAL_CORE",
                          "GOVERNED_EXECUTION_LAYER"],
    "WORKFLOW_THREE_GATE": ["OPERATIONAL_GATEWAY", "CONSTITUTIONAL_INTEGRATION"],
    "ARTIFACT_CUSTODY": ["PORTABLE_BOOTSTRAP", "CUSTODY_FEDERATION"],
    "INTEGRATION_JOURNAL": ["INTEGRATION_JOURNAL"],
    "REALIZATION_SELECTION": ["REALIZATION_SPACE"],
    "EVIDENCE_VERIFICATION": ["NATIVE_PROOF", "COURT_EXECUTION", "QUALIFICATION_CONTROL",
                              "POINT_OF_USE_ADMISSIBILITY"],
    "CORRESPONDENCE_COURT": ["COURT_EXECUTION", "APPLICATION_GATEWAY"],
    "POLICY_PACKS": ["AMCAS_INTEGRATION", "QUALIFICATION_CONTROL"],
    "SEMANTIC_GRAPH": ["PROJECT_INTELLIGENCE"],
    "DEPENDENCY_EVIDENCE_GRAPH": ["DEPENDENCY_EVIDENCE_GRAPH", "PROJECT_INTELLIGENCE",
                                  "QUALIFICATION_CONTROL", "INTEGRATION_JOURNAL"],
    "PRESENTATION_ABI": ["APPLICATION_GATEWAY"],
    "AGENT_ABI": ["AGENT_WORKBENCH"],
    "TEST_REPAIR_CONTROL": ["C_CODING_PREFLIGHT", "QUALIFICATION_CONTROL"],
    "LIFECYCLE_MIGRATION": ["AUTONOMOUS_PROJECT_MANAGER", "PORTABLE_BOOTSTRAP",
                            "PROCESS_GOVERNANCE"],
    "PRIVACY_DISCLOSURE": ["AMCAS_INTEGRATION"],
    "PORTABLE_BOOTSTRAP": ["PORTABLE_BOOTSTRAP"],
    "FEDERATION_CONTINUITY": ["CUSTODY_FEDERATION"],
    "NATIVE_PROOF": ["NATIVE_PROOF", "UCL_LANGUAGE", "TESSERA_COMPILATION"],
    "PORTFOLIO_OBSERVABILITY": ["INTEGRATION_PORTFOLIO", "PROJECT_INTELLIGENCE"],
    "DEVELOPMENT_STANDARDS": ["DEVELOPMENT_STANDARDS"],
    "PIPPI_MEDIATION": ["PIPPI_MEDIATION"],
    "SEMANTIC_PASSAGE": ["SEMANTIC_PASSAGE"],
    "CONSTITUTIONAL_LAUNCH": ["CONSTITUTIONAL_LAUNCH"],
    "BEHAVIORAL_HARNESS": ["BEHAVIORAL_HARNESS"],
}

_PARTIAL_ELEMENTS = {"PRESENTATION_ABI", "PRIVACY_DISCLOSURE", "SEMANTIC_PASSAGE"}
_ADAPTER_ELEMENTS = {"CORRESPONDENCE_COURT", "SEMANTIC_GRAPH", "CONSTITUTIONAL_LAUNCH",
                     "DEPENDENCY_EVIDENCE_GRAPH"}


def _body_root(value: dict[str, Any], field: str) -> str:
    return root({key: raw for key, raw in value.items() if key != field})


def build_amcas_registry() -> dict[str, Any]:
    elements = []
    profiles = sorted(PROFILE_DEFINITIONS)
    for element_id, title, classification, role in _ELEMENT_DEFINITIONS:
        required_profiles = profiles if classification == "CORE_REQUIRED" else (
            ["AUTHORING", "OPERATIONAL", "VERIFY_ONLY"]
            if classification == "PROFILE_REQUIRED" else ["AUTHORING", "OPERATIONAL"])
        body = {
            "element_id": element_id,
            "title": title,
            "classification": classification,
            "plain_role": role,
            "contract_schema": f"mosaic.amcas.baseline.{element_id.lower().replace('_', '-')}.v0.1",
            "required_profiles": required_profiles,
            "change_policy": "VERSIONED_REPAIR_DELTA_AND_EXPLICIT_MIGRATION",
        }
        elements.append({**body, "element_root": root(body)})
    elements.sort(key=lambda row: row["element_id"])
    body = {
        "schema": REGISTRY_SCHEMA,
        "registry_id": "AMCAS.BASELINE.ARCHITECTURE.V1",
        "amcas_contract_schema": AMCAS_SCHEMA,
        "classifications": sorted(CLASSIFICATIONS),
        "elements": elements,
        "rules": [
            "UNKNOWN_ELEMENT_REFUSES",
            "AMCAS_IS_NORMATIVE_UCM_IS_REALIZATION",
            "NO_APPROXIMATE_PARITY",
            "APPLICATION_LOCAL_DOES_NOT_ENTER_CORE_IMPLICITLY",
            "CHANGE_EMITS_MIGRATION_OBLIGATIONS",
            "NO_REGISTRY_AUTHORITY_EFFECT",
        ],
        **BOUNDARY,
    }
    return {**body, "registry_root": root(body)}


def validate_amcas_registry(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "registry_id", "amcas_contract_schema",
        "classifications", "elements", "rules", "standing", "authority_effect",
        "real_a5", "g0", "registry_root"})
    require(item["schema"] == REGISTRY_SCHEMA
            and item["amcas_contract_schema"] == AMCAS_SCHEMA,
            "AMCAS_REGISTRY_SCHEMA_INVALID")
    require(item["classifications"] == sorted(CLASSIFICATIONS),
            "AMCAS_REGISTRY_CLASSIFICATIONS_INVALID")
    ids = []
    for raw in item["elements"]:
        row = exact_keys(raw, {"element_id", "title", "classification", "plain_role",
            "contract_schema", "required_profiles", "change_policy", "element_root"})
        require(row["classification"] in CLASSIFICATIONS
                and row["required_profiles"] == sorted(set(row["required_profiles"]))
                and set(row["required_profiles"]) <= set(PROFILE_DEFINITIONS),
                "AMCAS_REGISTRY_ELEMENT_INVALID")
        require(row["element_root"] == _body_root(row, "element_root"),
                "AMCAS_REGISTRY_ELEMENT_ROOT_INVALID")
        ids.append(row["element_id"])
    require(ids == sorted(set(ids)), "AMCAS_REGISTRY_ELEMENT_ORDER_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "AMCAS_REGISTRY_AUTHORITY_INVALID")
    require(item["registry_root"] == _body_root(item, "registry_root"),
            "AMCAS_REGISTRY_ROOT_INVALID")
    require(item == build_amcas_registry(), "AMCAS_REGISTRY_MISMATCH")
    return deepcopy(item)


def build_ucm_coverage_registry(amcas_registry_value: Any | None = None) -> dict[str, Any]:
    amcas_registry = validate_amcas_registry(amcas_registry_value or build_amcas_registry())
    capabilities = capability_registry()
    profiles = profile_registry()
    systems = {row[0] for row in SYSTEMS}
    require(set(_SYSTEM_TO_ELEMENT) == systems, "AMCAS_COVERAGE_SYSTEM_MAP_INCOMPLETE")
    rows = []
    for element in amcas_registry["elements"]:
        element_id = element["element_id"]
        implementation_system_ids = sorted(_ELEMENT_IMPLEMENTATION_SYSTEMS[element_id])
        require(set(implementation_system_ids) <= systems,
                "AMCAS_COVERAGE_SYSTEM_UNKNOWN")
        surface_names = sorted(row["name"] for row in capabilities["surfaces"]
            if row["system"] in implementation_system_ids)
        status = ("PARTIAL" if element_id in _PARTIAL_ELEMENTS else
                  "APPLICATION_ADAPTER_REQUIRED" if element_id in _ADAPTER_ELEMENTS else
                  "IMPLEMENTED")
        body = {
            "element_id": element_id,
            "element_root": element["element_root"],
            "classification": element["classification"],
            "coverage_status": status,
            "implementation_system_ids": implementation_system_ids,
            "surface_names": surface_names,
            "profile_ids": element["required_profiles"],
            "evidence_test_ids": [f"AMCAS_PARITY:{element_id}"],
            "migration_status": "CURRENT" if status == "IMPLEMENTED" else "OPEN_OBLIGATION",
        }
        rows.append({**body, "coverage_row_root": root(body)})
    surface_overrides = {"MANAGE_BOUNDED_CORRECTION": "ARTIFACT_CUSTODY"}
    assigned = {row["name"]: surface_overrides.get(row["name"], _SYSTEM_TO_ELEMENT[row["system"]])
                for row in capabilities["surfaces"]}
    body = {
        "schema": COVERAGE_SCHEMA,
        "amcas_registry_root": amcas_registry["registry_root"],
        "capability_registry_root": capabilities["root"],
        "profile_registry_root": profiles["profile_registry_root"],
        "coverage_rows": rows,
        "active_surface_assignments": dict(sorted(assigned.items())),
        "active_surface_count": len(assigned),
        "unaccounted_surface_names": [],
        "unknown_system_ids": [],
        "status": "COMPLETE_DENOMINATOR_WITH_DECLARED_GAPS",
        **BOUNDARY,
    }
    return {**body, "coverage_root": root(body)}


def validate_ucm_coverage_registry(value: Any,
                                   amcas_registry_value: Any | None = None) -> dict[str, Any]:
    expected = build_ucm_coverage_registry(amcas_registry_value)
    require(value == expected, "AMCAS_UCM_COVERAGE_REGISTRY_MISMATCH")
    return deepcopy(value)


def compile_amcas_baseline(contract_value: Any, *,
                           amcas_registry_value: Any | None = None,
                           coverage_value: Any | None = None) -> dict[str, Any]:
    contract = validate_contract(contract_value)
    registry = validate_amcas_registry(amcas_registry_value or build_amcas_registry())
    coverage = validate_ucm_coverage_registry(
        coverage_value or build_ucm_coverage_registry(registry), registry)
    ir = compile_contract(contract)
    capability_names = {row["id"] for row in contract["capabilities"]}
    profile_rows = []
    ucm_profiles = profile_registry()
    for profile in ucm_profiles["profiles"]:
        allowed = sorted(capability_names & set(profile["surface_names"]))
        body = {
            "profile_id": profile["profile_id"],
            "ucm_surface_set_root": profile["surface_set_root"],
            "application_capability_ids": allowed,
            "application_capability_root": root(allowed),
            "status": "BOUND" if allowed else "BOUND_EMPTY",
        }
        profile_rows.append({**body, "profile_binding_root": root(body)})
    element_requirements = []
    coverage_by_id = {row["element_id"]: row for row in coverage["coverage_rows"]}
    for element in registry["elements"]:
        row = coverage_by_id[element["element_id"]]
        required = element["classification"] in {"CORE_REQUIRED", "PROFILE_REQUIRED"}
        body = {
            "element_id": element["element_id"],
            "element_root": element["element_root"],
            "required": required,
            "coverage_row_root": row["coverage_row_root"],
            "coverage_status": row["coverage_status"],
            "integration_status": ("READY" if row["coverage_status"] == "IMPLEMENTED"
                                   else "MIGRATION_OR_ADAPTER_REQUIRED"),
        }
        element_requirements.append({**body, "requirement_root": root(body)})
    migration = []
    for row in element_requirements:
        if row["integration_status"] == "READY":
            continue
        body = {
            "obligation_id": f"MIGRATE:{row['element_id']}",
            "element_id": row["element_id"],
            "requirement_root": row["requirement_root"],
            "reason_code": f"AMCAS_{row['coverage_status']}",
            "status": "OPEN",
        }
        migration.append({**body, "obligation_root": root(body)})
    body = {
        "schema": PROGRAM_SCHEMA,
        "contract_root": contract["contract_root"],
        "ir_root": ir["ir_root"],
        "application_id": contract["application"]["id"],
        "application_source_root": contract["subject"]["source_root"],
        "amcas_registry_root": registry["registry_root"],
        "coverage_root": coverage["coverage_root"],
        "profile_bindings": profile_rows,
        "element_requirements": element_requirements,
        "migration_obligations": migration,
        "required_policy_pack_ids": [
            "NO_AUTHORITY_V1", "SOURCE_BOUND_V1", "OFFLINE_PORTABLE_V1"],
        "workflow_policy": "G1_EXTERNAL_EXECUTOR_G2_G3",
        "journal_policy": "EXPECTED_HEAD_PORTABLE_EXPORT_NO_BLIND_REDISPATCH",
        "status": "READY_WITH_MIGRATION_OBLIGATIONS" if migration else "READY",
        "non_claims": ["NOT_APPLICATION_ADMISSION", "NOT_EXECUTION_AUTHORITY",
                       "NOT_SEMANTIC_EQUIVALENCE"],
        **BOUNDARY,
    }
    return {**body, "program_root": root(body)}


def semantic_diff_amcas(old_value: Any, new_value: Any) -> dict[str, Any]:
    old = validate_contract(old_value); new = validate_contract(new_value)
    changes = []
    authority_sections = {
        "acceptance", "application", "authority_ceiling", "capabilities",
        "cm1.requirements", "dependencies", "effects", "identities",
        "integration_boundary", "realization.authority", "realization.subject",
        "subject",
    }
    def add_change(section: str, identifier: str, before: Any, after: Any) -> None:
        if before == after:
            return
        kind = "ADDED" if before is None else "REMOVED" if after is None else "CHANGED"
        body = {"section": section, "identifier": identifier,
                "change_kind": kind,
                "old_root": root(before) if before is not None else None,
                "new_root": root(after) if after is not None else None,
                "authority_adjacent": section in authority_sections}
        changes.append({**body, "change_root": root(body)})
    def compare_rows(section: str, old_rows: list[dict[str, Any]],
                     new_rows: list[dict[str, Any]], id_field: str = "id") -> None:
        left = {row[id_field]: row for row in old_rows}
        right = {row[id_field]: row for row in new_rows}
        for identifier in sorted(set(left) | set(right)):
            add_change(section, identifier, left.get(identifier), right.get(identifier))
    add_change("schema", "schema", old["schema"], new["schema"])
    add_change("integration_id", "integration_id",
               old["integration_id"], new["integration_id"])
    add_change("cm1.membership_policy", "membership_policy",
               old["cm1"]["membership_policy"], new["cm1"]["membership_policy"])
    add_change("cm2.selection_policy", "selection_policy",
               old["cm2"]["selection_policy"], new["cm2"]["selection_policy"])
    for section in ("application", "subject", "identities", "integration_boundary",
                    "authority_ceiling", "portability", "reporting"):
        add_change(section, section, old[section], new[section])
    compare_rows("cm1.requirements", old["cm1"]["requirements"], new["cm1"]["requirements"])
    compare_rows("cm2.preferences", old["cm2"]["preferences"], new["cm2"]["preferences"])
    for section in ("capabilities", "effects", "dependencies", "acceptance"):
        compare_rows(section, old[section], new[section])
    compare_rows("realization.axes", old["realization_contract"]["axes"],
                 new["realization_contract"]["axes"])
    compare_rows("realization.constraints", old["realization_contract"]["constraints"],
                 new["realization_contract"]["constraints"])
    compare_rows("realization.objectives", old["realization_contract"]["objectives"],
                 new["realization_contract"]["objectives"], "metric_id")
    compare_rows("realization.lowering.targets",
                 old["realization_contract"]["lowering"]["targets"],
                 new["realization_contract"]["lowering"]["targets"], "target_id")
    for section in ("authority", "evidence", "possibility", "selection", "subject"):
        add_change(f"realization.{section}", section,
                   old["realization_contract"][section],
                   new["realization_contract"][section])
    add_change("realization.capabilities", "capabilities",
               old["realization_contract"]["capabilities"],
               new["realization_contract"]["capabilities"])
    changes.sort(key=lambda row: (row["section"], row["identifier"]))
    body = {"schema": DIFF_SCHEMA, "old_contract_root": old["contract_root"],
            "new_contract_root": new["contract_root"], "changes": changes,
            "change_count": len(changes),
            "authority_adjacent_change_count": sum(row["authority_adjacent"] for row in changes),
            "migration_required": bool(changes), **BOUNDARY}
    return {**body, "diff_root": root(body)}


def run_amcas_ucm_parity(amcas_registry_value: Any | None = None,
                         coverage_value: Any | None = None) -> dict[str, Any]:
    registry = validate_amcas_registry(amcas_registry_value or build_amcas_registry())
    coverage = validate_ucm_coverage_registry(
        coverage_value or build_ucm_coverage_registry(registry), registry)
    rows = []
    def add(check_id: str, status: str, subject_root: str, diagnostic: str) -> None:
        body = {"check_id": check_id, "status": status,
                "subject_root": require_root(subject_root), "diagnostic": diagnostic}
        rows.append({**body, "check_root": root(body)})
    coverage_by_id = {row["element_id"]: row for row in coverage["coverage_rows"]}
    for element in registry["elements"]:
        row = coverage_by_id.get(element["element_id"])
        add(f"ELEMENT:{element['element_id']}",
            "PASS" if row and row["coverage_status"] != "UNIMPLEMENTED" else "REFUSED",
            element["element_root"], row["coverage_status"] if row else "MISSING")
    for name, element_id in coverage["active_surface_assignments"].items():
        add(f"SURFACE:{name}", "PASS", root({"surface": name, "element": element_id}),
            f"ACCOUNTED_BY:{element_id}")
    gaps = [row for row in coverage["coverage_rows"]
            if row["coverage_status"] != "IMPLEMENTED"]
    body = {
        "schema": COURT_SCHEMA,
        "amcas_registry_root": registry["registry_root"],
        "coverage_root": coverage["coverage_root"],
        "fixed_denominator": len(rows),
        "completed_denominator": len(rows),
        "rows": rows,
        "failed": sum(row["status"] != "PASS" for row in rows),
        "declared_gap_element_ids": [row["element_id"] for row in gaps],
        "status": ("PASS_COMPLETE" if not gaps else "PASS_WITH_DECLARED_GAPS"),
        **BOUNDARY,
    }
    return {**body, "court_root": root(body)}


def compile_stage_i3_profile_set(plan_value: Any,
                                 amcas_registry_value: Any | None = None,
                                 coverage_value: Any | None = None) -> dict[str, Any]:
    require(type(plan_value) is dict
            and plan_value.get("schema") == "mosaic.ucm.stage-i3-shadow-plan.v0.1",
            "AMCAS_PROFILE_PLAN_SCHEMA_INVALID")
    require(plan_value.get("plan_root") == _body_root(plan_value, "plan_root"),
            "AMCAS_PROFILE_PLAN_ROOT_INVALID")
    registry = validate_amcas_registry(amcas_registry_value or build_amcas_registry())
    coverage = validate_ucm_coverage_registry(
        coverage_value or build_ucm_coverage_registry(registry), registry)
    projections = plan_value.get("capability_projections")
    require(type(projections) is list, "AMCAS_PROFILE_PLAN_CAPABILITIES_INVALID")
    profiles = []
    for profile_id in sorted(PROFILE_DEFINITIONS):
        if profile_id == "COMPATIBILITY":
            selected = []
        elif profile_id == "OPERATIONAL":
            selected = sorted(row["capability_id"] for row in projections)
        else:
            selected = sorted(row["capability_id"] for row in projections
                              if row["effect_class"] in {"PURE_COMPUTATION", "READ_ONLY"})
        body = {"profile_id": profile_id, "capability_ids": selected,
                "capability_set_root": root(selected),
                "status": "BOUND" if selected else "BOUND_EMPTY"}
        profiles.append({**body, "profile_root": root(body)})
    body = {"schema": PROFILE_SET_SCHEMA,
            "application_id": plan_value["application_id"],
            "plan_root": plan_value["plan_root"],
            "amcas_registry_root": registry["registry_root"],
            "coverage_root": coverage["coverage_root"],
            "profiles": profiles,
            "native_authority_preserved": True,
            "status": "PROFILED_NOT_ADMITTED", **BOUNDARY}
    return {**body, "profile_set_root": root(body)}


def validate_stage_i3_profile_set(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "application_id", "plan_root",
        "amcas_registry_root", "coverage_root", "profiles",
        "native_authority_preserved", "status", "standing",
        "authority_effect", "real_a5", "g0", "profile_set_root"})
    require(item["schema"] == PROFILE_SET_SCHEMA,
            "AMCAS_PROFILE_SET_SCHEMA_INVALID")
    require(item["amcas_registry_root"] == build_amcas_registry()["registry_root"]
            and item["coverage_root"] == build_ucm_coverage_registry()["coverage_root"],
            "AMCAS_PROFILE_SET_BASELINE_MISMATCH")
    require(item["native_authority_preserved"] is True
            and item["status"] == "PROFILED_NOT_ADMITTED"
            and {key: item[key] for key in BOUNDARY} == BOUNDARY,
            "AMCAS_PROFILE_SET_AUTHORITY_INVALID")
    require(type(item["profiles"]) is list,
            "AMCAS_PROFILE_SET_PROFILES_INVALID")
    profile_ids = []
    for raw in item["profiles"]:
        profile = exact_keys(raw, {"profile_id", "capability_ids",
            "capability_set_root", "status", "profile_root"})
        require(profile["profile_id"] in PROFILE_DEFINITIONS
                and profile["capability_ids"] == sorted(set(profile["capability_ids"]))
                and profile["capability_set_root"] == root(profile["capability_ids"])
                and profile["status"] == ("BOUND" if profile["capability_ids"] else "BOUND_EMPTY")
                and profile["profile_root"] == _body_root(profile, "profile_root"),
                "AMCAS_PROFILE_SET_PROFILE_INVALID")
        profile_ids.append(profile["profile_id"])
    require(profile_ids == sorted(PROFILE_DEFINITIONS),
            "AMCAS_PROFILE_SET_DENOMINATOR_INVALID")
    require(item["profile_set_root"] == _body_root(item, "profile_set_root"),
            "AMCAS_PROFILE_SET_ROOT_INVALID")
    require(item["application_id"] in CANONICAL_STAGE_I3_PROFILE_ROOTS
            and item["profile_set_root"] ==
                CANONICAL_STAGE_I3_PROFILE_ROOTS[item["application_id"]],
            "AMCAS_PROFILE_CANONICAL_ROOT_MISMATCH")
    return deepcopy(item)


def build_portfolio_observatory(*, profile_sets: list[Any],
                                parity_result: Any,
                                consolidation_roots: list[str] | None = None) -> dict[str, Any]:
    require(type(parity_result) is dict and parity_result.get("schema") == COURT_SCHEMA
            and parity_result.get("court_root") == _body_root(parity_result, "court_root"),
            "AMCAS_OBSERVATORY_PARITY_INVALID")
    checked = []
    for raw in profile_sets:
        checked.append(validate_stage_i3_profile_set(raw))
    checked.sort(key=lambda row: row["application_id"])
    require(len(checked) == len({row["application_id"] for row in checked}),
            "AMCAS_OBSERVATORY_APPLICATION_DUPLICATE")
    roots = sorted(set(consolidation_roots or []))
    for value in roots: require_root(value)
    body = {
        "schema": OBSERVATORY_SCHEMA,
        "parity_court_root": parity_result["court_root"],
        "application_profile_roots": {row["application_id"]: row["profile_set_root"]
                                      for row in checked},
        "application_count": len(checked),
        "consolidation_roots": roots,
        "successor_rebindings_required": ["MOSAIC.2D_3D->MOSAIC.WORLD_ENGINE"],
        "stage_i1_intake_required": ["MOSAIC.UI", "MOSAIC.TERMINAL_UI", "MOSAIC.VOCAL_LAB"],
        "open_parity_elements": parity_result["declared_gap_element_ids"],
        "read_only": True,
        "status": "PASS_OBSERVATION_ONLY", **BOUNDARY}
    return {**body, "observatory_root": root(body)}
