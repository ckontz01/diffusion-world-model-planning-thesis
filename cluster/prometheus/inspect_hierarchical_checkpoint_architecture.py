#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

import torch

from h_le_wm.checkpoint_compat import register_legacy_checkpoint_modules


def register_stable_worldmodel_lewm_compat() -> None:
    """Provide module aliases needed by older official LeWM object checkpoints."""
    import jepa
    import module
    import stable_worldmodel.wm as stable_wm_package

    if not hasattr(module, "Predictor"):
        module.Predictor = module.ARPredictor
    baseline_dynamic = sys.modules.get("_baseline_lewm_module")
    if baseline_dynamic is not None and not hasattr(baseline_dynamic, "Predictor"):
        baseline_dynamic.Predictor = baseline_dynamic.ARPredictor

    lewm_package = types.ModuleType("stable_worldmodel.wm.lewm")
    lewm_package.__path__ = []
    lewm_implementation = types.ModuleType("stable_worldmodel.wm.lewm.lewm")
    lewm_implementation.LeWM = jepa.JEPA
    lewm_implementation.JEPA = jepa.JEPA
    lewm_package.LeWM = jepa.JEPA
    lewm_package.JEPA = jepa.JEPA
    lewm_package.lewm = lewm_implementation
    lewm_package.module = module
    sys.modules.setdefault("stable_worldmodel.wm.lewm", lewm_package)
    sys.modules.setdefault("stable_worldmodel.wm.lewm.lewm", lewm_implementation)
    sys.modules.setdefault("stable_worldmodel.wm.lewm.module", module)
    if not hasattr(stable_wm_package, "lewm"):
        stable_wm_package.lewm = lewm_package


def module_summary(module: torch.nn.Module) -> dict:
    state = module.state_dict()
    return {
        "type": f"{type(module).__module__}.{type(module).__name__}",
        "parameter_count": sum(parameter.numel() for parameter in module.parameters()),
        "trainable_parameter_count": sum(
            parameter.numel() for parameter in module.parameters() if parameter.requires_grad
        ),
        "state_shapes": {name: list(value.shape) for name, value in state.items()},
    }


def states_equal(left: torch.nn.Module, right: torch.nn.Module) -> bool:
    left_state = left.state_dict()
    right_state = right.state_dict()
    if left_state.keys() != right_state.keys():
        return False
    return all(torch.equal(left_state[key].cpu(), right_state[key].cpu()) for key in left_state)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hierarchical", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    register_legacy_checkpoint_modules()
    register_stable_worldmodel_lewm_compat()
    hierarchical = torch.load(
        args.hierarchical, map_location="cpu", weights_only=False
    )
    base = torch.load(args.base, map_location="cpu", weights_only=False)
    if hasattr(hierarchical, "model"):
        hierarchical = hierarchical.model
    if hasattr(base, "model"):
        base = base.model

    module_names = [
        "encoder",
        "low_predictor",
        "action_encoder",
        "high_predictor",
        "latent_action_encoder",
        "macro_to_condition",
        "projector",
        "low_pred_proj",
        "high_pred_proj",
    ]
    modules = {}
    for name in module_names:
        value = getattr(hierarchical, name)
        modules[name] = module_summary(value)

    shared_pairs = {
        "encoder": "encoder",
        "low_predictor": "predictor",
        "action_encoder": "action_encoder",
        "projector": "projector",
        "low_pred_proj": "pred_proj",
    }
    shared_equal = {
        hierarchical_name: states_equal(
            getattr(hierarchical, hierarchical_name), getattr(base, base_name)
        )
        for hierarchical_name, base_name in shared_pairs.items()
    }

    payload = {
        "hierarchical_type": f"{type(hierarchical).__module__}.{type(hierarchical).__name__}",
        "base_type": f"{type(base).__module__}.{type(base).__name__}",
        "hierarchical_parameter_count": sum(
            parameter.numel() for parameter in hierarchical.parameters()
        ),
        "hierarchical_trainable_parameter_count": sum(
            parameter.numel()
            for parameter in hierarchical.parameters()
            if parameter.requires_grad
        ),
        "modules": modules,
        "frozen_low_level_state_equals_base": shared_equal,
        "freeze_flags": getattr(hierarchical, "_freeze_flags", None),
    }
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
