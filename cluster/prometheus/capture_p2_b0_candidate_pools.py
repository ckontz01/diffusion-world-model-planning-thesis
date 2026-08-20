#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata as metadata
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch
from gymnasium.spaces import Box

from h_le_wm.eval.determinism import configure_process_determinism
from h_le_wm.eval.hierarchical import force_torch_load_map_location


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise RuntimeError(f"empty TSV: {path}")
    return rows


def hash_u64(payload: str) -> int:
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


class RecordingCostModel:
    """Transparent cost adapter that retains the latest official CEM call."""

    def __init__(self, base_model: torch.nn.Module) -> None:
        self.base_model = base_model
        self.call_count = 0
        self.last_candidates: torch.Tensor | None = None
        self.last_costs: torch.Tensor | None = None

    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> torch.Tensor:
        costs = self.base_model.get_cost(info_dict, action_candidates)
        self.call_count += 1
        # Retain the final population on its original device. The released CEM
        # computes top-k and its elite mean on GPU; moving first and reducing on
        # CPU changes float32 summation order at roughly 1e-7.
        self.last_candidates = action_candidates.detach().clone()
        self.last_costs = costs.detach().clone()
        return costs


def select_queries(
    *,
    manifest_rows: list[dict[str, str]],
    cache_rows: np.ndarray,
    cache_episode: np.ndarray,
    cache_step: np.ndarray,
    partition: str,
    goal_offset: int,
    pool_count: int,
    seed: int,
    hash_namespace: str,
    dataset_namespace: str,
) -> list[dict[str, int]]:
    declared = {
        int(row["episode_id"]): int(row["episode_length"])
        for row in manifest_rows
        if row["partition"] == partition
    }
    eligible_declared = {
        episode_id: episode_length
        for episode_id, episode_length in declared.items()
        if episode_length > goal_offset
    }
    if len(eligible_declared) < pool_count:
        raise RuntimeError(
            f"not enough D{goal_offset}-eligible {partition} episodes for "
            f"{pool_count} pools"
        )
    observed = set(int(value) for value in np.unique(cache_episode))
    if observed != set(declared):
        raise RuntimeError(
            f"latent-cache episode set differs from {partition} manifest: "
            f"observed={len(observed)}, declared={len(declared)}"
        )

    ordered_episodes = sorted(
        eligible_declared,
        key=lambda episode_id: hash_u64(
            f"{dataset_namespace}\0{seed}\0{hash_namespace}_pool_episode\0{episode_id}"
        ),
    )
    queries: list[dict[str, int]] = []
    for pool_id, episode_id in enumerate(ordered_episodes[:pool_count]):
        mask = cache_episode == episode_id
        episode_rows = cache_rows[mask]
        episode_steps = cache_step[mask]
        if len(episode_rows) != declared[episode_id]:
            raise RuntimeError(f"episode length mismatch for {episode_id}")
        eligible = episode_rows[episode_steps + goal_offset < declared[episode_id]]
        if eligible.size == 0:
            raise RuntimeError(
                f"episode {episode_id} has no start supporting offset {goal_offset}"
            )
        offset_hash = hash_u64(
            f"{dataset_namespace}\0{seed}\0{hash_namespace}_pool_start\0{episode_id}"
        )
        source_row = int(eligible[offset_hash % eligible.size])
        source_position = int(np.searchsorted(cache_rows, source_row))
        goal_row = source_row + goal_offset
        goal_position = int(np.searchsorted(cache_rows, goal_row))
        if (
            source_position >= len(cache_rows)
            or cache_rows[source_position] != source_row
            or goal_position >= len(cache_rows)
            or cache_rows[goal_position] != goal_row
            or cache_episode[source_position] != episode_id
            or cache_episode[goal_position] != episode_id
            or cache_step[goal_position] - cache_step[source_position] != goal_offset
        ):
            raise RuntimeError(f"invalid source/goal row mapping for episode {episode_id}")
        planner_seed = hash_u64(
            f"{dataset_namespace}\0{seed}\0{hash_namespace}_cem\0{pool_id}\0{episode_id}\0{source_row}"
        ) & ((1 << 63) - 1)
        queries.append(
            {
                "pool_id": pool_id,
                "episode_id": episode_id,
                "source_global_row": source_row,
                "source_cache_position": source_position,
                "source_step": int(cache_step[source_position]),
                "goal_global_row": goal_row,
                "goal_cache_position": goal_position,
                "goal_step": int(cache_step[goal_position]),
                "planner_seed": planner_seed,
            }
        )
    return queries


def selected_candidate_indices(
    *,
    num_samples: int,
    candidate_count: int,
    seed: int,
    pool_id: int,
    hash_namespace: str,
    dataset_namespace: str,
) -> np.ndarray:
    if candidate_count > num_samples:
        raise RuntimeError("candidate_count cannot exceed final CEM population")
    ranked = sorted(
        range(num_samples),
        key=lambda candidate_index: hash_u64(
            f"{dataset_namespace}\0{seed}\0{hash_namespace}_candidate\0{pool_id}\0{candidate_index}"
        ),
    )
    return np.asarray(ranked[:candidate_count], dtype=np.int64)


def build_solver(
    *,
    recorder: RecordingCostModel,
    latent_action_dim: int,
    horizon: int,
    action_block: int,
    num_samples: int,
    n_steps: int,
    topk: int,
    planner_seed: int,
    device: torch.device,
) -> Any:
    solver = swm.solver.CEMSolver(
        model=recorder,
        batch_size=1,
        num_samples=num_samples,
        var_scale=1.0,
        n_steps=n_steps,
        topk=topk,
        device=device,
        seed=planner_seed,
    )
    action_dim = action_block * latent_action_dim
    action_space = Box(
        low=-np.ones((1, latent_action_dim), dtype=np.float32),
        high=np.ones((1, latent_action_dim), dtype=np.float32),
        dtype=np.float32,
    )
    solver.configure(
        action_space=action_space,
        n_envs=1,
        config=SimpleNamespace(horizon=horizon, action_block=action_block),
    )
    if int(solver.action_dim) != action_dim:
        raise RuntimeError("configured high-level CEM action dimension mismatch")
    return solver


@torch.inference_mode()
def run_pool(
    *,
    model: torch.nn.Module,
    z_init: torch.Tensor,
    z_goal: torch.Tensor,
    latent_action_dim: int,
    args: argparse.Namespace,
    planner_seed: int,
) -> dict[str, torch.Tensor | int | float]:
    recorder = RecordingCostModel(model)
    solver = build_solver(
        recorder=recorder,
        latent_action_dim=latent_action_dim,
        horizon=args.high_horizon,
        action_block=args.high_action_block,
        num_samples=args.high_num_samples,
        n_steps=args.high_iters,
        topk=args.high_topk,
        planner_seed=planner_seed,
        device=z_init.device,
    )
    outputs = solver({"z_init": z_init, "z_goal": z_goal}, init_action=None)
    if recorder.call_count != args.high_iters:
        raise RuntimeError(
            f"expected {args.high_iters} cost calls, observed {recorder.call_count}"
        )
    if recorder.last_candidates is None or recorder.last_costs is None:
        raise RuntimeError("official CEM emitted no candidate population")
    candidates = recorder.last_candidates[0]
    costs = recorder.last_costs[0]
    top_indices = torch.topk(
        costs, k=args.high_topk, dim=0, largest=False
    ).indices
    recomputed_action = candidates.index_select(0, top_indices).mean(dim=0)
    returned_action = outputs["actions"][0]
    selected_max_abs = float(
        (recomputed_action.detach().cpu() - returned_action).abs().max().item()
    )
    if selected_max_abs != 0.0:
        raise RuntimeError(
            "captured final elites do not exactly reproduce official CEM output: "
            f"max_abs={selected_max_abs}"
        )
    return {
        "candidates": candidates.detach().cpu(),
        "costs": costs.detach().cpu(),
        "returned_action": returned_action,
        "selected_max_abs": selected_max_abs,
        "call_count": recorder.call_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--partition", default="P2")
    parser.add_argument("--environment", choices=("pusht", "tworoom"), default="pusht")
    parser.add_argument("--policy", required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--pool-count", type=int, default=8)
    parser.add_argument("--candidate-count", type=int, default=64)
    parser.add_argument("--goal-offset", type=int, default=75)
    parser.add_argument("--high-horizon", type=int, default=2)
    parser.add_argument("--high-action-block", type=int, default=1)
    parser.add_argument("--high-num-samples", type=int, default=1200)
    parser.add_argument("--high-iters", type=int, default=60)
    parser.add_argument("--high-topk", type=int, default=10)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--repeat-check", action="store_true")
    args = parser.parse_args()

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite candidate-pool outputs")
    if args.partition not in {"P2", "P3"}:
        raise SystemExit("candidate capture supports only P2 development or locked P3")
    environment = args.environment
    dataset_namespace = "pusht_expert_train" if environment == "pusht" else "tworoom"
    hash_namespace = f"{args.partition.lower()}_stratum3"
    classification = (
        f"{args.partition.lower()}_stratum3_b0_candidate_pools"
        if environment == "pusht"
        else f"tworoom_{args.partition.lower()}_stratum3_b0_candidate_pools"
    )
    expected_goal_offset = 75 if environment == "pusht" else 25
    expected_high_budget = (1200, 60, 10) if environment == "pusht" else (300, 20, 10)
    if (
        args.goal_offset != expected_goal_offset
        or args.high_horizon != 2
        or args.high_action_block != 1
    ):
        raise SystemExit(
            f"{environment} stratum-3 capture is frozen to "
            f"D{expected_goal_offset}/H2/action-block-1"
        )
    if args.smoke:
        expected = (1, 8, 64, 2, 8)
        observed = (
            args.pool_count,
            args.candidate_count,
            args.high_num_samples,
            args.high_iters,
            args.high_topk,
        )
        if observed != expected:
            raise SystemExit(f"smoke configuration must be {expected}, got {observed}")
    else:
        if args.candidate_count != 64:
            raise SystemExit("non-smoke candidate pools are frozen to 64 candidates")
        expected_pool_count = 12 if args.partition == "P2" else 24
        if args.pool_count != expected_pool_count:
            raise SystemExit(
                f"{args.partition} candidate capture requires {expected_pool_count} pools"
            )
        if (args.high_num_samples, args.high_iters, args.high_topk) != expected_high_budget:
            raise SystemExit(
                f"non-smoke CEM must match the released {environment} budget "
                f"{expected_high_budget}"
            )

    started = time.time()
    determinism = configure_process_determinism(seed=42, mode="strict")
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok" or latent_manifest.get("partitions") != [
        args.partition
    ]:
        raise RuntimeError(
            f"latent manifest is not the completed {args.partition} cache"
        )
    if sha256_file(args.latent_h5) != latent_manifest["output_h5_sha256"]:
        raise RuntimeError(f"{args.partition} latent cache does not match its manifest")
    if sha256_file(args.partition_manifest) != latent_manifest[
        "partition_manifest_sha256"
    ]:
        raise RuntimeError(
            f"partition manifest does not match the {args.partition} latent cache"
        )
    if sha256_file(args.checkpoint_file) != latent_manifest["checkpoint_sha256"]:
        raise RuntimeError(f"checkpoint does not match the {args.partition} latent cache")

    with h5py.File(args.latent_h5, "r") as handle:
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        cache_episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        cache_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
        latent_np = np.asarray(handle["latent"][:], dtype=np.float32)
    if (
        cache_rows.ndim != 1
        or latent_np.ndim != 2
        or len(cache_rows) != len(latent_np)
        or not np.all(cache_rows[1:] > cache_rows[:-1])
        or not np.isfinite(latent_np).all()
    ):
        raise RuntimeError(f"invalid {args.partition} latent cache")

    queries = select_queries(
        manifest_rows=read_tsv(args.partition_manifest),
        cache_rows=cache_rows,
        cache_episode=cache_episode,
        cache_step=cache_step,
        partition=args.partition,
        goal_offset=args.goal_offset,
        pool_count=args.pool_count,
        seed=args.seed,
        hash_namespace=hash_namespace,
        dataset_namespace=dataset_namespace,
    )

    device = torch.device("cuda")
    with force_torch_load_map_location("cuda"):
        model = swm.policy.AutoCostModel(args.policy, cache_dir=args.stablewm_home)
    model = model.to(device).eval()
    model.requires_grad_(False)
    model.interpolate_pos_encoding = True
    latent_action_dim = int(model._infer_latent_action_dim())
    latent_dim = int(latent_np.shape[1])

    final_candidates: list[np.ndarray] = []
    final_costs: list[np.ndarray] = []
    returned_actions: list[np.ndarray] = []
    selected_indices: list[np.ndarray] = []
    selected_actions: list[np.ndarray] = []
    selected_costs: list[np.ndarray] = []
    selected_subgoals: list[np.ndarray] = []
    source_latents: list[np.ndarray] = []
    goal_latents: list[np.ndarray] = []
    solver_checks: list[dict[str, Any]] = []

    for query in queries:
        z_init = torch.from_numpy(
            latent_np[query["source_cache_position"] : query["source_cache_position"] + 1]
        ).to(device)
        z_goal = torch.from_numpy(
            latent_np[query["goal_cache_position"] : query["goal_cache_position"] + 1]
        ).to(device)
        result = run_pool(
            model=model,
            z_init=z_init,
            z_goal=z_goal,
            latent_action_dim=latent_action_dim,
            args=args,
            planner_seed=query["planner_seed"],
        )
        candidates_t = result["candidates"]
        costs_t = result["costs"]
        assert isinstance(candidates_t, torch.Tensor)
        assert isinstance(costs_t, torch.Tensor)
        chosen = selected_candidate_indices(
            num_samples=args.high_num_samples,
            candidate_count=args.candidate_count,
            seed=args.seed,
            pool_id=query["pool_id"],
            hash_namespace=hash_namespace,
            dataset_namespace=dataset_namespace,
        )
        chosen_t = torch.from_numpy(chosen)
        chosen_actions_t = candidates_t.index_select(0, chosen_t)
        chosen_costs_t = costs_t.index_select(0, chosen_t)
        z_init_samples = z_init.unsqueeze(1).expand(1, args.candidate_count, latent_dim)
        first_macro = chosen_actions_t[:, :1, :].to(device).unsqueeze(0)
        z_subgoal = model.rollout_high(z_init_samples, first_macro)[:, :, 0, :]

        if args.repeat_check:
            repeated = run_pool(
                model=model,
                z_init=z_init,
                z_goal=z_goal,
                latent_action_dim=latent_action_dim,
                args=args,
                planner_seed=query["planner_seed"],
            )
            repeated_candidates = repeated["candidates"]
            repeated_costs = repeated["costs"]
            assert isinstance(repeated_candidates, torch.Tensor)
            assert isinstance(repeated_costs, torch.Tensor)
            if not torch.equal(candidates_t, repeated_candidates) or not torch.equal(
                costs_t, repeated_costs
            ):
                raise RuntimeError("same-seed official CEM repeat was not byte-identical")

        final_candidates.append(candidates_t.numpy().astype(np.float32, copy=False))
        final_costs.append(costs_t.numpy().astype(np.float32, copy=False))
        returned = result["returned_action"]
        assert isinstance(returned, torch.Tensor)
        returned_actions.append(returned.numpy().astype(np.float32, copy=False))
        selected_indices.append(chosen)
        selected_actions.append(chosen_actions_t.numpy().astype(np.float32, copy=False))
        selected_costs.append(chosen_costs_t.numpy().astype(np.float32, copy=False))
        selected_subgoals.append(
            z_subgoal[0].detach().cpu().numpy().astype(np.float32, copy=False)
        )
        source_latents.append(z_init[0].detach().cpu().numpy())
        goal_latents.append(z_goal[0].detach().cpu().numpy())
        solver_checks.append(
            {
                "pool_id": query["pool_id"],
                "cost_calls": result["call_count"],
                "elite_mean_vs_returned_max_abs": result["selected_max_abs"],
                "repeat_check": bool(args.repeat_check),
            }
        )
        print(
            json.dumps(
                {
                    "pool_completed": query["pool_id"],
                    "episode_id": query["episode_id"],
                    "source_global_row": query["source_global_row"],
                    "planner_seed": query["planner_seed"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(
        f".{args.output_h5.name}.partial-{os.getpid()}"
    )
    if partial_h5.exists():
        raise RuntimeError(f"refusing to reuse partial output: {partial_h5}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = (
                "development_smoke" if args.smoke else classification
            )
            output.attrs["environment"] = environment
            output.attrs["dataset_namespace"] = dataset_namespace
            output.attrs["partition"] = args.partition
            output.attrs["seed"] = args.seed
            output.attrs["goal_offset_primitive_steps"] = args.goal_offset
            output.create_dataset(
                "pool_id", data=np.asarray([q["pool_id"] for q in queries], dtype=np.int64)
            )
            for key in (
                "episode_id",
                "source_global_row",
                "source_step",
                "goal_global_row",
                "goal_step",
                "planner_seed",
            ):
                output.create_dataset(
                    key, data=np.asarray([q[key] for q in queries], dtype=np.int64)
                )
            output.create_dataset("z_init", data=np.stack(source_latents), compression="gzip")
            output.create_dataset("z_goal", data=np.stack(goal_latents), compression="gzip")
            output.create_dataset(
                "final_candidate_actions", data=np.stack(final_candidates), compression="gzip"
            )
            output.create_dataset("final_nominal_cost", data=np.stack(final_costs), compression="gzip")
            output.create_dataset(
                "official_returned_action", data=np.stack(returned_actions), compression="gzip"
            )
            output.create_dataset("selected_final_index", data=np.stack(selected_indices))
            output.create_dataset(
                "selected_actions", data=np.stack(selected_actions), compression="gzip"
            )
            output.create_dataset(
                "selected_first_macro",
                data=np.stack(selected_actions)[:, :, 0, :],
                compression="gzip",
            )
            output.create_dataset(
                "selected_nominal_cost", data=np.stack(selected_costs), compression="gzip"
            )
            output.create_dataset(
                "selected_z_subgoal", data=np.stack(selected_subgoals), compression="gzip"
            )
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_candidate_pool_retained={partial_h5}", file=sys.stderr)
        raise

    h5_sha256 = sha256_file(args.output_h5)
    manifest = {
        "status": "ok",
        "classification": "development_smoke"
        if args.smoke
        else classification,
        "environment": environment,
        "dataset": dataset_namespace,
        "partition": args.partition,
        "seed": args.seed,
        "query_selection": {
            "hash_namespace": hash_namespace,
            "episode_rule": "first pool_count episodes sorted by domain-separated SHA-256",
            "start_rule": "domain-separated SHA-256 modulo eligible within-episode starts",
            "episode_distinct": True,
            "queries": queries,
        },
        "candidate_selection": {
            "source": "final population from unmodified stable_worldmodel.solver.CEMSolver",
            "rule": "first candidate_count indices sorted by domain-separated SHA-256",
            "candidate_count_per_pool": args.candidate_count,
            "shared_query_within_pool": True,
        },
        "planner": {
            "goal_offset_primitive_steps": args.goal_offset,
            "high_horizon": args.high_horizon,
            "high_action_block": args.high_action_block,
            "latent_action_dim": latent_action_dim,
            "num_samples": args.high_num_samples,
            "n_steps": args.high_iters,
            "topk": args.high_topk,
            "var_scale": 1.0,
            "initial_mean": 0.0,
            "initial_standard_deviation": 1.0,
            "candidate_clipping": False,
            "official_solver_unchanged": True,
        },
        "shapes": {
            "pools": args.pool_count,
            "final_population": list(np.stack(final_candidates).shape),
            "selected_actions": list(np.stack(selected_actions).shape),
            "selected_z_subgoal": list(np.stack(selected_subgoals).shape),
            "latent_dim": latent_dim,
        },
        "solver_checks": solver_checks,
        "repeat_check": bool(args.repeat_check),
        "determinism": determinism,
        "inputs": {
            "policy": args.policy,
            "checkpoint_file": str(args.checkpoint_file),
            "checkpoint_sha256": latent_manifest["checkpoint_sha256"],
            "latent_h5": str(args.latent_h5),
            "latent_h5_sha256": latent_manifest["output_h5_sha256"],
            "latent_manifest_sha256": sha256_file(args.latent_manifest),
            "partition_manifest": str(args.partition_manifest),
            "partition_manifest_sha256": latent_manifest[
                "partition_manifest_sha256"
            ],
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": h5_sha256,
        "runtime": {
            "python": sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "gpu": torch.cuda.get_device_name(device),
        },
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
