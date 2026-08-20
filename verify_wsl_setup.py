"""Non-training verification for the SSD-backed Hi-LeWM workspace."""

from __future__ import annotations

import gc
from pathlib import Path

import gymnasium as gym
import h5py
import numpy as np
import stable_worldmodel  # noqa: F401 - registers the swm/* environments
import torch

import h_le_wm.eval.hierarchical  # noqa: F401 - registers checkpoint aliases
from h_le_wm.probe.model import load_hi_checkpoint


ROOT = Path("/home/chris/thesis/data/stablewm")


def verify_environments() -> None:
    for env_id in ("swm/PushT-v1", "swm/OGBCube-v0"):
        env = gym.make(env_id)
        observation, _ = env.reset(seed=0)
        shape = (
            {key: tuple(value.shape) for key, value in observation.items()}
            if isinstance(observation, dict)
            else tuple(observation.shape)
        )
        print(f"[ok] {env_id} reset(seed=0): {shape}")
        env.close()


def verify_checkpoints() -> None:
    checkpoints = (
        ("baseline PushT", ROOT / "pusht/lewm_object.ckpt", "object"),
        ("baseline Cube", ROOT / "cube/lewm_object.ckpt", "object"),
        (
            "Hi-LeWM PushT",
            ROOT
            / "runs/pusht_hierarchical_default/"
            "pusht_hierarchical_default_epoch_15_object.ckpt",
            "hi",
        ),
        (
            "Hi-LeWM Cube",
            ROOT
            / "runs/cube_hierarchical_default/"
            "cube_hierarchical_default_epoch_15_object.ckpt",
            "hi",
        ),
        (
            "probe phase A",
            ROOT / "runs/pusht_probe_phase_a/pusht_probe_phase_a_probe.pt",
            "payload",
        ),
        (
            "probe phase B",
            ROOT / "runs/pusht_probe_phase_b/pusht_probe_phase_b_probe.pt",
            "payload",
        ),
    )
    for label, path, kind in checkpoints:
        if kind == "hi":
            obj = load_hi_checkpoint(path)
        else:
            obj = torch.load(path, map_location="cpu", weights_only=False)
        if isinstance(obj, dict):
            detail = f"keys={sorted(map(str, obj))[:8]}"
        else:
            parameters = sum(p.numel() for p in obj.parameters())
            detail = f"type={type(obj).__module__}.{type(obj).__name__}; params={parameters}"
        print(f"[ok] {label}: {detail}")
        del obj
        gc.collect()


def verify_datasets() -> None:
    for path in (
        ROOT / "pusht_expert_train.h5",
        ROOT / "cube_single_expert.h5",
    ):
        dataset_count = 0
        logical_bytes = 0
        top_level_keys: list[str] = []
        with h5py.File(path, "r") as handle:
            top_level_keys = sorted(handle.keys())

            def inspect_dataset(_name: str, obj: h5py.Dataset | h5py.Group) -> None:
                nonlocal dataset_count, logical_bytes
                if not isinstance(obj, h5py.Dataset):
                    return
                dataset_count += 1
                logical_bytes += int(np.prod(obj.shape, dtype=np.int64)) * obj.dtype.itemsize
                if obj.size:
                    if obj.ndim:
                        _ = obj[0]
                        _ = obj[-1]
                    else:
                        _ = obj[()]

            handle.visititems(inspect_dataset)
        print(
            f"[ok] {path.name}: file_bytes={path.stat().st_size}; "
            f"datasets={dataset_count}; logical_bytes={logical_bytes}; "
            f"top_level={top_level_keys}"
        )


if __name__ == "__main__":
    print(f"torch={torch.__version__}; cuda_available={torch.cuda.is_available()}")
    verify_environments()
    verify_checkpoints()
    verify_datasets()
