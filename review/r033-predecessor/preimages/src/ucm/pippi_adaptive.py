"""Portable adaptive-orchestration records for P/PPI.

This module is deliberately host-neutral.  It describes what an adaptive host
can substantiate, prepares exact context, and binds observable turn reports.
It never claims tool interception, hidden-reasoning access, or effect authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, root

from .pippi_global import BOUNDARY, validate_project
from .pippi_portability import validate_execution_context


HOST_MODES = ("EXECUTABLE_LOCAL", "ARTIFACT_MEDIATED_WEB", "NATIVE_ENFORCED")
CAPSULE_PROFILES = ("CONTEXT_ONLY", "WORK_CAPSULE", "PROJECT_PORTABLE",
                    "AIRGAP_COMPLETE", "FULL_REFERENCE")
FACT_CLASSES = ("OBSERVED", "DERIVED", "AGENT_REPORTED", "USER_REPORTED",
                "UNRESOLVED")

ADAPTIVE_CLI_ROUTES = {
    "DISCOVER_PIPPI_MEDIATION_LIBRARY": "mediation-library",
    "NEGOTIATE_PIPPI_HOST_MODE": "host-negotiate",
    "PREPARE_PIPPI_TURN": "turn-prepare",
    "BUILD_PIPPI_TURN_REPORT": "turn-report",
    "RECONCILE_PIPPI_TURN": "turn-reconcile",
    "BUILD_PIPPI_PROJECT_CAPSULE": "capsule-build",
    "VERIFY_PIPPI_PROJECT_CAPSULE": "capsule-verify",
    "INSPECT_PIPPI_INTERFACE_CONFORMANCE": "interface-doctor",
    "DISCOVER_PIPPI_PACK_REGISTRY": "pack-list",
    "BUILD_PIPPI_INSTALL_PLAN": "install-plan",
    "EXPLAIN_PIPPI_PROJECT_PORTABILITY": "project-portability",
    "BUILD_PIPPI_EXECUTION_CONTEXT": "environment-observe",
    "DISCOVER_PIPPI_PORTABILITY_POLICY": "portability-policy",
    "BUILD_PIPPI_PORTABILITY_WITNESS": "portability-witness",
    "EVALUATE_PIPPI_PORTABILITY_GATE": "portability-gate",
    "INSPECT_PIPPI_PORTABLE_SOURCE": "portability-source-doctor",
    "VERIFY_TRANSTEMPORAL_REVISION": "archive-verify",
    "DIFF_TRANSTEMPORAL_REVISIONS": "archive-diff",
    "INSPECT_TRANSTEMPORAL_STORAGE": "archive-report",
    "BUILD_SEMCRYS_TRANSTEMPORAL_PLAN": "archive-semcrys-plan",
    "DISCOVER_CONSTITUTIONAL_STANDARDS_ATLAS": "standards",
    "DISCOVER_PIPPI_PIPELINE_MODEL": "pipeline-model",
    "EXPLAIN_PIPPI_STANDARD_RULE": "standard-explain",
    "EXPLAIN_PIPPI_PIPELINE_TRANSITION": "transition-explain",
    "EXPLAIN_PIPPI_CONTEXT_SELECTION": "context-explain",
    "BUILD_PIPPI_COLLABORATOR_BINDING": "collaborator-bind",
    "DISCOVER_PIPPI_CREDENTIAL_BROKER_POLICY": "credential-policy",
    "BUILD_PIPPI_CREDENTIAL_REFERENCE": "credential-reference",
    "BUILD_SIGNED_CONSTITUTIONAL_CHANGE_CAPSULE": "change-capsule-build",
    "VERIFY_SIGNED_CONSTITUTIONAL_CHANGE_CAPSULE": "change-capsule-verify",
    "BUILD_PIPPI_STORAGE_LOCATOR": "storage-locator",
    "BUILD_SIGNED_STORAGE_PUBLICATION_RECEIPT": "publication-receipt",
    "VERIFY_SIGNED_STORAGE_PUBLICATION_RECEIPT": "publication-receipt-verify",
    "BUILD_SIGNED_STORAGE_RETRIEVAL_RECEIPT": "retrieval-receipt",
    "VERIFY_SIGNED_STORAGE_RETRIEVAL_RECEIPT": "retrieval-receipt-verify",
    "BUILD_PIPPI_CCP_TRANSITION_BINDING": "ccp-transition",
}

PIPPI_EXIT_CODES = {
    "SUCCESS": 0,
    "TYPED_REFUSAL": 3,
    "USAGE_ERROR": 64,
    "UNSUPPORTED_SURFACE": 69,
    "INTERNAL_FAULT": 70,
    "CUSTODY_FAILURE": 74,
}

PIPPI_BASE_COMMANDS = (
    "onboard", "project-add", "project-revise", "projects", "verify",
    "dashboard", "dashboard-probe", "serve", "profile-show", "project-brief",
    "profile-set", "sessions", "migrate-discover", "migrate-import",
    "preferences-show", "preferences-set", "timeline", "context",
    "review-envelope-build", "review-envelope-verify", "reviews",
    "review-run-local", "review-dispatch-courthouse", "review-import-return",
    "review-compare", "review-publication-proposal", "research-record-verify",
    "work-selection-verify", "completion", "pack-inventory", "pack-record",
    "archive-ingest", "archive-materialize", "archive-native-manifest",
    "installer", "installer-probe",
)


def pippi_shell_completion(shell: str) -> dict[str, Any]:
    require(shell in {"bash", "zsh", "fish", "powershell"},
            "PIPPI_COMPLETION_SHELL_UNSUPPORTED")
    commands = sorted(set(PIPPI_BASE_COMMANDS) | set(ADAPTIVE_CLI_ROUTES.values()))
    words = " ".join(commands)
    if shell == "powershell":
        quoted = "','".join(commands)
        script = ("Register-ArgumentCompleter -Native -CommandName pippi -ScriptBlock {\n"
                  "  param($wordToComplete)\n"
                  f"  @('{quoted}') | Where-Object {{ $_ -like \"$wordToComplete*\" }}\n"
                  "}\n")
    elif shell == "fish":
        script = "\n".join(f"complete -c pippi -f -a '{name}'" for name in commands) + "\n"
    elif shell == "zsh":
        script = f"#compdef pippi\n_arguments '1:command:(({words}))'\n"
    else:
        script = ("_pippi_complete() { COMPREPLY=( $(compgen -W '" + words
                  + "' -- \"${COMP_WORDS[1]}\") ); }\ncomplete -F _pippi_complete pippi\n")
    body = {"schema": "mosaic.ucm.pippi-shell-completion.v0.1", "shell": shell,
            "commands": commands, "adaptive_cli_routes": deepcopy(ADAPTIVE_CLI_ROUTES),
            "script": script, **BOUNDARY}
    return {**body, "completion_root": root(body)}

_RULES = (
    ("AUTHORITY_BOUNDARY", "AUTHORITY", ("TURN_START", "EFFECT_PROPOSAL"),
     "Planning, context, and reports do not grant authority; effects require the governed gateway."),
    ("VERSION_POLICY", "IDENTITY", ("TURN_START", "RELEASE_PLANNING"),
     "Preserve public v0.1 unless the user explicitly authorizes a version change; prefer one r### successor per accepted freeze."),
    ("PROJECT_ENTRYPOINTS", "PROJECT", ("TURN_START", "LAUNCH_REQUEST"),
     "Use the project's declared application and verification entrypoints."),
    ("ARCHIVE_POLICY", "CUSTODY", ("ARTIFACT_CREATED", "TURN_CLOSE"),
     "Keep exact bytes content-addressed; progress is never evidence and private credentials never enter portable capsules."),
    ("COURTHOUSE_ROUTING", "CORRESPONDENCE", ("REMOTE_WORK", "CROSS_JURISDICTION"),
     "Route remote or cross-jurisdiction work through a receipted Courthouse envelope."),
    ("VISIBILITY_POLICY", "PRESENTATION", ("TURN_START", "LONG_OPERATION"),
     "Keep the user-facing projection synchronized with governed state and emit nonsemantic progress for long work."),
    ("SEVEN_CHANNEL_COVERAGE", "MEDIATION", ("TURN_START",),
     "Account for model input, draft, visible output, tool proposal, dispatch, result, and journal write without claiming hidden reasoning."),
    ("UGK_FGA", "UGK", ("STATE_TRANSITION",),
     "Name the predecessor, admissibility rule, transition, successor, and receipt for every governed state change."),
    ("UGK_THREE_HASH_RULE", "UGK", ("ARTIFACT_CREATED", "TURN_CLOSE"),
     "Keep exact state, semantic meaning, governance/admissibility, jurisdiction/locality, and receipt commitments separate."),
    ("UGK_IEL", "UGK", ("IMPORT", "MUTATION", "RECOVERY"),
     "Validate before mutation, distinguish corrupt from missing, stage atomically, and never redispatch an uncertain effect."),
    ("UGK_CLAIM_DISCIPLINE", "UGK", ("TURN_CLOSE", "REVIEW"),
     "Distinguish design, implementation, execution evidence, conformance, and deployment claims."),
    ("ACCEPTANCE_CASE_SELECTION", "PROCESS", ("TURN_START", "WORK_SELECTION"),
     "Every implementation step names the acceptance case it closes; shared infrastructure requires an exact rooted blocker."),
    ("EXECUTION_CONTEXT_DISCIPLINE", "PORTABILITY",
     ("TURN_START", "SHELL_SWITCH", "FILESYSTEM_CROSSING", "TEXT_WRITE"),
     "Read the bound execution-context capsule before choosing shell quoting, paths, encodings, line endings, or filesystem operations; do not rely on remembered host rules."),
    ("PORTABILITY_DETERMINISM", "PORTABILITY",
     ("PACKAGING", "RELEASE_PLANNING", "PORTABILITY_CLAIM"),
     "Use relative POSIX keys for deterministic ordering, canonical UTF-8/LF source policy, native WSL storage for the Linux leg, and compare canonical outputs rather than platform-specific receipt roots."),
)

# A scenario is an observable turn class, while rule triggers are the exact
# constitutional moments that class necessarily crosses.  The mapping keeps
# callers from silently omitting required guidance while still allowing them
# to request additional rules for a more specific task.
SCENARIO_TRIGGERS = {
    "CODING": ("TURN_START", "WORK_SELECTION", "STATE_TRANSITION"),
    "PACKAGING": ("TURN_START", "PACKAGING", "ARTIFACT_CREATED"),
    "RELEASE_PLANNING": ("TURN_START", "RELEASE_PLANNING", "ARTIFACT_CREATED"),
    "PORTABILITY_CLAIM": ("TURN_START", "PORTABILITY_CLAIM", "FILESYSTEM_CROSSING"),
    "REVIEW": ("TURN_START", "REVIEW"),
    "RECOVERY": ("TURN_START", "RECOVERY", "STATE_TRANSITION"),
    "REMOTE_WORK": ("TURN_START", "REMOTE_WORK", "CROSS_JURISDICTION"),
}


def _root_value(value: Any, code: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    require(type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value), code)
    return value


def _strings(values: Any, code: str, *, roots: bool = False) -> list[str]:
    require(type(values) is list and values == sorted(set(values)), code)
    for value in values:
        require(type(value) is str and bool(value), code)
        if roots:
            _root_value(value, code)
    return list(values)


def mediation_library() -> dict[str, Any]:
    rules = [{"rule_id": rule_id, "domain": domain, "triggers": list(triggers),
              "exact_context": exact_context,
              "source_system": "UGK" if domain == "UGK" else "PIPPI"}
             for rule_id, domain, triggers, exact_context in _RULES]
    body = {"schema": "mosaic.ucm.pippi-mediation-library.v0.1",
            "rules": rules,
            "scenario_triggers": {key: list(value)
                                  for key, value in sorted(SCENARIO_TRIGGERS.items())},
            "selection_rule": "SCENARIO_REQUIRED_RULES_PLUS_EXPLICIT_REQUESTS",
            "context_is_not_authority": True, **BOUNDARY}
    return {**body, "mediation_library_root": root(body)}


def negotiate_host_mode(*, host_id: str, requested_mode: str,
                        capability_ids: list[str], adapter_root: str | None) -> dict[str, Any]:
    require(type(host_id) is str and bool(host_id), "PIPPI_HOST_ID_INVALID")
    require(requested_mode in HOST_MODES, "PIPPI_HOST_MODE_INVALID")
    capabilities = _strings(capability_ids, "PIPPI_HOST_CAPABILITIES_INVALID")
    _root_value(adapter_root, "PIPPI_HOST_ADAPTER_ROOT_INVALID", optional=True)
    required = {
        "EXECUTABLE_LOCAL": {"ARTIFACT_EXCHANGE", "FILESYSTEM_READ", "PROCESS_EXECUTION"},
        "ARTIFACT_MEDIATED_WEB": {"ARTIFACT_EXCHANGE"},
        "NATIVE_ENFORCED": {"ARTIFACT_EXCHANGE", "TOOL_INTERPOSITION", "VISIBLE_OUTPUT_INTERPOSITION"},
    }[requested_mode]
    missing = sorted(required - set(capabilities))
    # The portable adaptive profile has no independent adapter verifier.  A
    # caller-supplied root and capability list are declarations, so they can
    # never establish enforced-host status on their own.
    enforced = False
    if requested_mode == "NATIVE_ENFORCED":
        status = "REFUSED_NATIVE_ENFORCEMENT_UNSUBSTANTIATED"
        effective_mode = "SIDECAR_PARTIAL"
    elif missing:
        status = "REFUSED_HOST_CAPABILITY_INSUFFICIENT"
        effective_mode = "UNAVAILABLE"
    else:
        status = "PASS"
        effective_mode = requested_mode
    body = {"schema": "mosaic.ucm.pippi-host-capability-profile.v0.1",
            "host_id": host_id, "requested_mode": requested_mode,
            "effective_mode": effective_mode, "capability_ids": capabilities,
            "missing_capability_ids": missing, "adapter_root": adapter_root,
            "enforced_host_verified": enforced, "status": status, **BOUNDARY}
    return {**body, "host_profile_root": root(body)}


def validate_host_profile(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "host_id", "requested_mode", "effective_mode",
        "capability_ids", "missing_capability_ids", "adapter_root", "enforced_host_verified",
        "status", "standing", "authority_effect", "real_a5", "g0", "host_profile_root"})
    expected = negotiate_host_mode(host_id=item["host_id"], requested_mode=item["requested_mode"],
        capability_ids=item["capability_ids"], adapter_root=item["adapter_root"])
    require(item == expected, "PIPPI_HOST_PROFILE_INVALID")
    return deepcopy(item)


def prepare_turn(*, project: dict[str, Any], host_profile: dict[str, Any], sequence: int,
                 previous_turn_root: str | None, scenario: str, requested_rule_ids: list[str],
                 acceptance_case_roots: list[str], journal_head: str | None,
                 execution_context: dict[str, Any]) -> dict[str, Any]:
    project = validate_project(project)
    host_profile = validate_host_profile(host_profile)
    execution_context = validate_execution_context(execution_context)
    require(host_profile["status"] == "PASS", "PIPPI_HOST_PROFILE_NOT_READY")
    require(type(sequence) is int and sequence >= 1, "PIPPI_TURN_SEQUENCE_INVALID")
    require((sequence == 1) == (previous_turn_root is None), "PIPPI_TURN_PREDECESSOR_INVALID")
    _root_value(previous_turn_root, "PIPPI_TURN_PREDECESSOR_INVALID", optional=True)
    _root_value(journal_head, "PIPPI_JOURNAL_HEAD_INVALID", optional=True)
    require(scenario in SCENARIO_TRIGGERS, "PIPPI_SCENARIO_INVALID")
    requested = _strings(requested_rule_ids, "PIPPI_CONTEXT_RULE_INVALID")
    library = mediation_library()
    by_id = {row["rule_id"]: row for row in library["rules"]}
    require(set(requested) <= set(by_id), "PIPPI_CONTEXT_RULE_INVALID")
    triggers = set(SCENARIO_TRIGGERS[scenario])
    required = {row["rule_id"] for row in library["rules"]
                if triggers.intersection(row["triggers"])}
    selected = sorted(set(requested) | required)
    cases = _strings(acceptance_case_roots, "PIPPI_ACCEPTANCE_CASE_ROOT_INVALID", roots=True)
    context = [deepcopy(by_id[rule_id]) for rule_id in selected]
    body = {"schema": "mosaic.ucm.pippi-turn-opening.v0.1",
            "project_id": project["project_id"], "project_root": project["project_root"],
            "host_profile_root": host_profile["host_profile_root"], "sequence": sequence,
            "execution_context_root": execution_context["execution_context_root"],
            "previous_turn_root": previous_turn_root, "scenario": scenario,
            "rule_ids": selected, "context": context,
            "mediation_library_root": library["mediation_library_root"],
            "acceptance_case_roots": cases, "journal_head": journal_head,
            "state": "OPENED", "observable_scope": "ADAPTIVE_HOST_REPORTED_ACTIVITY",
            **BOUNDARY}
    return {**body, "turn_opening_root": root(body)}


def validate_turn_opening(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "project_id", "project_root", "host_profile_root",
        "execution_context_root", "sequence", "previous_turn_root", "scenario", "rule_ids", "context",
        "mediation_library_root", "acceptance_case_roots", "journal_head", "state",
        "observable_scope", "standing", "authority_effect", "real_a5", "g0",
        "turn_opening_root"})
    require(item["schema"] == "mosaic.ucm.pippi-turn-opening.v0.1"
            and type(item["project_id"]) is str and bool(item["project_id"])
            and item["scenario"] in SCENARIO_TRIGGERS
            and type(item["sequence"]) is int and item["sequence"] >= 1,
            "PIPPI_TURN_OPENING_INVALID")
    for value_root in (item["project_root"], item["host_profile_root"], item["execution_context_root"],
                       item["mediation_library_root"]):
        _root_value(value_root, "PIPPI_TURN_OPENING_INVALID")
    _root_value(item["previous_turn_root"], "PIPPI_TURN_OPENING_INVALID", optional=True)
    _root_value(item["journal_head"], "PIPPI_TURN_OPENING_INVALID", optional=True)
    require((item["sequence"] == 1) == (item["previous_turn_root"] is None),
            "PIPPI_TURN_OPENING_INVALID")
    rules = _strings(item["rule_ids"], "PIPPI_TURN_OPENING_INVALID")
    cases = _strings(item["acceptance_case_roots"], "PIPPI_TURN_OPENING_INVALID", roots=True)
    library = mediation_library(); by_id = {row["rule_id"]: row for row in library["rules"]}
    required = {row["rule_id"] for row in library["rules"]
                if set(SCENARIO_TRIGGERS[item["scenario"]]).intersection(row["triggers"])}
    require(set(rules) <= set(by_id) and required <= set(rules)
            and item["context"] == [by_id[rule_id] for rule_id in rules]
            and item["mediation_library_root"] == library["mediation_library_root"],
            "PIPPI_TURN_OPENING_INVALID")
    body = {key: deepcopy(row) for key, row in item.items() if key != "turn_opening_root"}
    require(item["turn_opening_root"] == root(body)
            and all(item[key] == row for key, row in BOUNDARY.items())
            and item["state"] == "OPENED"
            and item["observable_scope"] == "ADAPTIVE_HOST_REPORTED_ACTIVITY"
            and cases == item["acceptance_case_roots"], "PIPPI_TURN_OPENING_INVALID")
    return deepcopy(item)


def build_turn_report(*, opening: dict[str, Any], summary: str,
                      changed_paths: list[str], artifact_roots: list[str],
                      evidence_roots: list[str], unresolved_items: list[dict[str, Any]],
                      next_action: str, claim_class: str) -> dict[str, Any]:
    opening = validate_turn_opening(opening)
    require(type(summary) is str and bool(summary.strip()), "PIPPI_TURN_SUMMARY_INVALID")
    require(type(next_action) is str and bool(next_action.strip()), "PIPPI_NEXT_ACTION_INVALID")
    require(claim_class in {"DESIGN", "IMPLEMENTATION", "EXECUTION_EVIDENCE",
                            "CONFORMANCE", "DEPLOYMENT"}, "PIPPI_CLAIM_CLASS_INVALID")
    paths = _strings(changed_paths, "PIPPI_CHANGED_PATHS_INVALID")
    artifacts = _strings(artifact_roots, "PIPPI_ARTIFACT_ROOTS_INVALID", roots=True)
    evidence = _strings(evidence_roots, "PIPPI_EVIDENCE_ROOTS_INVALID", roots=True)
    require(type(unresolved_items) is list, "PIPPI_UNRESOLVED_ITEMS_INVALID")
    unresolved = []
    for raw in unresolved_items:
        row = exact_keys(raw, {"item_id", "fact_class", "statement"})
        require(type(row["item_id"]) is str and bool(row["item_id"]), "PIPPI_UNRESOLVED_ITEM_INVALID")
        require(row["fact_class"] in FACT_CLASSES, "PIPPI_FACT_CLASS_INVALID")
        require(type(row["statement"]) is str and bool(row["statement"].strip()),
                "PIPPI_UNRESOLVED_ITEM_INVALID")
        unresolved.append(deepcopy(row))
    require([row["item_id"] for row in unresolved] == sorted({row["item_id"] for row in unresolved}),
            "PIPPI_UNRESOLVED_ITEMS_INVALID")
    body = {"schema": "mosaic.ucm.pippi-turn-report.v0.1",
            "turn_opening_root": opening["turn_opening_root"], "project_root": opening["project_root"],
            "sequence": opening["sequence"], "summary": summary, "changed_paths": paths,
            "artifact_roots": artifacts, "evidence_roots": evidence,
            "unresolved_items": unresolved, "next_action": next_action,
            "claim_class": claim_class, "state": "REPORT_SUBMITTED",
            "report_is_agent_observable_record": True, **BOUNDARY}
    return {**body, "turn_report_root": root(body)}


def validate_turn_report(value: Any, *, opening: dict[str, Any]) -> dict[str, Any]:
    opening = validate_turn_opening(opening)
    require(type(value) is dict and value.get("schema") == "mosaic.ucm.pippi-turn-report.v0.1",
            "PIPPI_TURN_REPORT_INVALID")
    expected = build_turn_report(opening=opening, summary=value.get("summary"),
        changed_paths=value.get("changed_paths"), artifact_roots=value.get("artifact_roots"),
        evidence_roots=value.get("evidence_roots"), unresolved_items=value.get("unresolved_items"),
        next_action=value.get("next_action"), claim_class=value.get("claim_class"))
    require(value == expected, "PIPPI_TURN_REPORT_INVALID")
    return deepcopy(value)


def reconcile_turn(*, opening: dict[str, Any], report: dict[str, Any],
                   current_project_root: str, current_journal_head: str | None) -> dict[str, Any]:
    opening = validate_turn_opening(opening)
    report = validate_turn_report(report, opening=opening)
    _root_value(current_project_root, "PIPPI_PROJECT_ROOT_INVALID")
    _root_value(current_journal_head, "PIPPI_JOURNAL_HEAD_INVALID", optional=True)
    require(current_project_root == opening["project_root"], "PIPPI_PROJECT_CHANGED_DURING_TURN")
    require(current_journal_head == opening["journal_head"], "PIPPI_JOURNAL_CHANGED_DURING_TURN")
    body = {"schema": "mosaic.ucm.pippi-turn-reconciliation.v0.1",
            "turn_opening_root": opening["turn_opening_root"],
            "turn_report_root": report["turn_report_root"],
            "project_root": current_project_root, "predecessor_journal_head": current_journal_head,
            "accepted_artifact_roots": report["artifact_roots"],
            "accepted_evidence_roots": report["evidence_roots"],
            "unresolved_items": report["unresolved_items"],
            "next_action": report["next_action"], "state": "RECONCILED",
            "effects_observed_not_inferred": True, **BOUNDARY}
    return {**body, "reconciliation_root": root(body)}


def build_project_capsule(*, profile: str, project: dict[str, Any],
                          host_profile: dict[str, Any], ucm_root: str, ugk_root: str,
                          mediation_library_root: str, journal_head: str | None,
                          turn_root: str | None, public_identity_roots: list[str],
                          members: list[dict[str, Any]]) -> dict[str, Any]:
    require(profile in CAPSULE_PROFILES, "PIPPI_CAPSULE_PROFILE_INVALID")
    project = validate_project(project); host_profile = validate_host_profile(host_profile)
    for value, code in ((ucm_root, "PIPPI_UCM_ROOT_INVALID"), (ugk_root, "PIPPI_UGK_ROOT_INVALID"),
                        (mediation_library_root, "PIPPI_MEDIATION_ROOT_INVALID")):
        _root_value(value, code)
    _root_value(journal_head, "PIPPI_JOURNAL_HEAD_INVALID", optional=True)
    _root_value(turn_root, "PIPPI_TURN_ROOT_INVALID", optional=True)
    identities = _strings(public_identity_roots, "PIPPI_IDENTITY_ROOT_INVALID", roots=True)
    require(type(members) is list, "PIPPI_CAPSULE_MEMBERS_INVALID")
    normalized = []
    for raw in members:
        row = exact_keys(raw, {"path", "sha256", "bytes", "role"})
        require(type(row["path"]) is str and row["path"] and "\\" not in row["path"]
                and not row["path"].startswith("/") and ".." not in row["path"].split("/"),
                "PIPPI_CAPSULE_PATH_INVALID")
        _root_value(row["sha256"], "PIPPI_CAPSULE_HASH_INVALID")
        require(type(row["bytes"]) is int and row["bytes"] >= 0
                and type(row["role"]) is str and bool(row["role"]), "PIPPI_CAPSULE_MEMBER_INVALID")
        normalized.append(deepcopy(row))
    require(normalized == sorted(normalized, key=lambda row: row["path"])
            and len({row["path"] for row in normalized}) == len(normalized),
            "PIPPI_CAPSULE_MEMBERS_INVALID")
    body = {"schema": "mosaic.ucm.pippi-project-capsule.v0.1", "profile": profile,
            "project_id": project["project_id"], "project_root": project["project_root"],
            "host_profile_root": host_profile["host_profile_root"], "ucm_root": ucm_root,
            "ugk_root": ugk_root, "mediation_library_root": mediation_library_root,
            "journal_head": journal_head, "turn_root": turn_root,
            "public_identity_roots": identities, "members": normalized,
            "private_material_present": False, "portable_mode": host_profile["effective_mode"],
            **BOUNDARY}
    return {**body, "capsule_root": root(body)}


def verify_project_capsule(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "profile", "project_id", "project_root",
        "host_profile_root", "ucm_root", "ugk_root", "mediation_library_root",
        "journal_head", "turn_root", "public_identity_roots", "members",
        "private_material_present", "portable_mode", "standing", "authority_effect",
        "real_a5", "g0", "capsule_root"})
    require(item["schema"] == "mosaic.ucm.pippi-project-capsule.v0.1"
            and item["profile"] in CAPSULE_PROFILES
            and type(item["project_id"]) is str and bool(item["project_id"]),
            "PIPPI_CAPSULE_INVALID")
    for value_root in (item["project_root"], item["host_profile_root"], item["ucm_root"],
                       item["ugk_root"], item["mediation_library_root"]):
        _root_value(value_root, "PIPPI_CAPSULE_INVALID")
    _root_value(item["journal_head"], "PIPPI_CAPSULE_INVALID", optional=True)
    _root_value(item["turn_root"], "PIPPI_CAPSULE_INVALID", optional=True)
    _strings(item["public_identity_roots"], "PIPPI_CAPSULE_INVALID", roots=True)
    require(type(item["members"]) is list, "PIPPI_CAPSULE_MEMBERS_INVALID")
    paths = []
    for raw in item["members"]:
        row = exact_keys(raw, {"path", "sha256", "bytes", "role"})
        require(type(row["path"]) is str and row["path"] and "\\" not in row["path"]
                and not row["path"].startswith("/") and ".." not in row["path"].split("/"),
                "PIPPI_CAPSULE_PATH_INVALID")
        _root_value(row["sha256"], "PIPPI_CAPSULE_HASH_INVALID")
        require(type(row["bytes"]) is int and row["bytes"] >= 0
                and type(row["role"]) is str and bool(row["role"]),
                "PIPPI_CAPSULE_MEMBER_INVALID")
        paths.append(row["path"])
    body = {key: deepcopy(row) for key, row in item.items() if key != "capsule_root"}
    require(item["capsule_root"] == root(body)
            and item["private_material_present"] is False
            and item["portable_mode"] in HOST_MODES
            and all(item[key] == row for key, row in BOUNDARY.items()),
            "PIPPI_CAPSULE_INVALID")
    require(paths == sorted(set(paths)), "PIPPI_CAPSULE_MEMBERS_INVALID")
    result = {"schema": "mosaic.ucm.pippi-project-capsule-verification.v0.1",
              "capsule_root": item["capsule_root"], "profile": item["profile"],
              "member_count": len(paths), "status": "PASS", **BOUNDARY}
    return {**result, "verification_root": root(result)}


def interface_conformance() -> dict[str, Any]:
    from .system import CAPABILITY_DEFINITIONS, CAPABILITY_PAYLOAD_FIELDS
    expected = {row[0] for row in CAPABILITY_DEFINITIONS}
    payload = set(CAPABILITY_PAYLOAD_FIELDS)
    missing_payload = sorted(expected - payload)
    duplicate_names = sorted({name for name in expected
                              if sum(row[0] == name for row in CAPABILITY_DEFINITIONS) > 1})
    missing_routes = sorted(row[0] for row in CAPABILITY_DEFINITIONS
                            if not isinstance(row[4], str) or not row[4].strip())
    missing_schemas = sorted(row[0] for row in CAPABILITY_DEFINITIONS
                             if not row[5] or not row[6])
    rows = {row[0]: row for row in CAPABILITY_DEFINITIONS}
    adaptive_route_mismatches = sorted(name for name, command in ADAPTIVE_CLI_ROUTES.items()
        if name not in rows or rows[name][4] != f"pippi {command}")
    missing_adaptive_dispatch = sorted(name for name in ADAPTIVE_CLI_ROUTES if name not in payload)
    exit_code_values = list(PIPPI_EXIT_CODES.values())
    exit_code_conflicts = sorted(code for code in set(exit_code_values)
                                 if exit_code_values.count(code) > 1)
    status = "PASS" if not (missing_payload or duplicate_names or missing_routes or missing_schemas
        or adaptive_route_mismatches or missing_adaptive_dispatch or exit_code_conflicts) else "REFUSED"
    body = {"schema": "mosaic.ucm.interface-conformance.v0.1",
            "capability_count": len(expected), "missing_payload_definitions": missing_payload,
            "duplicate_surface_names": duplicate_names, "missing_routes": missing_routes,
            "missing_schemas": missing_schemas,
            "adaptive_cli_routes": deepcopy(ADAPTIVE_CLI_ROUTES),
            "adaptive_route_mismatches": adaptive_route_mismatches,
            "missing_adaptive_dispatch": missing_adaptive_dispatch,
            "exit_codes": deepcopy(PIPPI_EXIT_CODES),
            "exit_code_conflicts": exit_code_conflicts,
            "status": status, **BOUNDARY}
    return {**body, "conformance_root": root(body)}
