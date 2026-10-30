"""Universal Constitutional Machine public v0.1 interface."""

from .system import VERSION, capability_registry, orientation
from .realization import (
    project_to_ucl_tessera,
    select_configuration,
    trace_preservation,
    validate_configuration,
    validate_contract,
)


def invoke(request):
    """Invoke a capability without importing optional capability providers early."""
    from .capabilities import invoke as dispatch
    return dispatch(request)

__all__ = [
    "VERSION",
    "capability_registry",
    "orientation",
    "validate_contract",
    "validate_configuration",
    "select_configuration",
    "project_to_ucl_tessera",
    "trace_preservation",
    "invoke",
]

