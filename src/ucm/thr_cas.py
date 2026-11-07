"""Three-Hash-Rule commitments for content-addressed integration artifacts.

The five commitments stay separate by construction:

* H_s: exact state members;
* H_c: admissibility and governance;
* H_m: normalized meaning;
* H_j: locality and jurisdiction;
* H_r: receipt identity.

``h_body`` binds the complete THR record.  It is integrity, not another
semantic commitment and not authority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


SCHEMA = "mosaic.ucm.thr-cas-manifest.v0.1"
MAPPING = {
    "H_s": "state",
    "H_c": "admissibility",
    "H_m": "meaning",
    "H_j": "locality",
    "H_r": "receipt_identity",
    "h_body": "whole_body_integrity",
}
STATE_SCHEMA = "mosaic.ucm.thr.state.v0.1"
ADMISSIBILITY_SCHEMA = "mosaic.ucm.thr.admissibility.v0.1"
MEANING_SCHEMA = "mosaic.ucm.thr.meaning.v0.1"
LOCALITY_SCHEMA = "mosaic.ucm.thr.locality.v0.1"
RECEIPT_SCHEMA = "mosaic.ucm.thr.receipt-identity.v0.1"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def state_members(payloads: dict[str, bytes]) -> list[dict[str, Any]]:
    rows = []
    for path, raw in sorted(payloads.items()):
        require(type(path) is str and path and type(raw) is bytes,
                "THR_STATE_MEMBER_INVALID")
        rows.append({"path": path, "sha256": _sha(raw), "bytes": len(raw)})
    require(bool(rows), "THR_STATE_MEMBERS_EMPTY")
    return rows


def build_thr_manifest(*, application_id: str, payloads: dict[str, bytes],
                       meaning: dict[str, Any], admissibility: dict[str, Any],
                       locality: dict[str, Any], receipts: dict[str, Any]) -> dict[str, Any]:
    require(type(application_id) is str and bool(application_id),
            "THR_APPLICATION_ID_INVALID")
    states = {"schema": STATE_SCHEMA, "members": state_members(payloads)}
    meaning = {"schema": MEANING_SCHEMA, **deepcopy(meaning)}
    admissibility = {"schema": ADMISSIBILITY_SCHEMA, **deepcopy(admissibility)}
    locality = {"schema": LOCALITY_SCHEMA, **deepcopy(locality)}
    receipts = {"schema": RECEIPT_SCHEMA, **deepcopy(receipts)}
    commitments = {
        "H_s": root(states),
        "H_c": root(admissibility),
        "H_m": root(meaning),
        "H_j": root(locality),
        "H_r": root(receipts),
    }
    body = {
        "schema": SCHEMA,
        "application_id": application_id,
        "semantic_mapping": deepcopy(MAPPING),
        "state": states,
        "admissibility": admissibility,
        "meaning": meaning,
        "locality": locality,
        "receipt_identity": receipts,
        "commitments": commitments,
        **BOUNDARY,
    }
    return {**body, "h_body": root(body)}


def verify_thr_manifest(value: Any, *, payloads: dict[str, bytes]) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "application_id", "semantic_mapping", "state", "admissibility",
        "meaning", "locality", "receipt_identity", "commitments", "standing",
        "authority_effect", "real_a5", "g0", "h_body",
    })
    require(item["schema"] == SCHEMA and item["semantic_mapping"] == MAPPING,
            "THR_MANIFEST_IDENTITY_INVALID")
    require(type(item["application_id"]) is str and bool(item["application_id"]),
            "THR_APPLICATION_ID_INVALID")
    state = exact_keys(item["state"], {"schema", "members"})
    require(state["schema"] == STATE_SCHEMA
            and state["members"] == state_members(payloads),
            "THR_STATE_COMMITMENT_INPUT_MISMATCH")
    sections = {
        "H_s": (item["state"], STATE_SCHEMA),
        "H_c": (item["admissibility"], ADMISSIBILITY_SCHEMA),
        "H_m": (item["meaning"], MEANING_SCHEMA),
        "H_j": (item["locality"], LOCALITY_SCHEMA),
        "H_r": (item["receipt_identity"], RECEIPT_SCHEMA),
    }
    commitments = exact_keys(item["commitments"], set(sections))
    for name, (section, schema) in sections.items():
        require(type(section) is dict and section.get("schema") == schema,
                "THR_SECTION_SCHEMA_INVALID", detail=name)
        require_root(commitments[name])
        require(commitments[name] == root(section),
                "THR_COMMITMENT_INVALID", detail=name)
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "THR_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "h_body"}
    require(item["h_body"] == root(body), "THR_BODY_INTEGRITY_INVALID")
    return deepcopy(item)
