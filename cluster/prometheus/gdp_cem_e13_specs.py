"""Static, outcome-free specification for E13's matched PRISM-DP study."""

from __future__ import annotations

import hashlib
from typing import Any

import gdp_cem_e11_specs as e11


TASKS = ("pusht", "reacher", "cube")
SEEDS = (6101, 6102, 6103)
COUNT = 400
SHARD_SIZE = 50
SHARD_COUNT = 8
SELECTION_NAMESPACE = "gdp-e13-d4"
SELECTION_SEED = 2026082201
PROTOCOL_SHA256 = "65d56b613f12ad896c395e6feb4fc6d39f404bc802045369d0a88b638690af58"
EXPECTED_GPU_NAME = "NVIDIA RTX 6000 Ada Generation"
EXPECTED_HOSTNAME = "gpu09.cluster"
UNTOUCHED_P3_CAPACITY = {"pusht": 1360, "reacher": 556, "cube": 489}

ARMS = (
    "latent_gaussian_select_k300",
    "vp_select_k300",
    "prism_dp_select_k300",
    "vp_select_k16",
    "prism_dp_select_k16",
)
E11_SELECTOR_ARMS = (
    "latent_gaussian_select_k300",
    "vp_select_k300",
    "vp_select_k16",
)
PRISM_DP_ARMS = ("prism_dp_select_k300", "prism_dp_select_k16")

CANDIDATE_COUNT = {
    "latent_gaussian_select_k300": 300,
    "vp_select_k300": 300,
    "prism_dp_select_k300": 300,
    "vp_select_k16": 16,
    "prism_dp_select_k16": 16,
}
ITERATIONS = {arm: 1 for arm in ARMS}

PLANNER_BASE_SEEDS = (8301, 8302, 8303)
VELOCITY_BASE_SEEDS = (9101, 9102, 9103)
GAUSSIAN_BASE_SEEDS = (9201, 9202, 9203)
PRISM_DP_BASE_SEEDS = (9301, 9302, 9303)

PRIMARY_BOOTSTRAP_SEED = 2026082202
TWO_WAY_BOOTSTRAP_SEED = 2026082203
BOOTSTRAP_REPETITIONS = 100_000

E12_PROTOCOL_SHA256 = (
    "08cbe26c3186f06d6731defc8fc66f63c2a55c1102f6d089f1e286176f9ed927"
)
E12_STAGE_B_AUDIT_SHA256 = (
    "14b4e4ad00bbbe9f51205541a5fa812334f843995ca9ed7a2acec2acd090b480"
)
E12_TRAINING_SOURCE_MANIFEST_SHA256 = (
    "e2faf062f3eec188b8b78d167f6e75de29b5ff64446843c04696ed53d4bd856b"
)

PRISM_DP_ARTIFACT_SHA256 = {
    "pusht": {
        6101: (
            "187c4a56e1588f8513b66712cf7c29fcdc2f743065e4b16b13f444f6907b392f",
            "7432d05bd7ac8c136a576771d4ef52acd03e786c79ccd8da125c50f73391f329",
        ),
        6102: (
            "ff457a39fcdd63fd8bf99b1e1636aadc982f2a2b375c8ce7be3969c674fb5da8",
            "ddb22d46e25b8b72cee495799d75801004f5ea6ec3ca21d4a907e610d4180049",
        ),
        6103: (
            "889342b4b086d506cc9f43be6a14c90a48fc0b007ca05ab933ddaa22b5ceb46e",
            "81dfb55650e4302b2fa729da662653db90efccef70638b9f9590bc6d6d307146",
        ),
    },
    "reacher": {
        6101: (
            "c76f519f50d4b579261df21cd24869f1719f3168c29d11e310685682a474adeb",
            "c8a650cd1255c5e84788a48140697e01395afa820fa2e2557b93c1abb1fb34ad",
        ),
        6102: (
            "49c5fd8c1052b93da32605b69ad0d86aadd79558e46d94ef787dff997932fbe1",
            "0aeaaa5e85bd9869c283d9bf8dcefd86ee8e1a8a0ac450e9d9c9ce8b437bb144",
        ),
        6103: (
            "99a5720073ebba4aa781b98110509fcb7858dcc34067325bdb1c6796fa1522c4",
            "6414ff5f6e873cca4367c9e5831a341b8573e84a1c8fb9a4fbe424f1a7c7a756",
        ),
    },
    "cube": {
        6101: (
            "3000a082d3c7745ae43c08260df821e1ab36090feb269a8d0ebd636c08d7395f",
            "cccad64a1279eac9df32bd546f510339a130bf85be3e6c805f87660ef0b1d01c",
        ),
        6102: (
            "fe43fbadd36b3878428687d82b7b76f6d78ccc57db900e585c3d2d459c4ccf79",
            "062e3ce2dd7b39aa5c98e7f744b2d0092816f60bc6ba232e7611ec5a2ea39ca5",
        ),
        6103: (
            "1f7b54885ceabd24956f9547147dbbf79a666a4f4a46ea9f93f85cbc7b13bf67",
            "f95b4bf3b304331f5d8c546c8e4997a2a01baf4dc90bfdf433653a3faa09f7ae",
        ),
    },
}

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
        raise ValueError(f"invalid E13 model seed {seed}") from error


def derived_seed(namespace: str, task: str, base_seed: int, shard: int) -> int:
    if namespace not in {"planner", "velocity", "gaussian", "prism_dp"}:
        raise ValueError("invalid E13 seed namespace")
    if task not in TASKS or shard not in range(SHARD_COUNT):
        raise ValueError("invalid E13 task or shard")
    payload = f"gdp-e13|{namespace}|{task}|{base_seed}|{shard}".encode("utf-8")
    value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "little")
    return value % (2**63 - 1)
