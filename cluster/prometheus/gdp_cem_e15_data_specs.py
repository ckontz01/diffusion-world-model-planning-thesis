"""Frozen non-outcome specification for the E15 data-only preflight."""

from __future__ import annotations

import hashlib
from typing import Any


TASKS = ("pusht", "cube")
DELTA_VALUES = (15, 20, 25, 30, 40, 45, 50, 60, 65, 75, 90, 100, 115, 125, 140, 150)
TAU_VALUES = (15, 20, 25)
DELTA_TAU_PAIRS = tuple(
    (delta, tau)
    for delta in DELTA_VALUES
    for tau in TAU_VALUES
    if tau <= delta
)
ACTION_HORIZON = 25
ACTION_BLOCK = 5
LATENT_DIM = 192
TRAIN_ROWS_PER_CELL = 6_500
VALIDATION_ROWS_PER_CELL = 2_000
TRAIN_ROWS = TRAIN_ROWS_PER_CELL * len(DELTA_TAU_PAIRS)
VALIDATION_ROWS = VALIDATION_ROWS_PER_CELL * len(DELTA_TAU_PAIRS)
SPLIT_SALT = "gdp-cem-e15-split"
NEAR_BOUNDARY_MARGINS = (1.0e-6, 1.0e-4, 1.0e-3, 1.0e-2, 5.0e-2)
JACOBIAN_THRESHOLDS = (1.0e-2, 1.0e-3, 1.0e-4)
RAW_ROUNDING_TOLERANCE = 4.0 * 1.1920928955078125e-7
PREFLIGHT_SPEC_SHA256 = "34ab12ba8f60fbcfd03361301fc69245719776c763aad88eb1162b520743d610"


TASK_SPEC: dict[str, dict[str, Any]] = {
    "pusht": {
        "dataset_file": "pusht_expert_train.h5",
        "dataset_sha256": "b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb",
        "state_dim": 7,
        "primitive_action_dim": 2,
        "artifact_slug": "lewm-hf-22b330c",
        "latent_job": 296628,
        "latent_sha256": "5c8ad694712c202ce6114f68d8155a41e2cf88c1c86d1dd442f70e29dc90e7e8",
        "latent_manifest_sha256": "d8e7dd2080edcf7dec20b57bccc929cc7a4a62691e4325244782ef414a9de2a7",
        "transition_job": 296629,
        "transition_sha256": "f21c7db64df174c73ab5f7c278c136590f378371ed668291dfecb59d6c6989f5",
        "e14_cache_job": "298993-0",
        "e14_cache_sha256": "ff102572c7eed39134002aa90af0bd324df1d1312522c994d19206ec5ac6bac9",
        "e14_cache_manifest_sha256": "93a20e7d46e5142e2231630ae74caeec4638ad8aaeab95ef5b4cbd8513b90c54",
    },
    "cube": {
        "dataset_file": "cube_single_expert.h5",
        "dataset_sha256": "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625",
        "state_dim": 28,
        "primitive_action_dim": 5,
        "artifact_slug": "lewm-hf-b0747c5",
        "latent_job": 296666,
        "latent_sha256": "81eb8b967168c5f30b25a99f1f766579f40adcdd71a77861f84ffaf20f3ac69d",
        "latent_manifest_sha256": "255ee1ab73152f7609a0606bd194d0f698f16043bbf406710fc77110be166404",
        "transition_job": 296667,
        "transition_sha256": "6b80c957821d285141fe85524d2ac8206bd3699049997a01971b36b869d611eb",
        "e14_cache_job": "298993-1",
        "e14_cache_sha256": "b7b4b63669d6eb05ccbc9cd7cc9a40e401f1a36ef0bdd9b61724dceb988b15f6",
        "e14_cache_manifest_sha256": "4385e22fcf199922d954a137817d283e829b345e66444a8644776ed592ef888e",
    },
}


def episode_is_validation(task: str, episode: int) -> bool:
    if task not in TASKS or episode < 0:
        raise ValueError("invalid E15 split key")
    payload = f"{SPLIT_SALT}\0{task}\0{episode}".encode("utf-8")
    value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return value % 4 == 0


def derived_seed(label: str) -> int:
    value = hashlib.sha256(f"gdp-cem-e15|{label}".encode("utf-8")).digest()
    return int.from_bytes(value[:8], "little") % (2**63 - 1)


assert len(DELTA_TAU_PAIRS) == 45
assert TRAIN_ROWS == 292_500
assert VALIDATION_ROWS == 90_000
