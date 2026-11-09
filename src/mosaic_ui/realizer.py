"""Portable realizer protocol and conformance harness."""
from __future__ import annotations

import copy
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable

from .canonical import commitment
from .headless import HeadlessUI, LayoutProvider
from .model import UIRefusal


PROTOCOL_SCHEMA = "mosaic.ui.realizer-protocol.v0.1"
SUPPORTED_PROTOCOLS = (PROTOCOL_SCHEMA,)


class RealizerRefusal(UIRefusal):
    pass


def negotiate_protocol(
    offered: tuple[str, ...] | list[str],
    *,
    required_projections: tuple[str, ...] = (),
    descriptor: "RealizerDescriptor | None" = None,
) -> dict[str, Any]:
    if not isinstance(offered, (tuple, list)) or not offered \
            or not all(isinstance(item, str) and item for item in offered):
        raise RealizerRefusal("REALIZER_PROTOCOL_OFFER_REFUSED", "INVALID_OFFER")
    if len(set(offered)) != len(offered):
        raise RealizerRefusal("REALIZER_PROTOCOL_OFFER_REFUSED", "DUPLICATE_PROTOCOL")
    selected = next((item for item in offered if item in SUPPORTED_PROTOCOLS), None)
    if selected is None:
        raise RealizerRefusal("REALIZER_PROTOCOL_NEGOTIATION_REFUSED", ",".join(offered))
    projections = set(descriptor.projections) if descriptor is not None else set()
    missing = sorted(set(required_projections) - projections) if descriptor is not None else []
    if missing:
        raise RealizerRefusal("REALIZER_PROJECTION_NEGOTIATION_REFUSED", ",".join(missing))
    value = {
        "schema": "mosaic.ui.realizer-protocol-negotiation.v0.1",
        "offered": list(offered),
        "supported": list(SUPPORTED_PROTOCOLS),
        "selected": selected,
        "required_projections": list(required_projections),
        "disposition": "PASS_LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.REALIZER_PROTOCOL_NEGOTIATION.v0.1", value)
    return value


@dataclass(frozen=True)
class RealizerDescriptor:
    realizer_id: str
    protocol: str
    projections: tuple[str, ...]
    host_effects: tuple[str, ...]
    component_kinds: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.realizer-descriptor.v0.1",
            "realizer_id": self.realizer_id,
            "protocol": self.protocol,
            "projections": list(self.projections),
            "host_effects": list(self.host_effects),
            "component_kinds": list(self.component_kinds),
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.REALIZER_DESCRIPTOR.v0.1", value)
        return value


@runtime_checkable
class Realizer(Protocol):
    @property
    def descriptor(self) -> RealizerDescriptor: ...

    def apply(self, event: dict[str, Any]) -> dict[str, Any]: ...

    def snapshot(self) -> dict[str, Any]: ...

    def project(self, width: int, height: int) -> dict[str, Any]: ...

    def close(self) -> None: ...


class HeadlessRealizer:
    def __init__(
        self, payload: dict[str, Any], layout_provider: LayoutProvider | None = None,
        *, catalog: dict[str, Any] | None = None,
    ) -> None:
        self.runtime = HeadlessUI(payload, layout_provider, catalog=catalog)
        kinds = sorted({item["kind"] for item in self.runtime.nodes.values()})
        self._descriptor = RealizerDescriptor(
            "HEADLESS", PROTOCOL_SCHEMA,
            ("SEMANTICS", "GEOMETRY", "ACCESSIBILITY", "DRAW_STREAM", "GATES"),
            (), tuple(kinds),
        )

    @property
    def descriptor(self) -> RealizerDescriptor:
        return self._descriptor

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.apply(copy.deepcopy(event))

    def snapshot(self) -> dict[str, Any]:
        return self.runtime.snapshot()

    def project(self, width: int, height: int) -> dict[str, Any]:
        return self.runtime.project(width, height).as_dict()

    def close(self) -> None:
        return None


Factory = Callable[..., Realizer]


def _browser_factory(
    payload: dict[str, Any], layout: LayoutProvider | None, catalog: dict[str, Any] | None = None,
) -> Realizer:
    from .browser_realizer import BrowserRealizer

    return BrowserRealizer(payload, layout, catalog=catalog)


_FACTORIES: dict[str, Factory] = {
    "HEADLESS": lambda payload, layout, catalog=None: HeadlessRealizer(payload, layout, catalog=catalog),
    "BROWSER": _browser_factory,
}


def register_realizer(realizer_id: str, factory: Factory) -> None:
    key = realizer_id.strip().upper()
    if not key or key in _FACTORIES:
        raise RealizerRefusal("REALIZER_REGISTRATION_REFUSED", key)
    _FACTORIES[key] = factory


def enable_win32_realizer(*, width: int = 1280, height: int = 800, window_factory=None) -> None:
    """Install the native adapter explicitly; creating it may allocate a visible HWND."""
    def factory(
        payload: dict[str, Any], layout_provider: LayoutProvider | None,
        catalog: dict[str, Any] | None = None,
    ):
        from .native_realizer import NativeSemanticUI

        return NativeSemanticUI(
            payload, layout_provider, width=width, height=height,
            window_factory=window_factory, catalog=catalog,
        )

    _FACTORIES["WIN32"] = factory


def create_realizer(
    realizer_id: str,
    payload: dict[str, Any],
    layout_provider: LayoutProvider | None = None,
    *,
    catalog: dict[str, Any] | None = None,
    protocols: tuple[str, ...] = SUPPORTED_PROTOCOLS,
) -> Realizer:
    key = realizer_id.strip().upper()
    factory = _FACTORIES.get(key)
    if factory is None:
        raise RealizerRefusal("REALIZER_NOT_REGISTERED", key)
    negotiate_protocol(protocols)
    copied_payload = copy.deepcopy(payload)
    try:
        inspect.signature(factory).bind(copied_payload, layout_provider, catalog)
    except TypeError:
        result = factory(copied_payload, layout_provider)
    else:
        result = factory(copied_payload, layout_provider, catalog)
    if not isinstance(result, Realizer):
        raise RealizerRefusal("REALIZER_PROTOCOL_REFUSED", key)
    descriptor = result.descriptor
    if descriptor.realizer_id != key or descriptor.protocol != PROTOCOL_SCHEMA:
        raise RealizerRefusal("REALIZER_DESCRIPTOR_REFUSED", key)
    negotiate_protocol(protocols, descriptor=descriptor)
    return result


def conformance_witness(
    realizer: Realizer,
    *,
    viewports: tuple[tuple[int, int], ...] = ((1280, 800), (800, 600)),
    events: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    if not isinstance(realizer, Realizer):
        raise RealizerRefusal("REALIZER_PROTOCOL_REFUSED", type(realizer).__name__)
    initial = realizer.snapshot()
    transitions = []
    for event in events:
        transitions.append({"event": copy.deepcopy(event), "state": realizer.apply(event)})
    projections = []
    failures = []
    for width, height in viewports:
        projection = realizer.project(width, height)
        gate = projection.get("gates", {})
        if gate.get("disposition") != "PASS":
            failures.append({"viewport": [width, height], "gate": gate})
        projections.append({"viewport": [width, height], "projection": projection})
    value = {
        "schema": "mosaic.ui.realizer-conformance-witness.v0.1",
        "protocol": PROTOCOL_SCHEMA,
        "negotiation": negotiate_protocol((PROTOCOL_SCHEMA,), descriptor=realizer.descriptor),
        "descriptor": realizer.descriptor.as_dict(),
        "initial_state": initial,
        "transitions": transitions,
        "projections": projections,
        "failure_count": len(failures),
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "PROTOCOL_CONFORMANCE_DOES_NOT_ESTABLISH_PLATFORM_INTEGRATION",
    }
    value["commitment"] = commitment("MOSAIC.UI.REALIZER_CONFORMANCE.v0.1", value)
    return value


__all__ = [
    "PROTOCOL_SCHEMA", "SUPPORTED_PROTOCOLS", "HeadlessRealizer", "Realizer", "RealizerDescriptor", "RealizerRefusal",
    "conformance_witness", "create_realizer", "enable_win32_realizer", "register_realizer",
    "negotiate_protocol",
]
