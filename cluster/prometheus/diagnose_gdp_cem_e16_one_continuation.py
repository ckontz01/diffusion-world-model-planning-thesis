#!/usr/bin/env python3
"""Run the frozen E16 one-continuation ranking diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

import gdp_cem_e15_specs as e15
import gdp_cem_e16_specs as spec
from acid_alternative.io_utils import resolve_policy_checkpoint
from evaluate_gdp_cem_e15_offline import load_model
from gdp_cem_e15_data import E15ArrayStore, sha256_file
from gdp_cem_e15_models import (
    CosineSchedule,
    VariableVelocityDiffusion,
    action_active_mask,
    bounded_actions_from_standardized_u,
    velocity_ddim_sample,
)
from gdp_cem_e16_models import LatentStateAdapter
from gdp_cem_latent_rollout import rollout_from_single_latent


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"E16 protected path is forbidden: {path}")


def atomic_json(path: Path, value: Any) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def array_sha256(value: np.ndarray | torch.Tensor) -> str:
    if torch.is_tensor(value):
        value = value.detach().cpu().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def selected_diagnostic_rows(store: E15ArrayStore, *, task: str) -> np.ndarray:
    result: list[int] = []
    for delta_value in spec.DIAGNOSTIC_DELTAS:
        rows = store.validation_rows[
            (store.delta[store.validation_rows] == delta_value)
            & (store.tau[store.validation_rows] == spec.TAU)
        ]
        ranked = sorted(
            rows.tolist(),
            key=lambda row: hashlib.sha256(
                (
                    f"{spec.DIAGNOSTIC_ROW_SALT}|task={task}|delta={delta_value}"
                    f"|cache_row={row}"
                ).encode("utf-8")
            ).digest(),
        )
        result.extend(sorted(ranked[: spec.DIAGNOSTIC_ROWS_PER_CELL]))
    value = np.asarray(result, dtype=np.int64)
    if (
        len(value)
        != len(spec.DIAGNOSTIC_DELTAS) * spec.DIAGNOSTIC_ROWS_PER_CELL
        or len(np.unique(value)) != len(value)
        or np.any(store.tau[value] != spec.TAU)
    ):
        raise RuntimeError("invalid E16 one-continuation row selection")
    return value


def deterministic_second_noise(
    *,
    task: str,
    cache_rows: np.ndarray,
    candidates: int,
    dimensions: int,
) -> torch.Tensor:
    """Generate one stateless CPU noise vector per query/first branch."""

    values = np.empty((len(cache_rows), candidates, dimensions), dtype=np.float32)
    for row_position, cache_row in enumerate(cache_rows.tolist()):
        for candidate in range(candidates):
            generator = np.random.default_rng(
                spec.derived_seed(
                    f"stage-b-second-noise|task={task}|cache-row={cache_row}"
                    f"|first-candidate={candidate}"
                )
            )
            values[row_position, candidate] = generator.standard_normal(
                dimensions, dtype=np.float32
            )
    return torch.from_numpy(values)


def verify_adapter(directory: Path, *, task: str) -> tuple[LatentStateAdapter, dict[str, Any]]:
    summary_path = directory / "summary.json"
    checkpoint_path = directory / "final.pt"
    checksum_path = directory / "sha256.txt"
    if not all(path.is_file() for path in (summary_path, checkpoint_path, checksum_path)):
        raise FileNotFoundError("incomplete E16 adapter result")
    records: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        records[name.lstrip("*")] = digest
    if records.get("final.pt") != sha256_file(checkpoint_path) or records.get(
        "summary.json"
    ) != sha256_file(summary_path):
        raise RuntimeError("E16 adapter checksum differs")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("task") != task
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != spec.DIAGNOSTIC_SOURCE_MANIFEST_SHA256
        or summary.get("adapter_gate", {}).get("passed") is not True
        or summary.get("checkpoint_sha256") != sha256_file(checkpoint_path)
    ):
        raise RuntimeError("E16 adapter gate/identity differs")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    architecture = payload.get("architecture", {})
    if (
        payload.get("kind") != "gdp_cem_e16_final_latent_state_adapter"
        or payload.get("task") != task
        or int(payload.get("seed", -1)) != spec.ADAPTER_SEED
        or int(payload.get("final_step", -1)) != spec.ADAPTER_STEPS
        or payload.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or payload.get("source_manifest_sha256")
        != spec.DIAGNOSTIC_SOURCE_MANIFEST_SHA256
        or int(architecture.get("latent_dim", -1)) != spec.LATENT_DIM
        or int(architecture.get("state_dim", -1))
        != int(e15.TASK_SPEC[task]["state_dim"])
        or int(architecture.get("width", -1)) != spec.ADAPTER_WIDTH
    ):
        raise RuntimeError("E16 adapter checkpoint identity differs")
    model = LatentStateAdapter(
        latent_dim=spec.LATENT_DIM,
        state_dim=int(architecture["state_dim"]),
        width=spec.ADAPTER_WIDTH,
    )
    model.load_state_dict(payload["ema_state_dict"], strict=True)
    return model.eval().requires_grad_(False), summary


def verify_stage_a(directory: Path) -> dict[str, Any]:
    audit_path = directory / "STAGE-A-AUDIT.json"
    table_path = directory / "task-first.tsv"
    checksum_path = directory / "sha256.txt"
    if not all(path.is_file() for path in (audit_path, table_path, checksum_path)):
        raise FileNotFoundError("incomplete E16 Stage-A audit")
    records: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        records[name.lstrip("*")] = digest
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        records.get("STAGE-A-AUDIT.json") != sha256_file(audit_path)
        or records.get("task-first.tsv") != sha256_file(table_path)
        or audit.get("status") != "ok"
        or audit.get("exact_e15_replay_all_tasks_passed") is not True
        or audit.get("stage_b_authorized") is not True
        or audit.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or audit.get("source_manifest_sha256")
        != spec.DIAGNOSTIC_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E16 Stage-A audit identity differs")
    return audit


def ordinal_rank(cost: torch.Tensor) -> torch.Tensor:
    if cost.ndim != 2:
        raise ValueError("invalid E16 branch-cost rank")
    order = torch.argsort(cost, dim=1, stable=True)
    rank = torch.empty_like(order)
    position = torch.arange(cost.shape[1], device=cost.device)[None].expand_as(order)
    rank.scatter_(1, order, position)
    return rank


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--training-dir", type=Path, required=True)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--stage-a-dir", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.training_dir,
        args.adapter_dir,
        args.stage_a_dir,
        args.latent_h5,
        args.latent_manifest,
        args.cache_h5,
        args.cache_manifest,
        args.world_model_checkpoint,
        args.stablewm_home,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E16 Stage-B protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E16 Stage-B output")
    if not torch.cuda.is_available():
        raise RuntimeError("E16 Stage-B requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E16 Stage-B GPU model differs")
    verify_stage_a(args.stage_a_dir)
    adapter, adapter_summary = verify_adapter(args.adapter_dir, task=args.task)
    adapter = adapter.to(device)
    task_spec = e15.TASK_SPEC[args.task]
    if (
        args.world_model_policy != task_spec["world_model_policy"]
        or sha256_file(args.world_model_checkpoint)
        != task_spec["world_model_sha256"]
        or resolve_policy_checkpoint(
            args.world_model_policy, args.stablewm_home
        ).resolve()
        != args.world_model_checkpoint.resolve()
    ):
        raise RuntimeError("E16 Stage-B world-model identity differs")

    torch.manual_seed(1617)
    np.random.seed(1617)
    torch.cuda.manual_seed_all(1617)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    store = E15ArrayStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    selected_rows = selected_diagnostic_rows(store, task=args.task)
    selected_set = set(selected_rows.tolist())
    model, model_record = load_model(
        args.training_dir,
        task=args.task,
        condition="vad",
        seed=spec.DIAGNOSTIC_MODEL_SEED,
        store=store,
        device=device,
    )
    if not isinstance(model, VariableVelocityDiffusion):
        raise RuntimeError("E16 Stage-B proposer type differs")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    schedule = CosineSchedule.build(e15.DIFFUSION_STEPS)
    replay_generator = torch.Generator(device=device).manual_seed(
        e15.derived_seed(
            f"offline-gpu|task={args.task}|condition=vad|seed={spec.DIAGNOSTIC_MODEL_SEED}"
        )
    )
    u_mean = torch.from_numpy(store.u_mean).to(device)
    u_std = torch.from_numpy(store.u_std).to(device)
    planner_mean = torch.from_numpy(store.planner_action_mean).to(device)
    planner_std = torch.from_numpy(store.planner_action_std).to(device)
    latent_mean = torch.from_numpy(store.latent_mean).to(device)
    latent_std = torch.from_numpy(store.latent_std).to(device)
    row_to_position = {row: index for index, row in enumerate(selected_rows.tolist())}
    metric_names = (
        "greedy_first_index",
        "continuation_first_index",
        "selection_changed",
        "greedy_first_far_cost",
        "continuation_first_far_cost",
        "greedy_first_local_cost",
        "continuation_first_local_cost",
        "continuation_selected_immediate_far_rank",
        "continuation_selected_immediate_local_rank",
        "continuation_selected_final_far_cost",
        "greedy_branch_final_far_cost",
    )
    metrics = {
        name: np.full(len(selected_rows), np.nan, dtype=np.float64)
        for name in metric_names
    }
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    for delta_value, tau_value in e15.DELTA_TAU_PAIRS:
        cell_rows = store.validation_rows[
            (store.delta[store.validation_rows] == delta_value)
            & (store.tau[store.validation_rows] == tau_value)
        ]
        for start in range(0, len(cell_rows), e15.OFFLINE_BATCH_SIZE):
            rows = cell_rows[start : start + e15.OFFLINE_BATCH_SIZE]
            batch = store.batch(rows)
            tau = batch.tau.to(device)
            active = action_active_mask(
                tau, primitive_action_dim=store.primitive_action_dim
            )
            flat_mask = active.reshape(len(rows), -1)
            noise = torch.randn(
                len(rows),
                e15.CANDIDATE_COUNT,
                flat_mask.shape[1],
                device=device,
                generator=replay_generator,
            ) * flat_mask[:, None]
            selected_in_batch = [i for i, row in enumerate(rows.tolist()) if row in selected_set]
            if not selected_in_batch:
                continue
            if tau_value != spec.TAU or delta_value not in spec.DIAGNOSTIC_DELTAS:
                raise RuntimeError("E16 selected row appeared outside frozen cells")
            current = batch.current.to(device)
            goal = batch.goal.to(device)
            state = batch.state.to(device)
            delta = batch.delta.to(device)
            standard_flat = velocity_ddim_sample(
                model,
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau,
                initial_noise=noise,
                active_mask=flat_mask,
                schedule=schedule,
                evaluations=e15.DIFFUSION_EVALUATIONS,
                guidance_scale=e15.GUIDANCE_SCALE,
            )
            index = torch.as_tensor(selected_in_batch, device=device)
            first_u = standard_flat.reshape(
                len(rows),
                e15.CANDIDATE_COUNT,
                e15.ACTION_HORIZON,
                store.primitive_action_dim,
            )[index, : spec.DIAGNOSTIC_FIRST_CANDIDATES]
            selected_batch_rows = rows[np.asarray(selected_in_batch)]
            selected_batch = store.batch(selected_batch_rows)
            selected_active = action_active_mask(
                selected_batch.tau.to(device),
                primitive_action_dim=store.primitive_action_dim,
            )
            _, first_planner, _ = bounded_actions_from_standardized_u(
                first_u,
                u_mean=u_mean,
                u_std=u_std,
                planner_mean=planner_mean,
                planner_std=planner_std,
                interior_scale=store.interior_scale,
                active_mask=selected_active,
            )
            first_macro = first_planner[:, :, : spec.TAU].reshape(
                len(selected_batch_rows),
                spec.DIAGNOSTIC_FIRST_CANDIDATES,
                spec.TAU // e15.ACTION_BLOCK,
                e15.ACTION_BLOCK * store.primitive_action_dim,
            )
            current_raw = selected_batch.current.to(device) * latent_std + latent_mean
            goal_normalized = selected_batch.goal.to(device)
            goal_raw = goal_normalized * latent_std + latent_mean
            local_raw = selected_batch.local.to(device) * latent_std + latent_mean
            first_terminal = rollout_from_single_latent(
                world_model, current=current_raw, macro_actions=first_macro
            )[:, :, -1]
            immediate_far = (first_terminal - goal_raw[:, None]).square().sum(dim=-1)
            immediate_local = (first_terminal - local_raw[:, None]).square().sum(dim=-1)

            flattened_terminal = first_terminal.reshape(-1, spec.LATENT_DIM)
            second_current = (flattened_terminal - latent_mean) / latent_std
            second_state = adapter(second_current)
            second_goal = goal_normalized[:, None].expand(
                -1, spec.DIAGNOSTIC_FIRST_CANDIDATES, -1
            ).reshape(-1, spec.LATENT_DIM)
            remaining = torch.as_tensor(
                selected_batch.delta.numpy() - spec.TAU,
                device=device,
                dtype=torch.long,
            )[:, None].expand(-1, spec.DIAGNOSTIC_FIRST_CANDIDATES).reshape(-1)
            second_tau = torch.full_like(remaining, spec.TAU)
            second_active = action_active_mask(
                second_tau, primitive_action_dim=store.primitive_action_dim
            )
            second_flat_mask = second_active.reshape(len(remaining), -1)
            keyed_noise = deterministic_second_noise(
                task=args.task,
                cache_rows=selected_batch_rows,
                candidates=spec.DIAGNOSTIC_FIRST_CANDIDATES,
                dimensions=second_flat_mask.shape[1],
            ).to(device).reshape(len(remaining), 1, -1)
            keyed_noise = keyed_noise * second_flat_mask[:, None]
            second_u = velocity_ddim_sample(
                model,
                current=second_current,
                goal=second_goal,
                state=second_state,
                delta=remaining,
                tau=second_tau,
                initial_noise=keyed_noise,
                active_mask=second_flat_mask,
                schedule=schedule,
                evaluations=e15.DIFFUSION_EVALUATIONS,
                guidance_scale=e15.GUIDANCE_SCALE,
            ).reshape(
                len(remaining), 1, e15.ACTION_HORIZON, store.primitive_action_dim
            )
            _, second_planner, _ = bounded_actions_from_standardized_u(
                second_u,
                u_mean=u_mean,
                u_std=u_std,
                planner_mean=planner_mean,
                planner_std=planner_std,
                interior_scale=store.interior_scale,
                active_mask=second_active,
            )
            second_macro = second_planner[:, :, : spec.TAU].reshape(
                len(remaining),
                1,
                spec.TAU // e15.ACTION_BLOCK,
                e15.ACTION_BLOCK * store.primitive_action_dim,
            )
            second_terminal = rollout_from_single_latent(
                world_model, current=flattened_terminal, macro_actions=second_macro
            )[:, 0, -1].reshape(
                len(selected_batch_rows), spec.DIAGNOSTIC_FIRST_CANDIDATES, -1
            )
            final_far = (second_terminal - goal_raw[:, None]).square().sum(dim=-1)
            greedy_index = immediate_far.argmin(dim=1)
            continuation_index = final_far.argmin(dim=1)
            batch_index = torch.arange(len(selected_batch_rows), device=device)
            immediate_far_rank = ordinal_rank(immediate_far)
            immediate_local_rank = ordinal_rank(immediate_local)
            values = {
                "greedy_first_index": greedy_index,
                "continuation_first_index": continuation_index,
                "selection_changed": greedy_index != continuation_index,
                "greedy_first_far_cost": immediate_far[batch_index, greedy_index],
                "continuation_first_far_cost": immediate_far[
                    batch_index, continuation_index
                ],
                "greedy_first_local_cost": immediate_local[
                    batch_index, greedy_index
                ],
                "continuation_first_local_cost": immediate_local[
                    batch_index, continuation_index
                ],
                "continuation_selected_immediate_far_rank": immediate_far_rank[
                    batch_index, continuation_index
                ]
                + 1,
                "continuation_selected_immediate_local_rank": immediate_local_rank[
                    batch_index, continuation_index
                ]
                + 1,
                "continuation_selected_final_far_cost": final_far[
                    batch_index, continuation_index
                ],
                "greedy_branch_final_far_cost": final_far[batch_index, greedy_index],
            }
            positions = np.asarray(
                [row_to_position[row] for row in selected_batch_rows.tolist()]
            )
            for name, value in values.items():
                metrics[name][positions] = value.double().cpu().numpy()

    if any(not np.isfinite(value).all() for value in metrics.values()):
        raise RuntimeError("E16 Stage-B contains missing metrics")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "metrics.h5"
    partial = metrics_path.with_name(f".{metrics_path.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as handle:
            handle.create_dataset("cache_row", data=selected_rows, compression="lzf")
            handle.create_dataset(
                "episode_idx", data=store.episode[selected_rows], compression="lzf"
            )
            handle.create_dataset(
                "delta", data=store.delta[selected_rows], compression="lzf"
            )
            handle.create_dataset(
                "tau", data=store.tau[selected_rows], compression="lzf"
            )
            group = handle.create_group("metrics")
            for name, value in metrics.items():
                group.create_dataset(name, data=value, compression="lzf")
            handle.attrs["task"] = args.task
            handle.attrs["protocol_sha256"] = spec.PROTOCOL_SHA256
        os.replace(partial, metrics_path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e16_one_continuation_diagnostic",
        "analysis_role": "outcome_informed_P1_validation_diagnostic",
        "task": args.task,
        "rows": len(selected_rows),
        "rows_per_cell": spec.DIAGNOSTIC_ROWS_PER_CELL,
        "deltas": list(spec.DIAGNOSTIC_DELTAS),
        "tau": spec.TAU,
        "first_candidates": spec.DIAGNOSTIC_FIRST_CANDIDATES,
        "continuations_per_first": spec.DIAGNOSTIC_CONTINUATIONS,
        "selected_rows_sha256": array_sha256(selected_rows),
        "adapter_summary_sha256": sha256_file(args.adapter_dir / "summary.json"),
        "adapter_checkpoint_sha256": adapter_summary["checkpoint_sha256"],
        "stage_a_audit_sha256": sha256_file(
            args.stage_a_dir / "STAGE-A-AUDIT.json"
        ),
        "model": model_record,
        "metrics_h5": str(metrics_path),
        "metrics_h5_sha256": sha256_file(metrics_path),
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "runtime": {
            "python": platform.python_version(),
            "torch": metadata.version("torch"),
            "numpy": metadata.version("numpy"),
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
        },
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    summary_path = args.output_dir / "summary.json"
    atomic_json(summary_path, summary)
    (args.output_dir / "sha256.txt").write_text(
        f"{sha256_file(metrics_path)}  metrics.h5\n"
        f"{sha256_file(summary_path)}  summary.json\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
