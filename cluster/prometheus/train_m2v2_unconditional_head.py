#!/usr/bin/env python3
"""Train the capacity-matched zero-source companion for the frozen M2v2 test."""

from __future__ import annotations

import json
from pathlib import Path

import torch

import train_m2_diffusion_head as base


OriginalConditionalEpsilonMLP = base.ConditionalEpsilonMLP


class ZeroSourceEpsilonMLP(OriginalConditionalEpsilonMLP):
    """Same parameterization as M2; source information is inaccessible."""

    def forward(
        self, noisy_target: torch.Tensor, sigma: torch.Tensor, source: torch.Tensor
    ) -> torch.Tensor:
        return super().forward(noisy_target, sigma, torch.zeros_like(source))


def patch_artifacts(output_dir: Path) -> dict:
    checkpoint_path = output_dir / "best-checkpoint.pt"
    result_path = output_dir / "training-result.json"
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if payload.get("condition") != "true" or result.get("condition") != "true":
        raise RuntimeError("base trainer did not use genuine P1 D25 pairs")

    payload["condition"] = "unconditional_zero_source"
    payload["source_mode"] = "hard_zero_every_call"
    payload["companion_for"] = "M2v2_conditional_minus_unconditional_error"
    base.atomic_torch_save(checkpoint_path, payload)

    result["classification"] = (
        "m2v2_unconditional_smoke" if result["classification"] == "development_smoke"
        else "m2v2_unconditional_training"
    )
    result["method"] = "M2v2_unconditional_epsilon_prediction"
    result["condition"] = "unconditional_zero_source"
    result["source_mode"] = "hard_zero_every_training_validation_and_scoring_call"
    result["model_spec"]["input"] = (
        "noisy standardized target + hard-zero source slot + log-sigma embedding"
    )
    result["checkpoint_sha256"] = base.sha256_file(checkpoint_path)
    base.atomic_json(result_path, result)
    return result


def self_test() -> None:
    base.configure_determinism(123)
    model = ZeroSourceEpsilonMLP(latent_dim=8, hidden_width=512)
    target = torch.randn(16, 8)
    sigma = torch.tensor(base.SIGMA_GRID * 4, dtype=torch.float32)[:16]
    epsilon = torch.randn_like(target)
    noisy = target + sigma.unsqueeze(-1) * epsilon
    first = model(noisy, sigma, torch.randn_like(target))
    second = model(noisy, sigma, torch.randn_like(target) * 100.0)
    if not torch.equal(first, second):
        raise RuntimeError("zero-source companion depends on its source argument")
    loss = (first - epsilon).square().mean()
    loss.backward()
    print(json.dumps({"status": "ok", "self_test": True, "source_invariant": True}))


def main() -> None:
    parser = base.build_parser()
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.condition != "true":
        raise SystemExit("M2v2 unconditional companion requires genuine --condition true pairs")
    # Reuse the already audited training loop without modifying the frozen M2 file.
    base.ConditionalEpsilonMLP = ZeroSourceEpsilonMLP
    base.train(args)
    final = patch_artifacts(args.output_dir)
    print(json.dumps(final, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
