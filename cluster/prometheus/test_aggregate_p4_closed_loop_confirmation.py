#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np

import aggregate_p4_closed_loop_confirmation as aggregate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finish_artifact(directory: Path, manifest: dict[str, object]) -> None:
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directory / "provenance.txt").write_text("synthetic_test=true\n", encoding="utf-8")
    names = sorted(path.name for path in directory.iterdir())
    (directory / "checksums.sha256").write_text(
        "".join(f"{sha256(directory / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def make_query_artifact(root: Path) -> tuple[Path, str, str]:
    directory = root / "queries"
    directory.mkdir()
    path = directory / "queries.h5"
    with h5py.File(path, "x") as handle:
        handle.create_dataset("query_id", data=np.arange(40, dtype=np.int64))
        handle.create_dataset("episode_id", data=1000 + np.arange(40, dtype=np.int64))
        handle.create_dataset("source_global_row", data=2000 + 100 * np.arange(40))
        handle.create_dataset("goal_global_row", data=2075 + 100 * np.arange(40))
        handle.create_dataset("source_step", data=10 + np.arange(40, dtype=np.int64))
        handle.create_dataset("planner_seed", data=3000 + np.arange(40, dtype=np.int64))
    digest = sha256(path)
    finish_artifact(
        directory,
        {
            "status": "ok",
            "classification": "p4_closed_loop_d75_queries",
            "partition": "P4",
            "query_count": 40,
            "output_h5_sha256": digest,
        },
    )
    return directory, digest, sha256(directory / "manifest.json")


def make_promotion_artifact(root: Path) -> tuple[Path, str]:
    directory = root / "promotion"
    directory.mkdir()
    path = directory / "audit.h5"
    with h5py.File(path, "x") as handle:
        handle.attrs["classification"] = "p3_locked_scorer_audit_and_promotion"
    digest = sha256(path)
    finish_artifact(
        directory,
        {
            "status": "ok",
            "classification": "p3_locked_scorer_audit_and_promotion",
            "partition": "P3-locked",
            "coverage": {"training_seeds": [11, 22, 33]},
            "selected_configuration": {
                "M1_width": 512,
                "M2_width": 1024,
                "M2_sigma": 0.25,
            },
            "promoted_arms": ["M2"],
            "promotion": {
                "M1": {"promoted": False},
                "M2": {"promoted": True},
                "M3": {"promoted": False},
            },
            "inputs": {
                "p2_true_score_h5_sha256": "1" * 64,
                "p2_calibration_h5_sha256": "2" * 64,
                "stats_npz_sha256": "3" * 64,
                "noise_npy_sha256": "4" * 64,
            },
            "checkpoints": [
                {
                    "method": method,
                    "condition": "true",
                    "seed": seed,
                    "checkpoint_sha256": f"{method[-1]}{seed}".ljust(64, "0"),
                }
                for method in ("M1", "M2", "M3")
                for seed in (11, 22, 33)
            ],
            "output_h5_sha256": digest,
        },
    )
    return directory, digest


def make_task(
    directory: Path,
    *,
    arm: str,
    query_index: int,
    query_h5_sha: str,
    query_manifest_sha: str,
    promotion_h5_sha: str,
) -> None:
    directory.mkdir(parents=True)
    learned = arm == "M2"
    classification = (
        "p4_augmented_closed_loop_confirmation"
        if learned
        else "p4_b0_b1_d75_confirmation"
    )
    success_modulus = {"B0": 4, "B1": 3, "M2": 2}[arm]
    succeeded = query_index % success_modulus == 0
    result_h5 = directory / "result.h5"
    with h5py.File(result_h5, "x") as handle:
        handle.attrs["classification"] = classification
        handle.attrs["partition"] = "P4-locked"
        handle.attrs["pool_index"] = query_index
        handle.attrs["planner_seed"] = 3000 + query_index
        handle.attrs["episode_success"] = succeeded
        handle.create_dataset(
            "step_current_latent", shape=(150, 192), dtype=np.float32, fillvalue=0.0
        )
    result_digest = sha256(result_h5)
    manifest: dict[str, object] = {
        "status": "ok",
        "classification": classification,
        "partition": "P4-locked",
        "query": {
            "pool_index": query_index,
            "episode_id": 1000 + query_index,
            "source_global_row": 2000 + 100 * query_index,
            "goal_global_row": 2075 + 100 * query_index,
            "source_step": 10 + query_index,
            "goal_step": 85 + query_index,
            "planner_seed_63bit": 3000 + query_index,
        },
        "episode_success": succeeded,
        "planner": {
            "eval_budget_primitive_steps": 150,
            "high": {"num_samples": 1200, "iterations": 60, "topk": 10},
            "low": {"num_samples": 1200, "iterations": 30, "topk": 150},
            "high_cost_calls": 1800,
            "high_candidate_evaluations": 2_160_000,
        },
        "diagnostics": {"step_count": 150},
        "inputs": {
            "candidate_h5_sha256": query_h5_sha,
            "candidate_manifest_sha256": query_manifest_sha,
        },
        "runtime": {
            "execution_seconds": 100.0 + query_index,
            "peak_gpu_allocated_bytes": 1_000_000 + query_index,
            "peak_gpu_reserved_bytes": 2_000_000 + query_index,
        },
        "output_h5_sha256": result_digest,
    }
    if learned:
        manifest.update(
            {
                "method": "M2",
                "weight": 1.0,
                "cost": {
                    "nominal_equivalence": {
                        "max_abs": 0.0,
                        "shape": [1, 4],
                        "status": "ok",
                    },
                    "timing": {
                        "cost_calls": 1800,
                        "completed_high_solves": 30,
                        "candidate_evaluations": 2_160_000,
                        "scorer_ms": 1234.0,
                    },
                    "scorer_artifacts": {
                        "method": "M2",
                        "width": 1024,
                        "sigma": 0.25,
                        "seeds": [11, 22, 33],
                        "checkpoints": [
                            {
                                "seed": seed,
                                "checkpoint_sha256": f"2{seed}".ljust(64, "0"),
                            }
                            for seed in (11, 22, 33)
                        ],
                        "true_selection_h5_sha256": "1" * 64,
                        "calibration_h5_sha256": "2" * 64,
                        "statistics_sha256": "3" * 64,
                        "noise": {"npy_sha256": "4" * 64},
                    },
                },
            }
        )
        manifest["inputs"]["p3_promotion_h5_sha256"] = promotion_h5_sha  # type: ignore[index]
    else:
        manifest["arm"] = arm
    finish_artifact(directory, manifest)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="p4-aggregate-test-") as raw_root:
        root = Path(raw_root)
        query_dir, query_h5_sha, query_manifest_sha = make_query_artifact(root)
        promotion_dir, promotion_h5_sha = make_promotion_artifact(root)
        baseline_root = root / "baseline"
        m2_root = root / "m2"
        for index in range(40):
            for arm in ("B0", "B1"):
                make_task(
                    baseline_root / f"arm-{arm}" / f"query-{index:02d}",
                    arm=arm,
                    query_index=index,
                    query_h5_sha=query_h5_sha,
                    query_manifest_sha=query_manifest_sha,
                    promotion_h5_sha=promotion_h5_sha,
                )
            make_task(
                m2_root / f"query-{index:02d}",
                arm="M2",
                query_index=index,
                query_h5_sha=query_h5_sha,
                query_manifest_sha=query_manifest_sha,
                promotion_h5_sha=promotion_h5_sha,
            )

        aggregate.QUERY_H5_SHA256 = query_h5_sha
        output_h5 = root / "confirmation.h5"
        output_json = root / "manifest.json"
        sys.argv = [
            "aggregate_p4_closed_loop_confirmation.py",
            "--query-dir",
            str(query_dir),
            "--promotion-dir",
            str(promotion_dir),
            "--baseline-root",
            str(baseline_root),
            "--m2-root",
            str(m2_root),
            "--output-h5",
            str(output_h5),
            "--output-json",
            str(output_json),
        ]
        aggregate.main()

        result = json.loads(output_json.read_text(encoding="utf-8"))
        assert result["coverage"]["arms"] == ["B0", "B1", "M2"]
        assert result["arms"]["B0"]["success_count_of_40"] == 10
        assert result["arms"]["B1"]["success_count_of_40"] == 14
        assert result["arms"]["M2"]["success_count_of_40"] == 20
        assert result["primary_endpoint"]["status"] == "evaluated"
        assert result["bootstrap"] == {
            "interval": "2.5th and 97.5th percentiles using NumPy linear quantiles",
            "paired": True,
            "replicates": 10_000,
            "seed": 20260728,
            "unit": "complete P4 query/evaluation seed",
        }
        with h5py.File(output_h5, "r") as handle:
            assert handle["episode_success"].shape == (3, 40)
            assert handle["bootstrap/success_rate_percent"].shape == (3, 10_000)
            assert handle["bootstrap/difference_vs_B0/M2"].shape == (10_000,)

    paired = aggregate.exact_paired_sign_pvalue(
        np.zeros(10, dtype=np.bool_), np.ones(10, dtype=np.bool_)
    )
    assert paired["two_sided_exact_pvalue"] == 2 / 1024
    print("synthetic_p4_aggregate_integration_test=ok")


if __name__ == "__main__":
    main()
