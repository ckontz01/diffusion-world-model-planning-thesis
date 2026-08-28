#!/usr/bin/env python3
"""Audit legacy-pickle mapping without reading any experiment outcome."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch


EXPECTED_MODEL_TYPE = "stable_worldmodel.wm.lewm.lewm.LeWM"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def state_digest(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        value = state[name].detach().cpu().contiguous()
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(value.dtype).encode("ascii") + b"\0")
        digest.update(json.dumps(list(value.shape)).encode("ascii") + b"\0")
        digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def load_object(path: Path):
    import stable_worldmodel as swm

    suffix = "_object.ckpt"
    if not path.name.endswith(suffix):
        raise ValueError(f"not an AutoCostModel object checkpoint: {path}")
    model = swm.policy.AutoCostModel(str(path)[: -len(suffix)])
    model.eval().requires_grad_(False)
    return model


def model_type(model) -> str:
    return f"{type(model).__module__}.{type(model).__qualname__}"


def clone_info(info: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {name: value.detach().clone() for name, value in info.items()}


@torch.inference_mode()
def synthetic_cost_parity(reference, candidate, device: torch.device, seed: int) -> dict:
    reference = reference.to(device).eval()
    candidate = candidate.to(device).eval()
    reference_dtype = next(reference.parameters()).dtype
    candidate_dtype = next(candidate.parameters()).dtype
    if reference_dtype != candidate_dtype:
        raise AssertionError((reference_dtype, candidate_dtype))

    history = int(candidate.predictor.num_frames)
    embedding_dim = int(candidate.predictor.input_dim)
    action_dim = int(candidate.action_encoder.input_dim)
    batch, samples, horizon = 1, 2, history + 2
    generator = torch.Generator(device=device).manual_seed(seed)
    embedding = torch.randn(
        batch,
        samples,
        history,
        embedding_dim,
        generator=generator,
        device=device,
        dtype=candidate_dtype,
    )
    goal_embedding = torch.randn(
        batch,
        history,
        embedding_dim,
        generator=generator,
        device=device,
        dtype=candidate_dtype,
    )
    # Deliberately use float32 actions.  The obsolete Embedder forced float32
    # into a bf16 Conv1d and crashed; the pinned official implementation casts
    # inputs to the checkpoint weight dtype.
    actions = torch.randn(
        batch,
        samples,
        horizon,
        action_dim,
        generator=generator,
        device=device,
        dtype=torch.float32,
    )
    info = {
        "pixels": torch.zeros(
            batch, samples, history, 1, device=device, dtype=candidate_dtype
        ),
        "goal": torch.zeros(
            batch, samples, history, 1, device=device, dtype=candidate_dtype
        ),
        "emb": embedding,
        "goal_emb": goal_embedding,
    }

    reference_info = clone_info(info)
    candidate_info = clone_info(info)
    reference_cost = reference.get_cost(reference_info, actions.detach().clone())
    candidate_cost = candidate.get_cost(candidate_info, actions.detach().clone())
    exact_cost_parity = torch.equal(reference_cost, candidate_cost)
    max_abs_cost_difference = float(
        (reference_cost.float() - candidate_cost.float()).abs().max().item()
    )
    finite = bool(torch.isfinite(reference_cost).all() and torch.isfinite(candidate_cost).all())
    cached_goal_preserved = bool(
        torch.equal(reference_info["goal_emb"], goal_embedding)
        and torch.equal(candidate_info["goal_emb"], goal_embedding)
    )

    altered_info = clone_info(info)
    altered_info["goal_emb"] = altered_info["goal_emb"] + 0.25
    altered_cost = candidate.get_cost(altered_info, actions.detach().clone())
    cached_goal_affects_cost = not torch.equal(candidate_cost, altered_cost)

    flat_actions = actions.reshape(batch * samples, horizon, action_dim)
    encoded_actions = candidate.action_encoder(flat_actions)
    action_cast_passed = encoded_actions.dtype == candidate_dtype
    passed = bool(
        exact_cost_parity
        and finite
        and cached_goal_preserved
        and cached_goal_affects_cost
        and action_cast_passed
    )
    return {
        "device": str(device),
        "parameter_dtype": str(candidate_dtype),
        "action_input_dtype": str(actions.dtype),
        "action_encoder_output_dtype": str(encoded_actions.dtype),
        "history": history,
        "horizon": horizon,
        "embedding_dim": embedding_dim,
        "action_dim": action_dim,
        "exact_cost_parity": exact_cost_parity,
        "max_abs_cost_difference": max_abs_cost_difference,
        "finite": finite,
        "cached_goal_preserved": cached_goal_preserved,
        "cached_goal_affects_cost": cached_goal_affects_cost,
        "action_cast_passed": action_cast_passed,
        "passed": passed,
    }


def parse_pair(value: str) -> tuple[str, Path, Path]:
    name, separator, paths = value.partition("=")
    reference, comma, candidate = paths.partition(",")
    if not separator or not comma or not name or not reference or not candidate:
        raise argparse.ArgumentTypeError("pair must be NAME=REFERENCE,CANDIDATE")
    return name, Path(reference), Path(candidate)


def audit_pair(
    name: str,
    reference_path: Path,
    candidate_path: Path,
    device: torch.device | None,
    seed: int,
) -> dict:
    reference = load_object(reference_path)
    candidate = load_object(candidate_path)
    reference_state = reference.state_dict()
    candidate_state = candidate.state_dict()
    keys = sorted(reference_state)
    candidate_keys = sorted(candidate_state)
    mismatches = [
        key
        for key in sorted(set(keys).intersection(candidate_keys))
        if reference_state[key].shape != candidate_state[key].shape
        or reference_state[key].dtype != candidate_state[key].dtype
        or not torch.equal(reference_state[key].cpu(), candidate_state[key].cpu())
    ]
    reference_digest = state_digest(reference_state)
    candidate_digest = state_digest(candidate_state)
    tensor_identity = bool(
        keys == candidate_keys
        and not mismatches
        and reference_digest == candidate_digest
    )
    types_correct = bool(
        model_type(reference) == EXPECTED_MODEL_TYPE
        and model_type(candidate) == EXPECTED_MODEL_TYPE
    )
    synthetic = None
    if device is not None:
        synthetic = synthetic_cost_parity(reference, candidate, device, seed)
    passed = bool(tensor_identity and types_correct and (synthetic is None or synthetic["passed"]))
    return {
        "name": name,
        "reference_path": str(reference_path),
        "candidate_path": str(candidate_path),
        "reference_file_sha256": sha256_file(reference_path),
        "candidate_file_sha256": sha256_file(candidate_path),
        "reference_model_type": model_type(reference),
        "candidate_model_type": model_type(candidate),
        "reference_state_sha256": reference_digest,
        "candidate_state_sha256": candidate_digest,
        "reference_parameter_keys": len(keys),
        "candidate_parameter_keys": len(candidate_keys),
        "missing_from_candidate": sorted(set(keys) - set(candidate_keys)),
        "extra_in_candidate": sorted(set(candidate_keys) - set(keys)),
        "mismatched_tensor_keys": mismatches,
        "tensor_identity": tensor_identity,
        "official_runtime_types": types_correct,
        "synthetic_cost_parity": synthetic,
        "passed": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", action="append", type=parse_pair, required=True)
    parser.add_argument("--device", default=None)
    parser.add_argument("--seed", type=int, default=1901)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    device = torch.device(args.device) if args.device else None
    if device is not None and device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA runtime preflight requested but unavailable")
    rows = [
        audit_pair(name, reference, candidate, device, args.seed + index)
        for index, (name, reference, candidate) in enumerate(args.pair)
    ]
    payload = {
        "kind": "gdp_cem_e19_lewm_serialization_compatibility_audit",
        "expected_model_type": EXPECTED_MODEL_TYPE,
        "pairs": rows,
        "all_passed": all(row["passed"] for row in rows),
        "synthetic_runtime_executed": device is not None,
        "performance_metric_read": False,
        "protected_metric_artifact_read": False,
        "d5_read": False,
    }
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not payload["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
