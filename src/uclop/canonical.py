from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class Refusal(ValueError):
    def __init__(self, code: str, path: str = "$", detail: str = "") -> None:
        self.code, self.path, self.detail = code, path, detail
        super().__init__(f"{code}@{path}" + (f":{detail}" if detail else ""))


def require(condition: bool, code: str, path: str = "$", detail: str = "") -> None:
    if not condition:
        raise Refusal(code, path, detail)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY", "$", key)
        result[key] = value
    return result


def _int(raw: str) -> int:
    value = int(raw, 10)
    require(-(2**63) <= value <= 2**63 - 1, "INTEGER_OUT_OF_RANGE")
    return value


def _float(raw: str) -> None:
    raise Refusal("FLOAT_NOT_ALLOWED", detail=raw)


def _constant(raw: str) -> None:
    raise Refusal("NON_FINITE_NUMBER", detail=raw)


def validate_value(value: Any, path: str = "$", *, maximum_depth: int = 96) -> None:
    pending = [(value, path, 0)]
    while pending:
        current, current_path, depth = pending.pop()
        require(depth <= maximum_depth, "VALUE_DEPTH_EXCEEDED", current_path)
        if current is None or type(current) is bool:
            continue
        if type(current) is int:
            require(-(2**63) <= current <= 2**63 - 1, "INTEGER_OUT_OF_RANGE", current_path)
            continue
        if type(current) is float:
            raise Refusal("NON_FINITE_NUMBER" if not math.isfinite(current) else "FLOAT_NOT_ALLOWED", current_path)
        if type(current) is str:
            require(not any(0xD800 <= ord(ch) <= 0xDFFF for ch in current), "LONE_SURROGATE", current_path)
            require(len(current.encode("utf-8")) <= 4 * 1024 * 1024, "TEXT_TOO_LARGE", current_path)
            continue
        if type(current) is list:
            require(len(current) <= 100_000, "CONTAINER_TOO_LARGE", current_path)
            pending.extend((item, f"{current_path}[{index}]", depth + 1) for index, item in enumerate(current))
            continue
        if type(current) is dict:
            require(len(current) <= 100_000, "CONTAINER_TOO_LARGE", current_path)
            for key, item in current.items():
                require(type(key) is str and bool(key), "MAP_KEY_INVALID", current_path)
                pending.append((item, f"{current_path}.{key}", depth + 1))
            continue
        raise Refusal("VALUE_TYPE_UNSUPPORTED", current_path, type(current).__name__)


def strict_loads(raw: bytes | str) -> Any:
    if type(raw) is bytes:
        require(not raw.startswith(b"\xef\xbb\xbf"), "SOURCE_BOM_FORBIDDEN")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeError as error:
            raise Refusal("INVALID_UTF8") from error
    else:
        require(type(raw) is str, "SOURCE_INPUT_INVALID")
        text = raw
        require(not text.startswith("\ufeff"), "SOURCE_BOM_FORBIDDEN")
    depth = 0
    in_string = False
    escaped = False
    for index, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            require(depth <= 96, "VALUE_DEPTH_EXCEEDED", detail=str(index))
        elif ch in "]}":
            depth -= 1
            require(depth >= 0, "SOURCE_PARSE_FAILED", detail="UNBALANCED_CLOSE")
    try:
        result = json.loads(text, object_pairs_hook=_pairs, parse_int=_int, parse_float=_float, parse_constant=_constant)
    except Refusal:
        raise
    except (ValueError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise Refusal("SOURCE_PARSE_FAILED", detail=type(error).__name__) from error
    validate_value(result)
    return result


def canonical_bytes(value: Any) -> bytes:
    validate_value(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def root(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def require_root(value: Any, path: str = "$") -> str:
    require(type(value) is str and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value), "ROOT_INVALID", path)
    return value


def exact_keys(value: Any, required: set[str], path: str = "$") -> dict[str, Any]:
    require(type(value) is dict, "OBJECT_REQUIRED", path)
    missing, extra = required - set(value), set(value) - required
    require(not missing, "REQUIRED_FIELD_MISSING", path, ",".join(sorted(missing)))
    require(not extra, "UNKNOWN_FIELD", path, ",".join(sorted(extra)))
    return value
