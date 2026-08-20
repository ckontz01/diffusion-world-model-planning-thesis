"""Matched native-ACID and diffusion-verifier study components."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ConditionalDiffusionVerifier",
    "DeterministicForwardVerifier",
    "FlowInverseDynamics",
    "SharedRolloutCostModel",
    "TemporalReachabilityHead",
    "count_parameters",
    "model_from_config",
    "select_capacity_matched_width",
]

_EXPORT_MODULE = {
    "SharedRolloutCostModel": ".costs",
    "ConditionalDiffusionVerifier": ".models",
    "DeterministicForwardVerifier": ".models",
    "FlowInverseDynamics": ".models",
    "TemporalReachabilityHead": ".models",
    "count_parameters": ".models",
    "model_from_config": ".models",
    "select_capacity_matched_width": ".models",
}


def __getattr__(name: str) -> Any:
    """Load torch-dependent public exports only when they are requested."""

    try:
        module_name = _EXPORT_MODULE[name]
    except KeyError as error:
        raise AttributeError(name) from error
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value
