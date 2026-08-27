"""Frozen specification for the E18 exploratory continuation planner."""

from __future__ import annotations

import hashlib

import gdp_cem_e15_specs as e15


PROTOCOL_SHA256 = "aff490f3f000c7d9b261632dcd3ccfc76a630b2f44e41f78832c3719607b8459"
E15_TRAINING_SOURCE_MANIFEST_SHA256 = (
    "ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c"
)
E17_SOURCE_MANIFEST_SHA256 = (
    "9fb5a8c296feec81c7982a79272e502216eaf91ad987b0e70c156cb2c5ad9fc1"
)
E17_PROTOCOL_SHA256 = (
    "43ca72e15570c0aaeb26b5ce0f1e6a961d77fc7dd5b8d472938a8e8f00277c03"
)
E17_AUDIT_SHA256 = (
    "d819b5db889de3362f26c729df6000b53a7028917c3d527b7f74410aac5188f8"
)
E17_TASK_FIRST_SHA256 = (
    "3b3b37a25850d9fe2ff28f42595f4dc160a051cfa6923850ff461d17e227da07"
)
E17_SUMMARY_SHA256 = {
    "pusht": "9921b24e853259ddb5e7f1a4c530c11b1bf52346516d92e053a49ee900784b0a",
    "cube": "86bcc74435e3aed62377ed354eb90866e047d77baf61fbefbb6ad3c444831a33",
}
E17_CHECKPOINT_SHA256 = {
    "pusht": "c58726a3502bf52bbbaad6263c1f636ef393ecbd34835b021750f7451bed88b8",
    "cube": "008311d81dcf3753170a7ecfd886cfb23fddc0ec932150e609071d3c830214a0",
}
E17_GATE_PASSED = {"pusht": True, "cube": False}

TASKS = e15.TASKS
TASK_SPEC = e15.TASK_SPEC
MODEL_SEEDS = e15.MODEL_SEEDS
EXPECTED_GPU_NAME = e15.EXPECTED_GPU_NAME
LATENT_DIM = e15.LATENT_DIM
ACTION_HORIZON = e15.ACTION_HORIZON
ACTION_BLOCK = e15.ACTION_BLOCK
TAU = 15

HORIZONS = (75, 150)
BASE_STARTS = 12
SHARD_SIZE = 3
SHARD_COUNT = BASE_STARTS // SHARD_SIZE
SELECTION_SALT = "gdp-cem-e18-p2-continuation-20260827"

FIRST_CANDIDATES = 64
CONTINUATIONS_PER_FIRST = 8
CONTINUATION_BEST_COUNT = 2
GREEDY_CANDIDATES = 300
GREEDY_COMPUTE_MATCHED_CANDIDATES = 576

ARMS = (
    "vad_greedy_300",
    "vad_greedy_576",
    "vad_continuation",
    "diagonal_gaussian_continuation",
    "direct_gmm_continuation",
)

MINIMUM_FIRST_UNIQUE = {
    "vad_greedy_300": 285,
    "vad_greedy_576": 548,
    "vad_continuation": 61,
    "diagonal_gaussian_continuation": 61,
    "direct_gmm_continuation": 61,
}
MINIMUM_SECOND_UNIQUE = 7
MAXIMUM_TASK_AVERAGE_LOSS = 0.05
BOOTSTRAP_RESAMPLES = 10_000


def schedule_for(horizon: int) -> tuple[int, ...]:
    if horizon not in HORIZONS:
        raise ValueError(f"unsupported E18 horizon: {horizon}")
    result = e15.schedule_for(horizon)
    if any(value != TAU for value in result):
        raise RuntimeError("E18 schedule is not uniformly 15 actions")
    return result


def family_for_arm(arm: str) -> str:
    if arm.startswith("vad_"):
        return "vad"
    if arm == "diagonal_gaussian_continuation":
        return "diagonal_gaussian"
    if arm == "direct_gmm_continuation":
        return "direct_gmm"
    raise ValueError("invalid E18 arm")


def is_continuation_arm(arm: str) -> bool:
    if arm not in ARMS:
        raise ValueError("invalid E18 arm")
    return arm.endswith("_continuation")


def first_candidate_count(arm: str) -> int:
    if arm == "vad_greedy_300":
        return GREEDY_CANDIDATES
    if arm == "vad_greedy_576":
        return GREEDY_COMPUTE_MATCHED_CANDIDATES
    if is_continuation_arm(arm):
        return FIRST_CANDIDATES
    raise ValueError("invalid E18 arm")


def derived_seed(label: str) -> int:
    value = hashlib.sha256(f"gdp-cem-e18|{label}".encode("utf-8")).digest()
    return int.from_bytes(value[:8], "little") % (2**63 - 1)


assert set(E17_SUMMARY_SHA256) == set(TASKS)
assert set(E17_CHECKPOINT_SHA256) == set(TASKS)
assert set(E17_GATE_PASSED) == set(TASKS)
assert BASE_STARTS % SHARD_SIZE == 0
assert FIRST_CANDIDATES + FIRST_CANDIDATES * CONTINUATIONS_PER_FIRST == 576
assert CONTINUATION_BEST_COUNT <= CONTINUATIONS_PER_FIRST
assert len(ARMS) == 5
