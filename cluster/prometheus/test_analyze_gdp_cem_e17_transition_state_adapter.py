from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import gdp_cem_e17_specs as spec
from analyze_gdp_cem_e17_transition_state_adapter import verify_model


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(*, rows: int = 10, rmse: float = 0.2, maximum: float = 0.3, r2: float = 0.8):
    return {
        "rows": rows,
        "standardized_rmse": rmse,
        "coordinate_standardized_rmse": [rmse],
        "maximum_coordinate_standardized_rmse": maximum,
        "coordinate_r2": [r2],
        "median_coordinate_r2": r2,
        "per_example_standardized_rmse": {
            "q50": rmse,
            "q90": rmse,
            "q95": rmse,
            "q99": rmse,
            "maximum": rmse,
        },
    }


def build_result(tmp_path: Path, *, declared_pass: bool) -> tuple[Path, Path, str]:
    source_sha = "a" * 64
    cache = tmp_path / "cache"
    model = tmp_path / "model"
    cache.mkdir()
    model.mkdir()
    (cache / "cache.h5").write_bytes(b"cache")
    (cache / "manifest.json").write_text("{}\n", encoding="utf-8")
    (model / "final.pt").write_bytes(b"checkpoint")
    (model / "training.jsonl").write_text("{}\n", encoding="utf-8")
    task_spec = spec.TASK_SPEC["pusht"]
    architecture = {
        "latent_dim": spec.LATENT_DIM,
        "state_dim": int(task_spec["state_dim"]),
        "action_dim": int(task_spec["primitive_action_dim"]),
        "input_dim": spec.input_dim(
            state_dim=int(task_spec["state_dim"]),
            action_dim=int(task_spec["primitive_action_dim"]),
        ),
        "width": spec.MODEL_WIDTH,
        "residual_blocks": spec.MODEL_RESIDUAL_BLOCKS,
    }
    model_metrics = metrics()
    baseline = metrics(rmse=0.4, maximum=0.5, r2=0.2)
    gate = {
        "passed": declared_pass,
        "finite": True,
        "model": model_metrics,
        "copy_current": baseline,
        "model_to_copy_current_rmse_ratio": 0.5,
        "by_tau": {
            str(tau): {
                "model": model_metrics,
                "copy_current": baseline,
                "passed": True,
            }
            for tau in spec.TAU_VALUES
        },
        "thresholds": {
            "overall_standardized_rmse_max": spec.OVERALL_RMSE_MAX,
            "maximum_coordinate_standardized_rmse_max": spec.MAX_COORDINATE_RMSE_MAX,
            "median_coordinate_r2_min": spec.MEDIAN_COORDINATE_R2_MIN,
            "copy_current_rmse_ratio_max": spec.COPY_CURRENT_RMSE_RATIO_MAX,
            "per_tau_standardized_rmse_max": spec.TAU_RMSE_MAX,
            "per_tau_median_coordinate_r2_min": spec.TAU_MEDIAN_COORDINATE_R2_MIN,
        },
    }
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e17_transition_state_adapter_preflight",
        "task": "pusht",
        "seed": spec.MODEL_SEED,
        "architecture": architecture,
        "final_step": spec.TRAIN_STEPS,
        "checkpoint_sha256": sha(model / "final.pt"),
        "training_trace_sha256": sha(model / "training.jsonl"),
        "cache_h5_sha256": sha(cache / "cache.h5"),
        "cache_manifest_sha256": sha(cache / "manifest.json"),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": source_sha,
        "final_checkpoint_written_before_validation_open": True,
        "validation_payload_rows_read_before_checkpoint": 0,
        "validation_checkpoint_selection": False,
        "adapter_gate": gate,
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    (model / "summary.json").write_text(
        json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8"
    )
    (model / "sha256.txt").write_text(
        f"{sha(model / 'final.pt')}  final.pt\n"
        f"{sha(model / 'training.jsonl')}  training.jsonl\n"
        f"{sha(model / 'summary.json')}  summary.json\n",
        encoding="utf-8",
    )
    return model, cache, source_sha


def test_verify_model_recomputes_frozen_gate(tmp_path: Path) -> None:
    model, cache, source_sha = build_result(tmp_path, declared_pass=True)
    assert verify_model(
        model, task="pusht", source_sha=source_sha, cache_directory=cache
    )["adapter_gate"]["passed"] is True


def test_verify_model_rejects_incorrect_declared_gate(tmp_path: Path) -> None:
    model, cache, source_sha = build_result(tmp_path, declared_pass=False)
    with pytest.raises(RuntimeError, match="aggregate gate disagrees"):
        verify_model(
            model, task="pusht", source_sha=source_sha, cache_directory=cache
        )
