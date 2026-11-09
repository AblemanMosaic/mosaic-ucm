from __future__ import annotations

from typing import Any

from .canonical import I64_MAX, I64_MIN, MAX_CONTAINER_ITEMS, MAX_DEPTH, validate_value
from .errors import refuse, require


HEX = set("0123456789abcdefABCDEF")
WS = set(" \t\r\n")


class DeclaredJSONParser:
    """Deterministic recursive-descent realization of STRICT_JSON_UCL_SH_V1."""

    def __init__(self, text: str) -> None:
        require(type(text) is str, "SOURCE_INPUT_INVALID")
        require(not text.startswith("\ufeff"), "SOURCE_BOM_FORBIDDEN")
        self.text = text
        self.index = 0
        self.items = 0

    def parse(self) -> Any:
        self._ws()
        value = self._value(0)
        self._ws()
        require(self.index == len(self.text), "SOURCE_TRAILING_DATA", self._path())
        validate_value(value)
        return value

    def _path(self) -> str:
        return f"$@{self.index}"

    def _ws(self) -> None:
        while self.index < len(self.text) and self.text[self.index] in WS:
            self.index += 1

    def _take(self, expected: str) -> None:
        require(self.text.startswith(expected, self.index), "TOKEN_EXPECTED", self._path(), expected)
        self.index += len(expected)

    def _value(self, depth: int) -> Any:
        require(depth <= MAX_DEPTH, "VALUE_DEPTH_EXCEEDED", self._path())
        require(self.index < len(self.text), "UNEXPECTED_END", self._path())
        ch = self.text[self.index]
        if ch == '"':
            return self._string()
        if ch == "{":
            return self._object(depth + 1)
        if ch == "[":
            return self._array(depth + 1)
        if ch == "t":
            self._take("true")
            return True
        if ch == "f":
            self._take("false")
            return False
        if ch == "n":
            self._take("null")
            return None
        if ch == "-" or ch in "0123456789":
            return self._number()
        refuse("VALUE_TOKEN_INVALID", self._path(), ch)

    def _string(self) -> str:
        self._take('"')
        output: list[str] = []
        while self.index < len(self.text):
            ch = self.text[self.index]
            self.index += 1
            if ch == '"':
                result = "".join(output)
                validate_value(result, self._path())
                return result
            if ord(ch) < 0x20:
                refuse("STRING_CONTROL_CHARACTER", self._path())
            if ch != "\\":
                require(not 0xD800 <= ord(ch) <= 0xDFFF, "LONE_SURROGATE", self._path())
                output.append(ch)
                continue
            require(self.index < len(self.text), "STRING_ESCAPE_TRUNCATED", self._path())
            esc = self.text[self.index]
            self.index += 1
            mapping = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
            if esc in mapping:
                output.append(mapping[esc])
                continue
            require(esc == "u", "STRING_ESCAPE_INVALID", self._path(), esc)
            first = self._hex4()
            if 0xD800 <= first <= 0xDBFF:
                self._take("\\u")
                second = self._hex4()
                require(0xDC00 <= second <= 0xDFFF, "SURROGATE_PAIR_INVALID", self._path())
                output.append(chr(0x10000 + ((first - 0xD800) << 10) + (second - 0xDC00)))
            else:
                require(not 0xDC00 <= first <= 0xDFFF, "LONE_SURROGATE", self._path())
                output.append(chr(first))
        refuse("STRING_UNTERMINATED", self._path())

    def _hex4(self) -> int:
        require(self.index + 4 <= len(self.text), "UNICODE_ESCAPE_TRUNCATED", self._path())
        raw = self.text[self.index:self.index + 4]
        require(all(ch in HEX for ch in raw), "UNICODE_ESCAPE_INVALID", self._path(), raw)
        self.index += 4
        return int(raw, 16)

    def _number(self) -> int:
        start = self.index
        if self.text[self.index] == "-":
            self.index += 1
            require(self.index < len(self.text), "NUMBER_TRUNCATED", self._path())
        if self.text[self.index] == "0":
            self.index += 1
            require(self.index == len(self.text) or self.text[self.index] not in "0123456789", "NUMBER_LEADING_ZERO", self._path())
        else:
            require("1" <= self.text[self.index] <= "9", "NUMBER_INVALID", self._path())
            while self.index < len(self.text) and self.text[self.index] in "0123456789":
                self.index += 1
        if self.index < len(self.text) and self.text[self.index] in ".eE":
            refuse("FLOAT_NOT_ALLOWED", self._path())
        raw = self.text[start:self.index]
        value = int(raw, 10)
        require(I64_MIN <= value <= I64_MAX, "INTEGER_OUT_OF_RANGE", self._path(), raw)
        return value

    def _array(self, depth: int) -> list[Any]:
        self._take("[")
        self._ws()
        result: list[Any] = []
        if self.index < len(self.text) and self.text[self.index] == "]":
            self.index += 1
            return result
        while True:
            self.items += 1
            require(self.items <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", self._path())
            result.append(self._value(depth))
            self._ws()
            require(self.index < len(self.text), "ARRAY_UNTERMINATED", self._path())
            ch = self.text[self.index]
            self.index += 1
            if ch == "]":
                return result
            require(ch == ",", "ARRAY_SEPARATOR_INVALID", self._path())
            self._ws()

    def _object(self, depth: int) -> dict[str, Any]:
        self._take("{")
        self._ws()
        result: dict[str, Any] = {}
        if self.index < len(self.text) and self.text[self.index] == "}":
            self.index += 1
            return result
        while True:
            self.items += 1
            require(self.items <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", self._path())
            require(self.index < len(self.text) and self.text[self.index] == '"', "OBJECT_KEY_REQUIRED", self._path())
            key = self._string()
            require(key not in result, "DUPLICATE_JSON_KEY", self._path(), key)
            self._ws()
            self._take(":")
            self._ws()
            result[key] = self._value(depth)
            self._ws()
            require(self.index < len(self.text), "OBJECT_UNTERMINATED", self._path())
            ch = self.text[self.index]
            self.index += 1
            if ch == "}":
                return result
            require(ch == ",", "OBJECT_SEPARATOR_INVALID", self._path())
            self._ws()


def parse_declared_json(raw: bytes | str) -> Any:
    if type(raw) is bytes:
        require(not raw.startswith(b"\xef\xbb\xbf"), "SOURCE_BOM_FORBIDDEN")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            from .errors import UCLSHRefusal

            raise UCLSHRefusal("INVALID_UTF8") from exc
    else:
        require(type(raw) is str, "SOURCE_INPUT_INVALID")
        text = raw
    return DeclaredJSONParser(text).parse()

