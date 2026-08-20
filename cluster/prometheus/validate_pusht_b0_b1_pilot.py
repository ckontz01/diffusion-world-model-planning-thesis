#!/usr/bin/env python3

import argparse
import copy
import csv
import json
import re
from pathlib import Path

import yaml


SUCCESS_RE = re.compile(r"'success_rate':\s*([0-9]+(?:\.[0-9]+)?)")


def nested(config: dict, path: str):
    value = config
    for key in path.split("."):
        value = value[key]
    return value


def load_arm(base: Path, arm: str, expected_episodes: int) -> dict:
    arm_dir = base / arm
    result = arm_dir / f"{arm}_results.txt"
    episodes = arm_dir / f"{arm}_results_episodes.tsv"
    console = arm_dir / "console.log"

    for path in (result, episodes, console):
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"missing or empty {arm} artifact: {path}")

    result_text = result.read_text(encoding="utf-8")
    for marker in ("==== CONFIG ====", "==== DETERMINISM ====", "==== RESULTS ===="):
        if marker not in result_text:
            raise SystemExit(f"{arm} result lacks marker: {marker}")

    config_text = result_text.split("==== CONFIG ====", 1)[1].split(
        "==== DETERMINISM ====", 1
    )[0]
    config = yaml.safe_load(config_text)
    expected_config = {
        "seed": 42,
        "planning.mode": "hierarchical",
        "eval.num_eval": 50,
        "eval.goal_offset_steps": 25,
        "eval.eval_budget": 50,
        "planning.high.solver.device": "cuda",
        "planning.high.solver.batch_size": 1,
        "planning.high.solver.num_samples": 900,
        "planning.high.solver.var_scale": 1.0,
        "planning.high.solver.n_steps": 20,
        "planning.high.solver.topk": 10,
        "planning.high.plan_config.horizon": 1,
        "planning.high.plan_config.receding_horizon": 1,
        "planning.high.plan_config.action_block": 1,
        "planning.high.replan_interval": 5,
        "planning.high.empirical_macro.num_sequences": 4096,
        "planning.high.empirical_macro.chunk_len": 5,
        "planning.high.empirical_macro.residual_scale": 0.1,
        "planning.high.empirical_macro.min_residual_std": 0.001,
        "planning.high.empirical_macro.return_top_candidates": 8,
        "planning.high.empirical_macro.encode_batch_size": 4096,
        "planning.high.empirical_macro.stage_sampling": "sequence",
        "planning.high.empirical_macro.seed": 42,
        "planning.low.solver.device": "cuda",
        "planning.low.solver.batch_size": 1,
        "planning.low.solver.num_samples": 300,
        "planning.low.solver.var_scale": 1.0,
        "planning.low.solver.n_steps": 30,
        "planning.low.solver.topk": 150,
        "planning.low.plan_config.horizon": 2,
        "planning.low.plan_config.receding_horizon": 1,
        "planning.low.plan_config.action_block": 5,
    }
    mismatches = {
        path: {"expected": expected, "actual": nested(config, path)}
        for path, expected in expected_config.items()
        if nested(config, path) != expected
    }
    if mismatches:
        raise SystemExit(f"{arm} resolved-config mismatches: {mismatches}")

    expected_empirical = arm == "b1"
    actual_empirical = nested(config, "planning.high.empirical_macro.enabled")
    if actual_empirical is not expected_empirical:
        raise SystemExit(
            f"{arm} empirical setting is {actual_empirical}, expected {expected_empirical}"
        )

    match = SUCCESS_RE.search(result_text)
    if not match:
        raise SystemExit(f"unable to parse {arm} success rate")

    with episodes.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != expected_episodes:
        raise SystemExit(
            f"expected {expected_episodes} {arm} episode rows, found {len(rows)}"
        )
    if [int(row["eval_index"]) for row in rows] != list(range(expected_episodes)):
        raise SystemExit(f"{arm} eval_index values are not contiguous from zero")

    for row in rows:
        video = Path(row["video_path"])
        if video.parent.resolve() != arm_dir.resolve():
            raise SystemExit(f"{arm} video escapes output directory: {video}")
        if not video.is_file() or video.stat().st_size == 0:
            raise SystemExit(f"missing or empty {arm} video: {video}")

    successes = sum(row["status"] in {"PASS", "SUCCESS"} for row in rows)
    success_rate = float(match.group(1))
    expected_success_rate = 100.0 * successes / expected_episodes
    if abs(success_rate - expected_success_rate) > 1e-12:
        raise SystemExit(
            f"{arm} success-rate mismatch: metric={success_rate}, rows={successes}"
        )

    return {
        "success_rate": float(match.group(1)),
        "config": config,
        "episode_keys": [
            (row["eval_index"], row["episode_id"], row["start_step"]) for row in rows
        ],
        "successes": successes,
        "episode_rows": len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--expected-episodes", type=int, default=50)
    args = parser.parse_args()

    b0 = load_arm(args.output_dir, "b0", args.expected_episodes)
    b1 = load_arm(args.output_dir, "b1", args.expected_episodes)
    if b0["episode_keys"] != b1["episode_keys"]:
        raise SystemExit("B0 and B1 do not use identical evaluation episodes")

    b0_config = copy.deepcopy(b0["config"])
    b1_config = copy.deepcopy(b1["config"])
    b0_config["planning"]["high"]["empirical_macro"]["enabled"] = None
    b1_config["planning"]["high"]["empirical_macro"]["enabled"] = None
    b0_config.pop("output")
    b1_config.pop("output")
    if b0_config != b1_config:
        raise SystemExit("B0/B1 resolved configurations differ beyond arm output and B1 switch")

    summary = {
        "status": "ok",
        "classification": "development_pilot_not_paper_reproduction",
        "matched_episode_rows": args.expected_episodes,
        "b0": {
            "success_rate": b0["success_rate"],
            "successes": b0["successes"],
        },
        "b1": {
            "success_rate": b1["success_rate"],
            "successes": b1["successes"],
        },
        "difference_b1_minus_b0": b1["success_rate"] - b0["success_rate"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
