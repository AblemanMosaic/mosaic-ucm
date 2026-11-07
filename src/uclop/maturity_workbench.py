"""One supported agent facade over PI, APM, real workers, proofs and integration.

The legacy interface remains an exact compatibility ABI. New operations share
the maturity contracts and recheck the acknowledged context and current head.
"""
from __future__ import annotations
from copy import deepcopy
import base64
import binascii
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from . import autonomous_project_manager as apm
from . import project_intelligence as pi
from .maturity_semantics import BOUNDARY, bytes_ref, ceiling, contract_registry, result_state, seal, verify_ceiling
from .workbench import Workbench, capability_registry as legacy_registry, supported_effect_scope
from .workbench_manager import _head
from .workbench_contracts import reject_raw_secrets
from .workbench_orientation import verify_orientation
from .obligations import validate_inventory
from .workbench_workers import snapshot_source

M0_PIN = '5b38c2b67f8fac067b2275af9bb6c6de98950078c6803cdd1522cd3f9d36ac32'
EXTRA_SURFACES = {
    'DISCOVER': 'PURE_COMPUTATION', 'SEMANTIC_CONTRACTS': 'PURE_COMPUTATION',
    'PROJECT_DASHBOARD': 'READ_ONLY', 'PREPARE_AUTONOMOUS_PLAN': 'PURE_COMPUTATION',
    'VERIFY_PROOF_GATE': 'PURE_COMPUTATION', 'PREPARE_MOSAICOS_M1': 'PURE_COMPUTATION',
    'EXPORT_MATURITY_CONTEXT': 'READ_ONLY', 'VERIFY_MATURITY_CONTEXT': 'READ_ONLY',
    'INSPECT_APPLICATION_REQUEST': 'PURE_COMPUTATION', 'VERIFY_APPLICATION_RETURN': 'PURE_COMPUTATION',
}


def capability_registry() -> dict:
    surfaces = [{'name': name, 'effect_scope': effect, 'readiness_required': True}
                for name, effect in EXTRA_SURFACES.items()]
    surfaces += [{**row, 'name': 'WORKBENCH.' + row['name'],
                  'effect_scope': supported_effect_scope(row['name']),
                  **({'legacy_effect_scope': row['effect_scope']} if row['name'] == 'ATTEST_NOT_EXECUTED' else {})}
                 for row in legacy_registry()['surfaces']]
    return seal({'schema': 'ucl.ucm.maturity.capability_registry.v1',
        'subject': 'UCL-UCM-MATURITY-CONSOLIDATION-c1', 'surfaces': sorted(surfaces, key=lambda x: x['name']),
        'legacy_registry_root': legacy_registry()['registry_root'], 'semantic_registry_root': contract_registry()['root'],
        'application_kit': 'uclop.maturity_application', 'mosaicos_deep_integration': 'UNBOUND_PENDING_EXACT_ARTIFACTS',
        'signers': 'OPAQUE_EXTERNAL_PROVIDER_FOR_REAL_IDENTITIES', 'hostile_code_sandbox': 'UNBOUND_EXTERNAL_OS_SANDBOX',
        'authority_ceiling': ceiling(allowed_effects=['READ_WORKSPACE', 'WRITE_WORKSPACE', 'DELETE_WORKSPACE', 'LOCAL_PROCESS']),
        **BOUNDARY})


class MaturityWorkbench:
    def __init__(self, legacy: Workbench, *, expected_registry_root: str,
                 proof_plans: dict[str, dict] | None = None, expected_proof_plan_roots: dict[str, str] | None = None,
                 m0_archive: bytes | None = None, expected_m0_sha256: str = M0_PIN,
                 application_integrations: dict[str, dict] | None = None):
        require(type(legacy) is Workbench, 'MATURITY_REAL_WORKBENCH_REQUIRED')
        require(capability_registry()['root'] == require_root(expected_registry_root), 'MATURITY_REGISTRY_PIN_MISMATCH')
        self.legacy = legacy
        self.registry_root = expected_registry_root
        self.proof_plans = {} if proof_plans is None else deepcopy(proof_plans)
        self.proof_pins = {} if expected_proof_plan_roots is None else deepcopy(expected_proof_plan_roots)
        require(type(self.proof_plans) is dict and type(self.proof_pins) is dict
                and set(self.proof_plans) == set(self.proof_pins), 'MATURITY_PROOF_CONFIGURATION_INVALID')
        from .maturity_proof import verify_gate_plan
        for name, plan in self.proof_plans.items():
            require(type(name) is str and 0 < len(name) <= 128, 'MATURITY_PROOF_PLAN_ID_INVALID')
            verify_gate_plan(plan, **self._proof_arguments(name))
        self.m0 = None
        if m0_archive is not None:
            from .maturity_mosaicos import prepare_m1_from_m0_archive
            self.m0 = prepare_m1_from_m0_archive(m0_archive, expected_archive_sha256=require_root(expected_m0_sha256))
        self.applications = {} if application_integrations is None else deepcopy(application_integrations)
        require(type(self.applications) is dict, 'MATURITY_APPLICATION_CONFIGURATION_INVALID')
        from .maturity_application import verify_integration_request
        for identifier, configuration in self.applications.items():
            require(type(identifier) is str and 0 < len(identifier) <= 128, 'MATURITY_APPLICATION_ID_INVALID')
            exact_keys(configuration, {'request', 'input_members', 'expected_request_root', 'expected_pins', 'expected_case_ids'})
            checked_request = verify_integration_request(**configuration)
            pins = checked_request['pins']
            require(pins['project_snapshot_root'] == legacy.manager.project['snapshot_root']
                    and pins['work_plan_root'] == legacy.manager.plan['reference_proposal']['plan_root']
                    and pins['source']['digest'] == legacy.orientation['source_root']
                    and pins['source']['dialect'] == 'uclop-json-v1', 'MATURITY_APPLICATION_READY_CONTRACT_MISMATCH')

    def _proof_arguments(self, name: str) -> dict:
        require(name in self.proof_plans, 'MATURITY_PROOF_PLAN_NOT_CONFIGURED')
        plan = self.proof_plans[name]
        require(type(plan) is dict and type(plan.get('inventory')) is dict, 'MATURITY_PROOF_PLAN_INVALID')
        source = validate_inventory(plan['inventory'])
        return {'expected_subject_root': self.legacy.orientation['source_root'],
            'expected_plan_root': self.proof_pins[name], 'expected_inventory_root': source['inventory_root'],
            'expected_obligation_ids': [item['id'] for item in source['obligations']]}

    def _legacy_request(self, request: dict, surface: str, payload: dict) -> dict:
        return {'schema': 'ucl.ucm.workbench.request.v1', 'surface': surface, 'payload': payload,
            'context_root': request['context_root'], 'request_id': request['request_id'], 'expected_head': request['expected_head']}

    def _context(self, request: dict, now: int) -> dict:
        capsule = self.legacy.dispatch(self._legacy_request(request, 'EXPORT_CAPSULE', {}), now=now)['result']
        return seal({'schema': 'ucl.ucm.maturity.context.v1', 'orientation_root': self.legacy.orientation['root'],
            'source_root': self.legacy.orientation['source_root'], 'project_root': self.legacy.manager.project['snapshot_root'],
            'plan_root': self.legacy.manager.plan['plan_root'], 'registry_root': self.registry_root,
            'current_head': deepcopy(self.legacy.manager.current_head), 'legacy_capsule': capsule,
            'proof_plan_roots': deepcopy(self.proof_pins), 'm0_preparation_root': None if self.m0 is None else self.m0['root'],
            'application_request_roots': {name: config['expected_request_root'] for name, config in sorted(self.applications.items())},
            'meaning': 'CURRENT_CONTEXT_AND_CUSTODY_ONLY; NO_TRANSFER_OF_AUTHORITY', **BOUNDARY})

    def dispatch(self, request: Any, *, now: int) -> dict:
        item = exact_keys(request, {'schema', 'surface', 'payload', 'context_root', 'request_id', 'expected_head', 'registry_root'})
        # Validate the entire data envelope before a recovery route can persist
        # an attestation or another domain route can perform an effect.
        canonical_bytes(item)
        require(item['schema'] == 'ucl.ucm.maturity.request.v1', 'MATURITY_REQUEST_SCHEMA_INVALID')
        require(item['registry_root'] == self.registry_root == capability_registry()['root'], 'MATURITY_REGISTRY_PIN_MISMATCH')
        require(type(item['surface']) is str and type(item['payload']) is dict, 'MATURITY_REQUEST_INVALID')
        reject_raw_secrets(item['payload'])
        require(type(now) is int, 'MATURITY_TIME_INVALID')
        surface, payload = item['surface'], item['payload']
        expected_head = _head(item['expected_head'])
        require(expected_head == self.legacy.manager.current_head, 'MATURITY_HEAD_STALE')
        # Ordinary maturity operations require an ordinary current orientation.
        # Legacy bootstrap recovery routes retain their exact narrower gate.
        bootstrap = {'WORKBENCH.ATTEST_NOT_EXECUTED', 'WORKBENCH.PREPARE_RECOVERY_AUTHORIZATION'}
        if not surface.startswith('WORKBENCH.'):
            verify_orientation(self.legacy.orientation, external_pins=self.legacy.pins, now=now,
                               expected_head=self.legacy.orientation['current_head'])
            require(snapshot_source(self.legacy.worker.source) == self.legacy.worker.manifest, 'MATURITY_SOURCE_CHANGED')
        if surface not in bootstrap:
            self.legacy.dispatch(self._legacy_request(item, 'STATUS', {}), now=now)
        if surface.startswith('WORKBENCH.'):
            name = surface[len('WORKBENCH.'):]
            require(name in {row['name'] for row in legacy_registry()['surfaces']}, 'MATURITY_SURFACE_UNKNOWN')
            result = self.legacy.dispatch(self._legacy_request(item, name, payload), now=now)
            effect = supported_effect_scope(name)
        elif surface == 'DISCOVER':
            exact_keys(payload, set()); result = capability_registry(); effect = EXTRA_SURFACES[surface]
        elif surface == 'SEMANTIC_CONTRACTS':
            exact_keys(payload, set()); result = contract_registry(); effect = EXTRA_SURFACES[surface]
        elif surface == 'PROJECT_DASHBOARD':
            exact_keys(payload, set())
            require(snapshot_source(self.legacy.worker.source) == self.legacy.worker.manifest, 'MATURITY_SOURCE_CHANGED')
            pi.validate_project(self.legacy.manager.project, expected_source_root=self.legacy.orientation['source_root'])
            result = pi.project_dashboard(self.legacy.manager.project, self.legacy.worker.source)
            effect = EXTRA_SURFACES[surface]
        elif surface == 'PREPARE_AUTONOMOUS_PLAN':
            exact_keys(payload, {'changed_ids', 'changed_paths', 'objective'})
            pi.validate_project(self.legacy.manager.project, expected_source_root=self.legacy.orientation['source_root'])
            result = apm.make_plan(self.legacy.manager.project, payload['changed_ids'], payload['changed_paths'], objective=payload['objective'])
            effect = EXTRA_SURFACES[surface]
        elif surface == 'VERIFY_PROOF_GATE':
            exact_keys(payload, {'plan_id', 'proof_bundles'})
            require(type(payload['plan_id']) is str, 'MATURITY_PROOF_PLAN_ID_INVALID')
            args = self._proof_arguments(payload['plan_id'])
            from .maturity_proof import evaluate_gate
            result = evaluate_gate(self.proof_plans[payload['plan_id']], payload['proof_bundles'], **args)
            effect = EXTRA_SURFACES[surface]
        elif surface == 'PREPARE_MOSAICOS_M1':
            exact_keys(payload, set()); require(self.m0 is not None, 'MATURITY_M0_NOT_CONFIGURED')
            result = deepcopy(self.m0); effect = EXTRA_SURFACES[surface]
        elif surface in {'INSPECT_APPLICATION_REQUEST', 'VERIFY_APPLICATION_RETURN'}:
            fields = {'integration_id'} if surface == 'INSPECT_APPLICATION_REQUEST' else {'integration_id', 'return_packet', 'returned_members_base64'}
            exact_keys(payload, fields)
            require(type(payload['integration_id']) is str and payload['integration_id'] in self.applications, 'MATURITY_APPLICATION_NOT_CONFIGURED')
            config = self.applications[payload['integration_id']]
            if surface == 'INSPECT_APPLICATION_REQUEST':
                result = deepcopy(config['request'])
            else:
                encoded = payload['returned_members_base64']
                require(type(encoded) is dict and len(encoded) <= 256
                        and all(type(k) is str and type(v) is str for k, v in encoded.items()), 'MATURITY_APPLICATION_MEMBER_ENCODING_INVALID')
                require(sum(len(v) for v in encoded.values()) <= 24 * 1024 * 1024, 'MATURITY_APPLICATION_ENVELOPE_LIMIT')
                try:
                    returned = {key: base64.b64decode(value, validate=True) for key, value in encoded.items()}
                except (binascii.Error, ValueError) as error:
                    require(False, 'MATURITY_APPLICATION_MEMBER_ENCODING_INVALID')
                from .maturity_application import verify_integration_return
                result = verify_integration_return(payload['return_packet'], returned_members=returned, **config)
            effect = EXTRA_SURFACES[surface]
        elif surface in {'EXPORT_MATURITY_CONTEXT', 'VERIFY_MATURITY_CONTEXT'}:
            if surface == 'VERIFY_MATURITY_CONTEXT':
                exact_keys(payload, {'capsule', 'expected_root'})
            else:
                exact_keys(payload, set())
            result = self._context(item, now)
            if surface == 'VERIFY_MATURITY_CONTEXT':
                require(payload['expected_root'] == result['root'] and canonical_bytes(payload['capsule']) == canonical_bytes(result), 'MATURITY_CONTEXT_STALE_OR_SUBSTITUTED')
            effect = EXTRA_SURFACES[surface]
        else:
            require(False, 'MATURITY_SURFACE_UNKNOWN')
        # This records evaluation of a surface. Its domain-specific result retains
        # any FAIL, RESIDUAL, UNKNOWN or INCOMPLETE outcome without promotion.
        state = result_state(execution=['PASS'], completion='PENDING', observed_effects=['READ_WORKSPACE'],
                             inputs=[bytes_ref(canonical_bytes(item), 'CONTRACT')], outputs=[bytes_ref(canonical_bytes(result), 'RECEIPT')])
        return seal({'schema': 'ucl.ucm.maturity.response.v1', 'surface': surface,
            'request_root': root(item), 'context_root': self.legacy.orientation['root'],
            'current_head': deepcopy(self.legacy.manager.current_head), 'registry_root': self.registry_root,
            'effect_scope': effect, 'evaluation_scope': 'READINESS_AND_ENVELOPE_ONLY; DOMAIN_EFFECTS_RETAINED_IN_RESULT_RECEIPTS',
            'evaluation_state': state, 'result': result, **BOUNDARY})
