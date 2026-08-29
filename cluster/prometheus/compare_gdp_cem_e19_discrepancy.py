#!/usr/bin/env python3
"""Compare E19 LeWM loading and PushT transports on frozen real-input banks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import h5py
import hydra
import numpy as np
import torch
from omegaconf import OmegaConf

import gdp_cem_e19_discrepancy_specs as diagnostic_spec
import gdp_cem_e19_specs as e19_spec
from trace_gdp_cem_e19_discrepancy import (
    canonical_sha256,
    clone_value,
    value_record,
)


FLAT_DIRS = {
    "pusht": "pusht-22b330c28c27ead4bfd1888615af1340e3fe9052",
    "cube": "cube-b0747c5002e86d2ce8f3cd8178004b97524c587d",
}
OBJECT_FILES = {
    "pusht": "pusht/lewm_hf_22b330c_object.ckpt",
    "cube": "cube/lewm_hf_b0747c5_object.ckpt",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def state_record(model: torch.nn.Module) -> dict[str, Any]:
    state = model.state_dict()
    rows = {
        name: value_record(state[name].detach().cpu()) for name in sorted(state)
    }
    return {
        "model_type": f"{type(model).__module__}.{type(model).__qualname__}",
        "tensor_count": len(rows),
        "state_sha256": canonical_sha256(rows),
        "tensors": rows,
    }


def extract_state_dict(raw: Any) -> dict[str, torch.Tensor]:
    if not isinstance(raw, dict):
        raise TypeError(f"unsupported weights payload {type(raw)}")
    for key in ("state_dict", "model_state_dict", "model", "weights"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return raw


def strip_prefix(state: dict[str, torch.Tensor], prefix: str) -> dict[str, torch.Tensor]:
    return {
        (name[len(prefix) :] if name.startswith(prefix) else name): value
        for name, value in state.items()
    }


def strict_load(model: torch.nn.Module, state: dict[str, torch.Tensor]) -> str:
    attempts = (
        ("as-is", state),
        ("strip module.", strip_prefix(state, "module.")),
        ("strip model.", strip_prefix(state, "model.")),
        (
            "strip model.module.",
            strip_prefix(strip_prefix(state, "model."), "module."),
        ),
    )
    errors = []
    for name, candidate in attempts:
        try:
            model.load_state_dict(candidate, strict=True)
            return name
        except RuntimeError as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError("strict flat-weight load failed\n" + "\n".join(errors))


def load_compat(path: Path):
    import stable_worldmodel as swm

    suffix = "_object.ckpt"
    if not path.name.endswith(suffix):
        raise ValueError(path)
    model = swm.policy.AutoCostModel(str(path)[: -len(suffix)])
    return model.eval().requires_grad_(False)


def load_official_runtime(config: Path, weights: Path):
    cfg = OmegaConf.load(str(config))
    model = hydra.utils.instantiate(cfg)
    if not isinstance(model, torch.nn.Module):
        raise TypeError(f"official config produced {type(model)}")
    strategy = strict_load(
        model,
        extract_state_dict(
            torch.load(weights, map_location="cpu", weights_only=True)
        ),
    )
    return model.eval().requires_grad_(False), strategy


def move_tensor(value: torch.Tensor, device: torch.device, dtype: torch.dtype):
    target_dtype = dtype if value.is_floating_point() else None
    return value.to(device=device, dtype=target_dtype)


def task_latents(
    task: str, model: torch.nn.Module, info: dict[str, Any], device: torch.device
) -> tuple[torch.Tensor, torch.Tensor]:
    dtype = next(model.parameters()).dtype
    if task == "pusht":
        from sage.runtime.lewm import image_batch_to_lewm

        history = info["_proposal_pixels_raw"]
        if not torch.is_tensor(history):
            history = torch.as_tensor(history)
        if history.ndim == 6:
            history = history[:, 0]
        if history.shape[-1] in {1, 3, 4}:
            history = history.permute(0, 1, 4, 2, 3)
        history = image_batch_to_lewm(history, 224).to(device=device, dtype=dtype)
        history_latent = model.encode({"pixels": history})["emb"].float()
        goal = info["goal"]
        if goal.ndim == 6:
            goal = goal[:, 0]
        goal = move_tensor(goal, device, dtype)
        goal_latent = model.encode({"pixels": goal})["emb"].float()
        return history_latent, goal_latent

    from sage.runtime.lewm import encode_lewm_context

    history = info.get("prior_pixels", info["pixels"])
    if not torch.is_tensor(history):
        history = torch.as_tensor(history)
    history = move_tensor(history, device, dtype)
    if history.ndim == 6:
        history = history[:, 0]
    if history.ndim == 4:
        history = history[:, None]
    goal = info["goal"]
    if not torch.is_tensor(goal):
        goal = torch.as_tensor(goal)
    goal = move_tensor(goal, device, dtype)
    if goal.ndim == 6:
        goal = goal[:, 0]
    if goal.ndim == 4:
        goal = goal[:, None]
    return (
        encode_lewm_context(model, history[:, -3:]),
        encode_lewm_context(model, goal[:, -1:]),
    )


def expanded_cost_info(
    task: str,
    info: dict[str, Any],
    count: int,
    device: torch.device,
    dtype: torch.dtype,
    goal_latent: torch.Tensor,
) -> dict[str, Any]:
    expanded: dict[str, Any] = {}
    for key, value in info.items():
        if key.startswith("_") or (task == "cube" and key == "prior_pixels"):
            continue
        if torch.is_tensor(value):
            value = move_tensor(value, device, dtype)
            expanded[key] = value[:, None].expand(
                value.size(0), int(count), *value.shape[1:]
            )
        elif isinstance(value, np.ndarray):
            expanded[key] = np.repeat(value[:, None], int(count), axis=1)
        else:
            expanded[key] = value
    expanded["goal_emb"] = goal_latent
    return expanded


@torch.inference_mode()
def score_fixed_bank(
    *,
    task: str,
    model: torch.nn.Module,
    info: dict[str, Any],
    candidates: torch.Tensor,
    goal_latent: torch.Tensor,
    device: torch.device,
) -> torch.Tensor:
    dtype = next(model.parameters()).dtype
    candidates = move_tensor(candidates, device, dtype)
    if task == "pusht":
        expanded = expanded_cost_info(
            task, info, int(candidates.size(1)), device, dtype, goal_latent
        )
        return model.get_cost(expanded, candidates.detach().clone()).float()

    outputs = []
    for start in range(0, int(candidates.size(1)), 64):
        end = min(start + 64, int(candidates.size(1)))
        expanded = expanded_cost_info(
            task, info, end - start, device, dtype, goal_latent
        )
        outputs.append(
            model.get_cost(
                expanded, candidates[:, start:end].detach().clone()
            )
            .float()
            .cpu()
        )
    return torch.cat(outputs, dim=1).to(device)


@torch.inference_mode()
def runtime_bank_comparison(
    *,
    sentinel: diagnostic_spec.Sentinel,
    bank: dict[str, Any],
    compatibility: torch.nn.Module,
    official: torch.nn.Module,
    device: torch.device,
) -> dict[str, Any]:
    info = bank["info"]
    if "candidates" in bank:
        candidates = bank["candidates"]
    else:
        candidates = bank["top_actions"][:, None]
    compatibility = compatibility.to(device).to(torch.bfloat16)
    official = official.to(device).to(torch.bfloat16)
    compat_history, compat_goal = task_latents(
        sentinel.benchmark, compatibility, info, device
    )
    official_history, official_goal = task_latents(
        sentinel.benchmark, official, info, device
    )
    candidates = move_tensor(candidates, device, next(compatibility.parameters()).dtype)
    count = int(candidates.size(1))
    fixed_goal = bank["actual_local_goal"].to(device)
    compat_cost = score_fixed_bank(
        task=sentinel.benchmark,
        model=compatibility,
        info=info,
        candidates=candidates,
        goal_latent=fixed_goal,
        device=device,
    )
    official_cost = score_fixed_bank(
        task=sentinel.benchmark,
        model=official,
        info=info,
        candidates=candidates,
        goal_latent=fixed_goal,
        device=device,
    )
    compat_order = torch.argsort(compat_cost, dim=1)
    official_order = torch.argsort(official_cost, dim=1)
    elite_count = min(diagnostic_spec.PLANNER["elites"], count)
    compat_elite = torch.topk(
        compat_cost, elite_count, dim=1, largest=False
    ).indices
    official_elite = torch.topk(
        official_cost, elite_count, dim=1, largest=False
    ).indices
    source_cost_exact = (
        torch.equal(compat_cost.cpu(), bank["costs"].float())
        if "costs" in bank
        else True
    )
    checks = {
        "history_latents_exact": torch.equal(compat_history, official_history),
        "goal_latents_exact": torch.equal(compat_goal, official_goal),
        "costs_exact": torch.equal(compat_cost, official_cost),
        "candidate_order_exact": torch.equal(compat_order, official_order),
        "elite_indices_exact": torch.equal(compat_elite, official_elite),
        "finite": bool(
            torch.isfinite(compat_cost).all() and torch.isfinite(official_cost).all()
        ),
    }
    return {
        "sentinel_id": sentinel.sentinel_id,
        "benchmark": sentinel.benchmark,
        "method": sentinel.method,
        "bank_content_sha256": bank["content_sha256"],
        "history_compatibility": value_record(compat_history),
        "history_official": value_record(official_history),
        "goal_compatibility": value_record(compat_goal),
        "goal_official": value_record(official_goal),
        "fixed_actual_local_goal": value_record(fixed_goal),
        "cost_compatibility": value_record(compat_cost),
        "cost_official": value_record(official_cost),
        "order_compatibility": value_record(compat_order),
        "order_official": value_record(official_order),
        "elite_compatibility": value_record(compat_elite),
        "elite_official": value_record(official_elite),
        "compatibility_cost_matches_e19_bank": source_cost_exact,
        "bank_reconstruction_valid": source_cost_exact,
        "checks": checks,
        "runtime_mismatch": not all(checks.values()),
    }


def to_chw(images: Any) -> np.ndarray:
    value = np.asarray(images)
    if value.ndim != 4:
        raise ValueError(f"expected image batch, got {value.shape}")
    if value.shape[-1] in {1, 3, 4}:
        value = np.transpose(value, (0, 3, 1, 2))
    if value.shape[1] not in {1, 3, 4}:
        raise ValueError(f"cannot identify channel axis in {value.shape}")
    return np.ascontiguousarray(value)


def load_manifest_images(
    *,
    manifest: dict[str, Any],
    horizon: int,
    hdf5_path: Path,
    lance_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    import stable_worldmodel as swm

    episodes = np.asarray([int(row["episode_id"]) for row in manifest["records"]])
    starts = np.asarray([int(row["start_frame"]) for row in manifest["records"]])
    with h5py.File(hdf5_path, "r") as handle:
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64)
    start_rows = offsets[episodes] + starts
    goal_rows = start_rows + int(horizon)
    h5_dataset = swm.data.load_dataset(str(hdf5_path))
    lance_dataset = swm.data.load_dataset(str(lance_path))
    h5_start = to_chw(h5_dataset.get_row_data(start_rows.tolist())["pixels"])
    h5_goal = to_chw(h5_dataset.get_row_data(goal_rows.tolist())["pixels"])

    def decoded(rows: np.ndarray) -> np.ndarray:
        values = lance_dataset.get_row_data(rows.tolist())["pixels"]
        if isinstance(values, np.ndarray) and values.dtype == object:
            values = values.tolist()
        return to_chw(lance_dataset._decode_images(values).numpy())

    return h5_start, h5_goal, decoded(start_rows), decoded(goal_rows)


def prepared_images(images: np.ndarray) -> torch.Tensor:
    from sage.eval.pusht import image_transform

    transform = image_transform(224, torch.bfloat16)
    return torch.stack([transform(torch.from_numpy(row)) for row in images])


def replace_first_plan_images(
    info: dict[str, Any], current: np.ndarray, goal: np.ndarray
) -> dict[str, Any]:
    output = clone_value(info)
    current_prepared = prepared_images(current)
    goal_prepared = prepared_images(goal)
    for key, prepared in (("pixels", current_prepared), ("goal", goal_prepared)):
        template = output[key]
        if template.ndim == 4:
            replacement = prepared
        elif template.ndim == 5:
            replacement = prepared[:, None].expand(-1, template.size(1), -1, -1, -1)
        else:
            raise ValueError(f"unexpected {key} shape {tuple(template.shape)}")
        output[key] = replacement.contiguous()
    raw = output["_proposal_pixels_raw"]
    if raw.shape[-1] in {1, 3, 4}:
        source = torch.from_numpy(np.transpose(current, (0, 2, 3, 1)))
        replacement = source[:, None].expand(-1, raw.shape[1], -1, -1, -1)
    else:
        source = torch.from_numpy(current)
        replacement = source[:, None].expand(-1, raw.shape[1], -1, -1, -1)
    output["_proposal_pixels_raw"] = replacement.contiguous()
    return output


def rank_positions(costs: torch.Tensor) -> torch.Tensor:
    order = torch.argsort(costs, dim=1)
    positions = torch.empty_like(order)
    values = torch.arange(order.size(1), device=order.device).expand_as(order)
    positions.scatter_(1, order, values)
    return positions


def mean_spearman(left: torch.Tensor, right: torch.Tensor) -> float:
    count = int(left.size(1))
    if count < 2:
        return 1.0
    delta = (rank_positions(left) - rank_positions(right)).double()
    rho = 1.0 - 6.0 * delta.square().sum(1) / (count * (count * count - 1))
    return float(rho.mean().item())


@torch.inference_mode()
def score_pusht_variant(
    *,
    model: torch.nn.Module,
    info: dict[str, Any],
    candidates: torch.Tensor,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    history, goal = task_latents("pusht", model, info, device)
    dtype = next(model.parameters()).dtype
    candidates = move_tensor(candidates, device, dtype)
    expanded = expanded_cost_info(
        "pusht", info, int(candidates.size(1)), device, dtype, goal
    )
    costs = model.get_cost(expanded, candidates.detach().clone()).float()
    return history, goal, costs


@torch.inference_mode()
def transport_comparison(
    *,
    sentinel: diagnostic_spec.Sentinel,
    bank: dict[str, Any],
    model: torch.nn.Module,
    manifest: dict[str, Any],
    hdf5_path: Path,
    lance_path: Path,
    device: torch.device,
) -> dict[str, Any]:
    if "candidates" not in bank:
        raise ValueError("transport CEM comparison requires a candidate bank")
    h5_start, h5_goal, jpeg_start, jpeg_goal = load_manifest_images(
        manifest=manifest,
        horizon=sentinel.horizon,
        hdf5_path=hdf5_path,
        lance_path=lance_path,
    )
    jpeg_info = replace_first_plan_images(bank["info"], jpeg_start, jpeg_goal)
    lossless_info = replace_first_plan_images(bank["info"], h5_start, h5_goal)
    model = model.to(device).to(torch.bfloat16)
    jpeg_history, jpeg_goal_latent, jpeg_cost = score_pusht_variant(
        model=model,
        info=jpeg_info,
        candidates=bank["candidates"],
        device=device,
    )
    lossless_history, lossless_goal_latent, lossless_cost = score_pusht_variant(
        model=model,
        info=lossless_info,
        candidates=bank["candidates"],
        device=device,
    )
    bank_cost = bank["costs"].float()
    jpeg_order = torch.argsort(jpeg_cost, dim=1)
    lossless_order = torch.argsort(lossless_cost, dim=1)
    jpeg_elite = torch.topk(jpeg_cost, 30, dim=1, largest=False).indices
    lossless_elite = torch.topk(lossless_cost, 30, dim=1, largest=False).indices
    bank_elite = bank["elite_indices"].long()
    elite_set_equal = []
    for row in range(jpeg_elite.size(0)):
        elite_set_equal.append(
            set(jpeg_elite[row].cpu().tolist())
            == set(lossless_elite[row].cpu().tolist())
        )
    pixels = np.concatenate((h5_start, h5_goal), axis=0).astype(np.int16)
    jpeg_pixels = np.concatenate((jpeg_start, jpeg_goal), axis=0).astype(np.int16)
    pixel_delta = np.abs(pixels - jpeg_pixels)
    source_matches_bank = {
        "proposal_pixels": canonical_sha256(jpeg_info["_proposal_pixels_raw"])
        == canonical_sha256(bank["info"]["_proposal_pixels_raw"]),
        "pixels": canonical_sha256(jpeg_info["pixels"])
        == canonical_sha256(bank["info"]["pixels"]),
        "goal": canonical_sha256(jpeg_info["goal"])
        == canonical_sha256(bank["info"]["goal"]),
        "costs": torch.equal(jpeg_cost.cpu(), bank_cost),
        "elite_indices": torch.equal(jpeg_elite.cpu(), bank_elite),
    }
    valid = all(source_matches_bank.values())
    return {
        "sentinel_id": sentinel.sentinel_id,
        "method": sentinel.method,
        "manifest_record_count": len(manifest["records"]),
        "pixel_mean_absolute_error": float(pixel_delta.mean()),
        "pixel_maximum_absolute_error": int(pixel_delta.max()),
        "jpeg_history_latents": value_record(jpeg_history),
        "lossless_history_latents": value_record(lossless_history),
        "jpeg_goal_latents": value_record(jpeg_goal_latent),
        "lossless_goal_latents": value_record(lossless_goal_latent),
        "jpeg_costs": value_record(jpeg_cost),
        "lossless_costs": value_record(lossless_cost),
        "jpeg_order": value_record(jpeg_order),
        "lossless_order": value_record(lossless_order),
        "jpeg_elites": value_record(jpeg_elite),
        "lossless_elites": value_record(lossless_elite),
        "history_latents_exact": torch.equal(jpeg_history, lossless_history),
        "goal_latents_exact": torch.equal(jpeg_goal_latent, lossless_goal_latent),
        "costs_exact": torch.equal(jpeg_cost, lossless_cost),
        "candidate_order_exact": torch.equal(jpeg_order, lossless_order),
        "mean_spearman_rank_correlation": mean_spearman(jpeg_cost, lossless_cost),
        "elite_set_equal_by_environment": elite_set_equal,
        "elite_membership_changed_environment_count": elite_set_equal.count(False),
        "source_matches_e19_bank": source_matches_bank,
        "comparison_valid": valid,
        "transport_mismatch": valid and not all(elite_set_equal),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--stablewm-root", type=Path, required=True)
    parser.add_argument("--flat-root", type=Path, required=True)
    parser.add_argument("--pusht-hdf5", type=Path, required=True)
    parser.add_argument("--pusht-lance", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("A6000 comparison requested without CUDA")

    models: dict[str, tuple[torch.nn.Module, torch.nn.Module]] = {}
    model_audits = {}
    for task in e19_spec.BENCHMARKS:
        flat = args.flat_root / FLAT_DIRS[task]
        config = flat / "config.json"
        weights = flat / "weights.pt"
        expected = e19_spec.TASKS[task]
        if sha256_file(config) != expected["lewm_config_sha256"]:
            raise RuntimeError(f"{task} config hash mismatch")
        if sha256_file(weights) != expected["lewm_weights_sha256"]:
            raise RuntimeError(f"{task} weights hash mismatch")
        object_path = args.stablewm_root / OBJECT_FILES[task]
        if sha256_file(object_path) != expected["e18_object_sha256"]:
            raise RuntimeError(f"{task} compatibility-object hash mismatch")
        compatibility = load_compat(object_path)
        official, strategy = load_official_runtime(config, weights)
        compat_state = state_record(compatibility)
        official_state = state_record(official)
        state_exact = compat_state["tensors"] == official_state["tensors"]
        model_audits[task] = {
            "compatibility_object": str(object_path),
            "compatibility_object_sha256": sha256_file(object_path),
            "flat_config": str(config),
            "flat_config_sha256": sha256_file(config),
            "flat_weights": str(weights),
            "flat_weights_sha256": sha256_file(weights),
            "strict_load_strategy": strategy,
            "compatibility_state": compat_state,
            "official_state": official_state,
            "state_exact": state_exact,
        }
        models[task] = (compatibility, official)

    runtime_rows = []
    for sentinel in diagnostic_spec.SENTINELS:
        bank_path = (
            args.run_root
            / "sentinels"
            / f"s{sentinel.sentinel_id}"
            / "r0"
            / "comparison-bank.pt"
        )
        bank = torch.load(bank_path, map_location="cpu", weights_only=False)
        if canonical_sha256({key: value for key, value in bank.items() if key != "content_sha256"}) != bank["content_sha256"]:
            raise RuntimeError(f"bank content hash mismatch: {bank_path}")
        runtime_rows.append(
            runtime_bank_comparison(
                sentinel=sentinel,
                bank=bank,
                compatibility=models[sentinel.benchmark][0],
                official=models[sentinel.benchmark][1],
                device=device,
            )
        )

    transport_rows = []
    for sentinel in diagnostic_spec.SENTINELS:
        if sentinel.benchmark != "pusht" or sentinel.method not in {
            "base_cem",
            "far_goal_prior_cem",
        }:
            continue
        bank_path = (
            args.run_root
            / "sentinels"
            / f"s{sentinel.sentinel_id}"
            / "r0"
            / "comparison-bank.pt"
        )
        bank = torch.load(bank_path, map_location="cpu", weights_only=False)
        manifest_path = (
            args.snapshot
            / "official-sage"
            / "data"
            / "manifests"
            / "pusht"
            / f"seed{sentinel.seed}"
            / f"h{sentinel.horizon}.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        transport_rows.append(
            transport_comparison(
                sentinel=sentinel,
                bank=bank,
                model=models["pusht"][0],
                manifest=manifest,
                hdf5_path=args.pusht_hdf5,
                lance_path=args.pusht_lance,
                device=device,
            )
        )

    payload = {
        "kind": "gdp_cem_e19_official_sage_discrepancy_comparison",
        "diagnostic_source_manifest_sha256": sha256_file(
            args.snapshot / "SOURCE-MANIFEST.sha256"
        ),
        "diagnostic_protocol_sha256": sha256_file(
            args.snapshot / diagnostic_spec.PROTOCOL_FILENAME
        ),
        "e19_source_manifest_sha256": diagnostic_spec.E19_SOURCE_MANIFEST_SHA256,
        "e19_protocol_sha256": diagnostic_spec.E19_PROTOCOL_SHA256,
        "official_sage_commit": diagnostic_spec.SAGE_GIT_COMMIT,
        "official_sage_tree": diagnostic_spec.SAGE_GIT_TREE,
        "model_load_audits": model_audits,
        "runtime_real_bank_comparisons": runtime_rows,
        "pusht_transport_comparisons": transport_rows,
        "model_state_mismatch": not all(
            row["state_exact"] for row in model_audits.values()
        ),
        "runtime_mismatch": any(row["runtime_mismatch"] for row in runtime_rows),
        "runtime_bank_reconstruction_valid": all(
            row["bank_reconstruction_valid"] for row in runtime_rows
        ),
        "transport_mismatch": any(row["transport_mismatch"] for row in transport_rows),
        "transport_comparisons_valid": all(
            row["comparison_valid"] for row in transport_rows
        ),
        "episode_executed": False,
        "official_sage_source_modified": False,
        "checkpoint_modified": False,
        "planner_parameter_modified": False,
        "expected_values_modified": False,
        "tolerance_modified": False,
        "manifest_modified": False,
        "e19_result_modified": False,
        "protected_metric_artifact_read": False,
        "e18_vs_sage_comparison_run": False,
        "d5_read": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
