"""E19-L1 observational diagnostics; never imported by a frozen evaluator."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import torch
from torch.overrides import TorchFunctionMode


def tensor_delta(left: Any, right: Any) -> dict[str, Any]:
    a = left.detach().cpu() if torch.is_tensor(left) else torch.as_tensor(np.asarray(left))
    b = right.detach().cpu() if torch.is_tensor(right) else torch.as_tensor(np.asarray(right))
    result = {"left_shape": list(a.shape), "right_shape": list(b.shape),
              "left_dtype": str(a.dtype), "right_dtype": str(b.dtype)}
    if a.shape != b.shape:
        return {**result, "exact": False, "shape_matches": False}
    unequal = a != b
    finite = torch.isfinite(a).all().item() and torch.isfinite(b).all().item()
    delta = a.double() - b.double()
    return {**result, "shape_matches": True,
            "exact": a.dtype == b.dtype and torch.equal(a, b),
            "finite": bool(finite), "elements": a.numel(),
            "changed_elements": int(unequal.sum()),
            "changed_rows": int(unequal.reshape(a.shape[0], -1).any(1).sum()) if a.ndim else int(unequal),
            "max_abs": float(delta.abs().max()) if a.numel() and finite else None,
            "mean_abs": float(delta.abs().mean()) if a.numel() and finite else None,
            "rms": float(delta.square().mean().sqrt()) if a.numel() and finite else None}


def leaves(value: Any, path: str = ""):
    if isinstance(value, dict):
        if value.get("kind") in {"torch", "numpy", "repr"}:
            yield path, value
        else:
            for key in sorted(value):
                yield from leaves(value[key], f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, f"{path}[{index}]")
    else:
        yield path, value


def record_differences(left: Any, right: Any) -> list[dict[str, Any]]:
    a, b = dict(leaves(left)), dict(leaves(right))
    return [{"path": path, "left": a.get(path), "right": b.get(path),
             "left_present": path in a, "right_present": path in b}
            for path in sorted(a.keys() | b.keys()) if a.get(path) != b.get(path) or (path in a) != (path in b)]


def opaque_paths(record: Any) -> list[str]:
    return [path for path, value in leaves(record)
            if isinstance(value, dict) and value.get("kind") == "repr"]


def trace_comparison(left: dict, right: dict) -> dict:
    """Align by plan/kind/occurrence, not by a shifted raw sequence offset."""
    def keyed(events):
        seen = Counter()
        rows = {}
        for event in events:
            group = (event["plan_index"], event["kind"])
            key = (*group, seen[group])
            seen[group] += 1
            rows[key] = event
        return rows

    a, b = keyed(left["events"]), keyed(right["events"])
    counts, field_counts, coverage = Counter(), Counter(), Counter()
    samples, numerical_samples, non_time_samples = [], [], []
    missing = []
    opaque = set()
    other_differences = 0
    for key in dict.fromkeys([*a, *b]):
        if key not in a or key not in b:
            missing.append({"key": list(key), "left_present": key in a, "right_present": key in b})
            continue
        x, y = a[key], b[key]
        coverage[x["kind"]] += 1
        differences = record_differences(x, y)
        for event in (x, y):
            opaque.update(f"{key}:{path}" for path in opaque_paths(event))
        if differences:
            counts[x["kind"]] += 1
        for difference in differences:
            path = difference["path"]
            field_counts[f"{x['kind']}.{path}"] += 1
            row = {"sequence_left": x["sequence"], "sequence_right": y["sequence"],
                   "kind": x["kind"], "plan_index": x["plan_index"],
                   "round_index": x.get("round_index"), **difference}
            if len(samples) < 24:
                samples.append(row)
            numeric = any(isinstance(difference.get(side), dict)
                          and difference[side].get("kind") in {"torch", "numpy"}
                          for side in ("left", "right"))
            if numeric and len(numerical_samples) < 16:
                numerical_samples.append(row)
            time_only = x["kind"] == "solver_input" and path in {
                "mapping.render_time", "mapping_sha256"}
            if not time_only:
                other_differences += 1
                if len(non_time_samples) < 24:
                    non_time_samples.append(row)
    return {"left_event_count": len(left["events"]), "right_event_count": len(right["events"]),
            "order_exact": list(a) == list(b), "missing_event_count": len(missing),
            "missing_event_examples": missing[:16], "event_coverage": dict(coverage),
            "events_differing_by_kind": dict(counts), "differences_by_field": dict(field_counts),
            "first_differences": samples, "first_tensor_differences": numerical_samples,
            "differences_excluding_render_time_and_derived_mapping_hash": other_differences,
            "first_non_render_time_differences": non_time_samples,
            "opaque_repr_path_count": len(opaque), "opaque_repr_path_examples": sorted(opaque)[:16],
            "later_round_magnitude_available": False,
            "limitation": "Only first-call round-zero banks contain raw candidate/cost tensors; later rounds contain hashes."}


class CaptureTopK(TorchFunctionMode):
    """Capture results of the actual operation, without a second selection."""

    def __init__(self):
        super().__init__()
        self.outputs = []

    def __torch_function__(self, func, types, args=(), kwargs=None):
        result = func(*args, **(kwargs or {}))
        if func is torch.topk:
            self.outputs.append((result.values.detach().clone(), result.indices.detach().clone()))
        return result


def observe_fit(fit, candidates, costs, elites=30):
    with CaptureTopK() as observer:
        mean, std, values = fit(candidates, costs, elites)
    if len(observer.outputs) != 1:
        raise RuntimeError(f"expected exactly one original topk, got {len(observer.outputs)}")
    actual_values, indices = observer.outputs[0]
    if not torch.equal(values, actual_values):
        raise RuntimeError("captured topk values differ from original fit return")
    return mean, std, values, indices


def selected_distribution(candidates, indices, *, clamp):
    rows = torch.arange(candidates.size(0), device=candidates.device)[:, None]
    selected = candidates[rows, indices]
    mean, std = selected.mean(1), selected.std(1)
    return mean, std.clamp_min(1e-6) if clamp else std


def boundary_rows(costs: torch.Tensor, k: int = 30) -> list[dict]:
    ordered = costs.detach().cpu().double().sort(1).values
    if ordered.ndim != 2 or not 0 < k < ordered.shape[1] or not torch.isfinite(ordered).all():
        raise ValueError("boundary audit requires finite costs and 0 < k < candidates")
    rows = []
    for index, values in enumerate(ordered):
        threshold, next_cost = float(values[k - 1]), float(values[k])
        gap = next_cost - threshold
        rows.append({"environment_index": index, "elite_boundary_cost": threshold,
                     "next_excluded_cost": next_cost, "boundary_gap": gap,
                     "boundary_gap_relative": gap / max(1.0, abs(threshold)),
                     "exact_boundary_tie": gap == 0.0,
                     "near_boundary_1e_6_relative": gap <= 1e-6 * max(1.0, abs(threshold)),
                     "candidates_at_boundary_value": int((values == threshold).sum()),
                     "adjacent_exact_ties": int((values[1:] == values[:-1]).sum())})
    return rows


def elite_rows(left, right) -> list[dict]:
    if left.shape != right.shape or left.ndim != 2:
        raise ValueError("elite geometry mismatch")
    output = []
    for index, (a, b) in enumerate(zip(left.cpu().tolist(), right.cpu().tolist())):
        x, y = set(a), set(b)
        if len(x) != len(a) or len(y) != len(b):
            raise ValueError("duplicate elite index")
        intersection = len(x & y)
        output.append({"environment_index": index, "intersection": intersection,
                       "replaced_elites": len(x) - intersection,
                       "overlap_fraction": intersection / len(x),
                       "jaccard": intersection / len(x | y), "order_exact": a == b})
    return output


def outcome_comparison(left: dict, right: dict) -> dict:
    identity = ("benchmark", "method", "seed", "horizon", "num_eval", "schedule", "planner")
    if any(left.get(key) != right.get(key) for key in identity):
        raise ValueError("result identity differs")
    if left.get("record_ids") != right.get("record_ids"):
        raise ValueError("result record ordering differs")
    a = np.asarray(left["metrics"]["episode_successes"], dtype=bool)
    b = np.asarray(right["metrics"]["episode_successes"], dtype=bool)
    if a.shape != (50,) or b.shape != (50,):
        raise ValueError("expected 50 paired episode outcomes")
    return {"episode_count": 50, "left_successes": int(a.sum()), "right_successes": int(b.sum()),
            "left_to_right_success_rate_pp": 100.0 * float(b.mean() - a.mean()),
            "changed_episode_count": int((a != b).sum()),
            "changed_episode_indices": np.flatnonzero(a != b).tolist(),
            "lost_success_indices": np.flatnonzero(a & ~b).tolist(),
            "gained_success_indices": np.flatnonzero(~a & b).tolist(),
            "record_ids_available": "record_ids" in left,
            "elapsed_seconds_left": left.get("elapsed_seconds"),
            "elapsed_seconds_right": right.get("elapsed_seconds")}
