import json
from pathlib import Path

import numpy as np
from acid_alternative.io_utils import sha256_file
from acid_alternative_diagnostics.analyze_validation_identification import (
    episode_accuracy,
    load_run,
    parse_run_spec,
    stratified_episode_bootstrap,
)


def test_parse_run_spec_preserves_equals_in_path():
    task, path = parse_run_spec("pusht=/tmp/result=a/summary.json")
    assert task == "pusht"
    assert path.as_posix() == "/tmp/result=a/summary.json"


def test_episode_accuracy_weights_episodes_equally_after_within_episode_mean():
    episodes, means = episode_accuracy(
        np.asarray([1, 0, 1, 0], dtype=bool),
        np.asarray([7, 7, 7, 9]),
    )
    np.testing.assert_array_equal(episodes, [7, 9])
    np.testing.assert_allclose(means, [2 / 3, 0])


def test_stratified_bootstrap_is_reproducible_and_task_weighted():
    values = {
        "pusht": np.asarray([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]]),
        "cube": np.asarray([[0.5], [0.5], [0.5]]),
    }
    first = stratified_episode_bootstrap(values, seed=19, repetitions=100)
    second = stratified_episode_bootstrap(values, seed=19, repetitions=100)
    assert first == second
    assert first["estimate"] == 0.5
    assert first["by_task"]["pusht"]["estimate"] == 0.5
    assert first["by_task"]["cube"]["estimate"] == 0.5


def test_c1_loader_requires_and_reads_never_used_test_artifact(tmp_path: Path):
    artifact = tmp_path / "identification-examples.npz"
    pair_index = np.arange(200, dtype=np.int64)
    permuted = pair_index[::-1]
    episode_idx = np.arange(1000, 1200, dtype=np.int64)
    step_idx = np.zeros(200, dtype=np.int64)
    correct = np.linspace(0.2, 0.3, 200, dtype=np.float32)
    mismatch = np.linspace(0.5, 0.6, 200, dtype=np.float32)
    np.savez_compressed(
        artifact,
        pair_index=pair_index,
        episode_idx=episode_idx,
        step_idx=step_idx,
        permuted_pair_index=permuted,
        permuted_episode_idx=episode_idx[::-1],
        permuted_step_idx=step_idx,
        correct_cost=correct,
        permuted_cost=mismatch,
        correct_minus_permuted_margin=mismatch - correct,
    )
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "status": "ok",
                "kind": "flat_transition_identification_evaluation",
                "analysis_role": "C1",
                "data_role": "I1",
                "task": "pusht",
                "test_limit": None,
                "test_pairs_total": 200,
                "test_pairs_evaluated": 200,
                "identification_episodes_evaluated": 200,
                "confirmation_test_outcomes_previously_used_for_training_or_selection": False,
                "model": "diffusion",
                "condition": "true",
                "training_seed": 6101,
                "transition_h5_sha256": "transition",
                "identification_transition_h5_sha256": "i1-transition",
                "identification_episode_manifest_sha256": "i1-manifest",
                "latent_h5_sha256": "i1-latent",
                "source_manifest_sha256": "source",
                "confirmation_authorization_sha256": "authorization",
                "parameter_count": 10,
                "identification_examples": str(artifact),
                "identification_examples_sha256": sha256_file(artifact),
            }
        ),
        encoding="utf-8",
    )
    loaded = load_run("pusht", summary, "C1")
    assert loaded["data_role"] == "I1"
    assert loaded["seed"] == 6101
