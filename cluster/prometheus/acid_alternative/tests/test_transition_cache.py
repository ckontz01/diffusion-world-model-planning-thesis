from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest
from acid_alternative.build_reachability_pairs import pusht_task_state_distance
from acid_alternative.build_transition_cache import fit_finite_action_standardizer
from acid_alternative.io_utils import sha256_file
from sklearn import preprocessing


def test_action_standardizer_ignores_episode_end_nan_sentinel():
    actions = np.asarray([[1.0, 2.0], [3.0, 4.0], [np.nan, np.nan]], dtype=np.float32)
    actual = fit_finite_action_standardizer(actions)
    expected = preprocessing.StandardScaler().fit(actions[:2])
    np.testing.assert_array_equal(actual.mean_, expected.mean_)
    np.testing.assert_array_equal(actual.scale_, expected.scale_)
    np.testing.assert_array_equal(
        actual.transform(actions), expected.transform(actions)
    )


def test_action_standardizer_rejects_no_finite_rows():
    with pytest.raises(RuntimeError, match="no non-NaN row"):
        fit_finite_action_standardizer(
            np.asarray([[np.nan, np.nan], [0.0, np.nan]], dtype=np.float32)
        )


def test_action_standardizer_rejects_infinity():
    with pytest.raises(RuntimeError, match="contains infinity"):
        fit_finite_action_standardizer(
            np.asarray([[1.0, 2.0], [np.inf, 0.0]], dtype=np.float32)
        )


def test_transition_cache_uses_five_actions_and_never_crosses_episode(tmp_path: Path):
    dataset = tmp_path / "data.h5"
    with h5py.File(dataset, "w") as handle:
        handle.create_dataset("ep_offset", data=np.array([0, 7], dtype=np.int64))
        handle.create_dataset("ep_len", data=np.array([7, 8], dtype=np.int32))
        handle.create_dataset("episode_idx", data=np.repeat([0, 1], [7, 8]))
        handle.create_dataset(
            "step_idx",
            data=np.concatenate((np.arange(7), np.arange(10, 18))),
        )
        handle.create_dataset(
            "action", data=np.arange(30, dtype=np.float32).reshape(15, 2)
        )

    latent_h5 = tmp_path / "latent.h5"
    with h5py.File(latent_h5, "w") as handle:
        handle.create_dataset("row_index", data=np.arange(15, dtype=np.int64))
        handle.create_dataset("episode_idx", data=np.repeat([0, 1], [7, 8]))
        handle.create_dataset(
            "step_idx",
            data=np.concatenate((np.arange(7), np.arange(10, 18))),
        )
        handle.create_dataset(
            "latent", data=np.arange(60, dtype=np.float32).reshape(15, 4)
        )
    latent_manifest = tmp_path / "latent.json"
    latent_manifest.write_text(
        json.dumps({"status": "ok", "output_h5_sha256": sha256_file(latent_h5)}),
        encoding="utf-8",
    )
    roles = tmp_path / "roles.tsv"
    with roles.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["episode_id", "p1_role"], delimiter="\t"
        )
        writer.writeheader()
        writer.writerow({"episode_id": 0, "p1_role": "P1_train"})
        writer.writerow({"episode_id": 1, "p1_role": "P1_val"})

    output_h5 = tmp_path / "transitions.h5"
    output_json = tmp_path / "transitions.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_alternative.build_transition_cache",
            "--dataset",
            str(dataset),
            "--latent-h5",
            str(latent_h5),
            "--latent-manifest",
            str(latent_manifest),
            "--p1-role-manifest",
            str(roles),
            "--frameskip",
            "5",
            "--output-h5",
            str(output_h5),
            "--output-json",
            str(output_json),
        ],
        check=True,
    )
    with h5py.File(output_h5, "r") as handle:
        assert handle["action"].shape == (5, 10)
        np.testing.assert_array_equal(handle["episode_idx"][:], [0, 0, 1, 1, 1])
        np.testing.assert_array_equal(handle["step_idx"][:], [0, 1, 10, 11, 12])
        np.testing.assert_array_equal(
            handle["target_index"][:] - handle["source_index"][:], 5
        )
        assert np.all(handle["role"][:2] == 0)
        assert np.all(handle["role"][2:] == 1)
        raw_actions = np.arange(30, dtype=np.float32).reshape(15, 2)
        processor = preprocessing.StandardScaler().fit(raw_actions)
        np.testing.assert_array_equal(
            handle["stats/planner_primitive_action_mean"][:], processor.mean_
        )
        np.testing.assert_array_equal(
            handle["stats/planner_primitive_action_std"][:], processor.scale_
        )
        expected_first = processor.transform(raw_actions)[:5].reshape(-1)
        np.testing.assert_array_equal(handle["action"][0], expected_first)


def test_i1_cache_reuses_frozen_stats_and_allows_terminal_nan_sentinel(
    tmp_path: Path,
):
    source_manifest = tmp_path / "source.sha256"
    source_manifest.write_text("frozen source\n", encoding="utf-8")
    dataset = tmp_path / "data.h5"
    raw_actions = np.arange(28, dtype=np.float32).reshape(14, 2)
    raw_actions[[6, 13]] = np.nan
    with h5py.File(dataset, "w") as handle:
        handle.create_dataset("ep_offset", data=np.asarray([0, 7], dtype=np.int64))
        handle.create_dataset("ep_len", data=np.asarray([7, 7], dtype=np.int64))
        handle.create_dataset("action", data=raw_actions)

    identification = tmp_path / "i1.tsv"
    with identification.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("episode_id", "episode_length", "partition"),
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerow(
            {"episode_id": 1, "episode_length": 7, "partition": "I1"}
        )

    latent_h5 = tmp_path / "i1-latents.h5"
    with h5py.File(latent_h5, "w") as handle:
        handle.create_dataset("row_index", data=np.arange(7, 14, dtype=np.int64))
        handle.create_dataset("episode_idx", data=np.ones(7, dtype=np.int64))
        handle.create_dataset("step_idx", data=np.arange(7, dtype=np.int64))
        handle.create_dataset(
            "latent", data=np.arange(28, dtype=np.float32).reshape(7, 4)
        )
    latent_manifest = tmp_path / "i1-latents.json"
    latent_manifest.write_text(
        json.dumps(
            {
                "status": "ok",
                "kind": "flat_frozen_encoder_latent_cache",
                "output_h5_sha256": sha256_file(latent_h5),
                "dataset_sha256": sha256_file(dataset),
                "source_manifest_sha256": sha256_file(source_manifest),
                "partition_manifest_sha256": sha256_file(identification),
                "partitions": ["I1"],
            }
        ),
        encoding="utf-8",
    )

    training_h5 = tmp_path / "training-transitions.h5"
    planner_mean = np.asarray([1.0, 2.0], dtype=np.float64)
    planner_std = np.asarray([2.0, 4.0], dtype=np.float64)
    with h5py.File(training_h5, "w") as handle:
        stats = handle.create_group("stats")
        stats.create_dataset("planner_primitive_action_mean", data=planner_mean)
        stats.create_dataset("planner_primitive_action_std", data=planner_std)
        stats.create_dataset("latent_mean", data=np.zeros(4, dtype=np.float32))
        stats.create_dataset("latent_std", data=np.ones(4, dtype=np.float32))
        stats.create_dataset("acid_action_mean", data=np.zeros(10, dtype=np.float32))
        stats.create_dataset("acid_action_std", data=np.ones(10, dtype=np.float32))
    training_manifest = tmp_path / "training-transitions.json"
    training_manifest.write_text(
        json.dumps(
            {
                "status": "ok",
                "kind": "flat_one_model_step_transition_cache",
                "output_h5_sha256": sha256_file(training_h5),
                "dataset_sha256": sha256_file(dataset),
                "source_manifest_sha256": sha256_file(source_manifest),
                "frameskip": 5,
                "latent_dim": 4,
                "action_block_dim": 10,
            }
        ),
        encoding="utf-8",
    )

    output_h5 = tmp_path / "i1-transitions.h5"
    output_json = tmp_path / "i1-transitions.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_alternative.build_identification_transition_cache",
            "--task",
            "pusht",
            "--dataset",
            str(dataset),
            "--latent-h5",
            str(latent_h5),
            "--latent-manifest",
            str(latent_manifest),
            "--identification-manifest",
            str(identification),
            "--training-transition-h5",
            str(training_h5),
            "--training-transition-manifest",
            str(training_manifest),
            "--source-manifest",
            str(source_manifest),
            "--frameskip",
            "5",
            "--output-h5",
            str(output_h5),
            "--output-json",
            str(output_json),
        ],
        check=True,
    )
    with h5py.File(output_h5, "r") as handle:
        assert handle["action"].shape == (2, 10)
        assert np.isfinite(handle["action"][:]).all()
        expected = raw_actions.copy()
        expected -= planner_mean
        expected /= planner_std
        np.testing.assert_array_equal(handle["action"][0], expected[7:12].reshape(-1))
        np.testing.assert_array_equal(handle["episode_idx"][:], [1, 1])
        np.testing.assert_array_equal(handle["step_idx"][:], [0, 1])
    manifest = json.loads(output_json.read_text(encoding="utf-8"))
    assert manifest["task"] == "pusht"
    assert manifest["data_role"] == "I1"
    assert manifest["confirmation_identification_outcomes_computed"] is False


def test_reachability_pair_cache_is_disjoint_symmetric_and_task_state_labeled(
    tmp_path: Path,
):
    dataset = tmp_path / "data.h5"
    offsets = np.array([0, 7], dtype=np.int64)
    lengths = np.array([7, 8], dtype=np.int32)
    states = np.zeros((15, 7), dtype=np.float32)
    states[:, 0] = np.arange(15)
    states[:, 1] = np.arange(15) * 2
    states[:, 2] = np.arange(15) * 3
    states[:, 3] = np.arange(15) * 4
    states[:, 4] = np.linspace(-3.0, 3.0, 15)
    with h5py.File(dataset, "w") as handle:
        handle.create_dataset("ep_offset", data=offsets)
        handle.create_dataset("ep_len", data=lengths)
        handle.create_dataset("state", data=states)

    latent_h5 = tmp_path / "latent.h5"
    with h5py.File(latent_h5, "w") as handle:
        handle.create_dataset("row_index", data=np.arange(15, dtype=np.int64))
        handle.create_dataset(
            "latent", data=np.arange(60, dtype=np.float32).reshape(15, 4)
        )
    latent_manifest = tmp_path / "latent.json"
    latent_manifest.write_text(
        json.dumps({"status": "ok", "output_h5_sha256": sha256_file(latent_h5)}),
        encoding="utf-8",
    )
    roles = tmp_path / "roles.tsv"
    with roles.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["episode_id", "p1_role"], delimiter="\t"
        )
        writer.writeheader()
        writer.writerow({"episode_id": 0, "p1_role": "P1_train"})
        writer.writerow({"episode_id": 1, "p1_role": "P1_val"})

    output_h5 = tmp_path / "pairs.h5"
    output_json = tmp_path / "pairs.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_alternative.build_reachability_pairs",
            "--dataset",
            str(dataset),
            "--latent-h5",
            str(latent_h5),
            "--latent-manifest",
            str(latent_manifest),
            "--p1-role-manifest",
            str(roles),
            "--target",
            "pusht_task_state",
            "--train-pairs",
            "8",
            "--validation-pairs",
            "8",
            "--seed",
            "1234",
            "--output-h5",
            str(output_h5),
            "--output-json",
            str(output_json),
        ],
        check=True,
    )
    with h5py.File(output_h5, "r") as handle:
        first = handle["first_row"][:]
        second = handle["second_row"][:]
        episode = handle["episode_idx"][:]
        role = handle["role"][:]
        label = handle["label"][:]
        assert (
            len(
                set(
                    zip(
                        episode.tolist(),
                        np.minimum(first, second),
                        np.maximum(first, second),
                    )
                )
            )
            == 16
        )
        assert np.all(episode[role == 0] == 0)
        assert np.all(episode[role == 1] == 1)
        expected = pusht_task_state_distance(states[first], states[second])
        np.testing.assert_allclose(label, expected, rtol=1e-6, atol=1e-6)
        assert np.any(handle["swapped"][:]) and np.any(~handle["swapped"][:])
        assert float(handle.attrs["target_scale"]) == 224.0
    manifest = json.loads(output_json.read_text(encoding="utf-8"))
    assert manifest["label"]["scale_for_training"] == 224.0


def test_temporal_reachability_scale_comes_from_training_episodes(tmp_path: Path):
    dataset = tmp_path / "data.h5"
    offsets = np.array([0, 7], dtype=np.int64)
    lengths = np.array([7, 8], dtype=np.int32)
    with h5py.File(dataset, "w") as handle:
        handle.create_dataset("ep_offset", data=offsets)
        handle.create_dataset("ep_len", data=lengths)

    latent_h5 = tmp_path / "latent.h5"
    with h5py.File(latent_h5, "w") as handle:
        handle.create_dataset("row_index", data=np.arange(15, dtype=np.int64))
        handle.create_dataset(
            "latent", data=np.arange(60, dtype=np.float32).reshape(15, 4)
        )
    latent_manifest = tmp_path / "latent.json"
    latent_manifest.write_text(
        json.dumps({"status": "ok", "output_h5_sha256": sha256_file(latent_h5)}),
        encoding="utf-8",
    )
    roles = tmp_path / "roles.tsv"
    with roles.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["episode_id", "p1_role"], delimiter="\t"
        )
        writer.writeheader()
        writer.writerow({"episode_id": 0, "p1_role": "P1_train"})
        writer.writerow({"episode_id": 1, "p1_role": "P1_val"})

    output_h5 = tmp_path / "pairs.h5"
    output_json = tmp_path / "pairs.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_alternative.build_reachability_pairs",
            "--dataset",
            str(dataset),
            "--latent-h5",
            str(latent_h5),
            "--latent-manifest",
            str(latent_manifest),
            "--p1-role-manifest",
            str(roles),
            "--target",
            "temporal",
            "--train-pairs",
            "8",
            "--validation-pairs",
            "8",
            "--seed",
            "1234",
            "--output-h5",
            str(output_h5),
            "--output-json",
            str(output_json),
        ],
        check=True,
    )
    manifest = json.loads(output_json.read_text(encoding="utf-8"))
    assert manifest["label"]["scale_for_training"] == 6.0
    assert (
        manifest["label"]["scale_rule"]
        == "maximum available within-episode separation in P1_train"
    )
    with h5py.File(output_h5, "r") as handle:
        np.testing.assert_array_equal(handle["label"][:], handle["delta"][:])
        assert float(handle.attrs["target_scale"]) == 6.0
