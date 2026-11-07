"""Public MosaicID descriptors. No key generation, custody, admission or grants."""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import time
from typing import Any, Callable
import zipfile

PASSPORT_SCHEMA = "mosaic.identity.passport.v0.1"
SUITE = "ed25519-public-key-blake3-256-v1"
PROOF_DOMAIN = b"MOSAIC_ID_PASSPORT_POSSESSION_V1\x00"
MAX_BYTES = 262144
MAX_ARCHIVE_BYTES = 524288
README = ("MosaicID Passport v0.1 candidate\n"
          "PUBLIC IDENTITY DESCRIPTOR. Possession and permission are separate checks.\n"
          "No private keys, authority grants, or executable files are included.\n"
          "Context declarations are unverified. Namespace selectors grant no rights.\n").encode("ascii")
CEILING = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
           "real_a5": False, "g0": "CLOSED"}


class Refusal(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Refusal(code)


def fields(value: Any, names: set[str]) -> dict:
    require(type(value) is dict and set(value) == names, "IDENTITY_FIELDS_INVALID")
    return value


def hex_value(value: Any, count: int = 64) -> str:
    require(type(value) is str and re.fullmatch("[0-9a-f]{%d}" % count, value) is not None,
            "IDENTITY_HEX_INVALID")
    return value


def text(value: Any) -> str:
    require(type(value) is str and 0 < len(value) <= 256 and value.isascii()
            and all(32 <= ord(c) <= 126 for c in value) and value == value.strip(),
            "IDENTITY_TEXT_INVALID")
    return value


def integer(value: Any) -> int:
    require(type(value) is int and 0 <= value < 2**63, "IDENTITY_INTEGER_INVALID")
    return value


def canonical(value: Any) -> bytes:
    def check(item: Any, depth: int = 0) -> None:
        require(depth <= 24, "IDENTITY_DEPTH_EXCEEDED")
        if item is None or type(item) is bool:
            return
        if type(item) is int:
            integer(item)
        elif type(item) is str:
            require(len(item) <= 8192 and not any(0xD800 <= ord(c) <= 0xDFFF for c in item),
                    "IDENTITY_STRING_INVALID")
        elif type(item) is list:
            require(len(item) <= 128, "IDENTITY_CONTAINER_LIMIT")
            for child in item:
                check(child, depth + 1)
        elif type(item) is dict:
            require(len(item) <= 64 and all(type(k) is str for k in item),
                    "IDENTITY_CONTAINER_LIMIT")
            for key, child in item.items():
                check(key, depth + 1)
                check(child, depth + 1)
        else:
            raise Refusal("IDENTITY_VALUE_TYPE_INVALID")
    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def decode(raw: bytes) -> Any:
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, "IDENTITY_INPUT_LIMIT")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "IDENTITY_DUPLICATE_KEY")
            result[key] = value
        return result
    def forbidden(_):
        raise Refusal("IDENTITY_NUMBER_INVALID")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_float=forbidden, parse_constant=forbidden)
        require(canonical(value) == raw, "IDENTITY_JSON_NOT_CANONICAL")
        return value
    except Refusal:
        raise
    except (ValueError, UnicodeError, RecursionError) as error:
        raise Refusal("IDENTITY_JSON_INVALID") from error


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def mosaic_id(public_key_hex: str) -> str:
    key = bytes.fromhex(hex_value(public_key_hex))
    try:
        from blake3 import blake3
    except ImportError as error:
        raise Refusal("IDENTITY_DEPENDENCY_MISSING_BLAKE3") from error
    return blake3(key).hexdigest()


def context(value: Any = None) -> dict:
    if value is None:
        value = {"universe_root": None, "epoch": None, "semantic_namespace": None}
    item = fields(value, {"universe_root", "epoch", "semantic_namespace"})
    if item["universe_root"] is not None:
        ref = fields(item["universe_root"], {"algorithm", "digest"})
        require(ref["algorithm"] == "blake3", "IDENTITY_UNIVERSE_ALGORITHM_INVALID")
        hex_value(ref["digest"])
    if item["epoch"] is not None:
        epoch = fields(item["epoch"], {"phase_id", "public_key_hex"})
        text(epoch["phase_id"])
        hex_value(epoch["public_key_hex"])
    if item["semantic_namespace"] is not None:
        # This is a preserved declaration, never a pattern used for authorization.
        text(item["semantic_namespace"])
    return copy.deepcopy(item)


def create_passport(public_key_hex: str, declared_context: Any = None) -> dict:
    return {"schema": PASSPORT_SCHEMA, "identity_suite": SUITE,
            "public_key_hex": hex_value(public_key_hex),
            "mosaic_id": mosaic_id(public_key_hex),
            "declared_context": context(declared_context)}


def verify_passport(value: Any, *, expected_mosaic_id: str | None = None) -> dict:
    item = fields(value, {"schema", "identity_suite", "public_key_hex", "mosaic_id",
                          "declared_context"})
    require(item["schema"] == PASSPORT_SCHEMA and item["identity_suite"] == SUITE,
            "IDENTITY_PROFILE_UNSUPPORTED")
    rebuilt = create_passport(item["public_key_hex"], item["declared_context"])
    require(item == rebuilt, "IDENTITY_DERIVATION_MISMATCH")
    if expected_mosaic_id is not None:
        require(item["mosaic_id"] == hex_value(expected_mosaic_id),
                "IDENTITY_EXPECTED_ID_MISMATCH")
    return {"schema": "mosaic.identity.inspection.v0.1", "status": "PASS_SELF_CERTIFIED",
            "mosaic_id": rebuilt["mosaic_id"], "passport_sha256": digest(rebuilt),
            "public_key_hex": rebuilt["public_key_hex"],
            "declared_context": rebuilt["declared_context"],
            "possession_verified": False, "context_verified": False,
            "namespace_authority_bound": False, "permission_granted": False, **CEILING}


def archive_bytes(passport: Any) -> bytes:
    verify_passport(passport)
    payloads = {"MOSAIC-ID-PASSPORT.json": canonical(passport), "README.txt": README}
    manifest = {"schema": "mosaic.identity.archive.v0.1", "files": [
        {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(payloads.items())]}
    payloads["MANIFEST.json"] = canonical(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


def load_archive(raw: bytes) -> dict:
    require(type(raw) is bytes and len(raw) <= MAX_ARCHIVE_BYTES, "IDENTITY_ARCHIVE_LIMIT")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            require(len(infos) == 3 and {i.filename for i in infos} ==
                    {"MOSAIC-ID-PASSPORT.json", "MANIFEST.json", "README.txt"},
                    "IDENTITY_ARCHIVE_MEMBERS_INVALID")
            require(all(i.file_size <= MAX_BYTES and i.compress_type == zipfile.ZIP_STORED
                        for i in infos), "IDENTITY_ARCHIVE_MEMBER_INVALID")
            value = decode(archive.read("MOSAIC-ID-PASSPORT.json"))
        # A byte-exact rebuild checks manifest, comments, duplicates, metadata and trailing data.
        require(archive_bytes(value) == raw, "IDENTITY_ARCHIVE_NOT_CANONICAL")
        return value
    except Refusal:
        raise
    except (zipfile.BadZipFile, KeyError, ValueError, NotImplementedError, RuntimeError,
            OSError, EOFError) as error:
        raise Refusal("IDENTITY_ARCHIVE_INVALID") from error


def read_bounded(path: Path, maximum: int) -> bytes:
    try:
        with path.open("rb") as stream:
            raw = stream.read(maximum + 1)
    except OSError as error:
        raise Refusal("IDENTITY_FILE_UNREADABLE") from error
    require(len(raw) <= maximum, "IDENTITY_INPUT_LIMIT")
    return raw


def load_passport(path: Path) -> dict:
    raw = read_bounded(path, MAX_ARCHIVE_BYTES)
    value = load_archive(raw) if raw.startswith(b"PK") else decode(raw)
    verify_passport(value)
    return value


def create_challenge(passport: Any, *, expected_mosaic_id: str, session_mosaic_id: str,
                     audience: str, context_sha256: str, issued_at: int,
                     expires_at: int, nonce: str) -> dict:
    identity = verify_passport(passport, expected_mosaic_id=expected_mosaic_id)
    hex_value(session_mosaic_id)
    require(session_mosaic_id != identity["mosaic_id"], "IDENTITY_SESSION_MUST_BE_DISTINCT")
    integer(issued_at)
    integer(expires_at)
    require(0 < expires_at - issued_at <= 600, "IDENTITY_CHALLENGE_LIFETIME_INVALID")
    return {"schema": "mosaic.identity.challenge.v0.1",
            "subject_mosaic_id": identity["mosaic_id"],
            "passport_sha256": identity["passport_sha256"],
            "session_mosaic_id": session_mosaic_id, "audience": text(audience),
            "context_sha256": hex_value(context_sha256), "issued_at": issued_at,
            "expires_at": expires_at, "nonce": hex_value(nonce)}


def verify_challenge(passport: Any, value: Any) -> dict:
    item = fields(value, {"schema", "subject_mosaic_id", "passport_sha256",
                          "session_mosaic_id", "audience", "context_sha256",
                          "issued_at", "expires_at", "nonce"})
    rebuilt = create_challenge(passport, expected_mosaic_id=item["subject_mosaic_id"],
        session_mosaic_id=item["session_mosaic_id"], audience=item["audience"],
        context_sha256=item["context_sha256"], issued_at=item["issued_at"],
        expires_at=item["expires_at"], nonce=item["nonce"])
    require(item == rebuilt, "IDENTITY_CHALLENGE_INVALID")
    return rebuilt


def possession_message(passport: Any, challenge: Any) -> bytes:
    return PROOF_DOMAIN + canonical(verify_challenge(passport, challenge))


_ED25519_P = 2**255 - 19
_ED25519_D = (-121665 * pow(121666, _ED25519_P - 2, _ED25519_P)) % _ED25519_P
_ED25519_SQRT_M1 = pow(2, (_ED25519_P - 1) // 4, _ED25519_P)
_ED25519_L = 2**252 + 27742317777372353535851937790883648493
_ED25519_IDENTITY = (0, 1)


def _ed25519_decode_point(encoded: bytes) -> tuple[int, int] | None:
    """Decode the canonical compressed Edwards point without external code."""
    if len(encoded) != 32:
        return None
    value = int.from_bytes(encoded, "little")
    sign = (value >> 255) & 1
    y = value & ((1 << 255) - 1)
    if y >= _ED25519_P:
        return None
    y2 = y * y % _ED25519_P
    denominator = (_ED25519_D * y2 + 1) % _ED25519_P
    if denominator == 0:
        return None
    x2 = (y2 - 1) * pow(denominator, _ED25519_P - 2, _ED25519_P) % _ED25519_P
    x = pow(x2, (_ED25519_P + 3) // 8, _ED25519_P)
    if x * x % _ED25519_P != x2:
        x = x * _ED25519_SQRT_M1 % _ED25519_P
    if x * x % _ED25519_P != x2 or (x == 0 and sign):
        return None
    if x & 1 != sign:
        x = _ED25519_P - x
    return x, y


def _ed25519_add(first: tuple[int, int], second: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = first; x2, y2 = second
    product = _ED25519_D * x1 * x2 * y1 * y2 % _ED25519_P
    x3 = (x1 * y2 + y1 * x2) * pow(1 + product, _ED25519_P - 2,
                                             _ED25519_P) % _ED25519_P
    y3 = (y1 * y2 + x1 * x2) * pow(1 - product, _ED25519_P - 2,
                                             _ED25519_P) % _ED25519_P
    return x3, y3


def _ed25519_scalar(point: tuple[int, int], scalar: int) -> tuple[int, int]:
    result = _ED25519_IDENTITY
    addend = point
    while scalar:
        if scalar & 1:
            result = _ed25519_add(result, addend)
        addend = _ed25519_add(addend, addend)
        scalar >>= 1
    return result


def _native_ed25519_is_valid_point(key: bytes) -> bool:
    point = _ed25519_decode_point(key)
    return (point is not None and point != _ED25519_IDENTITY
            and _ed25519_scalar(point, _ED25519_L) == _ED25519_IDENTITY)


def validate_signing_key(public_key_hex: str) -> None:
    """Require a canonical, nonidentity point in Ed25519's prime subgroup."""
    key = bytes.fromhex(hex_value(public_key_hex))
    try:
        from nacl.bindings import (crypto_core_ed25519_is_valid_point,
                                   crypto_core_ed25519_add,
                                   crypto_scalarmult_ed25519_noclamp)
    except ImportError:
        require(_native_ed25519_is_valid_point(key), "IDENTITY_PUBLIC_KEY_INVALID")
    else:
        require(crypto_core_ed25519_is_valid_point(key), "IDENTITY_PUBLIC_KEY_INVALID")
        # https://doc.libsodium.org/advanced/point-arithmetic#point-validation
        order_minus_one = bytes.fromhex(
            "ecd3f55c1a631258d69cf7a2def9de1400000000000000000000000000000010")
        try:
            product = crypto_scalarmult_ed25519_noclamp(order_minus_one, key)
            checked = crypto_core_ed25519_add(product, key)
        except (RuntimeError, ValueError) as error:
            raise Refusal("IDENTITY_PUBLIC_KEY_INVALID") from error
        require(checked == b"\x01" + b"\x00" * 31, "IDENTITY_PUBLIC_KEY_INVALID")


def create_proof(passport: Any, challenge: Any, signer: Callable[[bytes], bytes]) -> dict:
    """The custody provider supplies a signing callable; no private material is accepted."""
    message = possession_message(passport, challenge)
    try:
        signature = signer(message)
    except Exception as error:
        raise Refusal("IDENTITY_SIGNER_FAILED") from error
    require(type(signature) is bytes and len(signature) == 64, "IDENTITY_SIGNATURE_INVALID")
    return {"schema": "mosaic.identity.possession.v0.1", "challenge": copy.deepcopy(challenge),
            "signature_algorithm": "Ed25519", "signature_hex": signature.hex()}


def verify_proof(passport: Any, proof: Any, *, expected_challenge: Any,
                 expected_mosaic_id: str, now: int) -> dict:
    """Pure cryptographic verification. Issuance/one-time consumption remain runtime obligations."""
    identity = verify_passport(passport, expected_mosaic_id=expected_mosaic_id)
    item = fields(proof, {"schema", "challenge", "signature_algorithm", "signature_hex"})
    require(item["schema"] == "mosaic.identity.possession.v0.1"
            and item["signature_algorithm"] == "Ed25519", "IDENTITY_PROOF_PROFILE_INVALID")
    verified_challenge = verify_challenge(passport, expected_challenge)
    require(canonical(item["challenge"]) == canonical(verified_challenge),
            "IDENTITY_CHALLENGE_SUBSTITUTED")
    integer(now)
    require(verified_challenge["issued_at"] <= now < verified_challenge["expires_at"],
            "IDENTITY_CHALLENGE_EXPIRED_OR_FUTURE")
    validate_signing_key(identity["public_key_hex"])
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as error:
        raise Refusal("IDENTITY_DEPENDENCY_MISSING_CRYPTOGRAPHY") from error
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(identity["public_key_hex"])).verify(
            bytes.fromhex(hex_value(item["signature_hex"], 128)),
            possession_message(passport, verified_challenge))
    except InvalidSignature as error:
        raise Refusal("IDENTITY_SIGNATURE_INVALID") from error
    return {"schema": "mosaic.identity.possession_check.v0.1", "status": "PASS_SIGNATURE",
            "mosaic_id": identity["mosaic_id"], "challenge_sha256": digest(verified_challenge),
            "public_key_validation": "ED25519_CANONICAL_PRIME_SUBGROUP_NONIDENTITY_V1",
            "possession_signature_verified": True, "challenge_issuance_verified": False,
            "replay_consumption_verified": False, "session_authenticated": False,
            "permission_granted": False, **CEILING}


def ucm_import_binding(passport: Any, *, expected_mosaic_id: str) -> dict:
    result = verify_passport(passport, expected_mosaic_id=expected_mosaic_id)
    return {"schema": "mosaic.ucm.identity_import.v0.1", "mosaic_id": result["mosaic_id"],
            "identity_suite": SUITE, "public_key_hex": result["public_key_hex"],
            "passport_sha256": result["passport_sha256"],
            "declared_context": result["declared_context"],
            "status": "PENDING_POSSESSION_AND_LOCAL_ADMISSION", "grant": None,
            "H_j": None, "namespace_authority_bound": False,
            "required_next_checks": ["FRESH_CHALLENGE", "DURABLE_ONE_TIME_CONSUMPTION",
                "PINNED_NAMESPACE_AND_THR_VERIFIERS", "LOCAL_CHARTER_AND_DELEGATION"], **CEILING}


def write_new(path: Path, raw: bytes) -> None:
    try:
        # Existing files, links and junction destinations are never replaced.
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise Refusal("IDENTITY_OUTPUT_EXISTS") from error
    except OSError as error:
        raise Refusal("IDENTITY_OUTPUT_WRITE_FAILED_MAY_BE_PARTIAL") from error


def issue_durable_challenge(journal, passport: Any, *, expected_mosaic_id: str,
                            session_mosaic_id: str, audience: str,
                            context_sha256: str, issued_at: int, expires_at: int,
                            nonce: str, event_id: str) -> dict:
    """Issue a challenge and bind it to the append-only campaign journal."""
    challenge = create_challenge(passport, expected_mosaic_id=expected_mosaic_id,
        session_mosaic_id=session_mosaic_id, audience=audience,
        context_sha256=context_sha256, issued_at=issued_at, expires_at=expires_at,
        nonce=nonce)
    challenge_sha256 = digest(challenge)
    event = journal.append(event_id=event_id, event_type="CHALLENGE_ISSUED",
        actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": session_mosaic_id},
        payload={"challenge": challenge, "challenge_sha256": challenge_sha256,
                 "subject_mosaic_id": expected_mosaic_id, "consumed": False})
    return {"challenge": challenge, "challenge_sha256": challenge_sha256,
            "journal_event_root": event["event_root"], **CEILING}


def consume_durable_proof(journal, passport: Any, proof: Any, *,
                          expected_challenge: Any, expected_mosaic_id: str,
                          now: int, event_id: str) -> dict:
    """Verify and consume one exact challenge once, including across restarts."""
    challenge_sha256 = digest(verify_challenge(passport, expected_challenge))
    events = journal.verify()
    issued = [event for event in events if event["event_type"] == "CHALLENGE_ISSUED"
              and event["payload"].get("challenge_sha256") == challenge_sha256]
    consumed = [event for event in events if event["event_type"] == "SESSION_AUTHENTICATED"
                and event["payload"].get("challenge_sha256") == challenge_sha256]
    require(len(issued) == 1 and not consumed, "IDENTITY_CHALLENGE_NOT_FRESH")
    result = verify_proof(passport, proof, expected_challenge=expected_challenge,
                          expected_mosaic_id=expected_mosaic_id, now=now)
    event = journal.append(event_id=event_id, event_type="SESSION_AUTHENTICATED",
        actor={"kind": "USER", "mosaic_id": expected_mosaic_id,
               "session_id": expected_challenge["session_mosaic_id"]},
        payload={"challenge_sha256": challenge_sha256,
                 "possession_check": result, "consumed": True})
    return {**result, "challenge_issuance_verified": True,
            "replay_consumption_verified": True, "session_authenticated": True,
            "journal_event_root": event["event_root"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="MosaicID public passport v0.1 candidate")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Wrap an existing PUBLIC Ed25519 key")
    create.add_argument("--public-key-hex", required=True)
    create.add_argument("--context", type=Path)
    create.add_argument("--out", type=Path, required=True)
    inspect = commands.add_parser("inspect", help="Verify a public descriptor or passport ZIP")
    inspect.add_argument("passport", type=Path)
    inspect.add_argument("--expected-id")
    export = commands.add_parser("export", help="Create a deterministic public-only ZIP")
    export.add_argument("passport", type=Path)
    export.add_argument("--expected-id", required=True)
    export.add_argument("--out", type=Path, required=True)
    bind = commands.add_parser("ucm-import", help="Prepare an unprivileged UCM binding")
    bind.add_argument("passport", type=Path)
    bind.add_argument("--expected-id", required=True)
    challenge = commands.add_parser("challenge", help="Prepare a fresh authentication challenge")
    challenge.add_argument("passport", type=Path)
    challenge.add_argument("--expected-id", required=True)
    challenge.add_argument("--session-id", required=True)
    challenge.add_argument("--audience", required=True)
    challenge.add_argument("--context-sha256", required=True)
    challenge.add_argument("--out", type=Path, required=True)
    check = commands.add_parser("check-proof", help="Check signature; does not consume a challenge")
    check.add_argument("passport", type=Path)
    check.add_argument("proof", type=Path)
    check.add_argument("--expected-challenge", type=Path, required=True)
    check.add_argument("--expected-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "create":
            declared = decode(read_bounded(args.context, MAX_BYTES)) if args.context else None
            passport = create_passport(args.public_key_hex, declared)
            write_new(args.out, canonical(passport))
            result = verify_passport(passport)
        else:
            passport = load_passport(args.passport)
            if args.command == "inspect":
                result = verify_passport(passport, expected_mosaic_id=args.expected_id)
            elif args.command == "export":
                result = verify_passport(passport, expected_mosaic_id=args.expected_id)
                raw = archive_bytes(passport)
                write_new(args.out, raw)
                result["archive_sha256"] = hashlib.sha256(raw).hexdigest()
            elif args.command == "ucm-import":
                result = ucm_import_binding(passport, expected_mosaic_id=args.expected_id)
            elif args.command == "challenge":
                now = int(time.time())
                result = create_challenge(passport, expected_mosaic_id=args.expected_id,
                    session_mosaic_id=args.session_id, audience=args.audience,
                    context_sha256=args.context_sha256, issued_at=now, expires_at=now + 300,
                    nonce=secrets.token_hex(32))
                write_new(args.out, canonical(result))
            else:
                result = verify_proof(passport, decode(read_bounded(args.proof, MAX_BYTES)),
                    expected_challenge=decode(read_bounded(args.expected_challenge, MAX_BYTES)),
                    expected_mosaic_id=args.expected_id, now=int(time.time()))
        print(canonical({"result": result, **CEILING}).decode("utf-8"))
        return 0
    except Refusal as error:
        print(canonical({"status": "REFUSED", "diagnostic": error.code, **CEILING}).decode())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
