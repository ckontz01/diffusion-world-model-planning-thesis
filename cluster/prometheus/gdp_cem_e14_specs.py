"""Frozen non-outcome specification for E14 long-horizon development."""

from __future__ import annotations

import hashlib
from typing import Any


TASKS = ("pusht", "cube")
MODEL_SEEDS = (6101, 6102, 6103)
DIAGNOSTIC_SEED = 6101
DELTA_VALUES = (15, 20, 25, 30, 40, 45, 50, 60, 65, 75, 90, 100, 115, 125, 140, 150)
TAU_VALUES = (15, 20, 25)
DELTA_TAU_PAIRS = tuple(
    (delta, tau)
    for delta in DELTA_VALUES
    for tau in TAU_VALUES
    if tau <= delta
)
TRAIN_ROWS = 400_000
VALIDATION_ROWS = 40_000
ACTION_HORIZON = 25
ACTION_BLOCK = 5
LATENT_DIM = 192
PROTOCOL_SHA256 = "9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6"
SAGE_SOURCE_TAR_SHA256 = "60167aed768eba55061f8a69e00ce6b81c19ff16e48bcbd6b16a59fd8d892180"

DIFFUSION_STEPS = 100
DIFFUSION_EVALUATIONS = 5
MODEL_WIDTH = 512
MODEL_DEPTH = 4
TIME_EMBEDDING_DIM = 128
TRAIN_STEPS = 30_000
BATCH_SIZE = 1_024
WARMUP_STEPS = 1_000
VALIDATION_EVERY = 1_000
CHECKPOINT_VALIDATION_ROWS = 8_192
VALIDATION_BATCH_SIZE = 2_048
LEARNING_RATE = 2.0e-4
WEIGHT_DECAY = 1.0e-4
GRADIENT_CLIP = 1.0
EMA_DECAY = 0.999
CONDITION_DROPOUT = 0.15
GUIDANCE_SCALE = 1.5

SCHEDULES: dict[int, tuple[int, ...]] = {
    25: (25,),
    50: (25, 25),
    75: (15, 15, 15, 15, 15),
    100: (15, 15, 15, 15, 15, 25),
    125: (15, 15, 15, 15, 15, 15, 15, 20),
    150: (15, 15, 15, 15, 15, 15, 15, 15, 15, 15),
}

TASK_SPEC: dict[str, dict[str, Any]] = {
    "pusht": {
        "dataset_name": "pusht_expert_train",
        "dataset_file": "pusht_expert_train.h5",
        "dataset_sha256": "b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb",
        "state_key": "state",
        "state_dim": 7,
        "primitive_action_dim": 2,
        "artifact_slug": "lewm-hf-22b330c",
        "latent_job": 296628,
        "latent_sha256": "5c8ad694712c202ce6114f68d8155a41e2cf88c1c86d1dd442f70e29dc90e7e8",
        "latent_manifest_sha256": "d8e7dd2080edcf7dec20b57bccc929cc7a4a62691e4325244782ef414a9de2a7",
        "transition_job": 296629,
        "transition_sha256": "f21c7db64df174c73ab5f7c278c136590f378371ed668291dfecb59d6c6989f5",
        "transition_manifest_sha256": "cd9cc114942538c9af40f27f53cf7c77d42e62ff42282210c1b6b706953193ca",
        "p1_role_sha256": "34dcff8a457fb636fbee836e836f752de66013154c36739613b9d5c81dcba5e6",
        "partition_manifest_sha256": "35cd851464f4d7243c3c07b794f65db0f32caa16bbc787a83dda68388c4898f0",
        "e14_cache_job": "298993-0",
        "e14_cache_sha256": "ff102572c7eed39134002aa90af0bd324df1d1312522c994d19206ec5ac6bac9",
        "e14_cache_manifest_sha256": "93a20e7d46e5142e2231630ae74caeec4638ad8aaeab95ef5b4cbd8513b90c54",
    },
    "cube": {
        "dataset_name": "ogbench/cube_single_expert",
        "dataset_file": "cube_single_expert.h5",
        "dataset_sha256": "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625",
        "state_key": "observation",
        "state_dim": 28,
        "primitive_action_dim": 5,
        "artifact_slug": "lewm-hf-b0747c5",
        "latent_job": 296666,
        "latent_sha256": "81eb8b967168c5f30b25a99f1f766579f40adcdd71a77861f84ffaf20f3ac69d",
        "latent_manifest_sha256": "255ee1ab73152f7609a0606bd194d0f698f16043bbf406710fc77110be166404",
        "transition_job": 296667,
        "transition_sha256": "6b80c957821d285141fe85524d2ac8206bd3699049997a01971b36b869d611eb",
        "transition_manifest_sha256": "3eb4df46fb4c458b822e4f33e7b19647ef8fab3c4426e2a6deff7df9c0fddfe1",
        "p1_role_sha256": "9f424915726822a251100c5a07e918ca811d6979ca30de7cf2d8960db9ffb516",
        "partition_manifest_sha256": "2bb7dbe8faedcf58dc00669def093efeb9b70198fe8602a9f650b09c5adfcf8d",
        "e14_cache_job": "298993-1",
        "e14_cache_sha256": "b7b4b63669d6eb05ccbc9cd7cc9a40e401f1a36ef0bdd9b61724dceb988b15f6",
        "e14_cache_manifest_sha256": "4385e22fcf199922d954a137817d283e829b345e66444a8644776ed592ef888e",
    },
}


def row_quotas(total: int) -> dict[tuple[int, int], int]:
    """Assign a deterministic near-equal quota to every valid pair."""

    if total < len(DELTA_TAU_PAIRS):
        raise ValueError("row total is smaller than the number of E14 cells")
    base, remainder = divmod(total, len(DELTA_TAU_PAIRS))
    return {
        pair: base + int(position < remainder)
        for position, pair in enumerate(DELTA_TAU_PAIRS)
    }


def schedule_for(horizon: int) -> tuple[int, ...]:
    try:
        schedule = SCHEDULES[int(horizon)]
    except (KeyError, ValueError) as error:
        raise ValueError(f"unsupported E14 horizon: {horizon}") from error
    if sum(schedule) != horizon or any(tau not in TAU_VALUES for tau in schedule):
        raise RuntimeError("invalid frozen E14 duration schedule")
    return schedule


def derived_seed(label: str) -> int:
    value = hashlib.sha256(f"gdp-cem-e14|{label}".encode("utf-8")).digest()
    return int.from_bytes(value[:8], "little") % (2**63 - 1)


assert len(DELTA_TAU_PAIRS) == 45
assert sum(row_quotas(TRAIN_ROWS).values()) == TRAIN_ROWS
assert sum(row_quotas(VALIDATION_ROWS).values()) == VALIDATION_ROWS
assert all(sum(value) == key for key, value in SCHEDULES.items())
