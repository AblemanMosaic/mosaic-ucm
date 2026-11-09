"""Local encrypted credential custody for P/PPI.

Secrets never enter the generic capability ABI, journals, project capsules, or
portable archives.  This module is called only by a trusted local host adapter.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import os
from pathlib import Path
import secrets
import stat
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from uclop.canonical import canonical_bytes, exact_keys, require, root

from .pippi_global import BOUNDARY
from .pippi_security import protect_private_file, verify_private_file


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(value: Any, code: str) -> bytes:
    require(type(value) is str, code)
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except Exception as exc:
        raise ValueError(code) from exc


def _key(passphrase: str, salt: bytes) -> bytes:
    require(type(passphrase) is str and len(passphrase) >= 12,
            "PIPPI_CREDENTIAL_PASSPHRASE_WEAK")
    return Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(
        passphrase.encode("utf-8"))


def seal_local_credential(*, secret: bytes, passphrase: str,
                          credential_reference: dict[str, Any]) -> dict[str, Any]:
    require(type(secret) is bytes and bool(secret), "PIPPI_CREDENTIAL_SECRET_INVALID")
    require(type(credential_reference) is dict
            and credential_reference.get("secret_material_present") is False
            and credential_reference.get("portable") is False,
            "PIPPI_CREDENTIAL_REFERENCE_INVALID")
    salt = os.urandom(16)
    nonce = os.urandom(12)
    associated = canonical_bytes(credential_reference)
    ciphertext = AESGCM(_key(passphrase, salt)).encrypt(nonce, secret, associated)
    body = {"schema": "mosaic.ucm.pippi-local-credential-envelope.v0.1",
            "credential_reference_root": credential_reference["credential_reference_root"],
            "kdf": {"algorithm": "SCRYPT", "n": 2 ** 15, "r": 8, "p": 1,
                    "salt_base64": _b64(salt)},
            "aead": {"algorithm": "AES-256-GCM", "nonce_base64": _b64(nonce),
                     "ciphertext_base64": _b64(ciphertext)},
            "associated_data_root": root(credential_reference),
            "portable": False, "secret_material_present": True,
            **BOUNDARY}
    return {**body, "credential_envelope_root": root(body)}


def open_local_credential(*, envelope: dict[str, Any], passphrase: str,
                          credential_reference: dict[str, Any]) -> bytes:
    item = validate_local_credential_envelope(envelope)
    require(item["credential_reference_root"] == credential_reference.get("credential_reference_root")
            and item["associated_data_root"] == root(credential_reference),
            "PIPPI_CREDENTIAL_REFERENCE_MISMATCH")
    kdf = item["kdf"]
    aead = item["aead"]
    salt = _unb64(kdf["salt_base64"], "PIPPI_CREDENTIAL_SALT_INVALID")
    nonce = _unb64(aead["nonce_base64"], "PIPPI_CREDENTIAL_NONCE_INVALID")
    ciphertext = _unb64(aead["ciphertext_base64"], "PIPPI_CREDENTIAL_CIPHERTEXT_INVALID")
    try:
        return AESGCM(_key(passphrase, salt)).decrypt(
            nonce, ciphertext, canonical_bytes(credential_reference))
    except Exception as exc:
        raise ValueError("PIPPI_CREDENTIAL_DECRYPTION_REFUSED") from exc


def validate_local_credential_envelope(envelope: Any) -> dict[str, Any]:
    item = exact_keys(envelope, {"schema", "credential_reference_root", "kdf", "aead",
        "associated_data_root", "portable", "secret_material_present", *BOUNDARY,
        "credential_envelope_root"})
    body = {key: deepcopy(value) for key, value in item.items()
            if key != "credential_envelope_root"}
    require(item["schema"] == "mosaic.ucm.pippi-local-credential-envelope.v0.1"
            and item["credential_envelope_root"] == root(body)
            and item["portable"] is False
            and item["secret_material_present"] is True
            and {key: item[key] for key in BOUNDARY} == BOUNDARY,
            "PIPPI_CREDENTIAL_ENVELOPE_INVALID")
    require(type(item["credential_reference_root"]) is str
            and len(item["credential_reference_root"]) == 64
            and type(item["associated_data_root"]) is str
            and len(item["associated_data_root"]) == 64,
            "PIPPI_CREDENTIAL_ENVELOPE_INVALID")
    kdf = exact_keys(item["kdf"], {"algorithm", "n", "r", "p", "salt_base64"})
    aead = exact_keys(item["aead"], {"algorithm", "nonce_base64", "ciphertext_base64"})
    require(kdf["algorithm"] == "SCRYPT" and (kdf["n"], kdf["r"], kdf["p"]) == (2 ** 15, 8, 1),
            "PIPPI_CREDENTIAL_KDF_INVALID")
    require(aead["algorithm"] == "AES-256-GCM", "PIPPI_CREDENTIAL_AEAD_INVALID")
    salt = _unb64(kdf["salt_base64"], "PIPPI_CREDENTIAL_SALT_INVALID")
    nonce = _unb64(aead["nonce_base64"], "PIPPI_CREDENTIAL_NONCE_INVALID")
    ciphertext = _unb64(aead["ciphertext_base64"], "PIPPI_CREDENTIAL_CIPHERTEXT_INVALID")
    require(len(salt) == 16, "PIPPI_CREDENTIAL_SALT_INVALID")
    require(len(nonce) == 12, "PIPPI_CREDENTIAL_NONCE_INVALID")
    require(len(ciphertext) >= 17, "PIPPI_CREDENTIAL_CIPHERTEXT_INVALID")
    return deepcopy(item)


def _refuse_link_or_reparse(path: Path, code: str) -> None:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    require(not stat.S_ISLNK(info.st_mode) and not reparse, code)


def write_local_credential(path: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    envelope = validate_local_credential_envelope(envelope)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _refuse_link_or_reparse(path.parent, "PIPPI_CREDENTIAL_PARENT_REPARSE_REFUSED")
    _refuse_link_or_reparse(path, "PIPPI_CREDENTIAL_TARGET_REPARSE_REFUSED")
    temporary = path.with_name(path.name + "." + secrets.token_hex(12) + ".pending")
    raw = canonical_bytes(envelope) + b"\n"
    descriptor = None
    created = False
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        protect_private_file(temporary)
        verify_private_file(temporary)
        _refuse_link_or_reparse(path, "PIPPI_CREDENTIAL_TARGET_REPARSE_REFUSED")
        os.replace(temporary, path)
        protect_private_file(path)
        verify_private_file(path)
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if created and temporary.exists() and not temporary.is_symlink():
            temporary.unlink()
        raise
    return {"schema": "mosaic.ucm.pippi-local-credential-write.v0.1",
            "credential_envelope_root": envelope["credential_envelope_root"],
            "bytes": len(raw), "status": "PASS_PRIVATE_LOCAL_CUSTODY", **BOUNDARY}


__all__ = ["seal_local_credential", "open_local_credential",
           "validate_local_credential_envelope", "write_local_credential"]
