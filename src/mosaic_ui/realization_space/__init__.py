"""Engine-neutral Realization Space Contract kernel for Mosaic systems."""

from .core import (
    APPLY_MODES,
    STATE_EFFECTS,
    RealizationSpaceError,
    canonical_bytes,
    canonical_root,
    compose_contracts,
    select_configuration,
    validate_configuration,
    validate_contract,
)
from .registry import RealizationSpaceRegistry
from .transactions import RealizationTransactionManager
from .acceptance import cross_domain_acceptance

__all__ = [
    "APPLY_MODES",
    "STATE_EFFECTS",
    "RealizationSpaceError",
    "RealizationSpaceRegistry",
    "RealizationTransactionManager",
    "canonical_bytes",
    "canonical_root",
    "compose_contracts",
    "cross_domain_acceptance",
    "select_configuration",
    "validate_configuration",
    "validate_contract",
]
