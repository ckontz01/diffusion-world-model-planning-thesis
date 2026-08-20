#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from score_and_select_p2_true_scorers import (
    LATENT_DIM,
    MACRO_DIM,
    NOISE_DRAWS,
    SEEDS,
    SIGMAS,
    sha256_file,
    training_paths,
    verify_inventory,
)
from train_m1_macro_cycle_head import MacroInverseDynamicsMLP
from train_m2_diffusion_head import ConditionalEpsilonMLP
from train_m3_temporal_head import TemporalPairHead


class FrozenCalibratedScorerEnsemble:
    """Three frozen scorer replicas plus their monotone P2 Platt maps."""

    def __init__(
        self,
        *,
        method: str,
        models: list[torch.nn.Module],
        payloads: list[dict[str, Any]],
        raw_slopes: torch.Tensor,
        raw_intercepts: torch.Tensor,
        device: torch.device,
        sigma: float | None,
        noise: torch.Tensor | None,
        artifact_record: dict[str, Any],
        m2_batch_size: int = 2048,
    ) -> None:
        if method not in {"M1", "M2", "M3"}:
            raise ValueError(f"unsupported scorer method: {method}")
        if len(models) != len(SEEDS) or len(payloads) != len(SEEDS):
            raise ValueError("scorer ensemble must contain exactly three seeds")
        self.method = method
        self.models = models
        self.payloads = payloads
        self.raw_slopes = raw_slopes.to(device=device, dtype=torch.float32)
        self.raw_intercepts = raw_intercepts.to(device=device, dtype=torch.float32)
        self.device = device
        self.sigma = sigma
        self.noise = noise
        self.artifact_record = artifact_record
        self.m2_batch_size = int(m2_batch_size)
        if self.raw_slopes.shape != (len(SEEDS),) or torch.any(self.raw_slopes < 0):
            raise ValueError("invalid monotone Platt slopes")
        if self.raw_intercepts.shape != (len(SEEDS),):
            raise ValueError("invalid Platt intercepts")
        if method == "M2":
            if sigma not in SIGMAS or noise is None or noise.shape != (
                NOISE_DRAWS,
                LATENT_DIM,
            ):
                raise ValueError("M2 requires its selected sigma and frozen noise bank")
        elif sigma is not None or noise is not None:
            raise ValueError("only M2 accepts sigma/noise inputs")

    @torch.inference_mode()
    def raw_scores(
        self,
        source_raw: torch.Tensor,
        target_raw: torch.Tensor,
        macro_raw: torch.Tensor,
    ) -> torch.Tensor:
        if source_raw.shape != target_raw.shape or source_raw.ndim != 2:
            raise RuntimeError("scorer source/target arrays must be matching 2D tensors")
        if source_raw.shape[1] != LATENT_DIM or macro_raw.shape != (
            len(source_raw),
            MACRO_DIM,
        ):
            raise RuntimeError("unexpected scorer latent or macro shape")
        seed_scores: list[torch.Tensor] = []
        for model, payload in zip(self.models, self.payloads, strict=True):
            if self.method == "M1":
                latent_mean = payload["latent_mean"].to(self.device)
                latent_std = payload["latent_std"].to(self.device)
                macro_mean = payload["macro_mean"].to(self.device)
                macro_std = payload["macro_std"].to(self.device)
                prediction = model(
                    (source_raw - latent_mean) / latent_std,
                    (target_raw - latent_mean) / latent_std,
                )
                raw_prediction = prediction * macro_std + macro_mean
                score = (macro_raw - raw_prediction).square().sum(dim=-1)
            elif self.method == "M2":
                assert self.noise is not None and self.sigma is not None
                mean = payload["latent_mean"].to(self.device)
                std = payload["latent_std"].to(self.device)
                source = (source_raw - mean) / std
                target = (target_raw - mean) / std
                count = len(source)
                source_expanded = source[:, None, :].expand(
                    count, NOISE_DRAWS, LATENT_DIM
                ).reshape(-1, LATENT_DIM)
                target_expanded = target[:, None, :].expand(
                    count, NOISE_DRAWS, LATENT_DIM
                ).reshape(-1, LATENT_DIM)
                epsilon = self.noise[None, :, :].expand(
                    count, NOISE_DRAWS, LATENT_DIM
                ).reshape(-1, LATENT_DIM)
                sigma_tensor = torch.full(
                    (count * NOISE_DRAWS,),
                    self.sigma,
                    device=self.device,
                    dtype=source.dtype,
                )
                squared_l2 = torch.empty(
                    count * NOISE_DRAWS, device=self.device, dtype=source.dtype
                )
                for start in range(0, len(squared_l2), self.m2_batch_size):
                    stop = min(start + self.m2_batch_size, len(squared_l2))
                    prediction = model(
                        target_expanded[start:stop]
                        + sigma_tensor[start:stop, None] * epsilon[start:stop],
                        sigma_tensor[start:stop],
                        source_expanded[start:stop],
                    )
                    squared_l2[start:stop] = (
                        epsilon[start:stop] - prediction
                    ).square().sum(dim=-1)
                score = squared_l2.reshape(count, NOISE_DRAWS).mean(dim=1)
            else:
                score = model(source_raw, target_raw) * 40.0
            if not torch.isfinite(score).all():
                raise RuntimeError(f"non-finite {self.method} score")
            seed_scores.append(score)
        return torch.stack(seed_scores, dim=0)

    @torch.inference_mode()
    def failure_probability(
        self,
        source_raw: torch.Tensor,
        target_raw: torch.Tensor,
        macro_raw: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        raw = self.raw_scores(source_raw, target_raw, macro_raw)
        probability_by_seed = torch.sigmoid(
            raw * self.raw_slopes[:, None] + self.raw_intercepts[:, None]
        )
        probability = probability_by_seed.mean(dim=0)
        if not torch.isfinite(probability).all() or torch.any(
            (probability < 0.0) | (probability > 1.0)
        ):
            raise RuntimeError("invalid calibrated failure probability")
        return probability, raw


def _selected_checkpoint_record(
    manifest: dict[str, Any], *, method: str, seed: int, width: int | None
) -> dict[str, Any]:
    matches = [
        record
        for record in manifest["checkpoints"]
        if record["method"] == method
        and record["condition"] == "true"
        and int(record["seed"]) == seed
        and (width is None or int(record["width"]) == width)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one selected checkpoint record for {method}/{seed}/{width}"
        )
    return matches[0]


def load_frozen_calibrated_ensemble(
    *,
    method: str,
    true_selection_dir: Path,
    calibration_dir: Path,
    m1_root: Path,
    m2_root: Path,
    m3_root: Path,
    noise_npy: Path,
    noise_manifest: Path,
    device: torch.device,
    m2_batch_size: int = 2048,
    environment: str = "pusht",
) -> FrozenCalibratedScorerEnsemble:
    if environment not in {"pusht", "tworoom"}:
        raise ValueError(f"unsupported scorer environment: {environment}")
    prefix = "tworoom_" if environment == "tworoom" else ""
    true_classification = f"{prefix}p2_true_scorer_raw_score_selection"
    calibration_classification = (
        f"{prefix}p2_null_control_scores_and_calibrators"
    )
    true_inventory = verify_inventory(true_selection_dir)
    calibration_inventory = verify_inventory(calibration_dir)
    if set(true_inventory) != {"scores.h5", "manifest.json", "provenance.txt"}:
        raise RuntimeError("unexpected true-selection inventory")
    if set(calibration_inventory) != {
        "audit-and-calibrators.h5",
        "manifest.json",
        "provenance.txt",
    }:
        raise RuntimeError("unexpected calibration inventory")
    true_manifest = json.loads(
        (true_selection_dir / "manifest.json").read_text(encoding="utf-8")
    )
    calibration_manifest = json.loads(
        (calibration_dir / "manifest.json").read_text(encoding="utf-8")
    )
    if (
        true_manifest.get("status") != "ok"
        or true_manifest.get("classification") != true_classification
        or true_manifest.get("environment", "pusht") != environment
    ):
        raise RuntimeError("invalid true-scorer selection artifact")
    if (
        calibration_manifest.get("status") != "ok"
        or calibration_manifest.get("classification")
        != calibration_classification
        or calibration_manifest.get("environment", "pusht") != environment
    ):
        raise RuntimeError("invalid calibration artifact")
    if calibration_manifest["inputs"]["true_score_h5_sha256"] != true_manifest[
        "output_h5_sha256"
    ]:
        raise RuntimeError("calibrators do not belong to the selected true scores")
    selected = calibration_manifest["selected_configuration"]
    width: int | None
    sigma: float | None
    if method == "M1":
        width = int(selected["M1_width"])
        sigma = None
        method_root = m1_root
        condition = "true"
    elif method == "M2":
        width = int(selected["M2_width"])
        sigma = float(selected["M2_sigma"])
        method_root = m2_root
        condition = "true"
    elif method == "M3":
        width = None
        sigma = None
        method_root = m3_root
        condition = "true"
    else:
        raise ValueError(method)

    calibration_h5 = calibration_dir / "audit-and-calibrators.h5"
    if calibration_manifest["output_h5_sha256"] != calibration_inventory[
        "audit-and-calibrators.h5"
    ]:
        raise RuntimeError("calibration HDF5 hash mismatch")
    raw_slopes = []
    raw_intercepts = []
    with h5py.File(calibration_h5, "r") as handle:
        if (
            handle.attrs["classification"] != calibration_classification
            or handle.attrs.get("environment", "pusht") != environment
        ):
            raise RuntimeError("calibration HDF5 classification mismatch")
        if int(handle.attrs["selected_m1_width"]) != int(selected["M1_width"]):
            raise RuntimeError("M1 selection changed in calibration HDF5")
        if int(handle.attrs["selected_m2_width"]) != int(selected["M2_width"]):
            raise RuntimeError("M2 width changed in calibration HDF5")
        if float(handle.attrs["selected_m2_sigma"]) != float(selected["M2_sigma"]):
            raise RuntimeError("M2 sigma changed in calibration HDF5")
        for seed in SEEDS:
            group = handle[f"calibrators/{method}/seed-{seed}"]
            slope = float(group.attrs["platt_raw_score_slope"])
            intercept = float(group.attrs["platt_raw_score_intercept"])
            if not np.isfinite(slope) or slope < 0.0 or not np.isfinite(intercept):
                raise RuntimeError("invalid stored Platt parameters")
            raw_slopes.append(slope)
            raw_intercepts.append(intercept)

    models: list[torch.nn.Module] = []
    payloads: list[dict[str, Any]] = []
    checkpoint_records = []
    stats_sha = calibration_manifest["inputs"]["stats_npz_sha256"]
    for seed_index, seed in enumerate(SEEDS):
        directory, checkpoint, result_path = training_paths(
            method_root,
            method.lower(),
            condition,
            width,
            seed_index,
            environment,
        )
        inventory = verify_inventory(directory)
        relative_checkpoint = str(checkpoint.resolve().relative_to(directory.resolve()))
        relative_result = str(result_path.resolve().relative_to(directory.resolve()))
        if relative_checkpoint not in inventory or relative_result not in inventory:
            raise RuntimeError(f"selected checkpoint absent from inventory: {directory}")
        selected_record = _selected_checkpoint_record(
            true_manifest, method=method, seed=seed, width=width
        )
        checkpoint_sha = inventory[relative_checkpoint]
        if checkpoint_sha != selected_record["checkpoint_sha256"]:
            raise RuntimeError("selected checkpoint hash differs from P2 record")
        payload = torch.load(checkpoint, map_location=device, weights_only=False)
        if payload["condition"] != "true" or int(payload["training_seed"]) != seed:
            raise RuntimeError("selected scorer checkpoint condition/seed mismatch")
        if method in {"M1", "M2"}:
            if int(payload["hidden_width"]) != width or payload[
                "stats_npz_sha256"
            ] != stats_sha:
                raise RuntimeError("selected scorer width/statistics mismatch")
        if method == "M1":
            assert width is not None
            model = MacroInverseDynamicsMLP(LATENT_DIM, MACRO_DIM, width)
        elif method == "M2":
            assert width is not None
            model = ConditionalEpsilonMLP(LATENT_DIM, width)
        else:
            if float(payload["target_scale"]) != 40.0:
                raise RuntimeError("M3 target scale changed")
            model = TemporalPairHead(LATENT_DIM)
        model.load_state_dict(payload["state_dict"])
        model.to(device).eval().requires_grad_(False)
        models.append(model)
        payloads.append(payload)
        checkpoint_records.append(
            {
                "seed": seed,
                "directory": str(directory),
                "checkpoint_sha256": checkpoint_sha,
                "training_result_sha256": inventory[relative_result],
            }
        )

    noise: torch.Tensor | None = None
    noise_record: dict[str, Any] | None = None
    if method == "M2":
        noise_info = json.loads(noise_manifest.read_text(encoding="utf-8"))
        if sha256_file(noise_npy) != noise_info["output_npy_sha256"]:
            raise RuntimeError("M2 frozen noise bank hash mismatch")
        noise_np = np.load(noise_npy, allow_pickle=False)
        if noise_np.shape != (NOISE_DRAWS, LATENT_DIM) or noise_np.dtype != np.float32:
            raise RuntimeError("invalid M2 frozen noise bank")
        noise = torch.from_numpy(noise_np).to(device)
        noise_record = {
            "npy_sha256": noise_info["output_npy_sha256"],
            "manifest": str(noise_manifest),
        }

    artifact_record = {
        "method": method,
        "environment": environment,
        "width": width,
        "sigma": sigma,
        "seeds": list(SEEDS),
        "checkpoints": checkpoint_records,
        "true_selection_manifest": str(true_selection_dir / "manifest.json"),
        "true_selection_h5_sha256": true_manifest["output_h5_sha256"],
        "calibration_manifest": str(calibration_dir / "manifest.json"),
        "calibration_h5_sha256": calibration_manifest["output_h5_sha256"],
        "statistics_sha256": stats_sha,
        "noise": noise_record,
        "raw_platt_slopes": raw_slopes,
        "raw_platt_intercepts": raw_intercepts,
    }
    return FrozenCalibratedScorerEnsemble(
        method=method,
        models=models,
        payloads=payloads,
        raw_slopes=torch.tensor(raw_slopes, dtype=torch.float32),
        raw_intercepts=torch.tensor(raw_intercepts, dtype=torch.float32),
        device=device,
        sigma=sigma,
        noise=noise,
        artifact_record=artifact_record,
        m2_batch_size=m2_batch_size,
    )


class FeasibilityAugmentedHighCost:
    """Exact Hi-LeWM high cost plus a weighted calibrated failure probability."""

    def __init__(
        self,
        *,
        base_model: torch.nn.Module,
        scorer: FrozenCalibratedScorerEnsemble,
        weight: float,
        cem_iterations: int,
        topk: int,
        environment: str = "pusht",
    ) -> None:
        if weight not in {0.25, 0.5, 1.0, 2.0, 4.0}:
            raise ValueError("weight is outside the frozen P2 grid")
        expected_budget = {
            "pusht": (60, 10),
            "tworoom": (20, 10),
        }.get(environment)
        if expected_budget is None or (cem_iterations, topk) != expected_budget:
            raise ValueError(
                f"wrapper received an invalid {environment} high-level CEM budget"
            )
        self.base_model = base_model
        self.scorer = scorer
        self.weight = float(weight)
        self.cem_iterations = int(cem_iterations)
        self.topk = int(topk)
        self.environment = environment
        self.call_count = 0
        self.candidate_evaluations = 0
        self.final_iteration_summaries: list[dict[str, Any]] = []
        self._timing_events: list[tuple[torch.cuda.Event, torch.cuda.Event, torch.cuda.Event]] = []

    @torch.inference_mode()
    def nominal_high_components(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if action_candidates.ndim != 4:
            raise ValueError("high-level candidates must have shape (B,S,H,D_high)")
        device = self.base_model._device()
        action_candidates = action_candidates.to(device)
        b, s, h, d_high = action_candidates.shape
        z_init = info_dict.get("z_init")
        z_goal = info_dict.get("z_goal")
        if not torch.is_tensor(z_init) or not torch.is_tensor(z_goal):
            raise ValueError("high-level cost requires z_init and z_goal tensors")
        z_init = self.base_model._expand_sample_dim(z_init.to(device), target_samples=s)
        z_goal = self.base_model._expand_sample_dim(z_goal.to(device), target_samples=s)
        latent_action_dim = self.base_model._infer_latent_action_dim()
        if latent_action_dim != MACRO_DIM:
            raise RuntimeError(
                f"frozen scorer expects {MACRO_DIM} macro dimensions, "
                f"but Hi-LeWM reports {latent_action_dim}"
            )
        if d_high % latent_action_dim != 0:
            raise ValueError("candidate action dimension is not divisible by macro dimension")
        high_action_block = d_high // latent_action_dim
        latent_actions = action_candidates.reshape(
            b, s, h * high_action_block, latent_action_dim
        )
        prediction = self.base_model.rollout_high(z_init, latent_actions)
        if prediction.ndim != 4 or prediction.shape[:3] != (
            b,
            s,
            h * high_action_block,
        ) or prediction.shape[-1] != LATENT_DIM:
            raise RuntimeError(
                f"unexpected Hi-LeWM rollout shape: {tuple(prediction.shape)}"
            )
        z_final = prediction[:, :, -1, :]
        nominal = (z_final - z_goal).pow(2).sum(dim=-1)
        z_subgoal = prediction[:, :, 0, :]
        first_macro = latent_actions[:, :, 0, :]
        return nominal, z_init, z_subgoal, first_macro

    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> torch.Tensor:
        is_high = torch.is_tensor(info_dict.get("z_init")) and torch.is_tensor(
            info_dict.get("z_goal")
        )
        if not is_high:
            return self.base_model.get_cost(info_dict, action_candidates)
        start_event = torch.cuda.Event(enable_timing=True)
        nominal_event = torch.cuda.Event(enable_timing=True)
        scorer_event = torch.cuda.Event(enable_timing=True)
        start_event.record()
        nominal, source, subgoal, first_macro = self.nominal_high_components(
            info_dict, action_candidates
        )
        nominal_event.record()
        batch, samples = nominal.shape
        probability, raw = self.scorer.failure_probability(
            source.reshape(batch * samples, LATENT_DIM),
            subgoal.reshape(batch * samples, LATENT_DIM),
            first_macro.reshape(batch * samples, MACRO_DIM),
        )
        probability = probability.reshape(batch, samples)
        raw = raw.reshape(len(SEEDS), batch, samples)
        augmented = nominal + self.weight * probability
        scorer_event.record()
        self._timing_events.append((start_event, nominal_event, scorer_event))
        self.call_count += 1
        self.candidate_evaluations += int(batch * samples)
        if self.call_count % self.cem_iterations == 0:
            top_indices = torch.topk(
                augmented, k=self.topk, dim=1, largest=False
            ).indices
            batch_indices = torch.arange(batch, device=augmented.device)[:, None]
            top_probability = probability[batch_indices, top_indices]
            self.final_iteration_summaries.append(
                {
                    "solve_index": len(self.final_iteration_summaries),
                    "candidate_count": int(batch * samples),
                    "nominal_cost_mean": float(nominal.mean().item()),
                    "nominal_cost_min": float(nominal.min().item()),
                    "failure_probability_mean": float(probability.mean().item()),
                    "failure_probability_min": float(probability.min().item()),
                    "failure_probability_max": float(probability.max().item()),
                    "topk_failure_probability_mean": float(
                        top_probability.mean().item()
                    ),
                    "augmented_cost_mean": float(augmented.mean().item()),
                    "augmented_cost_min": float(augmented.min().item()),
                    "seed_raw_score_means": [
                        float(raw[index].mean().item()) for index in range(len(SEEDS))
                    ],
                }
            )
        return augmented

    @torch.inference_mode()
    def assert_nominal_equivalence(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> dict[str, Any]:
        reference = self.base_model.get_cost_high(info_dict, action_candidates)
        candidate, _, _, _ = self.nominal_high_components(info_dict, action_candidates)
        max_abs = float((reference - candidate).abs().max().item())
        if max_abs != 0.0:
            raise RuntimeError(f"augmented wrapper changed nominal high cost: {max_abs}")
        return {
            "status": "ok",
            "max_abs": max_abs,
            "shape": list(reference.shape),
        }

    def timing_summary(self) -> dict[str, Any]:
        torch.cuda.synchronize()
        nominal_ms = sum(
            start.elapsed_time(nominal)
            for start, nominal, _ in self._timing_events
        )
        scorer_ms = sum(
            nominal.elapsed_time(scorer)
            for _, nominal, scorer in self._timing_events
        )
        candidate_evaluations = self.candidate_evaluations
        return {
            "cost_calls": self.call_count,
            "expected_calls_per_high_solve": self.cem_iterations,
            "completed_high_solves": len(self.final_iteration_summaries),
            "nominal_high_model_ms": float(nominal_ms),
            "scorer_ms": float(scorer_ms),
            "scorer_ms_per_cost_call": (
                float(scorer_ms / self.call_count) if self.call_count else None
            ),
            "scorer_microseconds_per_candidate": (
                float(scorer_ms * 1000.0 / candidate_evaluations)
                if candidate_evaluations
                else None
            ),
            "candidate_evaluations": candidate_evaluations,
        }
