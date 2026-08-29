#!/usr/bin/env python3
"""Trace frozen E19 sentinel cells without changing official planner operations."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import torch

import gdp_cem_e19_discrepancy_specs as spec


def _tensor_record(value: torch.Tensor) -> dict[str, Any]:
    tensor = value.detach().cpu().contiguous()
    raw = tensor.reshape(-1).view(torch.uint8).numpy().tobytes()
    return {
        "kind": "torch",
        "dtype": str(tensor.dtype),
        "shape": list(tensor.shape),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _array_record(value: np.ndarray) -> dict[str, Any]:
    array = np.asarray(value)
    if array.dtype.hasobject:
        raw = json.dumps(array.tolist(), sort_keys=True, default=str).encode()
    else:
        raw = np.ascontiguousarray(array).tobytes()
    return {
        "kind": "numpy",
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def value_record(value: Any) -> Any:
    if torch.is_tensor(value):
        return _tensor_record(value)
    if isinstance(value, np.ndarray):
        return _array_record(value)
    if isinstance(value, dict):
        return {str(key): value_record(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [value_record(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return {"kind": "repr", "value": repr(value)}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value_record(value), sort_keys=True, separators=(",", ":"), allow_nan=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clone_value(value: Any) -> Any:
    if torch.is_tensor(value):
        return value.detach().cpu().clone()
    if isinstance(value, np.ndarray):
        return value.copy()
    if isinstance(value, dict):
        return {key: clone_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clone_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(clone_value(item) for item in value)
    return value


def _vector(value: Any, default: int, batch: int) -> list[int]:
    if value is None:
        return [int(default)] * int(batch)
    if torch.is_tensor(value):
        array = value.detach().cpu().numpy()
    else:
        array = np.asarray(value)
    while array.ndim > 1:
        array = array[:, 0]
    flat = array.reshape(-1)
    if flat.size == 1:
        flat = np.repeat(flat, int(batch))
    return [int(item) for item in flat]


def _stage_keys(info: dict[str, Any], default_remaining: int) -> list[tuple[int, int, int, int]]:
    batch = len(info["pixels"])
    env_ids = _vector(info.get("_env_id"), 0, batch)
    call_ids = _vector(info.get("_plan_call"), 0, batch)
    remaining = _vector(info.get("_remaining_steps"), default_remaining, batch)
    duration = _vector(info.get("_option_duration_steps"), 25, batch)
    return [
        (env_ids[row], call_ids[row], remaining[row], duration[row])
        for row in range(batch)
    ]


class TraceRecorder:
    def __init__(
        self,
        *,
        sentinel: spec.Sentinel,
        repeat: int,
        trace_path: Path,
        bank_path: Path,
    ) -> None:
        self.sentinel = sentinel
        self.repeat = int(repeat)
        self.trace_path = trace_path
        self.bank_path = bank_path
        self.events: list[dict[str, Any]] = []
        self.plan_index = -1
        self.round_index = 0
        self.active_plan: int | None = None
        self.current_info: dict[str, Any] | None = None
        self.bank: dict[str, Any] | None = None
        self.latest_local_goal: torch.Tensor | None = None

    def event(self, kind: str, **payload: Any) -> None:
        self.events.append(
            {
                "sequence": len(self.events),
                "kind": kind,
                "plan_index": self.active_plan,
                **payload,
            }
        )

    def begin_plan(self, info: dict[str, Any], solver_kind: str) -> None:
        if self.active_plan is not None:
            raise RuntimeError("nested planner trace")
        self.plan_index += 1
        self.round_index = 0
        self.active_plan = self.plan_index
        self.current_info = clone_value(info)
        self.latest_local_goal = None
        self.event(
            "solver_input",
            solver_kind=solver_kind,
            mapping=value_record(info),
            mapping_sha256=canonical_sha256(info),
        )

    def end_plan(self, output: dict[str, Any] | None) -> None:
        if output is not None:
            self.event(
                "solver_output",
                actions=value_record(output.get("actions")),
                costs=value_record(output.get("costs")),
            )
        self.active_plan = None
        self.current_info = None
        self.latest_local_goal = None

    def observe_local_goal(self, value: torch.Tensor) -> None:
        self.latest_local_goal = clone_value(value)

    def fit(
        self,
        *,
        candidates: torch.Tensor,
        costs: torch.Tensor,
        indices: torch.Tensor,
        mean: torch.Tensor,
        effective_std: torch.Tensor,
        elite_costs: torch.Tensor,
    ) -> None:
        round_index = self.round_index
        self.round_index += 1
        payload: dict[str, Any] = {
            "round_index": round_index,
            "elite_indices": value_record(indices),
            "elite_costs": value_record(elite_costs),
            "mean": value_record(mean),
            "effective_std": value_record(effective_std),
        }
        if round_index == 0:
            payload["candidates"] = value_record(candidates)
            payload["costs"] = value_record(costs)
            self.capture_bank(candidates, costs, indices)
        self.event("cem_fit", **payload)

    def capture_bank(
        self,
        candidates: torch.Tensor,
        costs: torch.Tensor,
        indices: torch.Tensor,
    ) -> None:
        if self.bank is not None or self.active_plan != 0 or self.current_info is None:
            return
        if self.latest_local_goal is None:
            raise RuntimeError("local goal was not observed before first CEM fit")
        content = {
            "sentinel_id": self.sentinel.sentinel_id,
            "benchmark": self.sentinel.benchmark,
            "method": self.sentinel.method,
            "seed": self.sentinel.seed,
            "horizon": self.sentinel.horizon,
            "info": clone_value(self.current_info),
            "candidates": clone_value(candidates),
            "costs": clone_value(costs),
            "elite_indices": clone_value(indices),
            "actual_local_goal": clone_value(self.latest_local_goal),
        }
        content["content_sha256"] = canonical_sha256(content)
        self.bank = content

    def capture_top_bank(self, actions: torch.Tensor) -> None:
        if self.bank is not None or self.active_plan != 0 or self.current_info is None:
            return
        if self.latest_local_goal is None:
            raise RuntimeError("local goal was not observed before prior-top output")
        content = {
            "sentinel_id": self.sentinel.sentinel_id,
            "benchmark": self.sentinel.benchmark,
            "method": self.sentinel.method,
            "seed": self.sentinel.seed,
            "horizon": self.sentinel.horizon,
            "info": clone_value(self.current_info),
            "top_actions": clone_value(actions),
            "actual_local_goal": clone_value(self.latest_local_goal),
        }
        content["content_sha256"] = canonical_sha256(content)
        self.bank = content

    def write(self) -> None:
        if self.trace_path.exists() or self.bank_path.exists():
            raise FileExistsError("diagnostic trace output already exists")
        if self.bank is None:
            raise RuntimeError("first-call comparison bank was not captured")
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = Path(__file__).resolve().parent
        source_manifest = snapshot / "SOURCE-MANIFEST.sha256"
        payload = {
            "kind": "gdp_cem_e19_discrepancy_trace",
            "sentinel": {
                "sentinel_id": self.sentinel.sentinel_id,
                "e19_array_id": self.sentinel.e19_array_id,
                "benchmark": self.sentinel.benchmark,
                "method": self.sentinel.method,
                "seed": self.sentinel.seed,
                "horizon": self.sentinel.horizon,
                "e19_result_sha256": self.sentinel.e19_result_sha256,
            },
            "repeat": self.repeat,
            "planner": spec.PLANNER,
            "events": self.events,
            "event_stream_sha256": canonical_sha256(self.events),
            "bank_content_sha256": self.bank["content_sha256"],
            "diagnostic_source_manifest_sha256": (
                sha256_file(source_manifest) if source_manifest.exists() else None
            ),
            "diagnostic_protocol_sha256": sha256_file(
                snapshot / spec.PROTOCOL_FILENAME
            ),
            "e19_source_manifest_sha256": spec.E19_SOURCE_MANIFEST_SHA256,
            "e19_protocol_sha256": spec.E19_PROTOCOL_SHA256,
            "official_sage_commit": spec.SAGE_GIT_COMMIT,
            "official_sage_tree": spec.SAGE_GIT_TREE,
            "observational_only": True,
            "official_sage_source_modified": False,
            "checkpoint_modified": False,
            "planner_parameter_modified": False,
            "protected_metric_artifact_read": False,
            "e18_vs_sage_comparison_run": False,
            "d5_read": False,
        }
        self.trace_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        torch.save(self.bank, self.bank_path)


def _install_model_trace(module, recorder: TraceRecorder, benchmark: str) -> None:
    if benchmark == "pusht":
        original = module.SAGECostModel

        class TracedModel(original):
            def _history_latents(self, info):
                raw = info.get("_proposal_pixels_raw")
                output = super()._history_latents(info)
                recorder.event(
                    "history_latents",
                    input=value_record(raw),
                    output=value_record(output),
                )
                return output

            def _final_goal_latents(self, info):
                output = super()._final_goal_latents(info)
                recorder.event(
                    "final_goal_latents",
                    input=value_record(info.get("goal")),
                    output=value_record(output),
                )
                return output

            def _local_goal_latents(self, info):
                before = dict(self._subgoal_cache)
                output = super()._local_goal_latents(info)
                after = dict(self._subgoal_cache)
                recorder.observe_local_goal(output)
                recorder.event(
                    "local_goal",
                    cache_keys=[list(key) for key in sorted(after)],
                    cache_hits=sum(key in before for key in after),
                    new_cache_values={
                        str(key): value_record(after[key])
                        for key in sorted(set(after) - set(before))
                    },
                    output=value_record(output),
                )
                return output

            def top_candidate(self, info, *, action_horizon):
                output = super().top_candidate(info, action_horizon=action_horizon)
                recorder.event("prior_top_actions", output=value_record(output))
                return output

        module.SAGECostModel = TracedModel
        return

    original = module.CubeSAGEModel

    class TracedModel(original):
        def _history(self, info):
            source = info.get("prior_pixels", info.get("pixels"))
            output = super()._history(info)
            recorder.event(
                "history_latents", input=value_record(source), output=value_record(output)
            )
            return output

        def _goal(self, info):
            output = super()._goal(info)
            recorder.event(
                "final_goal_latents",
                input=value_record(info.get("goal")),
                output=value_record(output),
            )
            return output

        def local_goal(self, info):
            keys = _stage_keys(info, self.goal_offset_steps)
            before = {key: canonical_sha256(value) for key, value in self._cache.items()}
            output = super().local_goal(info)
            after = {key: canonical_sha256(value) for key, value in self._cache.items()}
            recorder.observe_local_goal(output)
            returned = [canonical_sha256(output[row : row + 1]) for row in range(len(keys))]
            recorder.event(
                "cube_local_goal_cache",
                stage_keys=[list(key) for key in keys],
                cache_hit=[key in before for key in keys],
                values_before={str(key): before[key] for key in sorted(before)},
                values_after={str(key): after[key] for key in sorted(after)},
                new_keys=[list(key) for key in sorted(set(after) - set(before))],
                returned_by_stage_key=returned,
                output=value_record(output),
            )
            return output

        def top_prior(self, info, horizon):
            output = super().top_prior(info, horizon)
            recorder.event("prior_top_actions", output=value_record(output))
            return output

    module.CubeSAGEModel = TracedModel


def _install_solver_trace(module, recorder: TraceRecorder, benchmark: str) -> None:
    original_prior = module.PriorInitializedCEM
    original_gaussian = module.GaussianCEM
    original_top = module.PriorTopMode

    class FitTraceMixin:
        _trace_clamp_after_fit = False

        def _fit(self, candidates, costs, elites):
            mean, std, elite_costs = super()._fit(candidates, costs, elites)
            _, indices = torch.topk(costs, k=elites, dim=1, largest=False)
            effective_std = (
                std.clamp_min(1.0e-6) if self._trace_clamp_after_fit else std
            )
            recorder.fit(
                candidates=candidates,
                costs=costs,
                indices=indices,
                mean=mean,
                effective_std=effective_std,
                elite_costs=elite_costs,
            )
            return mean, std, elite_costs

        def solve(self, info, init_action=None):
            recorder.begin_plan(info, type(self).__name__)
            output = None
            try:
                output = super().solve(info, init_action=init_action)
                return output
            finally:
                recorder.end_plan(output)

    class TracedPrior(FitTraceMixin, original_prior):
        pass

    class TracedGaussian(FitTraceMixin, original_gaussian):
        _trace_clamp_after_fit = benchmark == "pusht"

    class TracedTop(original_top):
        def solve(self, info, init_action=None):
            recorder.begin_plan(info, type(self).__name__)
            output = None
            try:
                output = super().solve(info, init_action=init_action)
                recorder.capture_top_bank(output["actions"])
                return output
            finally:
                recorder.end_plan(output)

    module.PriorInitializedCEM = TracedPrior
    module.GaussianCEM = TracedGaussian
    module.PriorTopMode = TracedTop


def main() -> None:
    sentinel_id = int(os.environ["E19_DISCREPANCY_SENTINEL_ID"])
    repeat = int(os.environ["E19_DISCREPANCY_REPEAT"])
    trace_path = Path(os.environ["E19_DISCREPANCY_TRACE"])
    bank_path = Path(os.environ["E19_DISCREPANCY_BANK"])
    sentinel = spec.sentinel_by_id(sentinel_id)
    if repeat not in spec.REPEATS:
        raise ValueError(f"invalid repeat {repeat}")
    recorder = TraceRecorder(
        sentinel=sentinel,
        repeat=repeat,
        trace_path=trace_path,
        bank_path=bank_path,
    )

    if sentinel.benchmark == "pusht":
        from sage.eval import pusht as evaluator
    else:
        from sage.eval import cube as evaluator
        from gdp_cem_e19_cube_generator_compat import (
            install_cube_generator_cache_compat,
        )

        install_cube_generator_cache_compat(evaluator)

    _install_model_trace(evaluator, recorder, sentinel.benchmark)
    _install_solver_trace(evaluator, recorder, sentinel.benchmark)
    error: BaseException | None = None
    try:
        evaluator.main()
    except BaseException as exc:  # preserve a technical trace before re-raising
        error = exc
        raise
    finally:
        if error is None:
            recorder.write()


if __name__ == "__main__":
    main()
