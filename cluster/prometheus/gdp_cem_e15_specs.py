"""Frozen non-outcome specification for E15 long-horizon development."""

from __future__ import annotations

import hashlib
from typing import Any


PROTOCOL_SHA256 = "bcbe66b3b7b2635473d5bd98b3a450c5e136879f275ac3a0ddd6d4bdb254755b"
DATA_PREFLIGHT_SOURCE_MANIFEST_SHA256 = (
    "1b97e2286e1237a8c758ed5951e9a64433b2e41b4d10a6eb79215dcf8bc1fd46"
)
SAGE_NORMALIZATION_AUDIT_SHA256 = (
    "985454c195d2f785c665eb59d81efadb789512a4d03f3e44ffa3ac24140b6b40"
)
SAGE_SOURCE_TAR_SHA256 = (
    "60167aed768eba55061f8a69e00ce6b81c19ff16e48bcbd6b16a59fd8d892180"
)
EXPECTED_GPU_NAME = "NVIDIA RTX 6000 Ada Generation"

TASKS = ("pusht", "cube")
MODEL_SEEDS = (7201, 7202, 7203)
NULL_SEED = 7201
DELTA_VALUES = (15, 20, 25, 30, 40, 45, 50, 60, 65, 75, 90, 100, 115, 125, 140, 150)
TAU_VALUES = (15, 20, 25)
DELTA_TAU_PAIRS = tuple(
    (delta, tau)
    for delta in DELTA_VALUES
    for tau in TAU_VALUES
    if tau <= delta
)
TRAIN_ROWS_PER_CELL = 6_500
VALIDATION_ROWS_PER_CELL = 2_000
TRAIN_ROWS = TRAIN_ROWS_PER_CELL * len(DELTA_TAU_PAIRS)
VALIDATION_ROWS = VALIDATION_ROWS_PER_CELL * len(DELTA_TAU_PAIRS)
ACTION_HORIZON = 25
ACTION_BLOCK = 5
LATENT_DIM = 192

MODEL_WIDTH = 512
MODEL_DEPTH = 4
TIME_EMBEDDING_DIM = 128
DIFFUSION_STEPS = 100
DIFFUSION_EVALUATIONS = 5
CONDITION_DROPOUT = 0.15
GUIDANCE_SCALE = 1.5
GMM_MODES = 8
GMM_BALANCE_WEIGHT = 0.05
LOG_STD_MIN = -5.0
LOG_STD_MAX = 2.0

TRAIN_STEPS = 30_000
BATCH_SIZE = 1_024
WARMUP_STEPS = 1_000
LEARNING_RATE = 2.0e-4
WEIGHT_DECAY = 1.0e-4
GRADIENT_CLIP = 1.0
EMA_DECAY = 0.999
LOG_EVERY = 1_000

CANDIDATE_COUNT = 300
CEM_ROUNDS = 30
CEM_ELITES = 30
OFFLINE_BATCH_SIZE = 8
MINIMUM_UNIQUE_CANDIDATES = 285
NEAR_BOUNDARY_MARGINS = (1.0e-6, 1.0e-4, 1.0e-3, 1.0e-2, 5.0e-2)
JACOBIAN_THRESHOLDS = (1.0e-2, 1.0e-3, 1.0e-4)
BOUNDARY_GATE_MARGIN = 1.0e-2
JACOBIAN_GATE_THRESHOLD = 1.0e-3
EXPERT_MEAN_ADDITIVE_ALLOWANCE = 0.05
EXPERT_Q99_ADDITIVE_ALLOWANCE = 0.15
GMM_MINIMUM_GLOBAL_MODE_MASS = 0.005
GMM_MINIMUM_POSTERIOR_USED_MODES = 6
GMM_MINIMUM_POSTERIOR_WIN_FRACTION = 0.001
GMM_MINIMUM_NORMALIZED_ENTROPY = 0.25

GATE_C_HORIZONS = (25, 75, 150)
GATE_C_LONG_HORIZONS = (75, 150)
GATE_C_BASE_STARTS = 20
GATE_C_SHARD_SIZE = 5
GATE_C_SHARD_COUNT = GATE_C_BASE_STARTS // GATE_C_SHARD_SIZE
ARMS = (
    "base_cem",
    "sage_reconstruction",
    "sage_one_stage",
    "vad",
    "direct_gmm",
    "diagonal_gaussian",
)
SCHEDULES: dict[int, tuple[int, ...]] = {
    25: (25,),
    75: (15, 15, 15, 15, 15),
    150: (15, 15, 15, 15, 15, 15, 15, 15, 15, 15),
}

TRAINING_CONDITIONS = (
    "vad",
    "diagonal_gaussian",
    "direct_gmm",
    "vad_shuffled",
    "vad_unconditional",
)

TASK_SPEC: dict[str, dict[str, Any]] = {
    "pusht": {
        "dataset_name": "pusht_expert_train",
        "dataset_file": "pusht_expert_train.h5",
        "dataset_sha256": "b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb",
        "state_key": "state",
        "state_dim": 7,
        "primitive_action_dim": 2,
        "artifact_slug": "lewm-hf-22b330c",
        "world_model_policy": "pusht/lewm_hf_22b330c",
        "world_model_file": "pusht/lewm_hf_22b330c_object.ckpt",
        "world_model_sha256": "c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659",
        "latent_job": 296628,
        "latent_sha256": "5c8ad694712c202ce6114f68d8155a41e2cf88c1c86d1dd442f70e29dc90e7e8",
        "latent_manifest_sha256": "d8e7dd2080edcf7dec20b57bccc929cc7a4a62691e4325244782ef414a9de2a7",
        "transition_job": 296629,
        "transition_sha256": "f21c7db64df174c73ab5f7c278c136590f378371ed668291dfecb59d6c6989f5",
        "e15_cache_sha256": "2efc57e077cc6e5a627bf73b8ee50eeb308091d52fb734c71a79eb37279146a9",
        "e15_cache_manifest_sha256": "c8af1ddbf5e830a9257dba3a484d9eb10272d20fc11ea0f348080e9443c16dcc",
        "p2_queries_sha256": "a2308d25a274c2459187220ed15a028734dd9bbfb92c7bd41b878f4d76df9ce3",
        "p2_manifest_sha256": "8730a5d659cb6f084f42ae666ea9689c9cc9c0fbdd7d38728b626db6e6e3251d",
        "partition_manifest_sha256": "35cd851464f4d7243c3c07b794f65db0f32caa16bbc787a83dda68388c4898f0",
    },
    "cube": {
        "dataset_name": "ogbench/cube_single_expert",
        "dataset_file": "cube_single_expert.h5",
        "dataset_sha256": "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625",
        "state_key": "observation",
        "state_dim": 28,
        "primitive_action_dim": 5,
        "artifact_slug": "lewm-hf-b0747c5",
        "world_model_policy": "cube/lewm_hf_b0747c5",
        "world_model_file": "cube/lewm_hf_b0747c5_object.ckpt",
        "world_model_sha256": "5175b8d7a99b3c19aeee08027c666fb0562e316f14c36e74ac3a52ecce531e07",
        "latent_job": 296666,
        "latent_sha256": "81eb8b967168c5f30b25a99f1f766579f40adcdd71a77861f84ffaf20f3ac69d",
        "latent_manifest_sha256": "255ee1ab73152f7609a0606bd194d0f698f16043bbf406710fc77110be166404",
        "transition_job": 296667,
        "transition_sha256": "6b80c957821d285141fe85524d2ac8206bd3699049997a01971b36b869d611eb",
        "e15_cache_sha256": "b48ebb4735662d702289b9da12e55dc31766e8f1f245c1486f50e58cb0fb2994",
        "e15_cache_manifest_sha256": "e8c547962238fcd37b463acc0343b997af5525a90116c01b5f9f889fb23fd4a9",
        "p2_queries_sha256": "936acc3998a4adaa2e6661111802f093e030e2cd3619059b4dc0b71a76fcaf35",
        "p2_manifest_sha256": "704ac338599894ebd6ae7989c5ba7a151259104c05a58e4e11c87e27e6b9a017",
        "partition_manifest_sha256": "2bb7dbe8faedcf58dc00669def093efeb9b70198fe8602a9f650b09c5adfcf8d",
    },
}


def schedule_for(horizon: int) -> tuple[int, ...]:
    try:
        result = SCHEDULES[int(horizon)]
    except (KeyError, ValueError) as error:
        raise ValueError(f"unsupported E15 horizon: {horizon}") from error
    if sum(result) != horizon or any(value not in TAU_VALUES for value in result):
        raise RuntimeError("invalid E15 schedule")
    return result


def derived_seed(label: str) -> int:
    value = hashlib.sha256(f"gdp-cem-e15|{label}".encode("utf-8")).digest()
    return int.from_bytes(value[:8], "little") % (2**63 - 1)


assert len(DELTA_TAU_PAIRS) == 45
assert TRAIN_ROWS == 292_500
assert VALIDATION_ROWS == 90_000
assert GATE_C_BASE_STARTS % GATE_C_SHARD_SIZE == 0
assert all(sum(value) == key for key, value in SCHEDULES.items())
