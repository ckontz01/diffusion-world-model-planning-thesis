#!/usr/bin/env python3
"""Evaluate frozen transition scorers on never-trained I1 episodes."""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import h5py
import numpy as np
import torch

from acid_alternative.io_utils import atomic_write_json, sha256_file
from acid_alternative.models import count_parameters
from acid_alternative.task_registry import TASKS
from acid_alternative.train_transition_scorer import (
    atomic_save_npz,
    configure_seed,
    fixed_derangement_indices,
    make_model,
    validate,
)

CONFIRMATION_PERMUTATION_SEED = 2026081312
CONFIRMATION_NOISE_SEED_BASE = 2026081313
VARIANT_BY_MODEL_CONDITION = {
    ("acid", "true"): "acid",
    ("diffusion", "true"): "diffusion",
    ("diffusion", "shuffled_action"): "diffusion_shuffled",
    ("diffusion", "action_ablated"): "diffusion_action_ablated",
    ("forward", "true"): "forward",
    ("forward", "shuffled_action"): "forward_shuffled",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=tuple(TASKS), required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--training-transition-h5", type=Path, required=True)
    parser.add_argument("--training-transition-manifest", type=Path, required=True)
    parser.add_argument("--identification-transition-h5", type=Path, required=True)
    parser.add_argument(
        "--identification-transition-manifest", type=Path, required=True
    )
    parser.add_argument("--identification-episode-manifest", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--confirmation-authorization", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--test-limit", type=int)
    args = parser.parse_args()
    for path in (
        args.checkpoint,
        args.latent_h5,
        args.latent_manifest,
        args.training_transition_h5,
        args.training_transition_manifest,
        args.identification_transition_h5,
        args.identification_transition_manifest,
        args.identification_episode_manifest,
        args.source_manifest,
        args.confirmation_authorization,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if args.batch_size <= 0 or (
        args.test_limit is not None and args.test_limit <= 0
    ):
        raise ValueError("batch size and optional test limit must be positive")
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    training_manifest = json.loads(
        args.training_transition_manifest.read_text(encoding="utf-8")
    )
    identification_manifest = json.loads(
        args.identification_transition_manifest.read_text(encoding="utf-8")
    )
    authorization = json.loads(
        args.confirmation_authorization.read_text(encoding="utf-8")
    )
    latent_hash = sha256_file(args.latent_h5)
    training_hash = sha256_file(args.training_transition_h5)
    identification_hash = sha256_file(args.identification_transition_h5)
    source_hash = sha256_file(args.source_manifest)
    if (
        latent_manifest.get("status") != "ok"
        or latent_manifest.get("kind") != "flat_frozen_encoder_latent_cache"
        or latent_manifest.get("output_h5_sha256") != latent_hash
        or latent_manifest.get("partitions") != ["I1"]
        or latent_manifest.get("source_manifest_sha256") != source_hash
    ):
        raise RuntimeError("latent cache hash mismatch")
    if (
        training_manifest.get("status") != "ok"
        or training_manifest.get("kind") != "flat_one_model_step_transition_cache"
        or training_manifest.get("output_h5_sha256") != training_hash
        or training_manifest.get("source_manifest_sha256") != source_hash
    ):
        raise RuntimeError("training transition cache provenance mismatch")
    if (
        identification_manifest.get("status") != "ok"
        or identification_manifest.get("kind")
        != "acid_alternative_i1_transition_cache"
        or identification_manifest.get("task") != args.task
        or identification_manifest.get("data_role") != "I1"
        or identification_manifest.get("episodes") != 200
        or identification_manifest.get("output_h5_sha256") != identification_hash
        or identification_manifest.get("latent_h5_sha256") != latent_hash
        or identification_manifest.get("training_transition_h5_sha256")
        != training_hash
        or identification_manifest.get("identification_manifest_sha256")
        != sha256_file(args.identification_episode_manifest)
        or identification_manifest.get("source_manifest_sha256") != source_hash
        or identification_manifest.get(
            "confirmation_identification_outcomes_computed"
        )
        is not False
    ):
        raise RuntimeError("I1 transition cache provenance mismatch")
    try:
        authorized_task = authorization["tasks"][args.task]
    except (KeyError, TypeError) as error:
        raise RuntimeError("C1 authorization lacks this task") from error
    if (
        authorization.get("status") != "authorized"
        or authorization.get("kind") != "acid_alternative_c1_authorization_v1"
        or authorization.get("confirmation_outcomes_unseen") is not True
        or authorization.get("source_manifest_sha256") != source_hash
        or authorized_task.get("identification_manifest_sha256")
        != sha256_file(args.identification_episode_manifest)
        or authorized_task.get("world_model_checkpoint_sha256")
        != latent_manifest.get("checkpoint_sha256")
    ):
        raise RuntimeError("I1 inputs differ from the C1 authorization")

    device = torch.device(args.device)
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model_name = checkpoint.get("model_name")
    condition = checkpoint.get("condition")
    training_seed = checkpoint.get("seed")
    if model_name not in {"acid", "diffusion", "forward"} or condition not in {
        "true",
        "shuffled_action",
        "action_ablated",
    }:
        raise RuntimeError("unexpected scorer checkpoint metadata")
    if not isinstance(training_seed, int):
        raise TypeError("scorer checkpoint lacks an integer training seed")
    try:
        scorer_variant = VARIANT_BY_MODEL_CONDITION[(model_name, condition)]
        authorized_scorer_hash = authorized_task["scorer_checkpoint_sha256"][
            scorer_variant
        ][str(training_seed)]
    except (KeyError, TypeError) as error:
        raise RuntimeError("scorer is not an authorized identification variant") from error
    checkpoint_hash = sha256_file(args.checkpoint)
    if (
        authorized_scorer_hash != checkpoint_hash
        or checkpoint.get("transition_h5_sha256") != training_hash
        or checkpoint.get("latent_h5_sha256")
        != training_manifest.get("latent_h5_sha256")
        or checkpoint.get("source_manifest_sha256") != source_hash
    ):
        raise RuntimeError("scorer checkpoint was trained from different frozen inputs")

    with h5py.File(args.latent_h5, "r") as handle:
        latents = torch.from_numpy(np.asarray(handle["latent"][:], dtype=np.float32))
    with h5py.File(args.identification_transition_h5, "r") as handle:
        source_index = torch.from_numpy(
            np.asarray(handle["source_index"][:], dtype=np.int64)
        )
        target_index = torch.from_numpy(
            np.asarray(handle["target_index"][:], dtype=np.int64)
        )
        actions = torch.from_numpy(np.asarray(handle["action"][:], dtype=np.float32))
        pair_episode = torch.from_numpy(
            np.asarray(handle["episode_idx"][:], dtype=np.int64)
        )
        pair_step = torch.from_numpy(np.asarray(handle["step_idx"][:], dtype=np.int64))
        latent_mean = torch.from_numpy(
            np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        )
        latent_std = torch.from_numpy(
            np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        )
        acid_action_mean = torch.from_numpy(
            np.asarray(handle["stats/acid_action_mean"][:], dtype=np.float32)
        )
        acid_action_std = torch.from_numpy(
            np.asarray(handle["stats/acid_action_std"][:], dtype=np.float32)
        )
    test_pairs_all = torch.arange(len(source_index), dtype=torch.int64)
    if len(test_pairs_all) != identification_manifest.get("pairs"):
        raise RuntimeError("I1 pair count differs from its transition manifest")
    test_pairs = (
        test_pairs_all
        if args.test_limit is None
        else test_pairs_all[: min(args.test_limit, len(test_pairs_all))]
    )
    if len(test_pairs) < 2:
        raise RuntimeError("I1 must contain at least two transitions")
    episode_count = int(torch.unique(pair_episode.index_select(0, test_pairs)).numel())
    if args.test_limit is None and episode_count != 200:
        raise RuntimeError("full I1 evaluation does not contain all 200 episodes")

    model, model_config = make_model(
        model_name, latent_dim=latents.shape[1], action_dim=actions.shape[1]
    )
    if model_config != checkpoint.get("model_config"):
        raise RuntimeError("reconstructed model configuration differs from checkpoint")
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model = model.to(device).eval()
    evaluation_seed = CONFIRMATION_NOISE_SEED_BASE + training_seed
    configure_seed(evaluation_seed)
    started = time.time()
    result = validate(
        model_name,
        model,
        test_pairs,
        source_index=source_index,
        target_index=target_index,
        latents=latents,
        actions=actions,
        latent_mean=latent_mean,
        latent_std=latent_std,
        acid_action_mean=acid_action_mean,
        acid_action_std=acid_action_std,
        device=device,
        batch_size=args.batch_size,
        seed=evaluation_seed,
        condition=condition,
        collect_examples=True,
        permutation_seed=CONFIRMATION_PERMUTATION_SEED,
    )
    correct = np.asarray(result.pop("_correct_cost_by_example"), dtype=np.float32)
    permuted = np.asarray(result.pop("_permuted_cost_by_example"), dtype=np.float32)
    permutation = fixed_derangement_indices(
        len(test_pairs), seed=CONFIRMATION_PERMUTATION_SEED
    )
    permuted_pairs = test_pairs.index_select(0, permutation)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    examples = args.output_dir / "identification-examples.npz"
    atomic_save_npz(
        examples,
        pair_index=test_pairs.numpy(),
        episode_idx=pair_episode.index_select(0, test_pairs).numpy(),
        step_idx=pair_step.index_select(0, test_pairs).numpy(),
        permuted_pair_index=permuted_pairs.numpy(),
        permuted_episode_idx=pair_episode.index_select(0, permuted_pairs).numpy(),
        permuted_step_idx=pair_step.index_select(0, permuted_pairs).numpy(),
        correct_cost=correct,
        permuted_cost=permuted,
        correct_minus_permuted_margin=permuted - correct,
    )
    summary = {
        "status": "ok",
        "kind": "flat_transition_identification_evaluation",
        "analysis_role": "C1",
        "data_role": "I1",
        "task": args.task,
        "model": model_name,
        "condition": condition,
        "scorer_variant": scorer_variant,
        "training_seed": training_seed,
        "parameter_count": count_parameters(model),
        "test_pairs_total": len(test_pairs_all),
        "test_pairs_evaluated": len(test_pairs),
        "identification_episodes_evaluated": episode_count,
        "test_limit": args.test_limit,
        "confirmation_test_outcomes_previously_used_for_training_or_selection": False,
        "identification": result,
        "identification_examples": str(examples),
        "identification_examples_sha256": sha256_file(examples),
        "action_permutation": {
            "kind": "single_cycle_random_derangement",
            "seed": CONFIRMATION_PERMUTATION_SEED,
            "fixed_points": 0,
        },
        "evaluation_noise_seed": evaluation_seed,
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": checkpoint_hash,
        "latent_h5": str(args.latent_h5),
        "latent_h5_sha256": latent_hash,
        "training_transition_h5": str(args.training_transition_h5),
        "training_transition_h5_sha256": training_hash,
        "transition_h5_sha256": training_hash,
        "identification_transition_h5": str(args.identification_transition_h5),
        "identification_transition_h5_sha256": identification_hash,
        "identification_episode_manifest": str(args.identification_episode_manifest),
        "identification_episode_manifest_sha256": sha256_file(
            args.identification_episode_manifest
        ),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_hash,
        "confirmation_authorization": str(args.confirmation_authorization),
        "confirmation_authorization_sha256": sha256_file(
            args.confirmation_authorization
        ),
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": str(device),
            "gpu": torch.cuda.get_device_name(device)
            if device.type == "cuda"
            else None,
        },
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
