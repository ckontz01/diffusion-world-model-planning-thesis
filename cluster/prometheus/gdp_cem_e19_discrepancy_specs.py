"""Frozen identities for the outcome-informed E19 discrepancy diagnostic."""

from __future__ import annotations

from dataclasses import dataclass


PROTOCOL_FILENAME = (
    "ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-DISCREPANCY-DIAGNOSTIC-"
    "PROTOCOL-2026-08-29.md"
)
E19_SNAPSHOT = (
    "/lustreFS/data/superworld/ckontzias/thesis/snapshots/"
    "gdp-cem-e19-9f5499887c0d2e1f"
)
E19_SOURCE_MANIFEST_SHA256 = (
    "9f5499887c0d2e1f9808cc5f493e7f172e717bcb8db202088e89e5c29f2a1d6c"
)
E19_PROTOCOL_SHA256 = (
    "759f64b67a5c8e9d33e03c4d7027ede7edf99f1a4186236fb8f0879fc7ed0e20"
)
E19_RUN_ROOT = (
    "/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/"
    "native-reproduction-run-20260828-9f549988"
)
SAGE_GIT_COMMIT = "8219029fd52e89157e05aebb998ab26f0ef46966"
SAGE_GIT_TREE = "0c64066eeac97c27fee382c1879bb26968b3fd56"
REPEATS = (0, 1)
EXPECTED_SENTINELS = 5
EXPECTED_RUNS = EXPECTED_SENTINELS * len(REPEATS)
EXPECTED_EPISODES_PER_RUN = 50
EXPECTED_TOTAL_EPISODES = EXPECTED_RUNS * EXPECTED_EPISODES_PER_RUN
PLANNER = {
    "candidates": 300,
    "cem_rounds": 30,
    "elites": 30,
    "action_block": 5,
    "history_length": 3,
    "frameskip": 5,
    "precision": "bf16",
    "warm_start": False,
}


@dataclass(frozen=True)
class Sentinel:
    sentinel_id: int
    e19_array_id: int
    benchmark: str
    method: str
    seed: int
    horizon: int
    e19_success_rate: float
    e19_result_sha256: str
    rationale: str


SENTINELS = (
    Sentinel(
        0,
        1,
        "pusht",
        "base_cem",
        32,
        50,
        60.0,
        "b4e27e36fc50286a09b8d6673e29c2c50fae4713493e6c4e9ba2e8c590b7479d",
        "first row rejected by the unchanged official summarizer",
    ),
    Sentinel(
        1,
        22,
        "pusht",
        "far_goal_prior_cem",
        32,
        125,
        12.0,
        "f6633208654b3c5d9d2e1d6b1fc7374be05634f29d0179ffe9102e93f05b0e46",
        "largest aggregate PushT far-goal-prior discrepancy",
    ),
    Sentinel(
        2,
        58,
        "pusht",
        "generator_prior_top",
        32,
        125,
        34.0,
        "e32189196a44ccddc6a94ea90716156f73ec39550acff75d78b39f5a089a263d",
        "non-CEM released-method control from a reproduced aggregate row",
    ),
    Sentinel(
        3,
        131,
        "cube",
        "lewm_generator",
        32,
        150,
        22.0,
        "f24b12870cd68fbf30f174f7924bbb03456570fc7b9836df2dbe489f3071c82e",
        "largest E19 discrepancy and the Cube generated-goal cache path",
    ),
    Sentinel(
        4,
        164,
        "cube",
        "sage",
        32,
        75,
        88.0,
        "a1cb1c15f958032e315c8f08189c8b9a5acad73b488a1a17d08c10e00e6577b2",
        "full-method Cube control from an exactly reproduced aggregate row",
    ),
)


def runs() -> tuple[tuple[int, Sentinel, int], ...]:
    rows: list[tuple[int, Sentinel, int]] = []
    for sentinel in SENTINELS:
        for repeat in REPEATS:
            rows.append((len(rows), sentinel, repeat))
    if len(rows) != EXPECTED_RUNS:
        raise AssertionError("E19 discrepancy run-count drift")
    return tuple(rows)


def sentinel_by_id(sentinel_id: int) -> Sentinel:
    matches = [row for row in SENTINELS if row.sentinel_id == int(sentinel_id)]
    if len(matches) != 1:
        raise ValueError(f"unknown sentinel id {sentinel_id}")
    return matches[0]
