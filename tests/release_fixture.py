from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

from uclop.canonical import canonical_bytes, root
from ucm.release_certification import (BOUNDARY,build_dkn_binding,
                                       build_embedded_metadata)


def _write(path: Path, payload: list[tuple[str,bytes]], metadata: dict[str,bytes]) -> dict:
    rows = sorted([*payload, *metadata.items()])
    members = [{"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data)} for name, data in rows]
    body = {"schema": "mosaic.ucm.artifact-manifest.v0.1",
            "artifact": "TEST_PUBLICATION_ARTIFACT", "version": "v0.1",
            "completeness": "COMPLETE_TEST_FIXTURE", "members": members,
            "member_count": len(members), "logical_bytes": sum(row["bytes"] for row in members),
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
    manifest = {**body, "root": root(body)}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("MANIFEST.json", canonical_bytes(manifest) + b"\n")
        for name, data in rows:
            archive.writestr(name, data)
    data = path.read_bytes()
    return {"path": path, "sha256": hashlib.sha256(data).hexdigest(),
            "metadata": {name: json.loads(value) for name, value in metadata.items()}}


def write_unbound_release_archive(path: Path, *, revision: str = "r008") -> dict:
    payload = [("payload.txt", b"exact publication fixture\n")]
    metadata = build_embedded_metadata(
        payload_rows=payload, artifact="TEST_PUBLICATION_ARTIFACT",
        completeness="COMPLETE_TEST_FIXTURE", version="v0.1",
        engineering_revision=revision, source_manifest_root="1" * 64,
        release_identity_root="2" * 64)
    return _write(path,payload,metadata)


def write_signed_release_archive(path: Path, *, revision: str = "r008") -> dict:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    payload = [("payload.txt", b"exact publication fixture\n")]
    private = Ed25519PrivateKey.generate()
    public_hex = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw).hex()
    dkn = build_dkn_binding(public_namespace="mosaic.ucm.v0.1",
                            authority_public_key_hex=public_hex,
                            dimension_id="3"*64,passport_root="4"*64)
    state_rows=[{"path":name,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
                for name,data in sorted(payload)]
    state_body={"schema":"mosaic.ucm.release-state-manifest.v0.1",
                "artifact":"TEST_PUBLICATION_ARTIFACT","version":"v0.1",
                "engineering_revision":revision,"members":state_rows,
                "member_count":len(state_rows),"logical_bytes":sum(row["bytes"] for row in state_rows),
                "scope":"LOGICAL_PAYLOAD_EXCLUDING_META_AND_TRANSPORT_CONTAINER",**BOUNDARY}
    state_root=root(state_body)
    meaning={"schema":"mosaic.ucm.thr.meaning.v0.1","product":"Universal Constitutional Machine",
             "artifact_role":"TEST_PUBLICATION_ARTIFACT","completeness":"COMPLETE_TEST_FIXTURE",
             "version":"v0.1","engineering_revision":revision,"publisher":"Ableman Mosaic"}
    admissibility={"schema":"mosaic.ucm.thr.admissibility.v0.1",
                   "source_manifest_root":"1"*64,"release_identity_root":"2"*64,
                   "authority_ceiling":dict(BOUNDARY),"publication_requires_explicit_human_authorization":True}
    locality={"schema":"mosaic.ucm.thr.locality.v0.1","dkn_binding_root":dkn["dkn_binding_root"],
              "public_namespace":dkn["public_namespace"],"dkn_status":"BOUND_EXTERNAL",
              "storage_location":"UNBOUND"}
    receipts={"schema":"mosaic.ucm.thr.receipt-identity.v0.1",
              "qualification_receipt":"EXTERNAL_TRANSPORT_BOUND_RECEIPT",
              "operator_tier1_evidence":"EXTERNAL_EXACT_ARTIFACT_EVIDENCE",
              "self_certificate_status":"PENDING_SIGNATURE"}
    state_section={"schema":"mosaic.ucm.thr.state.v0.1","state_root":state_root,
                   "member_count":len(state_rows),"logical_bytes":sum(row["bytes"] for row in state_rows)}
    commitments={"H_s":root(state_section),"H_c":root(admissibility),"H_m":root(meaning),
                 "H_j":root(locality),"H_r":root(receipts)}
    thr_body={"schema":"mosaic.ucm.release-thr-manifest.v0.1",
              "artifact":"TEST_PUBLICATION_ARTIFACT",
              "semantic_mapping":{"H_s":"state","H_c":"admissibility","H_m":"meaning",
                                  "H_j":"locality","H_r":"receipt_identity","h_body":"whole_body_integrity"},
              "state":state_section,"admissibility":admissibility,"meaning":meaning,
              "locality":locality,"receipt_identity":receipts,"commitments":commitments,**BOUNDARY}
    signing_body={"schema":"mosaic.ucm.release-self-certificate-signing-body.v0.1",
                  "artifact":"TEST_PUBLICATION_ARTIFACT","version":"v0.1",
                  "engineering_revision":revision,"state_root":state_root,
                  "thr_body_root":root(thr_body),"dkn_binding_root":dkn["dkn_binding_root"],
                  "source_manifest_root":"1"*64,"release_identity_root":"2"*64}
    signature=private.sign(canonical_bytes(signing_body)).hex()
    metadata=build_embedded_metadata(
        payload_rows=payload,artifact="TEST_PUBLICATION_ARTIFACT",
        completeness="COMPLETE_TEST_FIXTURE",version="v0.1",
        engineering_revision=revision,source_manifest_root="1"*64,
        release_identity_root="2"*64,dkn_binding=dkn,signature_hex=signature)
    return _write(path,payload,metadata)
