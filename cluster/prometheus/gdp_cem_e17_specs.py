"""Frozen specification for the E17 transition-state adapter preflight."""

from __future__ import annotations

import hashlib

import gdp_cem_e15_specs as e15


PROTOCOL_SHA256 = "43ca72e15570c0aaeb26b5ce0f1e6a961d77fc7dd5b8d472938a8e8f00277c03"
E16_STAGE_A_AUDIT_SHA256 = (
    "1eea0b08254b1de721f3db3c2106f51cfad825a27a5997134c5cbe2e34aea257"
)
E16_TASK_FIRST_SHA256 = (
    "790e7b7074cb4fb553c30a658548c132177380f72c962cb491ddcec307ff7773"
)
E16_ADAPTER_SUMMARY_SHA256 = {
    "pusht": "d1cdb460c46f34119b3f2d25ae25e8626814f7ff5d09cf2931c430471e7f4e66",
    "cube": "791593d4c9cf01647d47d28809ef552c78854661c7ed0772edc4db390e33b210",
}

TASKS = e15.TASKS
TASK_SPEC = e15.TASK_SPEC
EXPECTED_GPU_NAME = e15.EXPECTED_GPU_NAME
LATENT_DIM = e15.LATENT_DIM
ACTION_HORIZON = e15.ACTION_HORIZON
ACTION_BLOCK = e15.ACTION_BLOCK
TAU_VALUES = e15.TAU_VALUES

MODEL_SEED = 8171
MODEL_WIDTH = 512
MODEL_RESIDUAL_BLOCKS = 3
TRAIN_STEPS = 30_000
BATCH_SIZE = 1_024
WARMUP_STEPS = 1_000
LEARNING_RATE = 1.0e-3
WEIGHT_DECAY = 1.0e-4
GRADIENT_CLIP = 1.0
EMA_DECAY = 0.999
VALIDATION_BATCH_SIZE = 4_096
CACHE_BATCH_SIZE = 4_096

OVERALL_RMSE_MAX = 0.50
MAX_COORDINATE_RMSE_MAX = 0.85
MEDIAN_COORDINATE_R2_MIN = 0.50
COPY_CURRENT_RMSE_RATIO_MAX = 0.90
TAU_RMSE_MAX = 0.65
TAU_MEDIAN_COORDINATE_R2_MIN = 0.35


def input_dim(*, state_dim: int, action_dim: int) -> int:
    if min(state_dim, action_dim) <= 0:
        raise ValueError("invalid E17 task dimensions")
    return (
        3 * LATENT_DIM
        + state_dim
        + ACTION_HORIZON * action_dim
        + ACTION_HORIZON
        + len(TAU_VALUES)
    )


def derived_seed(label: str) -> int:
    value = hashlib.sha256(f"gdp-cem-e17|{label}".encode("utf-8")).digest()
    return int.from_bytes(value[:8], "little") % (2**63 - 1)


assert TAU_VALUES == (15, 20, 25)
assert all(value % ACTION_BLOCK == 0 for value in TAU_VALUES)
assert set(E16_ADAPTER_SUMMARY_SHA256) == set(TASKS)
