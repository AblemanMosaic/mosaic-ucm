from __future__ import annotations

import json
import unittest

from ucm.release_certification import (
    ReleaseCertificationRefusal,
    build_dkn_binding,
    build_embedded_metadata,
    verify_embedded_metadata,
)


class ReleaseCertificationTests(unittest.TestCase):
    def setUp(self):
        self.rows=[("README.md",b"hello\n"),("src/example.py",b"VALUE = 1\n")]
        self.args={"payload_rows":self.rows,"artifact":"UCM_RUNTIME",
            "completeness":"COMPLETE_RUNTIME","version":"v0.1",
            "engineering_revision":"r011","source_manifest_root":"1"*64,
            "release_identity_root":"2"*64}

    def test_embedded_metadata_is_storage_agnostic_and_verifies(self):
        metadata=build_embedded_metadata(**self.args)
        result=verify_embedded_metadata(metadata=metadata,**self.args)
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["dkn_status"],"DECLARED_UNBOUND")
        self.assertEqual(result["certificate_status"],
                         "READY_FOR_EXTERNAL_DKN_CERTIFICATION")
        certificate=json.loads(metadata["META/SELF-CERTIFICATE.json"])
        self.assertFalse(certificate["storage_location_bound"])
        self.assertEqual(certificate["transport_sha256_scope"],
                         "EXTERNAL_COMPLETE_ARCHIVE_BYTES")

    def test_payload_tamper_refuses(self):
        metadata=build_embedded_metadata(**self.args)
        changed={**self.args,"payload_rows":[("README.md",b"changed\n"),
                                             ("src/example.py",b"VALUE = 1\n")]}
        with self.assertRaises(ReleaseCertificationRefusal):
            verify_embedded_metadata(metadata=metadata,**changed)

    def test_partial_dkn_binding_refuses(self):
        with self.assertRaisesRegex(ReleaseCertificationRefusal,
                                    "RELEASE_DKN_BINDING_INCOMPLETE"):
            build_dkn_binding(public_namespace="mosaic.example",
                              authority_public_key_hex="0"*64)

    def test_unbound_certificate_refuses_injected_signature(self):
        with self.assertRaisesRegex(ReleaseCertificationRefusal,
                                    "UNBOUND_SIGNATURE_REFUSED"):
            build_embedded_metadata(**self.args,signature_hex="0"*128)


if __name__=="__main__":unittest.main()

