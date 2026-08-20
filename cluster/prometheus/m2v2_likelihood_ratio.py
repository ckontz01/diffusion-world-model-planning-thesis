#!/usr/bin/env python3
"""Frozen M2v2 conditional-versus-unconditional diffusion score."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from score_and_select_p2_true_scorers import (
    LATENT_DIM,
    MACRO_DIM,
    NOISE_DRAWS,
    SEEDS,
    SIGMAS,
    sha256_file,
)
from train_m2_diffusion_head import ConditionalEpsilonMLP


M2V2_WIDTH = 1024
SPAN_ABSOLUTE_FLOOR = 1.0e-7
SPAN_RELATIVE_FACTOR = 1.0e-7


def _load_checkpoint(
    path: Path,
    *,
    seed: int,
    condition: str,
    device: torch.device,
) -> tuple[ConditionalEpsilonMLP, dict[str, Any]]:
    payload = torch.load(path, map_location=device, weights_only=False)
    if (
        payload.get("condition") != condition
        or int(payload.get("training_seed", -1)) != seed
        or int(payload.get("hidden_width", -1)) != M2V2_WIDTH
        or int(payload.get("latent_dim", -1)) != LATENT_DIM
        or tuple(float(value) for value in payload.get("sigma_grid", ())) != SIGMAS
    ):
        raise RuntimeError(f"unexpected M2v2 checkpoint payload: {path}")
    if condition == "unconditional_zero_source" and payload.get("source_mode") != "hard_zero_every_call":
        raise RuntimeError(f"unconditional checkpoint does not freeze zero-source mode: {path}")
    model = ConditionalEpsilonMLP(LATENT_DIM, M2V2_WIDTH).to(device)
    model.load_state_dict(payload["state_dict"])
    model.eval().requires_grad_(False)
    return model, payload


def exact_midrank(values: torch.Tensor) -> tuple[torch.Tensor, int]:
    if values.ndim != 1 or len(values) < 2 or not torch.isfinite(values).all():
        raise RuntimeError("midrank requires at least two finite scores")
    sorted_values, order = torch.sort(values, stable=True)
    _, inverse, counts = torch.unique_consecutive(
        sorted_values, return_inverse=True, return_counts=True
    )
    ends = torch.cumsum(counts, dim=0).to(values.dtype)
    starts = ends - counts.to(values.dtype)
    group_midranks = (starts + ends - 1.0) / 2.0
    sorted_ranks = group_midranks.index_select(0, inverse)
    ranks = torch.empty_like(values)
    ranks.scatter_(0, order, sorted_ranks)
    return ranks / float(len(values) - 1), int(len(counts))


class M2v2LikelihoodRatioEnsemble:
    def __init__(
        self,
        *,
        conditional_models: list[ConditionalEpsilonMLP],
        unconditional_models: list[ConditionalEpsilonMLP],
        conditional_payloads: list[dict[str, Any]],
        unconditional_payloads: list[dict[str, Any]],
        reference_mean: torch.Tensor,
        reference_std: torch.Tensor,
        noise: torch.Tensor,
        device: torch.device,
        expected_candidate_count: int | None,
        artifact_record: dict[str, Any],
        batch_size: int = 8192,
    ) -> None:
        if len(conditional_models) != len(SEEDS) or len(unconditional_models) != len(SEEDS):
            raise ValueError("M2v2 requires exactly three conditional/unconditional pairs")
        if reference_mean.shape != (len(SEEDS), len(SIGMAS)) or reference_std.shape != reference_mean.shape:
            raise ValueError("invalid M2v2 P1 reference shape")
        if torch.any(reference_std <= 1.0e-6):
            raise ValueError("M2v2 P1 reference standard deviation is degenerate")
        if noise.shape != (NOISE_DRAWS, LATENT_DIM):
            raise ValueError("invalid frozen M2 noise bank")
        self.conditional_models = conditional_models
        self.unconditional_models = unconditional_models
        self.conditional_payloads = conditional_payloads
        self.unconditional_payloads = unconditional_payloads
        self.reference_mean = reference_mean.to(device=device, dtype=torch.float32)
        self.reference_std = reference_std.to(device=device, dtype=torch.float32)
        self.noise = noise.to(device=device, dtype=torch.float32)
        self.device = device
        self.expected_candidate_count = expected_candidate_count
        self.artifact_record = artifact_record
        self.batch_size = int(batch_size)
        self.population_diagnostics: list[dict[str, Any]] = []

        first_mean = conditional_payloads[0]["latent_mean"].to(device)
        first_std = conditional_payloads[0]["latent_std"].to(device)
        for conditional, unconditional in zip(
            conditional_payloads, unconditional_payloads, strict=True
        ):
            for payload in (conditional, unconditional):
                if not torch.equal(payload["latent_mean"].to(device), first_mean) or not torch.equal(
                    payload["latent_std"].to(device), first_std
                ):
                    raise RuntimeError("M2v2 paired checkpoints use different latent statistics")
            if conditional["stats_npz_sha256"] != unconditional["stats_npz_sha256"]:
                raise RuntimeError("M2v2 conditional/unconditional statistics hash mismatch")
        self.latent_mean = first_mean
        self.latent_std = first_std

    @torch.inference_mode()
    def raw_scores(
        self,
        source_raw: torch.Tensor,
        target_raw: torch.Tensor,
        macro_raw: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if source_raw.shape != target_raw.shape or source_raw.ndim != 2:
            raise RuntimeError("M2v2 source and target must be matching matrices")
        if source_raw.shape[1] != LATENT_DIM:
            raise RuntimeError("unexpected M2v2 latent width")
        if macro_raw is not None and macro_raw.shape != (len(source_raw), MACRO_DIM):
            raise RuntimeError("unexpected M2v2 macro shape")

        source = (source_raw.to(self.device) - self.latent_mean) / self.latent_std
        target = (target_raw.to(self.device) - self.latent_mean) / self.latent_std
        count = len(source)
        sigma_grid = torch.tensor(SIGMAS, device=self.device, dtype=source.dtype)
        source_expanded = source[:, None, None, :].expand(
            count, len(SIGMAS), NOISE_DRAWS, LATENT_DIM
        ).reshape(-1, LATENT_DIM)
        target_expanded = target[:, None, None, :].expand(
            count, len(SIGMAS), NOISE_DRAWS, LATENT_DIM
        ).reshape(-1, LATENT_DIM)
        epsilon = self.noise[None, None, :, :].expand(
            count, len(SIGMAS), NOISE_DRAWS, LATENT_DIM
        ).reshape(-1, LATENT_DIM)
        sigma = sigma_grid[None, :, None].expand(
            count, len(SIGMAS), NOISE_DRAWS
        ).reshape(-1)
        noisy_target = target_expanded + sigma[:, None] * epsilon
        zero_source = torch.zeros_like(source_expanded)

        seed_scores: list[torch.Tensor] = []
        for seed_index, (conditional, unconditional) in enumerate(
            zip(self.conditional_models, self.unconditional_models, strict=True)
        ):
            difference = torch.empty(len(sigma), device=self.device, dtype=source.dtype)
            for start in range(0, len(sigma), self.batch_size):
                stop = min(start + self.batch_size, len(sigma))
                cond_prediction = conditional(
                    noisy_target[start:stop], sigma[start:stop], source_expanded[start:stop]
                )
                uncond_prediction = unconditional(
                    noisy_target[start:stop], sigma[start:stop], zero_source[start:stop]
                )
                difference[start:stop] = (
                    (epsilon[start:stop] - cond_prediction).square().sum(dim=-1)
                    - (epsilon[start:stop] - uncond_prediction).square().sum(dim=-1)
                )
            by_sigma = difference.reshape(count, len(SIGMAS), NOISE_DRAWS).mean(dim=2)
            standardized = (
                by_sigma - self.reference_mean[seed_index][None, :]
            ) / self.reference_std[seed_index][None, :]
            seed_scores.append(standardized.mean(dim=1))
        result = torch.stack(seed_scores, dim=0)
        if not torch.isfinite(result).all():
            raise RuntimeError("non-finite M2v2 standardized score")
        return result

    @torch.inference_mode()
    def failure_probability(
        self,
        source_raw: torch.Tensor,
        target_raw: torch.Tensor,
        macro_raw: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if self.expected_candidate_count is not None and len(source_raw) != self.expected_candidate_count:
            raise RuntimeError(
                f"M2v2 expected {self.expected_candidate_count} candidates, got {len(source_raw)}"
            )
        seed_scores = self.raw_scores(source_raw, target_raw, macro_raw)
        score = seed_scores.mean(dim=0)
        score_min = float(score.min().item())
        score_max = float(score.max().item())
        score_mean = float(score.mean().item())
        span = score_max - score_min
        threshold = max(
            SPAN_ABSOLUTE_FLOOR,
            SPAN_RELATIVE_FACTOR * max(1.0, abs(score_mean)),
        )
        if not span > threshold:
            raise RuntimeError(
                f"M2v2 non-intervention gate failed: span={span:.9g}, threshold={threshold:.9g}"
            )
        penalty, unique_count = exact_midrank(score)
        diagnostic = {
            "cost_call_index": len(self.population_diagnostics),
            "candidate_count": len(score),
            "raw_score_mean": score_mean,
            "raw_score_min": score_min,
            "raw_score_max": score_max,
            "raw_score_span": span,
            "required_span": threshold,
            "unique_score_count": unique_count,
            "midrank_min": float(penalty.min().item()),
            "midrank_max": float(penalty.max().item()),
        }
        self.population_diagnostics.append(diagnostic)
        return penalty, seed_scores


def load_m2v2_ensemble(
    *,
    conditional_checkpoints: list[Path],
    unconditional_checkpoints: list[Path],
    reference_npz: Path,
    reference_manifest: Path,
    noise_npy: Path,
    noise_manifest: Path,
    spec: Path,
    environment: str,
    device: torch.device,
    expected_candidate_count: int | None,
    batch_size: int = 8192,
) -> M2v2LikelihoodRatioEnsemble:
    if len(conditional_checkpoints) != len(SEEDS) or len(unconditional_checkpoints) != len(SEEDS):
        raise RuntimeError("M2v2 checkpoint lists must follow the three frozen seeds")
    reference_info = json.loads(reference_manifest.read_text(encoding="utf-8"))
    expected_classification = f"{environment}_m2v2_p1_validation_reference"
    if (
        reference_info.get("status") != "ok"
        or reference_info.get("classification") != expected_classification
        or reference_info.get("environment") != environment
        or reference_info.get("spec_sha256") != sha256_file(spec)
        or reference_info.get("output_npz_sha256") != sha256_file(reference_npz)
    ):
        raise RuntimeError("invalid or mismatched M2v2 P1 reference artifact")
    with np.load(reference_npz, allow_pickle=False) as reference:
        seeds_np = np.asarray(reference["seeds"], dtype=np.int64)
        sigmas_np = np.asarray(reference["sigmas"], dtype=np.float64)
        reference_mean = np.asarray(reference["difference_mean"], dtype=np.float32)
        reference_std = np.asarray(reference["difference_std"], dtype=np.float32)
    if not np.array_equal(seeds_np, np.asarray(SEEDS)) or not np.array_equal(
        sigmas_np, np.asarray(SIGMAS)
    ):
        raise RuntimeError("M2v2 reference seed or sigma grid changed")

    noise_info = json.loads(noise_manifest.read_text(encoding="utf-8"))
    if noise_info.get("output_npy_sha256") != sha256_file(noise_npy):
        raise RuntimeError("M2v2 frozen noise bank hash mismatch")
    noise_np = np.load(noise_npy, allow_pickle=False)
    if noise_np.shape != (NOISE_DRAWS, LATENT_DIM) or noise_np.dtype != np.float32:
        raise RuntimeError("M2v2 frozen noise bank shape changed")

    conditional_models = []
    unconditional_models = []
    conditional_payloads = []
    unconditional_payloads = []
    checkpoint_records = []
    expected_records = reference_info.get("checkpoints")
    if not isinstance(expected_records, list) or len(expected_records) != 2 * len(SEEDS):
        raise RuntimeError("M2v2 reference checkpoint inventory is incomplete")
    expected_hashes = {
        (record["role"], int(record["seed"])): record["sha256"]
        for record in expected_records
    }
    for seed, conditional_path, unconditional_path in zip(
        SEEDS, conditional_checkpoints, unconditional_checkpoints, strict=True
    ):
        for role, path in (("conditional", conditional_path), ("unconditional", unconditional_path)):
            digest = sha256_file(path)
            if expected_hashes.get((role, seed)) != digest:
                raise RuntimeError(f"M2v2 {role} checkpoint differs from P1 reference: {path}")
            checkpoint_records.append({"role": role, "seed": seed, "path": str(path), "sha256": digest})
        conditional_model, conditional_payload = _load_checkpoint(
            conditional_path, seed=seed, condition="true", device=device
        )
        unconditional_model, unconditional_payload = _load_checkpoint(
            unconditional_path,
            seed=seed,
            condition="unconditional_zero_source",
            device=device,
        )
        conditional_models.append(conditional_model)
        unconditional_models.append(unconditional_model)
        conditional_payloads.append(conditional_payload)
        unconditional_payloads.append(unconditional_payload)

    artifact_record: dict[str, Any] = {
        "method": "M2v2",
        "environment": environment,
        "width": M2V2_WIDTH,
        "seeds": list(SEEDS),
        "sigmas": list(SIGMAS),
        "noise_draws": NOISE_DRAWS,
        "raw_score": "P1-standardized conditional-minus-unconditional epsilon squared-L2 error",
        "online_transform": "exact within-population midrank",
        "span_gate": {
            "absolute_floor": SPAN_ABSOLUTE_FLOOR,
            "relative_factor": SPAN_RELATIVE_FACTOR,
        },
        "checkpoints": checkpoint_records,
        "reference_manifest": str(reference_manifest),
        "reference_npz_sha256": reference_info["output_npz_sha256"],
        "noise_npy_sha256": noise_info["output_npy_sha256"],
        "spec": str(spec),
        "spec_sha256": sha256_file(spec),
    }
    return M2v2LikelihoodRatioEnsemble(
        conditional_models=conditional_models,
        unconditional_models=unconditional_models,
        conditional_payloads=conditional_payloads,
        unconditional_payloads=unconditional_payloads,
        reference_mean=torch.from_numpy(reference_mean),
        reference_std=torch.from_numpy(reference_std),
        noise=torch.from_numpy(noise_np),
        device=device,
        expected_candidate_count=expected_candidate_count,
        artifact_record=artifact_record,
        batch_size=batch_size,
    )


def self_test() -> None:
    values = torch.tensor([4.0, 1.0, 1.0, 3.0, 2.0])
    ranks, unique = exact_midrank(values)
    expected = torch.tensor([1.0, 0.125, 0.125, 0.75, 0.5])
    if unique != 4 or not torch.equal(ranks, expected):
        raise RuntimeError(f"midrank self-test failed: {ranks}")
    print(json.dumps({"status": "ok", "midrank": ranks.tolist(), "unique": unique}))


if __name__ == "__main__":
    self_test()
