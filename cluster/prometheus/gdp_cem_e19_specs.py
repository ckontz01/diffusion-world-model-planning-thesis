"""Frozen identities and cell registry for the E19 official SAGE audit."""

from __future__ import annotations

from dataclasses import dataclass


SAGE_GIT_URL = "https://github.com/PKU-ML/SAGE"
SAGE_GIT_COMMIT = "8219029fd52e89157e05aebb998ab26f0ef46966"
SAGE_GIT_TREE = "0c64066eeac97c27fee382c1879bb26968b3fd56"
SAGE_HF_REPO = "CLTRAY/SAGE"
SAGE_HF_REVISION = "1b5afbc8eeb1c8e99d9529099e1aa15f392a6346"
PROTOCOL_FILENAME = (
    "ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-"
    "PROTOCOL-2026-08-28.md"
)

METHODS = (
    "base_cem",
    "far_goal_prior_cem",
    "lewm_generator",
    "generator_prior_top",
    "sage",
)
SEEDS = (32, 42, 52)
HORIZONS = (25, 50, 75, 100, 125, 150)
BENCHMARKS = ("pusht", "cube")
EXPECTED_CELLS = 180
EXPECTED_EPISODES_PER_CELL = 50
EXPECTED_TOTAL_EPISODES = 9_000
EXPECTED_UPSTREAM_TESTS = 7
EXPECTED_MANIFESTS = 36
EXPECTED_RELEASE_BYTE_MISMATCHES = 36
EXPECTED_TOLERANCE_POINTS = 2.0

CHECKPOINTS = {
    "pusht_generator": {
        "filename": "pusht_generator.pt",
        "bytes": 233_878_994,
        "sha256": "0b3647a3a41435969d750ec58176ef5f92a419c4eacae2b5cda74b35e63f90da",
    },
    "pusht_action_prior": {
        "filename": "pusht_action_prior.pt",
        "bytes": 163_404_922,
        "sha256": "03ecab8f9d757eb8b3fc15e93481e830325428c24ede813c18f8692cc9b4bd80",
    },
    "pusht_far_action_prior": {
        "filename": "pusht_far_action_prior.pt",
        "bytes": 163_404_602,
        "sha256": "60ed6831750e478b22c259b69e671236b41164f90284cb0422fe56d99e8c1425",
    },
    "cube_generator": {
        "filename": "cube_generator.pt",
        "bytes": 233_981_650,
        "sha256": "5f48e6d8eb3fab78d8f54bb36e1e275eefaf1fb82338a9b05e8f5cf5437a1352",
    },
    "cube_action_prior": {
        "filename": "cube_action_prior.pt",
        "bytes": 164_984_570,
        "sha256": "7ab6d2baefdcf5c2edf23192db6e969621fad621e21251b784c9e2309a0fb8eb",
    },
    "cube_far_action_prior": {
        "filename": "cube_far_action_prior.pt",
        "bytes": 164_984_186,
        "sha256": "32eb053197fddcb26ee7a86ea1d43fed2e95a3366423d646721a56fc8ca9fbde",
    },
}

TASKS = {
    "pusht": {
        "dataset_file": "pusht_expert_train.h5",
        "dataset_sha256": "b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb",
        "episodes": 18_685,
        "split_file": "pusht_episode_split_seed42.json",
        "paper_dataset_kind": "lance",
        "lewm_repo": "quentinll/lewm-pusht",
        "lewm_revision": "22b330c28c27ead4bfd1888615af1340e3fe9052",
        "lewm_weights_sha256": "48938400ae3464c9680731287f583a9cb516f55a8ec64ea13a91be47fb15b607",
        "lewm_config_sha256": "2564086e961e7b5c7c04dffc451091115b389a590645ff19653c64fd0bc16e09",
        "e18_object_file": "pusht/lewm_hf_22b330c_object.ckpt",
        "e18_object_sha256": "c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659",
        "legacy_object_file": "pusht/lewm_object.ckpt",
        "legacy_object_sha256": "bd50860a45edc39feefff56f0d0812e74dc809029eac6d014efc89cc33bb2353",
    },
    "cube": {
        "dataset_file": "cube_single_expert.h5",
        "dataset_sha256": "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625",
        "episodes": 10_000,
        "split_file": "ogbench_cube_single_split_seed42.json",
        "paper_dataset_kind": "hdf5",
        "lewm_repo": "quentinll/lewm-cube",
        "lewm_revision": "b0747c5002e86d2ce8f3cd8178004b97524c587d",
        "lewm_weights_sha256": "2839a907362f403f9136383016e91774373a295d958ae75121791f22a9fddf89",
        "lewm_config_sha256": "4d446944fe28922cc2c5763f43d4ef9132a457bd89e9a0ce5dbceac183994999",
        "e18_object_file": "cube/lewm_hf_b0747c5_object.ckpt",
        "e18_object_sha256": "5175b8d7a99b3c19aeee08027c666fb0562e316f14c36e74ac3a52ecce531e07",
        "legacy_object_file": "cube/lewm_object.ckpt",
        "legacy_object_sha256": "ba14290ad48081c241d3f7150578102d41559b62d650b35b906fe339d801a9a0",
    },
}


@dataclass(frozen=True)
class Cell:
    array_id: int
    benchmark: str
    method: str
    seed: int
    horizon: int


def cells() -> tuple[Cell, ...]:
    rows: list[Cell] = []
    for benchmark in BENCHMARKS:
        for method in METHODS:
            for seed in SEEDS:
                for horizon in HORIZONS:
                    rows.append(
                        Cell(
                            array_id=len(rows),
                            benchmark=benchmark,
                            method=method,
                            seed=seed,
                            horizon=horizon,
                        )
                    )
    if len(rows) != EXPECTED_CELLS:
        raise AssertionError("E19 cell count drift")
    return tuple(rows)


def checkpoint_paths(benchmark: str, method: str) -> tuple[str | None, str]:
    if benchmark not in BENCHMARKS or method not in METHODS:
        raise ValueError(f"unknown E19 cell: {benchmark}/{method}")
    generator = (
        f"{benchmark}_generator.pt"
        if method in {"lewm_generator", "generator_prior_top", "sage"}
        else None
    )
    prior = (
        f"{benchmark}_far_action_prior.pt"
        if method == "far_goal_prior_cem"
        else f"{benchmark}_action_prior.pt"
    )
    return generator, prior
