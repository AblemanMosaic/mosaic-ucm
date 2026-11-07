"""Closed, deterministic localization and text-direction resolution."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .canonical import commitment
from .model import UIRefusal


SCHEMA = "mosaic.ui.localization.v0.1"
_LOCALE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
_MESSAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_DIRECTIONS = {"LTR", "RTL"}
_MAX_LOCALES = 64
_MAX_MESSAGES = 8192
_MAX_MESSAGE_LENGTH = 65536


@dataclass(frozen=True)
class LocalizationResolution:
    locale: str
    direction: str
    default_locale: str
    supported_locales: tuple[str, ...]
    message_count: int
    reference_count: int
    fallback_count: int
    contract_commitment: str

    def as_dict(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.localization-resolution.v0.1",
            "locale": self.locale,
            "direction": self.direction,
            "default_locale": self.default_locale,
            "supported_locales": list(self.supported_locales),
            "message_count": self.message_count,
            "reference_count": self.reference_count,
            "fallback_count": self.fallback_count,
            "contract_commitment": self.contract_commitment,
            "standing": "LOCAL_CANDIDATE_EVIDENCE",
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.LOCALIZATION_RESOLUTION.v0.1", value)
        return value


def _locale_key(value: str) -> str:
    return value.lower()


def _validate_locale(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _LOCALE.fullmatch(value):
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", f"{where}:LOCALE")
    return value


def _validate_contract(value: Any) -> tuple[dict[str, Any], tuple[str, ...]]:
    if value is None:
        value = {
            "schema": SCHEMA,
            "default_locale": "en",
            "supported_locales": ["en"],
            "directions": {"en": "LTR"},
            "messages": {"en": {}},
        }
    if not isinstance(value, dict):
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "NOT_OBJECT")
    allowed = {"schema", "default_locale", "supported_locales", "directions", "messages"}
    extra = sorted(set(value) - allowed)
    if extra or value.get("schema") != SCHEMA:
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "SCHEMA" if not extra else f"UNKNOWN:{','.join(extra)}")
    supported_value = value.get("supported_locales")
    if not isinstance(supported_value, list) or not supported_value or len(supported_value) > _MAX_LOCALES:
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "SUPPORTED_LOCALES")
    supported = tuple(_validate_locale(item, "SUPPORTED") for item in supported_value)
    if len({_locale_key(item) for item in supported}) != len(supported):
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "DUPLICATE_LOCALE")
    default = _validate_locale(value.get("default_locale"), "DEFAULT")
    lookup = {_locale_key(item): item for item in supported}
    if _locale_key(default) not in lookup:
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "DEFAULT_NOT_SUPPORTED")
    value["default_locale"] = lookup[_locale_key(default)]
    directions, messages = value.get("directions"), value.get("messages")
    if not isinstance(directions, dict) or set(directions) != set(supported):
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "DIRECTIONS")
    if any(direction not in _DIRECTIONS for direction in directions.values()):
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "DIRECTION")
    if not isinstance(messages, dict) or set(messages) != set(supported):
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "MESSAGES")
    for locale, bundle in messages.items():
        if not isinstance(bundle, dict) or len(bundle) > _MAX_MESSAGES:
            raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", f"BUNDLE:{locale}")
        for message_id, message in bundle.items():
            if not isinstance(message_id, str) or not _MESSAGE_ID.fullmatch(message_id):
                raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", f"MESSAGE_ID:{locale}")
            if not isinstance(message, str) or len(message) > _MAX_MESSAGE_LENGTH:
                raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", f"MESSAGE:{locale}:{message_id}")
    return copy.deepcopy(value), supported


def resolve_locale(
    contract: dict[str, Any] | None, requested_locale: str | None = None,
    accept_language: str | None = None,
) -> str:
    value, supported = _validate_contract(contract)
    lookup = {_locale_key(item): item for item in supported}

    def match(candidate: str) -> str | None:
        key = _locale_key(candidate)
        if key in lookup:
            return lookup[key]
        language = key.split("-", 1)[0]
        return next((item for item in supported if _locale_key(item).split("-", 1)[0] == language), None)

    if requested_locale is not None:
        candidate = _validate_locale(requested_locale, "REQUESTED")
        selected = match(candidate)
        if selected is None:
            raise UIRefusal("LOCALE_NEGOTIATION_REFUSED", candidate)
        return selected
    if accept_language:
        weighted: list[tuple[float, int, str]] = []
        if len(accept_language) > 4096:
            raise UIRefusal("LOCALE_NEGOTIATION_REFUSED", "HEADER_SIZE")
        for index, raw in enumerate(accept_language.split(",")):
            parts = [item.strip() for item in raw.split(";")]
            candidate, quality = parts[0], 1.0
            for parameter in parts[1:]:
                if parameter.lower().startswith("q="):
                    try:
                        quality = float(parameter[2:])
                    except ValueError:
                        quality = -1
            if quality < 0 or quality > 1:
                raise UIRefusal("LOCALE_NEGOTIATION_REFUSED", "QUALITY")
            if candidate == "*":
                candidate = str(value["default_locale"])
            elif not _LOCALE.fullmatch(candidate):
                continue
            weighted.append((-quality, index, candidate))
        for _quality, _index, candidate in sorted(weighted):
            selected = match(candidate)
            if selected is not None:
                return selected
    return lookup[_locale_key(str(value["default_locale"]))]


def _resolve_refs(
    value: Any, selected: dict[str, str], fallback: dict[str, str], counters: list[int],
) -> Any:
    if isinstance(value, dict):
        if set(value) == {"message_id"}:
            message_id = value.get("message_id")
            if not isinstance(message_id, str) or not _MESSAGE_ID.fullmatch(message_id):
                raise UIRefusal("LOCALIZATION_REFERENCE_REFUSED", "MESSAGE_ID")
            counters[0] += 1
            if message_id in selected:
                return selected[message_id]
            if message_id in fallback:
                counters[1] += 1
                return fallback[message_id]
            raise UIRefusal("LOCALIZATION_REFERENCE_REFUSED", message_id)
        if "message_id" in value:
            raise UIRefusal("LOCALIZATION_REFERENCE_REFUSED", "REFERENCE_SHAPE")
        return {key: _resolve_refs(item, selected, fallback, counters) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_refs(item, selected, fallback, counters) for item in value]
    return copy.deepcopy(value)


def resolve_payload(
    payload: dict[str, Any], requested_locale: str | None = None, accept_language: str | None = None,
) -> tuple[dict[str, Any], LocalizationResolution]:
    if not isinstance(payload, dict) or not isinstance(payload.get("application"), dict):
        raise UIRefusal("LOCALIZATION_CONTRACT_REFUSED", "APPLICATION")
    source = copy.deepcopy(payload)
    contract, supported = _validate_contract(source["application"].get("localization"))
    locale = resolve_locale(contract, requested_locale, accept_language)
    default = str(contract["default_locale"])
    counters = [0, 0]
    application = {key: item for key, item in source["application"].items() if key != "localization"}
    source["application"] = _resolve_refs(
        application, contract["messages"][locale], contract["messages"][default], counters,
    )
    source["application"]["localization"] = contract
    contract_root = commitment("MOSAIC.UI.LOCALIZATION_CONTRACT.v0.1", contract)
    resolution = LocalizationResolution(
        locale, str(contract["directions"][locale]), default, supported,
        len(contract["messages"][locale]), counters[0], counters[1], contract_root,
    )
    return source, resolution


def available_locales(payload: dict[str, Any]) -> tuple[str, ...]:
    application = payload.get("application", {}) if isinstance(payload, dict) else {}
    _contract, supported = _validate_contract(application.get("localization"))
    return supported


def mirror_layout(plan: dict[str, tuple[int, int, int, int]], width: int) -> dict[str, tuple[int, int, int, int]]:
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise UIRefusal("RTL_LAYOUT_REFUSED", "VIEWPORT_WIDTH")
    mirrored: dict[str, tuple[int, int, int, int]] = {}
    for key, rect in plan.items():
        if not isinstance(rect, tuple) or len(rect) != 4 or any(isinstance(v, bool) or not isinstance(v, int) for v in rect):
            raise UIRefusal("RTL_LAYOUT_REFUSED", str(key))
        x, y, item_width, item_height = rect
        mirrored[key] = (width - x - item_width, y, item_width, item_height)
    return mirrored


def localization_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    locales = available_locales(payload)
    rows = []
    failures = []
    for locale in locales:
        try:
            _resolved, resolution = resolve_payload(payload, locale)
            row = resolution.as_dict()
            if row["locale"] != locale or row["direction"] not in _DIRECTIONS:
                failures.append(f"RESOLUTION:{locale}")
            rows.append(row)
        except UIRefusal as exc:
            failures.append(f"{locale}:{exc.code}:{exc.detail}")
    value = {
        "schema": "mosaic.ui.localization-evidence.v0.1",
        "supported_locales": list(locales),
        "directions": sorted({row["direction"] for row in rows}),
        "resolutions": rows,
        "failure_count": len(failures),
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "DETERMINISTIC_CONTRACT_AND_HOST_PROJECTION_EVIDENCE_NOT_HUMAN_TRANSLATION_CERTIFICATION",
    }
    value["commitment"] = commitment("MOSAIC.UI.LOCALIZATION_EVIDENCE.v0.1", value)
    return value


__all__ = [
    "LocalizationResolution", "SCHEMA", "available_locales", "localization_evidence", "mirror_layout",
    "resolve_locale", "resolve_payload",
]
