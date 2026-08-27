#!/usr/bin/env python3
"""Build the frozen P1 E17 action-conditioned transition-state cache."""

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
import gdp_cem_e17_specs as spec
from acid_alternative.io_utils import resolve_policy_checkpoint
from gdp_cem_e15_data import sha256_file
from gdp_cem_latent_rollout import rollout_from_single_latent


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p2", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"E17 protected path is forbidden: {path}")


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


def select_unique_transition_rows(
    *,
    role: np.ndarray,
    source: np.ndarray,
    local: np.ndarray,
    raw_row: np.ndarray,
    episode: np.ndarray,
    step: np.ndarray,
    tau: np.ndarray,
    state: np.ndarray,
    action_raw: np.ndarray,
    action_mask: np.ndarray,
) -> np.ndarray:
    """Collapse far-goal duplicates only after exact transition agreement."""

    arrays = (role, source, local, raw_row, episode, step, tau)
    if any(value.ndim != 1 for value in arrays) or len({len(v) for v in arrays}) != 1:
        raise ValueError("invalid E17 transition-key arrays")
    if (
        state.ndim != 2
        or action_raw.ndim != 3
        or action_mask.ndim != 2
        or len(state) != len(role)
        or len(action_raw) != len(role)
        or len(action_mask) != len(role)
    ):
        raise ValueError("invalid E17 transition payload arrays")
    order = np.lexsort((tau, source, role)).astype(np.int64)
    same = (
        (role[order[1:]] == role[order[:-1]])
        & (source[order[1:]] == source[order[:-1]])
        & (tau[order[1:]] == tau[order[:-1]])
    )
    left = order[:-1][same]
    right = order[1:][same]
    for name, value in (
        ("local", local),
        ("raw_row", raw_row),
        ("episode", episode),
        ("step", step),
    ):
        if np.any(value[left] != value[right]):
            raise RuntimeError(f"E17 duplicate transition differs: {name}")
    for name, value in (
        ("state", state),
        ("action_raw", action_raw),
        ("action_mask", action_mask),
    ):
        if np.any(value[left] != value[right]):
            raise RuntimeError(f"E17 duplicate transition payload differs: {name}")
    start = np.concatenate((np.asarray([True]), ~same))
    selected = order[start]
    if (
        len(selected) == 0
        or set(np.unique(role[selected]).tolist()) != {0, 1}
        or len(selected)
        != len({(int(role[r]), int(source[r]), int(tau[r])) for r in selected})
    ):
        raise RuntimeError("invalid E17 unique transition selection")
    return selected.astype(np.int64)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--e16-stage-a-audit", type=Path, required=True)
    parser.add_argument("--e16-task-first", type=Path, required=True)
    parser.add_argument("--e16-adapter-summary", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.dataset,
        args.latent_h5,
        args.latent_manifest,
        args.cache_h5,
        args.cache_manifest,
        args.world_model_checkpoint,
        args.stablewm_home,
        args.e16_stage_a_audit,
        args.e16_task_first,
        args.e16_adapter_summary,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_h5, args.output_json):
        reject_protected_path(path)
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite E17 transition-state cache")
    checksum_path = args.output_json.parent / "sha256.txt"
    if args.output_h5.parent != args.output_json.parent or checksum_path.exists():
        raise SystemExit("E17 cache outputs must share one unused directory")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E17 protocol hash differs")
    if not torch.cuda.is_available():
        raise RuntimeError("E17 transition-cache build requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E17 cache-builder GPU model differs")

    task_spec = spec.TASK_SPEC[args.task]
    input_hashes = {
        "dataset_sha256": sha256_file(args.dataset),
        "latent_h5_sha256": sha256_file(args.latent_h5),
        "latent_manifest_sha256": sha256_file(args.latent_manifest),
        "cache_h5_sha256": sha256_file(args.cache_h5),
        "cache_manifest_sha256": sha256_file(args.cache_manifest),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "e16_stage_a_audit_sha256": sha256_file(args.e16_stage_a_audit),
        "e16_task_first_sha256": sha256_file(args.e16_task_first),
        "e16_adapter_summary_sha256": sha256_file(args.e16_adapter_summary),
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest_sha256": sha256_file(args.source_manifest),
    }
    expected_hashes = {
        "dataset_sha256": task_spec["dataset_sha256"],
        "latent_h5_sha256": task_spec["latent_sha256"],
        "latent_manifest_sha256": task_spec["latent_manifest_sha256"],
        "cache_h5_sha256": task_spec["e15_cache_sha256"],
        "cache_manifest_sha256": task_spec["e15_cache_manifest_sha256"],
        "world_model_checkpoint_sha256": task_spec["world_model_sha256"],
        "e16_stage_a_audit_sha256": spec.E16_STAGE_A_AUDIT_SHA256,
        "e16_task_first_sha256": spec.E16_TASK_FIRST_SHA256,
        "e16_adapter_summary_sha256": spec.E16_ADAPTER_SUMMARY_SHA256[args.task],
        "protocol_sha256": spec.PROTOCOL_SHA256,
    }
    for name, expected in expected_hashes.items():
        if input_hashes[name] != expected:
            raise RuntimeError(f"E17 pinned input hash differs: {name}")
    if (
        args.world_model_policy != task_spec["world_model_policy"]
        or resolve_policy_checkpoint(
            args.world_model_policy, args.stablewm_home
        ).resolve()
        != args.world_model_checkpoint.resolve()
    ):
        raise RuntimeError("E17 released world-model identity differs")

    cache_record = json.loads(args.cache_manifest.read_text(encoding="utf-8"))
    latent_record = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    e16_audit = json.loads(args.e16_stage_a_audit.read_text(encoding="utf-8"))
    e16_adapter = json.loads(args.e16_adapter_summary.read_text(encoding="utf-8"))
    if (
        cache_record.get("status") != "ok"
        or cache_record.get("kind")
        != "gdp_cem_e15_episode_disjoint_bounded_action_p1_cache"
        or cache_record.get("task") != args.task
        or cache_record.get("p2_read") is not False
        or cache_record.get("d5_read") is not False
        or latent_record.get("status") != "ok"
        or latent_record.get("output_h5_sha256")
        != input_hashes["latent_h5_sha256"]
        or e16_audit.get("status") != "ok"
        or e16_audit.get("exact_e15_replay_all_tasks_passed") is not True
        or e16_audit.get("claim_allowed") is not False
        or e16_adapter.get("status") != "ok"
        or e16_adapter.get("task") != args.task
        or e16_adapter.get("kind")
        != "gdp_cem_e16_latent_state_adapter_training_and_gate"
        or e16_adapter.get("claim_allowed") is not False
    ):
        raise RuntimeError("E17 upstream lineage record differs")
    if args.task == "pusht" and e16_adapter["adapter_gate"]["passed"] is not True:
        raise RuntimeError("E17 expected the frozen PushT E16 adapter pass")
    if args.task == "cube" and e16_adapter["adapter_gate"]["passed"] is not False:
        raise RuntimeError("E17 expected the frozen Cube E16 adapter failure")

    started = time.time()
    torch.manual_seed(spec.derived_seed(f"cache|task={args.task}"))
    np.random.seed(spec.derived_seed(f"cache-numpy|task={args.task}") % (2**32))
    torch.cuda.manual_seed_all(spec.derived_seed(f"cache-cuda|task={args.task}"))
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)

    with h5py.File(args.cache_h5, "r") as handle:
        source = np.asarray(handle["source_index"][:], dtype=np.int64)
        local = np.asarray(handle["local_index"][:], dtype=np.int64)
        raw_row = np.asarray(handle["raw_row_index"][:], dtype=np.int64)
        episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        step = np.asarray(handle["step_idx"][:], dtype=np.int64)
        role = np.asarray(handle["role"][:], dtype=np.uint8)
        tau = np.asarray(handle["tau"][:], dtype=np.int64)
        state = np.asarray(handle["state"][:], dtype=np.float32)
        action_raw = np.asarray(
            handle["action_raw_projected"][:], dtype=np.float32
        )
        action_mask = np.asarray(handle["action_mask"][:], dtype=np.bool_)
        latent_mean = np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        latent_std = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        state_mean = np.asarray(handle["stats/state_mean"][:], dtype=np.float32)
        state_std = np.asarray(handle["stats/state_std"][:], dtype=np.float32)
        planner_mean = np.asarray(
            handle["stats/planner_primitive_action_mean"][:], dtype=np.float32
        )
        planner_std = np.asarray(
            handle["stats/planner_primitive_action_std"][:], dtype=np.float32
        )
    expected_mask = np.arange(spec.ACTION_HORIZON)[None] < tau[:, None]
    if (
        len(role) != e15.TRAIN_ROWS + e15.VALIDATION_ROWS
        or state.shape != (len(role), int(task_spec["state_dim"]))
        or action_raw.shape
        != (
            len(role),
            spec.ACTION_HORIZON,
            int(task_spec["primitive_action_dim"]),
        )
        or action_mask.shape != expected_mask.shape
        or not np.array_equal(action_mask, expected_mask)
        or np.any(action_raw[~action_mask] != 0)
        or np.any(planner_std <= 0)
    ):
        raise RuntimeError("E17 upstream cache arrays differ")

    selected = select_unique_transition_rows(
        role=role,
        source=source,
        local=local,
        raw_row=raw_row,
        episode=episode,
        step=step,
        tau=tau,
        state=state,
        action_raw=action_raw,
        action_mask=action_mask,
    )
    selected_role = role[selected]
    train_count = int(np.count_nonzero(selected_role == 0))
    validation_count = int(np.count_nonzero(selected_role == 1))
    if (
        not np.all(selected_role[:train_count] == 0)
        or not np.all(selected_role[train_count:] == 1)
        or train_count == 0
        or validation_count == 0
        or set(episode[selected][selected_role == 0]).intersection(
            set(episode[selected][selected_role == 1])
        )
    ):
        raise RuntimeError("E17 selected role ordering or episode split differs")

    with h5py.File(args.latent_h5, "r") as handle:
        latent = np.asarray(handle["latent"][:], dtype=np.float32)
        latent_row = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent_episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        latent_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
    state_key = str(task_spec["state_key"])
    with h5py.File(args.dataset, "r") as handle:
        raw_state = np.asarray(handle[state_key][:], dtype=np.float32)
        episode_key = "episode_idx" if "episode_idx" in handle else "ep_idx"
        raw_episode = np.asarray(handle[episode_key][:], dtype=np.int64)
        raw_step = np.asarray(handle["step_idx"][:], dtype=np.int64)

    source_selected = source[selected]
    local_selected = local[selected]
    raw_selected = raw_row[selected]
    tau_selected = tau[selected]
    next_raw_row = raw_selected + tau_selected
    if (
        np.any(source_selected < 0)
        or np.any(local_selected >= len(latent))
        or np.any(next_raw_row >= len(raw_state))
        or np.any(latent_row[source_selected] != raw_selected)
        or np.any(latent_row[local_selected] != next_raw_row)
        or np.any(latent_episode[source_selected] != episode[selected])
        or np.any(latent_episode[local_selected] != episode[selected])
        or np.any(latent_step[source_selected] != step[selected])
        or np.any(latent_step[local_selected] != step[selected] + tau_selected)
        or np.any(raw_episode[raw_selected] != episode[selected])
        or np.any(raw_episode[next_raw_row] != episode[selected])
        or np.any(raw_step[raw_selected] != step[selected])
        or np.any(raw_step[next_raw_row] != step[selected] + tau_selected)
        or np.any(raw_state[raw_selected] != state[selected])
    ):
        raise RuntimeError("E17 raw/latent transition join differs")

    current_latent_raw = np.ascontiguousarray(latent[source_selected])
    current_latent = np.ascontiguousarray(
        (current_latent_raw - latent_mean) / latent_std, dtype=np.float32
    )
    current_state = np.ascontiguousarray(
        (state[selected] - state_mean) / state_std, dtype=np.float32
    )
    next_state = np.ascontiguousarray(
        (raw_state[next_raw_row] - state_mean) / state_std, dtype=np.float32
    )
    selected_action = np.ascontiguousarray(action_raw[selected])
    selected_mask = np.ascontiguousarray(action_mask[selected])
    del latent, raw_state, state, action_raw, action_mask

    planner_action = selected_action.copy()
    planner_action -= planner_mean[None, None]
    planner_action /= planner_std[None, None]
    terminal_latent_raw = np.empty_like(current_latent_raw)
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    torch.cuda.reset_peak_memory_stats(device)
    with torch.inference_mode():
        for tau_value in spec.TAU_VALUES:
            rows = np.flatnonzero(tau_selected == tau_value).astype(np.int64)
            if len(rows) == 0:
                raise RuntimeError("E17 empty tau cell")
            for start in range(0, len(rows), spec.CACHE_BATCH_SIZE):
                positions = rows[start : start + spec.CACHE_BATCH_SIZE]
                current_batch = torch.from_numpy(
                    current_latent_raw[positions]
                ).to(device)
                action_batch = torch.from_numpy(
                    planner_action[positions, :tau_value]
                ).to(device)
                macro = action_batch.reshape(
                    len(positions),
                    1,
                    tau_value // spec.ACTION_BLOCK,
                    spec.ACTION_BLOCK * int(task_spec["primitive_action_dim"]),
                )
                terminal = rollout_from_single_latent(
                    world_model, current=current_batch, macro_actions=macro
                )[:, 0, -1]
                terminal_latent_raw[positions] = terminal.float().cpu().numpy()
    terminal_latent = np.ascontiguousarray(
        (terminal_latent_raw - latent_mean) / latent_std, dtype=np.float32
    )
    if not all(
        np.isfinite(value).all()
        for value in (
            current_latent,
            terminal_latent,
            current_state,
            next_state,
            selected_action,
        )
    ):
        raise RuntimeError("E17 transition-state cache contains non-finite values")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(
        f".{args.output_h5.name}.partial-{os.getpid()}"
    )
    try:
        with h5py.File(partial, "x") as handle:
            scalar_chunk = min(65_536, len(selected))
            for name, value in (
                ("e15_cache_row", selected),
                ("source_index", source_selected),
                ("local_index", local_selected),
                ("raw_row_index", raw_selected),
                ("episode_idx", episode[selected]),
                ("step_idx", step[selected]),
                ("role", selected_role),
                ("tau", tau_selected),
            ):
                handle.create_dataset(
                    name, data=value, chunks=(scalar_chunk,), compression="lzf"
                )
            vector_chunk = min(4_096, len(selected))
            for name, value in (
                ("current_latent", current_latent),
                ("terminal_latent", terminal_latent),
                ("current_state", current_state),
                ("next_state", next_state),
            ):
                handle.create_dataset(
                    name,
                    data=value,
                    chunks=(vector_chunk, value.shape[1]),
                    compression="lzf",
                )
            handle.create_dataset(
                "action_raw",
                data=selected_action,
                chunks=(
                    vector_chunk,
                    spec.ACTION_HORIZON,
                    int(task_spec["primitive_action_dim"]),
                ),
                compression="lzf",
            )
            handle.create_dataset(
                "action_mask",
                data=selected_mask,
                chunks=(vector_chunk, spec.ACTION_HORIZON),
                compression="lzf",
            )
            stats = handle.create_group("stats")
            for name, value in (
                ("latent_mean", latent_mean),
                ("latent_std", latent_std),
                ("state_mean", state_mean),
                ("state_std", state_std),
                ("planner_primitive_action_mean", planner_mean),
                ("planner_primitive_action_std", planner_std),
            ):
                stats.create_dataset(name, data=value)
            handle.attrs["task"] = args.task
            handle.attrs["protocol_sha256"] = spec.PROTOCOL_SHA256
            handle.attrs["source_manifest_sha256"] = input_hashes[
                "source_manifest_sha256"
            ]
            for name, value in input_hashes.items():
                handle.attrs[f"input_{name}"] = value
        os.replace(partial, args.output_h5)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    counts = {
        f"role={role_value},tau={tau_value}": int(
            np.count_nonzero(
                (selected_role == role_value) & (tau_selected == tau_value)
            )
        )
        for role_value in (0, 1)
        for tau_value in spec.TAU_VALUES
    }
    manifest = {
        "status": "ok",
        "kind": "gdp_cem_e17_action_conditioned_transition_state_cache",
        "analysis_role": "P1_deterministic_feature_transformation_only",
        "task": args.task,
        "rows": int(len(selected)),
        "train_rows": train_count,
        "validation_rows": validation_count,
        "role_tau_counts": counts,
        "original_e15_rows": int(len(role)),
        "collapsed_duplicate_rows": int(len(role) - len(selected)),
        "selected_rows_sha256": array_sha256(selected),
        "terminal_latent_sha256": array_sha256(terminal_latent),
        "input_hashes": input_hashes,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint_sha256": input_hashes[
            "world_model_checkpoint_sha256"
        ],
        "output_h5": str(args.output_h5),
        "output_h5_sha256": sha256_file(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(
            torch.cuda.max_memory_allocated(device)
        ),
        "runtime": {
            "python": platform.python_version(),
            "torch": metadata.version("torch"),
            "numpy": metadata.version("numpy"),
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
        },
        "model_training_performed": False,
        "validation_metrics_computed": False,
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_json, manifest)
    checksum_path.write_text(
        f"{sha256_file(args.output_h5)}  {args.output_h5.name}\n"
        f"{sha256_file(args.output_json)}  {args.output_json.name}\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
