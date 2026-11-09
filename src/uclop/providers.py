from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Callable

from .canonical import Refusal, exact_keys, require, require_root, root, validate_value
from .ecosystem import EFFECT_CLASSES, effect_rank


_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")


def _validate_output_authority_boundary(value: Any) -> None:
    """Prevent a NONE-effect adapter from smuggling constitutional effects in its data."""
    pending = [(value, "$")]
    while pending:
        current, path = pending.pop()
        if type(current) is dict:
            for key, item in current.items():
                child = f"{path}.{key}"
                if key in {"effect_observed", "effects_observed", "authority_effect"}:
                    require(item == "NONE", "PROVIDER_OUTPUT_AUTHORITY_INVALID", child)
                elif key == "standing":
                    require(item == "INFORMATION_ONLY", "PROVIDER_OUTPUT_AUTHORITY_INVALID", child)
                elif key == "real_a5":
                    require(item is False, "PROVIDER_OUTPUT_AUTHORITY_INVALID", child)
                elif key == "g0":
                    require(item == "CLOSED", "PROVIDER_OUTPUT_AUTHORITY_INVALID", child)
                elif key in {"installed", "released", "production_active", "admitted", "identity_seated"}:
                    require(item is False, "PROVIDER_OUTPUT_AUTHORITY_INVALID", child)
                pending.append((item, child))
        elif type(current) is list:
            pending.extend((item, f"{path}[{index}]") for index, item in enumerate(current))


def make_provider_descriptor(
    *, provider_id: str, capability_id: str, implementation_root: str,
    input_schema_root: str, output_schema_root: str, effect_class: str,
    deterministic: bool, portable: bool,
) -> dict[str, Any]:
    require(type(provider_id) is str and bool(_ID.fullmatch(provider_id)), "PROVIDER_ID_INVALID")
    require(type(capability_id) is str and bool(_ID.fullmatch(capability_id)), "PROVIDER_CAPABILITY_INVALID")
    require(effect_class in EFFECT_CLASSES, "PROVIDER_EFFECT_CLASS_INVALID")
    require(type(deterministic) is bool and type(portable) is bool, "PROVIDER_FLAG_INVALID")
    body = {
        "schema": "ucl.ucm.provider_descriptor.v1", "provider_id": provider_id,
        "capability_id": capability_id, "implementation_root": require_root(implementation_root),
        "input_schema_root": require_root(input_schema_root), "output_schema_root": require_root(output_schema_root),
        "effect_class": effect_class, "deterministic": deterministic, "portable": portable,
        "private_material_mode": "EXTERNAL_OPAQUE", "current_execution_ceiling": "NONE",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "provider_root": root(body)}


def verify_provider_descriptor(value: Any, *, expected_capability_id: str | None = None, expected_effect_class: str | None = None) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "provider_id", "capability_id", "implementation_root", "input_schema_root",
        "output_schema_root", "effect_class", "deterministic", "portable", "private_material_mode",
        "current_execution_ceiling", "standing", "authority_effect", "provider_root",
    }, "$.provider")
    body = {key: item[key] for key in item if key != "provider_root"}
    expected = make_provider_descriptor(
        provider_id=item["provider_id"], capability_id=item["capability_id"],
        implementation_root=item["implementation_root"], input_schema_root=item["input_schema_root"],
        output_schema_root=item["output_schema_root"], effect_class=item["effect_class"],
        deterministic=item["deterministic"], portable=item["portable"],
    )
    require(item == expected and item["provider_root"] == root(body), "PROVIDER_DESCRIPTOR_INVALID")
    if expected_capability_id is not None:
        require(item["capability_id"] == expected_capability_id, "PROVIDER_CAPABILITY_MISMATCH")
    if expected_effect_class is not None:
        require(item["effect_class"] == expected_effect_class, "PROVIDER_EFFECT_CLASS_MISMATCH")
    return deepcopy(body)


def verify_provider_registry_snapshot(value: Any, *, expected_subject_root: str | None = None, expected_capability_roots: dict[str, str] | None = None) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "capability_roots", "capability_effects", "providers", "trusted_no_effect_implementation_roots", "trusted_schema_roots", "provider_count", "effectful_handlers_installed", "standing", "authority_effect", "registry_root"}, "$.provider_registry")
    body = {key: item[key] for key in item if key != "registry_root"}
    require(item["schema"] == "ucl.ucm.provider_registry.v1" and item["registry_root"] == root(body), "PROVIDER_REGISTRY_ROOT_INVALID")
    require_root(item["subject_root"])
    if expected_subject_root is not None: require(item["subject_root"] == require_root(expected_subject_root), "PROVIDER_REGISTRY_SUBJECT_MISMATCH")
    require(type(item["capability_roots"]) is dict and item["capability_roots"], "PROVIDER_CAPABILITY_ROOTS_INVALID")
    capability_roots = {key: require_root(value) for key, value in sorted(item["capability_roots"].items())}
    require(item["capability_roots"] == capability_roots, "PROVIDER_CAPABILITY_ROOTS_INVALID")
    if expected_capability_roots is not None: require(capability_roots == {key: require_root(value) for key, value in sorted(expected_capability_roots.items())}, "PROVIDER_CAPABILITY_ROOTS_MISMATCH")
    effects = item["capability_effects"]
    require(type(effects) is dict and set(effects) == set(capability_roots) and all(value in EFFECT_CLASSES for value in effects.values()), "PROVIDER_CAPABILITY_EFFECTS_INVALID")
    require(type(item["providers"]) is list and item["provider_count"] == len(item["providers"]), "PROVIDER_REGISTRY_COUNT_INVALID")
    trusted_implementations = item["trusted_no_effect_implementation_roots"]; trusted_schemas = item["trusted_schema_roots"]
    for values, code in ((trusted_implementations, "PROVIDER_TRUSTED_HANDLER_SET_INVALID"), (trusted_schemas, "PROVIDER_TRUSTED_SCHEMA_SET_INVALID")):
        require(type(values) is list and values == sorted(values) and len(values) == len(set(values)), code)
        for value in values: require_root(value)
    provider_ids = []
    for descriptor in item["providers"]:
        verify_provider_descriptor(descriptor)
        require(descriptor["capability_id"] in capability_roots and descriptor["effect_class"] == effects[descriptor["capability_id"]], "PROVIDER_REGISTRY_DESCRIPTOR_MISMATCH")
        if descriptor["effect_class"] == "NONE":
            require(descriptor["implementation_root"] in trusted_implementations and descriptor["input_schema_root"] in trusted_schemas and descriptor["output_schema_root"] in trusted_schemas, "PROVIDER_REGISTRY_TRUST_BINDING_MISSING")
        else:
            require(descriptor["implementation_root"] not in trusted_implementations, "EFFECTFUL_PROVIDER_HANDLER_FORBIDDEN")
        provider_ids.append(descriptor["provider_id"])
    require(provider_ids == sorted(provider_ids) and len(provider_ids) == len(set(provider_ids)), "PROVIDER_REGISTRY_ORDER_INVALID")
    require(item["effectful_handlers_installed"] is False and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "PROVIDER_REGISTRY_BOUNDARY_INVALID")
    return deepcopy(body)


class ProviderRegistry:
    """In-memory reference adapter registry. Effectful providers only emit proposals."""

    def __init__(self, *, subject_root: str, capability_roots: dict[str, str], capability_effects: dict[str, str] | None = None, trusted_no_effect_handlers: dict[str, Callable[[Any], Any]] | None = None, trusted_schema_validators: dict[str, Callable[[Any], bool]] | None = None) -> None:
        self.subject_root = require_root(subject_root)
        require(type(capability_roots) is dict and capability_roots, "PROVIDER_CAPABILITY_ROOTS_INVALID")
        self.capability_roots = {key: require_root(value) for key, value in sorted(capability_roots.items())}
        require(type(capability_effects) is dict and set(capability_effects) == set(self.capability_roots), "PROVIDER_CAPABILITY_EFFECTS_REQUIRED")
        require(all(value in EFFECT_CLASSES for value in capability_effects.values()), "PROVIDER_CAPABILITY_EFFECTS_INVALID")
        self.capability_effects = dict(sorted(capability_effects.items()))
        trusted_no_effect_handlers = {} if trusted_no_effect_handlers is None else trusted_no_effect_handlers
        require(type(trusted_no_effect_handlers) is dict, "PROVIDER_TRUSTED_HANDLER_SET_INVALID")
        self._trusted_handlers = {}
        for implementation_root, trusted_handler in trusted_no_effect_handlers.items():
            require_root(implementation_root); require(callable(trusted_handler), "PROVIDER_TRUSTED_HANDLER_SET_INVALID")
            self._trusted_handlers[implementation_root] = trusted_handler
        trusted_schema_validators = {} if trusted_schema_validators is None else trusted_schema_validators
        require(type(trusted_schema_validators) is dict, "PROVIDER_TRUSTED_SCHEMA_SET_INVALID")
        self._schema_validators: dict[str, Callable[[Any], bool]] = {}
        for schema_root, validator in trusted_schema_validators.items():
            require_root(schema_root); require(callable(validator), "PROVIDER_TRUSTED_SCHEMA_SET_INVALID")
            self._schema_validators[schema_root] = validator
        self._descriptors: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Callable[[Any], Any]] = {}

    def register(self, descriptor: dict[str, Any], handler: Callable[[Any], Any] | None = None) -> None:
        verify_provider_descriptor(descriptor)
        require(descriptor["capability_id"] in self.capability_roots, "PROVIDER_CAPABILITY_UNKNOWN")
        require(descriptor["effect_class"] == self.capability_effects[descriptor["capability_id"]], "PROVIDER_EFFECT_CLASS_MISMATCH")
        require(descriptor["provider_id"] not in self._descriptors, "PROVIDER_DUPLICATE")
        if descriptor["effect_class"] == "NONE":
            trusted_handler = self._trusted_handlers.get(descriptor["implementation_root"])
            require(trusted_handler is not None, "NO_EFFECT_PROVIDER_IMPLEMENTATION_UNTRUSTED")
            require(descriptor["input_schema_root"] in self._schema_validators, "PROVIDER_INPUT_SCHEMA_UNTRUSTED")
            require(descriptor["output_schema_root"] in self._schema_validators, "PROVIDER_OUTPUT_SCHEMA_UNTRUSTED")
            require(handler is None or handler is trusted_handler, "NO_EFFECT_PROVIDER_HANDLER_SUBSTITUTION")
            handler = trusted_handler
        else:
            require(handler is None, "EFFECTFUL_PROVIDER_HANDLER_FORBIDDEN")
        self._descriptors[descriptor["provider_id"]] = deepcopy(descriptor)
        if handler is not None:
            self._handlers[descriptor["provider_id"]] = handler

    def invoke(self, *, provider_id: str, capability_id: str, input_value: Any, request_root: str) -> dict[str, Any]:
        require(provider_id in self._descriptors, "PROVIDER_UNKNOWN")
        descriptor = self._descriptors[provider_id]
        require(descriptor["capability_id"] == capability_id, "PROVIDER_CAPABILITY_MISMATCH")
        require_root(request_root)
        input_root = root(input_value)
        if descriptor["effect_class"] != "NONE":
            body = {
                "schema": "ucl.ucm.provider_effect_proposal.v1", "provider_root": descriptor["provider_root"],
                "capability_id": capability_id, "request_root": request_root, "input_root": input_root,
                "effect_class": descriptor["effect_class"], "status": "UNBOUND_PROPOSAL",
                "executed": False, "effect_observed": "NONE", "standing": "INFORMATION_ONLY",
                "authority_effect": "NONE",
            }
            return {**body, "proposal_root": root(body)}
        try:
            require(self._schema_validators[descriptor["input_schema_root"]](deepcopy(input_value)) is True, "PROVIDER_INPUT_SCHEMA_MISMATCH")
        except Refusal as error:
            body = {
                "schema": "ucl.ucm.provider_execution_result.v1", "provider_root": descriptor["provider_root"],
                "capability_id": capability_id, "request_root": request_root, "input_root": input_root,
                "status": "REFUSED", "diagnostic": error.code, "detail": error.path,
                "output": None, "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            }
            return {**body, "result_root": root(body)}
        except Exception as error:
            body = {
                "schema": "ucl.ucm.provider_execution_result.v1", "provider_root": descriptor["provider_root"],
                "capability_id": capability_id, "request_root": request_root, "input_root": input_root,
                "status": "REFUSED", "diagnostic": "PROVIDER_INPUT_VALIDATOR_FAILED", "detail": type(error).__name__,
                "output": None, "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            }
            return {**body, "result_root": root(body)}
        try:
            output = self._handlers[provider_id](deepcopy(input_value))
        except Exception as error:
            body = {
                "schema": "ucl.ucm.provider_execution_result.v1", "provider_root": descriptor["provider_root"],
                "capability_id": capability_id, "request_root": request_root, "input_root": input_root,
                "status": "REFUSED", "diagnostic": "PROVIDER_HANDLER_FAILED", "detail": type(error).__name__,
                "output": None, "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            }
            return {**body, "result_root": root(body)}
        try:
            validate_value(output)
            _validate_output_authority_boundary(output)
            require(self._schema_validators[descriptor["output_schema_root"]](deepcopy(output)) is True, "PROVIDER_OUTPUT_SCHEMA_MISMATCH")
            safe_output = deepcopy(output)
        except Refusal as error:
            body = {
                "schema": "ucl.ucm.provider_execution_result.v1", "provider_root": descriptor["provider_root"],
                "capability_id": capability_id, "request_root": request_root, "input_root": input_root,
                "status": "REFUSED", "diagnostic": error.code, "detail": error.path,
                "output": None, "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            }
            return {**body, "result_root": root(body)}
        except Exception as error:
            body = {
                "schema": "ucl.ucm.provider_execution_result.v1", "provider_root": descriptor["provider_root"],
                "capability_id": capability_id, "request_root": request_root, "input_root": input_root,
                "status": "REFUSED", "diagnostic": "PROVIDER_OUTPUT_VALIDATOR_FAILED", "detail": type(error).__name__,
                "output": None, "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            }
            return {**body, "result_root": root(body)}
        body = {
            "schema": "ucl.ucm.provider_execution_result.v1", "provider_root": descriptor["provider_root"],
            "capability_id": capability_id, "request_root": request_root, "input_root": input_root,
            "status": "PASS", "diagnostic": "PASS", "detail": "", "output": safe_output,
            "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "result_root": root(body)}

    def snapshot(self) -> dict[str, Any]:
        providers = [deepcopy(self._descriptors[key]) for key in sorted(self._descriptors)]
        body = {
            "schema": "ucl.ucm.provider_registry.v1", "subject_root": self.subject_root,
            "capability_roots": self.capability_roots, "capability_effects": self.capability_effects, "providers": providers,
            "trusted_no_effect_implementation_roots": sorted(self._trusted_handlers),
            "trusted_schema_roots": sorted(self._schema_validators),
            "provider_count": len(providers), "effectful_handlers_installed": False,
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "registry_root": root(body)}

