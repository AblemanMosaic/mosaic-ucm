from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from uclop.canonical import canonical_bytes, root

from ucm.pippi_constitution import (
    build_collaborator_binding,
    build_ccp_transition_binding,
    build_constitutional_standards_atlas,
    build_credential_reference,
    build_pipeline_model,
    build_signed_change_capsule,
    build_signed_publication_receipt,
    build_signed_retrieval_receipt,
    build_storage_locator,
    change_capsule_signing_body,
    credential_broker_policy,
    explain_context_selection,
    explain_pipeline_transition,
    explain_standard_rule,
    publication_receipt_signing_body,
    retrieval_receipt_signing_body,
    validate_signed_change_capsule,
    validate_signed_publication_receipt,
    validate_signed_retrieval_receipt,
)
from ucm.identity import create_passport, mosaic_id
from ucm.pippi_credentials import (open_local_credential, seal_local_credential,
                                   validate_local_credential_envelope,
                                   write_local_credential)
from ucm import invoke
from test_ccp_admissibility_positive import fixture as ccp_fixture


R = [root({"r": index}) for index in range(30)]
TEST_TMP = Path(__file__).resolve().parents[1] / ".test-tmp"


class PippiConstitutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        cls.public = cls.private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    def test_atlas_has_total_mediation_rule_denominator(self) -> None:
        atlas = build_constitutional_standards_atlas()
        self.assertEqual(atlas["rule_count"], 14)
        self.assertEqual(atlas["co_projection_count"], 5)
        self.assertTrue(all(row["ablation_failure_modes"] for row in atlas["rules"]))
        self.assertTrue(all(not row["identity_equivalence_claimed"]
                            for row in atlas["co_projections"]))

    def test_pipeline_model_is_explainable_and_non_authorizing(self) -> None:
        model = build_pipeline_model()
        self.assertEqual(model["state_count"], 11)
        self.assertEqual(model["transition_count"], 10)
        explanation = explain_pipeline_transition("PREPARE_DISPATCH")
        self.assertEqual(explanation["next_action"], "OBTAIN_CCP_CURRENT_USE_DECISION")
        self.assertFalse(explanation["transition"]["automatic_authority_grant"])
        self.assertEqual(explain_standard_rule("AUTHORITY_BOUNDARY")["rule"]["classification"], "CM1")

    def test_context_explanation_shows_exact_reasons_and_variables(self) -> None:
        result = explain_context_selection(
            scenario="CODING", requested_rule_ids=["VERSION_POLICY"],
            variables={"project_root": R[0], "revision": "r029"})
        self.assertIn("ACCEPTANCE_CASE_SELECTION", result["required_rule_ids"])
        self.assertEqual(result["variables"]["revision"], "r029")
        self.assertTrue(all(row["reason"] in {"SCENARIO_REQUIRED", "EXPLICIT_REQUEST"}
                            for row in result["reason_paths"]))

    def test_signed_change_capsule_binds_base_delta_identity_and_dkn(self) -> None:
        fields = dict(base_root=R[0], result_root=R[1],
            changed_objects=[{"path": "src/example.c", "before_sha256": R[2],
                              "after_sha256": R[3], "semantic_role": "IMPLEMENTATION"}],
            acceptance_case_roots=[R[4]], standard_roots=[R[5]], policy_pack_roots=[R[6]],
            author_identity_root=mosaic_id(self.public), author_public_key_hex=self.public,
            dkn_namespace="mosaic.ucm.collaborator", dkn_epoch=1, revision="r029")
        signing = change_capsule_signing_body(**fields)
        capsule = build_signed_change_capsule(
            signature_hex=self.private.sign(canonical_bytes(signing)).hex(), **fields)
        self.assertEqual(validate_signed_change_capsule(capsule), capsule)
        tampered = deepcopy(capsule)
        tampered["signing_body"]["result_root"] = R[8]
        with self.assertRaisesRegex(ValueError, "PIPPI_CHANGE_SIGNATURE_INVALID|PIPPI_CHANGE_CAPSULE_INVALID"):
            validate_signed_change_capsule(tampered)
        mismatched = dict(fields)
        mismatched["author_identity_root"] = R[7]
        with self.assertRaisesRegex(ValueError, "PIPPI_CHANGE_AUTHOR_IDENTITY_KEY_MISMATCH"):
            change_capsule_signing_body(**mismatched)

    def test_credentials_are_opaque_nonportable_references(self) -> None:
        policy = credential_broker_policy()
        reference = build_credential_reference(
            provider_id="GITHUB", account_identity="AblemanMosaic",
            scopes=["CONTENTS_WRITE"], secret_handle="pippi-credential://github/main",
            storage_policy_root=policy["credential_broker_policy_root"],
            expires_at_epoch=None)
        self.assertFalse(reference["secret_material_present"])
        self.assertFalse(reference["portable"])
        with self.assertRaisesRegex(ValueError, "PIPPI_CREDENTIAL_HANDLE_INVALID"):
            build_credential_reference(provider_id="GITHUB", account_identity="a", scopes=[],
                secret_handle="pippi-credential://x?token=secret", storage_policy_root=R[1],
                expires_at_epoch=None)

    def test_storage_receipt_verifies_actual_artifact_and_key_bound_identities(self) -> None:
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            artifact = Path(folder) / "artifact.bin"
            artifact.write_bytes(b"exact r029 artifact")
            artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
            locator = build_storage_locator(provider_id="MEGA", locator="mega://folder/object",
                artifact_sha256=artifact_sha, provider_account_root=R[1],
                credential_reference_root=R[2])
            fields = dict(artifact_sha256=artifact_sha, state_root=R[3], semantic_root=R[4],
                metadata_root=R[5], governance_root=R[6], dkn_binding_root=R[7],
                storage_locator=locator, publisher_identity_root=mosaic_id(self.public),
                publisher_public_key_hex=self.public, published_epoch=3)
            signing = publication_receipt_signing_body(**fields)
            receipt = build_signed_publication_receipt(
                signature_hex=self.private.sign(canonical_bytes(signing)).hex(), **fields)
            self.assertEqual(validate_signed_publication_receipt(receipt), receipt)
            retrieval_fields = dict(publication_receipt=receipt,
                retrieved_artifact_path=str(artifact),
                retriever_identity_root=mosaic_id(self.public),
                retriever_public_key_hex=self.public, retrieved_epoch=4)
            retrieval_signing = retrieval_receipt_signing_body(**retrieval_fields)
            retrieval = build_signed_retrieval_receipt(
                signature_hex=self.private.sign(canonical_bytes(retrieval_signing)).hex(),
                **retrieval_fields)
            self.assertEqual(retrieval["custody_status"], "RETRIEVED_AND_HASH_VERIFIED")
            self.assertEqual(validate_signed_retrieval_receipt(
                retrieval, publication_receipt=receipt), retrieval)
            changed_retrieval = deepcopy(retrieval)
            changed_retrieval["signing_body"]["artifact_sha256"] = R[9]
            with self.assertRaisesRegex(ValueError, "PIPPI_RETRIEVAL_PUBLICATION_MISMATCH"):
                validate_signed_retrieval_receipt(
                    changed_retrieval, publication_receipt=receipt)
            credential_locator = deepcopy(locator)
            credential_locator["locator"] = "mega://folder/object?token=secret"
            credential_body = {key: value for key, value in credential_locator.items()
                if key != "storage_locator_root"}
            credential_locator["storage_locator_root"] = root(credential_body)
            credential_fields = dict(fields)
            credential_fields["storage_locator"] = credential_locator
            with self.assertRaisesRegex(ValueError,
                                        "PIPPI_STORAGE_LOCATOR_CONTAINS_CREDENTIAL"):
                publication_receipt_signing_body(**credential_fields)
            artifact.write_bytes(b"different")
            with self.assertRaisesRegex(ValueError, "PIPPI_RETRIEVAL_ARTIFACT_HASH_MISMATCH"):
                retrieval_receipt_signing_body(**retrieval_fields)
            bad_identity = dict(fields)
            bad_identity["publisher_identity_root"] = R[8]
            with self.assertRaisesRegex(ValueError, "PIPPI_PUBLICATION_IDENTITY_KEY_MISMATCH"):
                publication_receipt_signing_body(**bad_identity)

    def test_collaborator_binding_uses_verified_passport_and_dkn(self) -> None:
        binding = build_collaborator_binding(passport=create_passport(self.public),
            dkn_namespace="mosaic.ucm.collaborator", dkn_epoch=2)
        self.assertEqual(binding["dkn"]["stable_nonce"], "mosaic.ucm.v0.1")
        self.assertFalse(binding["authority_granted"])

    def test_local_credential_vault_is_encrypted_and_nonportable(self) -> None:
        reference = build_credential_reference(provider_id="GITHUB",
            account_identity="AblemanMosaic", scopes=["CONTENTS_WRITE"],
            secret_handle="pippi-credential://github/main",
            storage_policy_root=credential_broker_policy()["credential_broker_policy_root"],
            expires_at_epoch=None)
        envelope = seal_local_credential(secret=b"example-not-a-real-token",
            passphrase="correct horse battery staple", credential_reference=reference)
        self.assertNotIn("example", str(envelope))
        self.assertEqual(open_local_credential(envelope=envelope,
            passphrase="correct horse battery staple", credential_reference=reference),
            b"example-not-a-real-token")
        second = seal_local_credential(secret=b"example-not-a-real-token",
            passphrase="correct horse battery staple", credential_reference=reference)
        self.assertNotEqual(envelope["aead"]["nonce_base64"], second["aead"]["nonce_base64"])
        self.assertEqual(validate_local_credential_envelope(envelope), envelope)
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            target = Path(folder) / "credential.json"
            with patch("ucm.pippi_credentials.secrets.token_hex", return_value="fixed"):
                pending = target.with_name(target.name + ".fixed.pending")
                pending.write_bytes(b"preexisting")
                with self.assertRaises(FileExistsError):
                    write_local_credential(target, envelope)
                self.assertEqual(pending.read_bytes(), b"preexisting")
            invalid = deepcopy(envelope)
            invalid["portable"] = True
            invalid_body = {key: value for key, value in invalid.items()
                            if key != "credential_envelope_root"}
            invalid["credential_envelope_root"] = root(invalid_body)
            untouched_parent = Path(folder) / "must-not-exist"
            with self.assertRaisesRegex(ValueError, "PIPPI_CREDENTIAL_ENVELOPE_INVALID"):
                write_local_credential(untouched_parent / "credential.json", invalid)
            self.assertFalse(untouched_parent.exists())

    def test_ccp_binding_holds_nonadmitted_transition(self) -> None:
        records = ccp_fixture(operation="PROPOSE_PUBLICATION")
        evaluation = {"decision": records["decision"],
            "current_use_snapshot": records["use"], "evidence_snapshot": records["evidence"],
            "jurisdiction_profile": records["profile"],
            "enforcement_perimeter": records["perimeter"],
            "correspondence": records["correspondence"],
            "expected_anchors": records["anchors"]}
        admitted = build_ccp_transition_binding(
            transition_id="PROPOSE_PUBLICATION", ccp_evaluation=evaluation)
        self.assertTrue(admitted["transition_ready"])
        forged = deepcopy(evaluation)
        forged["decision"]["decision"] = "REFUSE"
        forged["decision"]["gateway_disposition"] = "NOT_ELIGIBLE_FOR_EFFECT"
        forged["decision"]["decision_root"] = root({key: value for key, value
            in forged["decision"].items() if key != "decision_root"})
        with self.assertRaisesRegex(ValueError, "CCP_ADMISSIBILITY_DECISION_INVALID"):
            build_ccp_transition_binding(
                transition_id="PROPOSE_PUBLICATION", ccp_evaluation=forged)
        ready = build_ccp_transition_binding(transition_id="ORIENT_PROJECT",
            ccp_evaluation=None)
        self.assertTrue(ready["transition_ready"])

    def test_public_abi_exposes_atlas_pipeline_and_explanations(self) -> None:
        atlas = invoke({"schema":"mosaic.ucm.request.v0.1","request_id":"r28-atlas",
            "surface":"DISCOVER_CONSTITUTIONAL_STANDARDS_ATLAS","payload":{}})
        model = invoke({"schema":"mosaic.ucm.request.v0.1","request_id":"r28-pipeline",
            "surface":"DISCOVER_PIPPI_PIPELINE_MODEL","payload":{}})
        explanation = invoke({"schema":"mosaic.ucm.request.v0.1","request_id":"r28-rule",
            "surface":"EXPLAIN_PIPPI_STANDARD_RULE","payload":{"rule_id":"AUTHORITY_BOUNDARY"}})
        self.assertEqual(atlas["result"]["atlas_root"], build_constitutional_standards_atlas()["atlas_root"])
        self.assertEqual(model["result"]["pipeline_model_root"], build_pipeline_model()["pipeline_model_root"])
        self.assertEqual(explanation["result"]["rule"]["rule_id"], "AUTHORITY_BOUNDARY")


if __name__ == "__main__":
    unittest.main()
