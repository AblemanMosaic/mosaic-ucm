from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .errors import UCLSHRefusal, refuse, require


MAX_DEPTH = 123
MAX_CONTAINER_ITEMS = 100_000
MAX_TEXT_BYTES = 4 * 1024 * 1024
I64_MIN = -(2**63)
I64_MAX = 2**63 - 1


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            refuse("DUPLICATE_JSON_KEY", "$", key)
        result[key] = value
    return result


def _parse_int(raw: str) -> int:
    value = int(raw, 10)
    require(I64_MIN <= value <= I64_MAX, "INTEGER_OUT_OF_RANGE", "$", raw)
    return value


def _reject_float(raw: str) -> None:
    refuse("FLOAT_NOT_ALLOWED", "$", raw)


def _reject_constant(raw: str) -> None:
    refuse("NON_FINITE_NUMBER", "$", raw)


def validate_value(value: Any, path: str = "$", depth: int = 0, *, max_depth: int = MAX_DEPTH) -> None:
    pending: list[tuple[Any, str, int]] = [(value, path, depth)]
    while pending:
        current, current_path, current_depth = pending.pop()
        require(current_depth <= max_depth, "VALUE_DEPTH_EXCEEDED", current_path)
        if current is None or type(current) is bool:
            continue
        if type(current) is int:
            require(I64_MIN <= current <= I64_MAX, "INTEGER_OUT_OF_RANGE", current_path)
            continue
        if type(current) is float:
            if not math.isfinite(current):
                refuse("NON_FINITE_NUMBER", current_path)
            refuse("FLOAT_NOT_ALLOWED", current_path)
        if type(current) is str:
            require(not any(0xD800 <= ord(ch) <= 0xDFFF for ch in current), "LONE_SURROGATE", current_path)
            require(len(current.encode("utf-8", errors="strict")) <= MAX_TEXT_BYTES, "TEXT_TOO_LARGE", current_path)
            continue
        if type(current) is list:
            require(len(current) <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", current_path)
            for index in range(len(current) - 1, -1, -1):
                pending.append((current[index], f"{current_path}[{index}]", current_depth + 1))
            continue
        if type(current) is dict:
            require(len(current) <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", current_path)
            for key, item in reversed(tuple(current.items())):
                require(type(key) is str and bool(key), "MAP_KEY_INVALID", current_path)
                pending.append((item, f"{current_path}.{key}", current_depth + 1))
                pending.append((key, f"{current_path}.<key>", current_depth + 1))
            continue
        refuse("VALUE_TYPE_UNSUPPORTED", current_path, type(current).__name__)


def strict_loads(raw: bytes | str) -> Any:
    if type(raw) is bytes:
        require(not raw.startswith(b"\xef\xbb\xbf"), "SOURCE_BOM_FORBIDDEN")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise UCLSHRefusal("INVALID_UTF8") from exc
    elif type(raw) is str:
        text = raw
        require(not text.startswith("\ufeff"), "SOURCE_BOM_FORBIDDEN")
    else:
        refuse("SOURCE_INPUT_INVALID")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_parse_int,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except UCLSHRefusal:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise UCLSHRefusal("SOURCE_PARSE_FAILED", detail=type(exc).__name__) from exc
    validate_value(value)
    return value


def canonical_bytes(value: Any, *, max_depth: int = MAX_DEPTH) -> bytes:
    validate_value(value, max_depth=max_depth)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise UCLSHRefusal("CANONICALIZATION_FAILED", detail=type(exc).__name__) from exc


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def root(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def require_root(value: Any, path: str = "$") -> str:
    require(
        type(value) is str
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value),
        "ROOT_INVALID",
        path,
    )
    return value

