#!/usr/bin/env python3
"""Validate one official SAGE result without reporting its performance."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import gdp_cem_e19_specs as spec


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--benchmark", choices=spec.BENCHMARKS, required=True)
    parser.add_argument("--method", choices=spec.METHODS, required=True)
    parser.add_argument("--seed", type=int, choices=spec.SEEDS, required=True)
    parser.add_argument("--horizon", type=int, choices=spec.HORIZONS, required=True)
    parser.add_argument("--paper-config", type=Path, required=True)
    parser.add_argument("--lewm", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    args = parser.parse_args()

    if args.status.exists():
        raise FileExistsError(args.status)
    payload = json.loads(args.result.read_text(encoding="utf-8"))
    paper = json.loads(args.paper_config.read_text(encoding="utf-8"))
    expected_generator, expected_prior = spec.checkpoint_paths(
        args.benchmark, args.method
    )
    checks = {
        "protocol": payload.get("protocol_id") == paper["protocol_id"]
        and payload.get("protocol_kind") == "paper",
        "benchmark": payload.get("benchmark") == args.benchmark,
        "method": payload.get("method") == args.method,
        "seed": payload.get("seed") == args.seed,
        "horizon": payload.get("horizon") == args.horizon,
        "schedule": payload.get("schedule") == paper["schedule"][str(args.horizon)],
        "num_eval": payload.get("num_eval") == spec.EXPECTED_EPISODES_PER_CELL,
        "planner": payload.get("planner", {}).get("candidates") == 300
        and payload.get("planner", {}).get("cem_rounds") == 30
        and payload.get("planner", {}).get("elites") == 30
        and payload.get("planner", {}).get("action_block") == 5
        and payload.get("planner", {}).get("history_length") == 3
        and payload.get("planner", {}).get("frameskip") == 5
        and payload.get("planner", {}).get("precision") == "bf16"
        and payload.get("planner", {}).get("warm_start") is False,
        "environment_budget": payload.get("environment_budget")
        == paper["environment_budget_multiplier"][args.benchmark] * args.horizon,
        "lewm_path": payload.get("checkpoints", {}).get("lewm") == str(args.lewm),
    }
    success = payload.get("metrics", {}).get("success_rate")
    episodes = payload.get("metrics", {}).get("episode_successes")
    checks["success_finite"] = isinstance(success, (int, float)) and math.isfinite(
        float(success)
    )
    checks["episode_vector"] = (
        isinstance(episodes, list)
        and len(episodes) == spec.EXPECTED_EPISODES_PER_CELL
        and all(isinstance(value, bool) for value in episodes)
    )
    generator = payload.get("checkpoints", {}).get("generator")
    prior = payload.get("checkpoints", {}).get("action_prior") or {}
    if expected_generator is None:
        checks["generator"] = generator is None
    else:
        expected_key = expected_generator.removesuffix(".pt")
        checks["generator"] = (
            isinstance(generator, dict)
            and Path(generator.get("path", "")).name == expected_generator
            and generator.get("sha256") == spec.CHECKPOINTS[expected_key]["sha256"]
        )
    expected_prior_key = expected_prior.removesuffix(".pt")
    checks["action_prior"] = (
        Path(prior.get("path", "")).name == expected_prior
        and prior.get("sha256") == spec.CHECKPOINTS[expected_prior_key]["sha256"]
    )
    passed = all(checks.values())
    status = {
        "kind": "gdp_cem_e19_official_sage_cell_integrity",
        "status": "passed" if passed else "failed",
        "benchmark": args.benchmark,
        "method": args.method,
        "seed": args.seed,
        "horizon": args.horizon,
        "result_sha256": sha256_file(args.result),
        "paper_config_sha256": sha256_file(args.paper_config),
        "lewm_path": str(args.lewm),
        "lewm_sha256": sha256_file(args.lewm),
        "checks": checks,
        "performance_value_reported": False,
        "d5_read": False,
    }
    args.status.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
