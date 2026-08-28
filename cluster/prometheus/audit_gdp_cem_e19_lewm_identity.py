#!/usr/bin/env python3
"""Compare serialized LeWM objects by parameters, not container bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

import gdp_cem_e19_specs as spec


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

    if not path.name.endswith("_object.ckpt"):
        raise ValueError(f"not an AutoCostModel object checkpoint: {path}")
    prefix = str(path)[: -len("_object.ckpt")]
    model = swm.policy.AutoCostModel(prefix)
    model.eval().requires_grad_(False)
    return model


def compare(name: str, reference: Path, candidate: Path) -> dict:
    reference_model = load_object(reference)
    candidate_model = load_object(candidate)
    reference_state = reference_model.state_dict()
    candidate_state = candidate_model.state_dict()
    reference_keys = sorted(reference_state)
    candidate_keys = sorted(candidate_state)
    common = sorted(set(reference_keys).intersection(candidate_keys))
    mismatched = []
    for key in common:
        left = reference_state[key].detach().cpu()
        right = candidate_state[key].detach().cpu()
        if left.shape != right.shape or left.dtype != right.dtype or not torch.equal(left, right):
            mismatched.append(key)
    return {
        "name": name,
        "reference_path": str(reference),
        "candidate_path": str(candidate),
        "reference_file_sha256": sha256_file(reference),
        "candidate_file_sha256": sha256_file(candidate),
        "reference_model_type": f"{type(reference_model).__module__}.{type(reference_model).__qualname__}",
        "candidate_model_type": f"{type(candidate_model).__module__}.{type(candidate_model).__qualname__}",
        "reference_state_sha256": state_digest(reference_state),
        "candidate_state_sha256": state_digest(candidate_state),
        "reference_parameter_keys": len(reference_keys),
        "candidate_parameter_keys": len(candidate_keys),
        "missing_from_candidate": sorted(set(reference_keys) - set(candidate_keys)),
        "extra_in_candidate": sorted(set(candidate_keys) - set(reference_keys)),
        "mismatched_tensor_keys": mismatched,
        "parameter_identical": (
            reference_keys == candidate_keys
            and not mismatched
            and state_digest(reference_state) == state_digest(candidate_state)
        ),
    }


def parse_pair(value: str) -> tuple[str, Path, Path]:
    parts = value.split("=", maxsplit=1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("pair must be NAME=REFERENCE,CANDIDATE")
    paths = parts[1].split(",", maxsplit=1)
    if len(paths) != 2:
        raise argparse.ArgumentTypeError("pair must be NAME=REFERENCE,CANDIDATE")
    return parts[0], Path(paths[0]), Path(paths[1])


def parse_source(value: str) -> tuple[str, Path]:
    parts = value.split("=", maxsplit=1)
    if len(parts) != 2 or parts[0] not in spec.BENCHMARKS:
        raise argparse.ArgumentTypeError("source must be TASK=DIRECTORY")
    return parts[0], Path(parts[1])


def audit_source(task: str, directory: Path) -> dict:
    task_spec = spec.TASKS[task]
    config = directory / "config.json"
    weights = directory / "weights.pt"
    source = directory / "source.txt"
    source_text = source.read_text(encoding="utf-8") if source.is_file() else ""
    checks = {
        "config_sha256": config.is_file()
        and sha256_file(config) == task_spec["lewm_config_sha256"],
        "weights_sha256": weights.is_file()
        and sha256_file(weights) == task_spec["lewm_weights_sha256"],
        "repository": f"repo={task_spec['lewm_repo']}" in source_text,
        "revision": f"revision={task_spec['lewm_revision']}" in source_text,
    }
    return {
        "task": task,
        "directory": str(directory),
        "repository": task_spec["lewm_repo"],
        "revision": task_spec["lewm_revision"],
        "config_sha256": sha256_file(config) if config.is_file() else None,
        "weights_sha256": sha256_file(weights) if weights.is_file() else None,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", action="append", type=parse_pair, required=True)
    parser.add_argument("--source", action="append", type=parse_source, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-identical", action="store_true")
    args = parser.parse_args()

    if {task for task, _ in args.source} != set(spec.BENCHMARKS):
        raise ValueError("exactly both PushT and Cube source directories are required")
    source_results = [audit_source(task, directory) for task, directory in args.source]
    results = [compare(name, reference, candidate) for name, reference, candidate in args.pair]
    payload = {
        "kind": "gdp_cem_e19_lewm_parameter_identity",
        "source_revisions": source_results,
        "all_source_files_verified": all(row["passed"] for row in source_results),
        "pairs": results,
        "all_parameter_identical": all(row["parameter_identical"] for row in results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not payload["all_source_files_verified"]:
        raise SystemExit(1)
    if args.require_identical and not payload["all_parameter_identical"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
