#!/usr/bin/env python3

from __future__ import annotations

import argparse
import inspect
from pathlib import Path

import stable_worldmodel as swm

from h_le_wm.eval.hierarchical import force_torch_load_map_location


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    args = parser.parse_args()

    with force_torch_load_map_location("cpu"):
        model = swm.policy.AutoCostModel(args.policy, cache_dir=args.stablewm_home)
    model_type = type(model)
    print(f"model_type={model_type.__module__}.{model_type.__qualname__}")
    print(f"source_file={inspect.getsourcefile(model_type)}")
    print("--- get_cost ---")
    print(inspect.getsource(model_type.get_cost))
    print("--- get_cost_high ---")
    print(inspect.getsource(model_type.get_cost_high))


if __name__ == "__main__":
    main()
