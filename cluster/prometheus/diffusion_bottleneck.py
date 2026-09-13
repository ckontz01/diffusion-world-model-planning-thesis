"""Post-result diagnostics for the completed independent PushT study.

No models, simulator, network, or scheduler are imported. Historical files are
read-only inputs. The CLI is pinned to the first completed look (1,600 records).
Exploratory intervals are NOT sequentially adjusted confirmatory intervals.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys
from typing import Any

import numpy as np

SOURCE_COMMIT = "001aad99a2e2e6a141797e0c516604e7188d706a"
ARMS = (
    "vad_continuation", "vad_greedy_300", "diagonal_gaussian_continuation",
    "vad_greedy_576", "direct_gmm_continuation", "sage",
)
HORIZONS = (75, 150)
SEEDS = (7201, 7202, 7203)
N = 1600
SUMMARY_SHA = "305be6aa678445dce5ceddda6bae14657a730810e448121df6c8783c4318da6d"
TENSOR_SHA = "afb181230eb36d0d6081477bef910814f8b2c0208d913063df48131e4e2af7e2"
VERIFIER_SHA = "a0476199cbdeee6a04676a7dd86d4b17d1abfab6a2c1212833d8320a92bb5380"
LOCK_SHA = "90ac1fd4e8e5fbaa3941ab9a5b7ed127bc20cb96018bed5d143b7dec2cbf64cb"
SCOPE = (
    "Post-result development analysis of the completed N=1600 study; no new "
    "efficacy experiment, no causal identification, no change to its stopping rule."
)


class IntegrityError(ValueError):
    """An input does not satisfy the declared artifact contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrityError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha(path: Path, expected: str) -> None:
    require(bool(re.fullmatch(r"[a-f0-9]{64}", expected)), "Invalid expected SHA256")
    require(sha256(path) == expected, f"SHA256 mismatch: {path}")


def read_json(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise IntegrityError(f"Nonfinite JSON constant: {value}")
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def checked_child(root: Path, name: str) -> Path:
    """Reject absolute paths, path traversal, and symlinks escaping the root."""
    require(isinstance(name, str) and bool(name), "Empty/non-string artifact name")
    require("\\" not in name, "Backslash is not an archive path separator")
    rel = Path(name)
    require(not rel.is_absolute() and ".." not in rel.parts, "Unsafe artifact path")
    base, child = root.resolve(), (root / rel).resolve()
    require(child != base and base in child.parents, "Artifact escapes input root")
    return child


def verified_summary(path: Path) -> dict[str, Any]:
    require_sha(path, SUMMARY_SHA)
    result = read_json(path)
    require(result["n"] == N and result["stage"] == 0, "Wrong completed look")
    require(result["complete_logical_runs"] == N * 2 * 3 * 6, "Wrong grid size")
    require(set(result["arm_success"]) == set(ARMS), "Wrong arm identities")
    require(result["horizons"] == list(HORIZONS), "Wrong horizon order")
    require(result["input_lock_sha256"] == LOCK_SHA, "Wrong input identity")
    require(result["stop"] is True and result["futility"] is True, "Wrong historical decision")
    return result


def summary_diagnostics(summary: dict[str, Any]) -> dict[str, Any]:
    """Arithmetic on the published summary; cannot recover paired outcomes."""
    effects = {}
    treatment = np.asarray(summary["per_horizon"][ARMS[0]], dtype=float)
    for arm in ARMS[1:]:
        difference = treatment - np.asarray(summary["per_horizon"][arm], dtype=float)
        effects[arm] = {
            "difference_pp": float(100 * difference.mean()),
            "h75_difference_pp": float(100 * difference[0]),
            "h150_difference_pp": float(100 * difference[1]),
            "horizon_interaction_point_pp": float(100 * (difference[1] - difference[0])),
        }
    return {
        "scope": SCOPE, "input_level": "published_summary_only",
        "paired_outcomes_reaggregated": False, "raw_trajectories_read": False,
        "effects": effects,
        "historical_decision_unchanged": summary["decision"],
        "not_identified": [
            "Per-episode method overlap and covariance",
            "Uncertainty of horizon interactions or secondary GMM contrast",
            "Proposal coverage, ranking error, adapter error, and causal SAGE advantage",
        ],
    }


def validate_tensor(values: np.ndarray, expected_n: int | None = None) -> np.ndarray:
    arr = np.asarray(values)
    require(arr.ndim == 4 and arr.shape[1:] == (2, 3, 6), "Expected N x horizon x seed x arm")
    require(arr.shape[0] >= 2, "Need at least two independent reference clusters")
    if expected_n is not None:
        require(arr.shape[0] == expected_n, "Unexpected reference count")
    require(arr.dtype.kind in "biuf", "Outcomes must be numeric, not objects")
    require(bool(np.isfinite(arr).all()), "Missing/nonfinite outcome")
    require(bool(np.isin(arr, (0, 1)).all()), "Non-binary outcome")
    # Conversion BEFORE subtraction prevents unsigned integer underflow.
    return arr.astype(np.float64, copy=False)


def checked_archive(archive: Path) -> tuple[np.ndarray, dict[str, Any]]:
    summary = verified_summary(archive / "SUMMARY.json")
    require_sha(archive / "EPISODE-TENSOR.npz", TENSOR_SHA)
    require_sha(archive / "INDEPENDENT-VERIFICATION.json", VERIFIER_SHA)
    verifier = read_json(archive / "INDEPENDENT-VERIFICATION.json")
    require(verifier.get("all_passed") is True, "Historical verifier did not pass")
    require(verifier.get("n") == N and verifier.get("logical_runs") == 57600, "Verifier count mismatch")
    require(verifier.get("summary_sha256") == SUMMARY_SHA, "Verifier/summary identity mismatch")
    require(verifier.get("input_lock_sha256") == LOCK_SHA, "Verifier input-lock mismatch")
    require(verifier.get("decision") == summary["decision"] and verifier.get("stop") is True,
            "Verifier/summary decision mismatch")
    with np.load(archive / "EPISODE-TENSOR.npz", allow_pickle=False) as loaded:
        require(loaded.files == ["success"], "Unexpected tensor keys")
        tensor = validate_tensor(loaded["success"].copy(), N)
    for index, arm in enumerate(ARMS):
        np.testing.assert_allclose(tensor[..., index].mean(), summary["arm_success"][arm], rtol=0, atol=1e-12)
        np.testing.assert_allclose(tensor[..., index].mean(axis=(0, 2)), summary["per_horizon"][arm], rtol=0, atol=1e-12)
    means = tensor.mean(axis=(1, 2))
    for control, original in summary["primary"].items():
        d = means[:, 0] - means[:, ARMS.index(control)]
        np.testing.assert_allclose(d.mean(), original["difference"], rtol=0, atol=1e-12)
        np.testing.assert_allclose(d.std(ddof=1) / np.sqrt(N), original["se"], rtol=0, atol=1e-12)
    return tensor, summary


def cluster_metrics(tensor: np.ndarray) -> tuple[list[str], np.ndarray]:
    x = validate_tensor(tensor)
    names, columns = [], []
    for j, control in enumerate(ARMS[1:], start=1):
        by_horizon = (x[..., 0] - x[..., j]).mean(axis=2)
        for label, column in (
            ("overall", by_horizon.mean(axis=1)),
            ("h75", by_horizon[:, 0]), ("h150", by_horizon[:, 1]),
            ("h150_minus_h75", by_horizon[:, 1] - by_horizon[:, 0]),
        ):
            names.append(f"vad_continuation-minus-{control}/{label}")
            columns.append(column)
    return names, np.stack(columns, axis=1)


def cluster_intervals(values: np.ndarray, repetitions: int, seed: int) -> dict[str, Any]:
    require(values.ndim == 2 and len(values) >= 2, "Expected reference x metric matrix")
    require(bool(np.isfinite(values).all()), "Nonfinite cluster metric")
    require(isinstance(repetitions, int) and 100 <= repetitions <= 100000, "Bootstrap count outside 100..100000")
    require(isinstance(seed, int) and seed >= 0, "Invalid random seed")
    rng = np.random.Generator(np.random.PCG64(seed))
    samples = np.empty((repetitions, values.shape[1]))
    # One row resample retains ALL horizons, arms, and fixed seeds together.
    for begin in range(0, repetitions, 64):
        end = min(begin + 64, repetitions)
        ids = rng.integers(0, len(values), size=(end - begin, len(values)))
        samples[begin:end] = values[ids].mean(axis=1)
    return {
        "method": "unadjusted exploratory reference-cluster percentile bootstrap",
        "sequentially_valid_confirmation": False, "multiplicity_adjusted": False,
        "repetitions": repetitions, "seed": seed,
        "lower_pp": (100 * np.quantile(samples, .025, axis=0)).tolist(),
        "upper_pp": (100 * np.quantile(samples, .975, axis=0)).tolist(),
    }


def paired_counts(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    require(left.shape == right.shape, "Unpaired outcome shapes")
    require(bool(np.isin(left, (0, 1)).all() and np.isin(right, (0, 1)).all()), "Nonbinary pairing")
    a, b = left.astype(bool), right.astype(bool)
    count = {"both_success": int((a & b).sum()), "left_only": int((a & ~b).sum()),
             "right_only": int((~a & b).sum()), "both_failure": int((~a & ~b).sum())}
    require(sum(count.values()) == left.size and left.size > 0, "Pair counting mismatch")
    count.update(
        paired_measurements=int(left.size),
        left_minus_right_pp=100 * (count["left_only"] - count["right_only"]) / left.size,
        nondeployable_whole_planner_oracle_success=(count["both_success"] + count["left_only"] + count["right_only"]) / left.size,
    )
    return count


def outcome_diagnostics(tensor: np.ndarray, repetitions: int = 0, seed: int = 20260913) -> dict[str, Any]:
    x = validate_tensor(tensor)
    names, values = cluster_metrics(x)
    metrics = {name: {"estimate_pp": float(100 * values[:, j].mean()),
                      "reference_cluster_se_pp": float(100 * values[:, j].std(ddof=1) / np.sqrt(len(x)))}
               for j, name in enumerate(names)}
    intervals = None if repetitions == 0 else cluster_intervals(values, repetitions, seed)
    if intervals is not None:
        for j, name in enumerate(names):
            metrics[name]["exploratory_interval_pp"] = [intervals["lower_pp"][j], intervals["upper_pp"][j]]
    pairs = {}
    for i, j in itertools.combinations(range(len(ARMS)), 2):
        left, right = x[..., i], x[..., j]
        d = (left - right).mean(axis=(1, 2))
        pairs[f"{ARMS[i]}__{ARMS[j]}"] = {
            "all": paired_counts(left, right),
            "h75": paired_counts(left[:, 0], right[:, 0]),
            "h150": paired_counts(left[:, 1], right[:, 1]),
            "reference_net_wins": int((d > 0).sum()),
            "reference_net_losses": int((d < 0).sum()),
            "reference_net_ties": int((d == 0).sum()),
        }
    return {
        "scope": SCOPE, "input_level": "complete_archived_binary_outcomes",
        "independent_references": len(x), "paired_measurements": int(x.size),
        "raw_trajectories_read": False, "model_runs": 0,
        "arm_order": list(ARMS), "horizons": list(HORIZONS), "fixed_seed_blocks": list(SEEDS),
        "per_fixed_block_success": {a: x[..., i].mean(axis=0).tolist() for i, a in enumerate(ARMS)},
        "metrics": metrics, "bootstrap": intervals, "method_pairs": pairs,
        "oracle_warning": (
            "The union uses known complete-policy outcomes. It is neither an achieved "
            "planner nor evidence of same-candidate ranking headroom or adapter error."
        ),
        "seed_warning": "Three fixed blocks are paired measurements, not a population of retrained models.",
    }


def trajectory_diagnostics(states: np.ndarray, goal: np.ndarray) -> dict[str, Any]:
    """Preserve the registered joint-position predicate and exclude initial t0."""
    states, goal = np.asarray(states), np.asarray(goal)
    require(states.ndim == 2 and states.shape[1] == 7 and len(states) >= 1, "Bad state trace shape")
    require(goal.shape == (7,), "Bad goal shape")
    require(bool(np.isfinite(states).all() and np.isfinite(goal).all()), "Nonfinite states")
    # Native float64 negative-tiny % (2*pi) can equal the exact divisor.
    # Admit that state endpoint only: do not normalize arrays or change any
    # historical arithmetic below. Goals remained strictly canonical in the
    # complete exposed inventory; their admission contract is unchanged.
    require(bool(((states[:, 4] >= 0) & (states[:, 4] <= 2 * np.pi)).all())
            and 0 <= goal[4] < 2 * np.pi, "Noncanonical angle: review, do not silently change the historical predicate")
    x = states[1:]
    if len(x) == 0:
        return {"success": False, "delivered": 0, "terminal_category": "no_action"}
    joint = np.linalg.norm(x[:, :4] - goal[:4], axis=1)
    agent = np.linalg.norm(x[:, :2] - goal[:2], axis=1)
    block = np.linalg.norm(x[:, 2:4] - goal[2:4], axis=1)
    angle = np.abs(x[:, 4] - goal[4])
    angle = np.minimum(angle, 2 * np.pi - angle)
    pos_ok, angle_ok = joint < 20, angle < np.pi / 9
    success = pos_ok & angle_ok
    first = int(np.flatnonzero(success)[0] + 1) if success.any() else None
    category = {(True, True): "joint_success", (True, False): "angle_only_miss",
                (False, True): "joint_position_only_miss", (False, False): "both_miss"}
    joint_margin = np.maximum(joint / 20, angle / (np.pi / 9))
    closest = int(np.argmin(joint_margin))
    return {
        "success": bool(success.any()), "first_success_step": first,
        "delivered": len(x), "terminal_category": category[(bool(pos_ok[-1]), bool(angle_ok[-1]))],
        "ever_block_pose_within_component_thresholds": bool(((block < 20) & angle_ok).any()),
        "ever_individual_positions_both_within_20_but_joint_outside": bool(((agent < 20) & (block < 20) & ~pos_ok).any()),
        "closest_joint_margin": float(joint_margin[closest]), "closest_step": closest + 1,
        "agent_distance_at_closest": float(agent[closest]), "block_distance_at_closest": float(block[closest]),
        "joint_position_distance_at_closest": float(joint[closest]), "angle_error_at_closest": float(angle[closest]),
    }


def write_report(path: Path, value: dict[str, Any], forbidden_roots: tuple[Path, ...]) -> None:
    resolved = path.resolve()
    for root in forbidden_roots:
        base = root.resolve()
        require(resolved != base and base not in resolved.parents, "Output would modify an input tree")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary", type=Path, help="Pinned SUMMARY.json; arithmetic only")
    group.add_argument("--archive", type=Path, help="Pinned look-0 archive; full paired outcomes")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=0, help="Exploratory only, 0 disables")
    parser.add_argument("--bootstrap-seed", type=int, default=20260913)
    args = parser.parse_args(argv)
    try:
        if args.summary:
            require(args.bootstrap == 0, "Cannot bootstrap aggregate means without paired outcomes")
            result = summary_diagnostics(verified_summary(args.summary))
            roots = (args.summary.parent,)
        else:
            tensor, summary = checked_archive(args.archive)
            result = outcome_diagnostics(tensor, args.bootstrap, args.bootstrap_seed)
            result["historical_decision_unchanged"] = summary["decision"]
            roots = (args.archive,)
        result.update(source_commit=SOURCE_COMMIT, summary_sha256=SUMMARY_SHA,
                      program_sha256=sha256(Path(__file__)))
        write_report(args.out, result, roots)
        print(json.dumps({"written": str(args.out), "input_level": result["input_level"]}))
        return 0
    except (IntegrityError, OSError, ValueError, KeyError, AssertionError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
