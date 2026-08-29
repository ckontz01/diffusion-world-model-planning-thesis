from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import torch

import gdp_cem_e19_discrepancy_specs as spec
from trace_gdp_cem_e19_discrepancy import (
    TraceRecorder,
    _install_solver_trace,
    _stage_keys,
    canonical_sha256,
    value_record,
)


def test_canonical_tensor_hash_records_dtype_shape_and_bytes() -> None:
    value = torch.tensor([[1.0, 2.0]], dtype=torch.bfloat16)
    record = value_record(value)
    assert record["dtype"] == "torch.bfloat16"
    assert record["shape"] == [1, 2]
    assert len(record["sha256"]) == 64
    assert canonical_sha256(value) == canonical_sha256(value.clone())
    assert canonical_sha256(value) != canonical_sha256(value + 1)


def test_stage_keys_ignore_candidate_expansion() -> None:
    info = {
        "pixels": torch.zeros(2, 300, 3, 3, 8, 8),
        "_env_id": np.asarray([[4] * 300, [9] * 300]),
        "_plan_call": torch.tensor([[7] * 300, [7] * 300]),
        "_remaining_steps": np.asarray([[100] * 300, [80] * 300]),
        "_option_duration_steps": np.asarray([[25] * 300, [25] * 300]),
    }
    assert _stage_keys(info, 150) == [(4, 7, 100, 25), (9, 7, 80, 25)]


def test_recorder_seals_first_round_and_bank(tmp_path) -> None:
    trace = tmp_path / "trace.json"
    bank = tmp_path / "bank.pt"
    recorder = TraceRecorder(
        sentinel=spec.SENTINELS[0], repeat=0, trace_path=trace, bank_path=bank
    )
    info = {"pixels": torch.arange(4).reshape(1, 1, 2, 2)}
    recorder.begin_plan(info, "mock")
    recorder.observe_local_goal(torch.ones(1, 1, 2))
    candidates = torch.arange(12, dtype=torch.float32).reshape(1, 3, 2, 2)
    costs = torch.tensor([[3.0, 1.0, 2.0]])
    indices = torch.tensor([[1, 2]])
    recorder.fit(
        candidates=candidates,
        costs=costs,
        indices=indices,
        mean=candidates[:, 1:].mean(1),
        effective_std=candidates[:, 1:].std(1),
        elite_costs=torch.tensor([[1.0, 2.0]]),
    )
    recorder.end_plan({"actions": torch.zeros(1, 2, 2), "costs": [1.5]})
    recorder.write()

    payload = json.loads(trace.read_text())
    saved = torch.load(bank, weights_only=False)
    assert payload["events"][1]["kind"] == "cem_fit"
    assert payload["events"][1]["round_index"] == 0
    assert saved["content_sha256"] == payload["bank_content_sha256"]
    assert torch.equal(saved["elite_indices"], indices)
    assert torch.equal(saved["actual_local_goal"], torch.ones(1, 1, 2))


def test_solver_wrapper_observes_original_fit_without_replacing_it(tmp_path) -> None:
    class PriorInitializedCEM:
        @staticmethod
        def _fit(candidates, costs, elites):
            values, indices = torch.topk(costs, elites, dim=1, largest=False)
            rows = torch.arange(candidates.size(0))[:, None]
            selected = candidates[rows, indices]
            return selected.mean(1), selected.std(1), values

        def solve(self, info, init_action=None):
            del init_action
            candidates = torch.tensor([[[[0.0]], [[2.0]], [[4.0]]]])
            costs = torch.tensor([[2.0, 0.0, 1.0]])
            recorder.observe_local_goal(torch.ones(1, 1, 1))
            mean, _, values = self._fit(candidates, costs, 2)
            return {"actions": mean, "costs": values.mean(1).tolist()}

    class GaussianCEM(PriorInitializedCEM):
        pass

    class PriorTopMode:
        def solve(self, info, init_action=None):
            del info, init_action
            return {"actions": torch.ones(1, 1, 1), "costs": [float("nan")]}

    module = SimpleNamespace(
        PriorInitializedCEM=PriorInitializedCEM,
        GaussianCEM=GaussianCEM,
        PriorTopMode=PriorTopMode,
    )
    recorder = TraceRecorder(
        sentinel=spec.SENTINELS[0],
        repeat=0,
        trace_path=tmp_path / "trace.json",
        bank_path=tmp_path / "bank.pt",
    )
    _install_solver_trace(module, recorder, "cube")
    result = module.GaussianCEM().solve({"pixels": torch.zeros(1, 1)})
    assert torch.equal(result["actions"], torch.tensor([[[3.0]]]))
    fit = next(row for row in recorder.events if row["kind"] == "cem_fit")
    assert fit["elite_indices"]["sha256"] == value_record(
        torch.tensor([[1, 2]])
    )["sha256"]
