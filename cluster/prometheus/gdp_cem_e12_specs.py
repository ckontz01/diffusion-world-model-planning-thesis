"""Static, outcome-free specification for E12's matched PRISM study."""

from __future__ import annotations

import hashlib
from typing import Any

import gdp_cem_e11_specs as e11


TASKS = ("pusht", "reacher", "cube")
SEEDS = (6101, 6102, 6103)
COUNT = 400
SHARD_SIZE = 50
SHARD_COUNT = 8
SELECTION_NAMESPACE = "gdp-e12-d4"
SELECTION_SEED = 2026082001
PROTOCOL_SHA256 = "08cbe26c3186f06d6731defc8fc66f63c2a55c1102f6d089f1e286176f9ed927"
EXPECTED_GPU_NAME = "NVIDIA RTX 6000 Ada Generation"
EXPECTED_HOSTNAME = "gpu09.cluster"
UNTOUCHED_P3_CAPACITY = {"pusht": 1360, "reacher": 556, "cube": 489}

ARMS = (
    "b0_cem_k300",
    "acid_cem_k300",
    "latent_gaussian_select_k300",
    "vp_select_k300",
    "prism_dp_select_k300",
    "vp_select_k16",
    "prism_dp_select_k16",
    "vanilla_mppi_k128",
    "prism_pog_h25_mppi_k128",
    "prism_pog_endframe_mppi_k128",
)
CEM_ARMS = ("b0_cem_k300", "acid_cem_k300")
E11_SELECTOR_ARMS = (
    "latent_gaussian_select_k300",
    "vp_select_k300",
    "vp_select_k16",
)
PRISM_DP_ARMS = ("prism_dp_select_k300", "prism_dp_select_k16")
MPPI_ARMS = (
    "vanilla_mppi_k128",
    "prism_pog_h25_mppi_k128",
    "prism_pog_endframe_mppi_k128",
)
PRISM_HEAD_ARMS = (
    "prism_pog_h25_mppi_k128",
    "prism_pog_endframe_mppi_k128",
)

CANDIDATE_COUNT = {
    "b0_cem_k300": 300,
    "acid_cem_k300": 300,
    "latent_gaussian_select_k300": 300,
    "vp_select_k300": 300,
    "prism_dp_select_k300": 300,
    "vp_select_k16": 16,
    "prism_dp_select_k16": 16,
    "vanilla_mppi_k128": 128,
    "prism_pog_h25_mppi_k128": 128,
    "prism_pog_endframe_mppi_k128": 128,
}
ITERATIONS = {
    arm: (30 if arm in CEM_ARMS or arm in MPPI_ARMS else 1) for arm in ARMS
}
GOAL_MODE = {
    "prism_pog_h25_mppi_k128": "h25",
    "prism_pog_endframe_mppi_k128": "endframe",
}

PLANNER_BASE_SEEDS = (8301, 8302, 8303)
VELOCITY_BASE_SEEDS = (9101, 9102, 9103)
GAUSSIAN_BASE_SEEDS = (9201, 9202, 9203)
PRISM_DP_BASE_SEEDS = (9301, 9302, 9303)
MPPI_BASE_SEEDS = (9401, 9402, 9403)

TASK_SPEC: dict[str, dict[str, Any]] = {
    task: dict(e11.TASK_SPEC[task]) for task in TASKS
}
TASK_SPEC["pusht"].update(
    sequence_cache_job="297698-0",
    latent_cache_job="296628",
    partition_variant="pusht-v1",
)
TASK_SPEC["reacher"].update(
    sequence_cache_job="297698-1",
    latent_cache_job="296647",
    partition_variant="reacher-v1",
)
TASK_SPEC["cube"].update(
    sequence_cache_job="297698-2",
    latent_cache_job="296666",
    partition_variant="cube-v1",
)

EXPECTED_PARTITION_SHA256 = {
    "pusht": "35cd851464f4d7243c3c07b794f65db0f32caa16bbc787a83dda68388c4898f0",
    "reacher": "d0628d371224bcccc4b65db20d91212aafdc91a5bbb2b707be10354470910fcd",
    "cube": "2bb7dbe8faedcf58dc00669def093efeb9b70198fe8602a9f650b09c5adfcf8d",
}
EXPECTED_EXCLUSION_SHA256 = {
    "pusht": {
        "r0": "232c71ec2c69c2f130d2506cc8b720448975728f6eb3ad763f648e74df13cd79",
        "d1": "948a5e0dc1f79551845a9ef039908729d3d0c4c4bee5deb8445fe465f694814e",
        "d2": "85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89",
        "d3": "fbe5699dead294002f085d1044d6b36d0935b57e7772405cb6ccfa87ebd4ed8f",
    },
    "reacher": {
        "r0": "7a72a2a3e1ea89b5ec8bb0a39807673621c2ae92e0c581b34276e0bc11f9279e",
        "d1": "0b6e89cbe785ec88b0a3ff8e2ff77375ba9518695ab54f9bc2d3256013084a56",
        "d2": "a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61",
        "d3": "566da39d7ad4fb67d1c73319b42ce3712e0358b8cd9856c32fb23b785aef828e",
    },
    "cube": {
        "r0": "7a72a2a3e1ea89b5ec8bb0a39807673621c2ae92e0c581b34276e0bc11f9279e",
        "d1": "9e5c3d336c44226dbd293c2f2c77427ef86941202d15874d509e884691cffcf4",
        "d2": "bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388",
        "d3": "641e55b7d4eba078c33923c9a5413673cfb38b827d295996ef7d09e425558b8c",
    },
}

CORE_CHECKPOINT_SHA256 = e11.CORE_CHECKPOINT_SHA256
E11_PROPOSAL_ARTIFACT_SHA256 = e11.PROPOSAL_ARTIFACT_SHA256
PROPOSAL_ARTIFACT_SHA256 = E11_PROPOSAL_ARTIFACT_SHA256
E10M_AGGREGATE_SHA256 = e11.E10M_AGGREGATE_SHA256
E10M_SOURCE_MANIFEST_SHA256 = e11.E10M_SOURCE_MANIFEST_SHA256
E10V_SOURCE_MANIFEST_SHA256 = e11.E10V_SOURCE_MANIFEST_SHA256


def seed_index(seed: int) -> int:
    try:
        return SEEDS.index(seed)
    except ValueError as error:
        raise ValueError(f"invalid E12 model seed {seed}") from error


def derived_seed(namespace: str, task: str, base_seed: int, shard: int) -> int:
    if namespace not in {"planner", "velocity", "gaussian", "prism_dp", "mppi"}:
        raise ValueError("invalid E12 seed namespace")
    if task not in TASKS or shard not in range(SHARD_COUNT):
        raise ValueError("invalid E12 task or shard")
    payload = f"gdp-e12|{namespace}|{task}|{base_seed}|{shard}".encode("utf-8")
    value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "little")
    return value % (2**63 - 1)
