"""Optional ontology correspondence without making RDF/OWL the UCM substrate."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root
from .maturity_semantics import BOUNDARY, seal

RELATIONS = {"BROADER_THAN", "EQUIVALENT", "NARROWER_THAN", "OVERLAPS", "RELATED", "UNRESOLVED"}


def make_correspondence(*, ucm_subject_root: str, ontology_root: str, mappings: list[dict[str, Any]],
                        adjudication: str = "PROPOSED") -> dict[str, Any]:
    require_root(ucm_subject_root); require_root(ontology_root)
    require(adjudication in {"PROPOSED", "REVIEWED", "REJECTED"}, "ONTOLOGY_ADJUDICATION_INVALID")
    checked = []
    for row in mappings:
        item = exact_keys(row, {"ucm_term", "external_term", "relation", "confidence_basis", "evidence_roots"}, "$.mapping")
        require(type(item["ucm_term"]) is str and item["ucm_term"] and type(item["external_term"]) is str and item["external_term"],
                "ONTOLOGY_TERM_INVALID")
        require(item["relation"] in RELATIONS and type(item["confidence_basis"]) is str and item["confidence_basis"],
                "ONTOLOGY_MAPPING_INVALID")
        require(type(item["evidence_roots"]) is list, "ONTOLOGY_EVIDENCE_INVALID")
        for evidence in item["evidence_roots"]: require_root(evidence)
        require(not (item["relation"] == "EQUIVALENT" and not item["evidence_roots"]), "ONTOLOGY_EQUIVALENCE_UNSUPPORTED")
        checked.append(deepcopy(item))
    return seal({"schema": "ucl.ucm.ontology_correspondence.v1", "ucm_subject_root": ucm_subject_root,
        "ontology_root": ontology_root, "mappings": checked, "adjudication": adjudication,
        "substrate_role": "OPTIONAL_INTEROPERABILITY_ADAPTER; NOT_UCM_SEMANTIC_AUTHORITY",
        "identity_rule": "SIMILARITY_NEVER_ESTABLISHES_IDENTITY_OR_AUTHORITY", **BOUNDARY})
