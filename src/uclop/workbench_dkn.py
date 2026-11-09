"""DKN v1 identity correspondence; local derivation grants no federation authority."""
from __future__ import annotations

import copy
import hashlib
from typing import Any

from .canonical import Refusal, exact_keys, require, require_root, root

DKN_SOURCE_SHA256 = "8c59cdfcab184b93d5232799aae1665a4cb6aedd2fd5532b151d292f2dd60707"


def _blake3(data: bytes) -> str:
    try:
        from blake3 import blake3
    except ImportError as error:
        raise Refusal("WORKBENCH_DKN_BLAKE3_DEPENDENCY_REQUIRED") from error
    return blake3(data).hexdigest()


def _public_bytes(public_key_hex: Any) -> bytes:
    require(type(public_key_hex) is str and len(public_key_hex) == 64 and all(ch in "0123456789abcdef" for ch in public_key_hex), "WORKBENCH_DKN_PUBLIC_KEY_INVALID")
    return bytes.fromhex(public_key_hex)


def mosaic_id(public_key_hex: str) -> str:
    """DKN v1: BLAKE3 of the raw 32-byte public key, without a text prefix."""
    return _blake3(_public_bytes(public_key_hex))


def dimension_id(phase_code: str, authority_public_key_hex: str) -> str:
    """Adapter interpretation v1: exact UTF-8 phase bytes || raw authority key."""
    require(type(phase_code) is str and 0 < len(phase_code) <= 128 and not any(0xD800 <= ord(c) <= 0xDFFF for c in phase_code), "WORKBENCH_DKN_PHASE_CODE_INVALID")
    return _blake3(phase_code.encode("utf-8") + _public_bytes(authority_public_key_hex))


def namespace_binding(*, contract_bytes: bytes, phase_code: str, authority_public_key_hex: str, universe_root: str, expected_authority_mosaic_id: str) -> dict[str, Any]:
    require(type(contract_bytes) is bytes and hashlib.sha256(contract_bytes).hexdigest() == DKN_SOURCE_SHA256, "WORKBENCH_DKN_SOURCE_CONTRACT_MISMATCH")
    identity = mosaic_id(authority_public_key_hex)
    require(identity == require_root(expected_authority_mosaic_id), "WORKBENCH_DKN_AUTHORITY_PIN_MISMATCH")
    body = {"schema": "ucl.ucm.workbench.dkn_namespace_binding.v1", "source_contract_sha256": DKN_SOURCE_SHA256, "byte_interpretation": "UTF8_PHASE_CODE_CONCAT_RAW_32_BYTE_PUBLIC_KEY", "phase_code": phase_code, "authority_public_key_hex": authority_public_key_hex, "authority_mosaic_id": identity, "dimension_id": dimension_id(phase_code, authority_public_key_hex), "universe_root": require_root(universe_root), "status": "LOCAL_IDENTITY_DERIVATION_ONLY", "governed_l2_ready": False, "missing_contracts": ["CONDEX_FORMAT_CONTRACT", "EXTERNAL_TRUSTED_PEER_ADMISSION"], "network_authority": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "root": root(body)}


def verify_namespace_binding(value: Any, *, contract_bytes: bytes, expected_authority_mosaic_id: str, expected_dimension_id: str, expected_universe_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "source_contract_sha256", "byte_interpretation", "phase_code", "authority_public_key_hex", "authority_mosaic_id", "dimension_id", "universe_root", "status", "governed_l2_ready", "missing_contracts", "network_authority", "standing", "authority_effect", "root"})
    rebuilt = namespace_binding(contract_bytes=contract_bytes, phase_code=item["phase_code"], authority_public_key_hex=item["authority_public_key_hex"], universe_root=expected_universe_root, expected_authority_mosaic_id=expected_authority_mosaic_id)
    require(item["dimension_id"] == require_root(expected_dimension_id), "WORKBENCH_DKN_DIMENSION_PIN_MISMATCH")
    require(item == rebuilt, "WORKBENCH_DKN_BINDING_FORGED")
    return copy.deepcopy(rebuilt)


def require_governed_l2_ready(value: Any) -> None:
    # A local identity derivation and a valid data signature are insufficient.
    require(False, "WORKBENCH_DKN_GOVERNED_L2_CONTRACTS_UNBOUND")
