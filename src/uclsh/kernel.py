from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any, Callable

from .canonical import canonical_bytes, root, sha256_bytes
from .errors import require


Primitive = Callable[[list[Any], "Kernel"], Any]

# This is a bootstrap pin, not data supplied by the module being executed.  It
# identifies the only self-hosted compiler whose private parser cursor may use
# the one-layer internal cursor allowance in the VM.
PINNED_SELFHOST_COMPILER_SEMANTIC_ROOT = "7aabf4ab759c7150d76ffc5a6cd5a9d023e2aab01944dd5eee1af4dc89f74e2e"


class Kernel:
    """Small no-effect meta-kernel used by both seed and self-hosted compilers."""

    def __init__(self) -> None:
        self.selfhost_compiler_semantic_root = PINNED_SELFHOST_COMPILER_SEMANTIC_ROOT
        self.primitives: dict[str, Primitive] = {
            "ASSERT_TRUE": self._assert_true,
            "BOOL_AND": self._bool_and,
            "BOOL_NOT": self._bool_not,
            "CANONICAL_BYTES_HEX": self._canonical_hex,
            "CODEPOINT": self._codepoint,
            "EQUAL": self._equal,
            "FROM_CODEPOINT": self._from_codepoint,
            "GET": self._get,
            "HASH_TEXT": self._hash_text,
            "HASH_VALUE": self._hash_value,
            "HMAC_SIGN_DOMAIN": self._hmac_sign,
            "HMAC_VERIFY_DOMAIN": self._hmac_verify,
            "IDENTIFIER_VALID": self._identifier_valid,
            "I64_ADD": self._i64_add,
            "I64_DIV": self._i64_div,
            "I64_LESS": self._i64_less,
            "I64_MOD": self._i64_mod,
            "I64_MUL": self._i64_mul,
            "I64_SUB": self._i64_sub,
            "LIST_APPEND": self._list_append,
            "LIST_LENGTH": self._list_length,
            "MAP_HAS": self._map_has,
            "MAP_KEYS_SORTED": self._map_keys_sorted,
            "MAP_PUT": self._map_put,
            "TEXT_AT": self._text_at,
            "TEXT_CONCAT": self._text_concat,
            "TEXT_LENGTH": self._text_length,
            "TEXT_SLICE": self._text_slice,
            "TYPE_IS": self._type_is,
        }

    @property
    def primitive_arities(self) -> dict[str, int]:
        return {
            "ASSERT_TRUE": 3,
            "BOOL_AND": 2,
            "BOOL_NOT": 1,
            "CANONICAL_BYTES_HEX": 1,
            "CODEPOINT": 1,
            "EQUAL": 2,
            "FROM_CODEPOINT": 1,
            "GET": 2,
            "HASH_TEXT": 1,
            "HASH_VALUE": 1,
            "HMAC_SIGN_DOMAIN": 3,
            "HMAC_VERIFY_DOMAIN": 4,
            "IDENTIFIER_VALID": 1,
            "I64_ADD": 2,
            "I64_DIV": 2,
            "I64_LESS": 2,
            "I64_MOD": 2,
            "I64_MUL": 2,
            "I64_SUB": 2,
            "LIST_APPEND": 2,
            "LIST_LENGTH": 1,
            "MAP_HAS": 2,
            "MAP_KEYS_SORTED": 1,
            "MAP_PUT": 3,
            "TEXT_AT": 2,
            "TEXT_CONCAT": 2,
            "TEXT_LENGTH": 1,
            "TEXT_SLICE": 3,
            "TYPE_IS": 2,
        }

    @property
    def primitive_names(self) -> set[str]:
        return set(self.primitives)

    @property
    def descriptor(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.selfhost.meta_kernel.v1",
            "primitives": sorted(self.primitives),
            "effect": "NONE",
            "integer_domain": "SIGNED_I64",
            "text_domain": "EXACT_UTF8_NO_NORMALIZATION",
            "map_order": "CANONICAL_UTF8_KEY_ORDER",
            "standing": "INFORMATION_ONLY",
        }
        return {"body": body, "root": root(body)}

    def invoke(self, name: str, args: list[Any]) -> Any:
        require(name in self.primitives, "PRIMITIVE_UNKNOWN", "$.primitive", name)
        return self.primitives[name](args, self)

    @staticmethod
    def _arity(args: list[Any], expected: int, name: str) -> None:
        require(len(args) == expected, "PRIMITIVE_ARITY", f"$.primitive.{name}")

    def _assert_true(self, args: list[Any], _: "Kernel") -> Any:
        self._arity(args, 3, "ASSERT_TRUE")
        condition, code, value = args
        require(type(condition) is bool and type(code) is str and bool(code) and code.isascii(), "ASSERT_ARGUMENT_INVALID", "$.primitive.ASSERT_TRUE")
        require(condition, code)
        return value

    def _bool_and(self, args: list[Any], _: "Kernel") -> bool:
        self._arity(args, 2, "BOOL_AND")
        require(all(type(item) is bool for item in args), "PRIMITIVE_TYPE", "$.primitive.BOOL_AND")
        return args[0] and args[1]

    def _bool_not(self, args: list[Any], _: "Kernel") -> bool:
        self._arity(args, 1, "BOOL_NOT")
        require(type(args[0]) is bool, "PRIMITIVE_TYPE", "$.primitive.BOOL_NOT")
        return not args[0]

    def _canonical_hex(self, args: list[Any], _: "Kernel") -> str:
        self._arity(args, 1, "CANONICAL_BYTES_HEX")
        return canonical_bytes(args[0]).hex()

    def _codepoint(self, args: list[Any], _: "Kernel") -> int:
        self._arity(args, 1, "CODEPOINT")
        require(type(args[0]) is str and len(args[0]) == 1, "PRIMITIVE_TYPE", "$.primitive.CODEPOINT")
        return ord(args[0])

    def _equal(self, args: list[Any], _: "Kernel") -> bool:
        self._arity(args, 2, "EQUAL")
        return type(args[0]) is type(args[1]) and args[0] == args[1]

    def _from_codepoint(self, args: list[Any], _: "Kernel") -> str:
        self._arity(args, 1, "FROM_CODEPOINT")
        value = args[0]
        require(type(value) is int and type(value) is not bool and 0 <= value <= 0x10FFFF and not 0xD800 <= value <= 0xDFFF, "CODEPOINT_INVALID", "$.primitive.FROM_CODEPOINT")
        return chr(value)

    def _get(self, args: list[Any], _: "Kernel") -> Any:
        self._arity(args, 2, "GET")
        container, key = args
        if type(container) is dict:
            require(type(key) is str and key in container, "MAP_KEY_MISSING", "$.primitive.GET", str(key))
            return container[key]
        require(type(container) is list and type(key) is int and type(key) is not bool and 0 <= key < len(container), "LIST_INDEX_INVALID", "$.primitive.GET")
        return container[key]

    def _hash_text(self, args: list[Any], _: "Kernel") -> str:
        self._arity(args, 1, "HASH_TEXT")
        require(type(args[0]) is str, "PRIMITIVE_TYPE", "$.primitive.HASH_TEXT")
        return sha256_bytes(args[0].encode("utf-8"))

    def _hash_value(self, args: list[Any], _: "Kernel") -> str:
        self._arity(args, 1, "HASH_VALUE")
        return root(args[0])

    @staticmethod
    def _fixture_key(value: Any, path: str) -> bytes:
        require(type(value) is str and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value), "FIXTURE_KEY_INVALID", path)
        return bytes.fromhex(value)

    def _hmac_payload(self, domain: Any, body: Any) -> bytes:
        require(type(domain) is str and bool(domain) and domain.isascii(), "SIGNATURE_DOMAIN_INVALID")
        return b"UCL-SH-HMAC-V1\x00" + domain.encode("ascii") + b"\x00" + canonical_bytes(body)

    def _hmac_sign(self, args: list[Any], _: "Kernel") -> dict[str, str]:
        self._arity(args, 3, "HMAC_SIGN_DOMAIN")
        domain, body, key_hex = args
        key = self._fixture_key(key_hex, "$.primitive.HMAC_SIGN_DOMAIN.key")
        value = hmac.new(key, self._hmac_payload(domain, body), hashlib.sha256).hexdigest()
        return {
            "algorithm": "HMAC-SHA256-FIXTURE-ONLY",
            "domain": domain,
            "key_root": sha256_bytes(key),
            "value": value,
        }

    def _hmac_verify(self, args: list[Any], _: "Kernel") -> bool:
        self._arity(args, 4, "HMAC_VERIFY_DOMAIN")
        domain, body, key_hex, signature = args
        require(type(signature) is dict, "SIGNATURE_INVALID")
        expected = self._hmac_sign([domain, body, key_hex], self)
        require(set(signature) == set(expected), "SIGNATURE_SHAPE_INVALID")
        require(signature["algorithm"] == expected["algorithm"], "SIGNATURE_ALGORITHM_INVALID")
        require(signature["domain"] == expected["domain"], "SIGNATURE_DOMAIN_MISMATCH")
        require(signature["key_root"] == expected["key_root"], "SIGNATURE_KEY_MISMATCH")
        require(type(signature["value"]) is str and hmac.compare_digest(signature["value"], expected["value"]), "SIGNATURE_INVALID")
        return True

    def _identifier_valid(self, args: list[Any], _: "Kernel") -> bool:
        self._arity(args, 1, "IDENTIFIER_VALID")
        return type(args[0]) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,127}", args[0]) is not None

    @staticmethod
    def _i64(value: Any, path: str) -> int:
        require(type(value) is int and type(value) is not bool and -(2**63) <= value <= 2**63 - 1, "I64_REQUIRED", path)
        return value

    def _i64_result(self, value: int, name: str) -> int:
        require(-(2**63) <= value <= 2**63 - 1, "I64_OVERFLOW", f"$.primitive.{name}")
        return value

    def _i64_add(self, args: list[Any], _: "Kernel") -> int:
        self._arity(args, 2, "I64_ADD")
        return self._i64_result(self._i64(args[0], "$.primitive.I64_ADD[0]") + self._i64(args[1], "$.primitive.I64_ADD[1]"), "I64_ADD")

    def _i64_sub(self, args: list[Any], _: "Kernel") -> int:
        self._arity(args, 2, "I64_SUB")
        return self._i64_result(self._i64(args[0], "$.primitive.I64_SUB[0]") - self._i64(args[1], "$.primitive.I64_SUB[1]"), "I64_SUB")

    def _i64_mul(self, args: list[Any], _: "Kernel") -> int:
        self._arity(args, 2, "I64_MUL")
        return self._i64_result(self._i64(args[0], "$.primitive.I64_MUL[0]") * self._i64(args[1], "$.primitive.I64_MUL[1]"), "I64_MUL")

    def _i64_div(self, args: list[Any], _: "Kernel") -> int:
        self._arity(args, 2, "I64_DIV")
        left = self._i64(args[0], "$.primitive.I64_DIV[0]")
        right = self._i64(args[1], "$.primitive.I64_DIV[1]")
        require(right != 0, "DIVISION_BY_ZERO", "$.primitive.I64_DIV")
        require(not (left == -(2**63) and right == -1), "I64_OVERFLOW", "$.primitive.I64_DIV")
        return abs(left) // abs(right) * (-1 if (left < 0) != (right < 0) else 1)

    def _i64_mod(self, args: list[Any], _: "Kernel") -> int:
        self._arity(args, 2, "I64_MOD")
        left = self._i64(args[0], "$.primitive.I64_MOD[0]")
        right = self._i64(args[1], "$.primitive.I64_MOD[1]")
        require(right != 0, "DIVISION_BY_ZERO", "$.primitive.I64_MOD")
        quotient = abs(left) // abs(right) * (-1 if (left < 0) != (right < 0) else 1)
        return left - quotient * right

    def _i64_less(self, args: list[Any], _: "Kernel") -> bool:
        self._arity(args, 2, "I64_LESS")
        return self._i64(args[0], "$.primitive.I64_LESS[0]") < self._i64(args[1], "$.primitive.I64_LESS[1]")

    def _list_append(self, args: list[Any], _: "Kernel") -> list[Any]:
        self._arity(args, 2, "LIST_APPEND")
        require(type(args[0]) is list, "PRIMITIVE_TYPE", "$.primitive.LIST_APPEND")
        return [*args[0], args[1]]

    def _list_length(self, args: list[Any], _: "Kernel") -> int:
        self._arity(args, 1, "LIST_LENGTH")
        require(type(args[0]) in {list, str, dict}, "PRIMITIVE_TYPE", "$.primitive.LIST_LENGTH")
        return len(args[0])

    def _map_has(self, args: list[Any], _: "Kernel") -> bool:
        self._arity(args, 2, "MAP_HAS")
        require(type(args[0]) is dict and type(args[1]) is str, "PRIMITIVE_TYPE", "$.primitive.MAP_HAS")
        return args[1] in args[0]

    def _map_keys_sorted(self, args: list[Any], _: "Kernel") -> list[str]:
        self._arity(args, 1, "MAP_KEYS_SORTED")
        require(type(args[0]) is dict, "PRIMITIVE_TYPE", "$.primitive.MAP_KEYS_SORTED")
        return sorted(args[0])

    def _map_put(self, args: list[Any], _: "Kernel") -> dict[str, Any]:
        self._arity(args, 3, "MAP_PUT")
        require(type(args[0]) is dict and type(args[1]) is str, "PRIMITIVE_TYPE", "$.primitive.MAP_PUT")
        require(bool(args[1]), "MAP_KEY_INVALID", "$.primitive.MAP_PUT")
        result = dict(args[0])
        result[args[1]] = args[2]
        return result

    def _text_at(self, args: list[Any], _: "Kernel") -> str:
        self._arity(args, 2, "TEXT_AT")
        text, index = args
        require(type(text) is str and type(index) is int and type(index) is not bool and 0 <= index < len(text), "TEXT_INDEX_INVALID", "$.primitive.TEXT_AT")
        return text[index]

    def _text_concat(self, args: list[Any], _: "Kernel") -> str:
        self._arity(args, 2, "TEXT_CONCAT")
        require(type(args[0]) is str and type(args[1]) is str, "PRIMITIVE_TYPE", "$.primitive.TEXT_CONCAT")
        return args[0] + args[1]

    def _text_length(self, args: list[Any], _: "Kernel") -> int:
        self._arity(args, 1, "TEXT_LENGTH")
        require(type(args[0]) is str, "PRIMITIVE_TYPE", "$.primitive.TEXT_LENGTH")
        return len(args[0])

    def _text_slice(self, args: list[Any], _: "Kernel") -> str:
        self._arity(args, 3, "TEXT_SLICE")
        text, start, end = args
        require(type(text) is str and type(start) is int and type(start) is not bool and type(end) is int and type(end) is not bool and 0 <= start <= end <= len(text), "TEXT_SLICE_INVALID", "$.primitive.TEXT_SLICE")
        return text[start:end]

    def _type_is(self, args: list[Any], _: "Kernel") -> bool:
        self._arity(args, 2, "TYPE_IS")
        value, expected = args
        require(type(expected) is str, "PRIMITIVE_TYPE", "$.primitive.TYPE_IS")
        checks = {
            "NULL": value is None,
            "BOOL": type(value) is bool,
            "I64": type(value) is int and type(value) is not bool,
            "TEXT": type(value) is str,
            "LIST": type(value) is list,
            "MAP": type(value) is dict,
            "ANY": True,
        }
        require(expected in checks, "VALUE_TYPE_UNKNOWN", "$.primitive.TYPE_IS", expected)
        return checks[expected]


