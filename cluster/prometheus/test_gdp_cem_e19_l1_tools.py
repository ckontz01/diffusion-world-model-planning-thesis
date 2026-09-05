import json

import pytest
import torch

from gdp_cem_e19_l1_tools import (
    boundary_rows, elite_rows, json_safe, observe_fit, opaque_paths, outcome_comparison,
    record_differences, selected_distribution, tensor_delta, trace_comparison,
)


def fit(candidates, costs, elites):
    values, indices = torch.topk(costs, elites, dim=1, largest=False)
    mean, std = selected_distribution(candidates, indices, clamp=False)
    return mean, std, values


def test_capture_is_original_selection_without_extra_topk():
    calls = []
    # Count low-level selection through a mode, not a replacement that changes func identity.
    class Count(torch.overrides.TorchFunctionMode):
        def __torch_function__(self, func, types, args=(), kwargs=None):
            if func is torch.topk:
                calls.append(1)
            return func(*args, **(kwargs or {}))
    candidates = torch.arange(24.).reshape(2, 6, 2)
    costs = torch.zeros(2, 6)
    with Count():
        mean, std, values, indices = observe_fit(fit, candidates, costs, 3)
    assert len(calls) == 1
    reconstructed = selected_distribution(candidates, indices, clamp=False)
    assert torch.equal(mean, reconstructed[0]) and torch.equal(std, reconstructed[1])
    # A different equally valid tied selection can produce another fitted distribution.
    alternative = indices.clone()
    for row in range(2):
        alternative[row] = torch.tensor([i for i in range(6) if i not in indices[row].tolist()])
    assert not torch.equal(mean, selected_distribution(candidates, alternative, clamp=False)[0])


def test_boundary_ties_and_near_ties():
    costs = torch.tensor([[0., 1., 1., 2.], [0., 1., 1.0000001, 2.]])
    rows = boundary_rows(costs, 2)
    assert rows[0]["exact_boundary_tie"]
    assert not rows[1]["exact_boundary_tie"]
    assert rows[1]["near_boundary_1e_6_relative"]


def test_elite_overlap_is_not_binary():
    row = elite_rows(torch.tensor([[0, 1, 2]]), torch.tensor([[1, 2, 3]]))[0]
    assert row["intersection"] == 2 and row["replaced_elites"] == 1
    assert row["jaccard"] == .5


def test_duplicate_elites_rejected():
    with pytest.raises(ValueError):
        elite_rows(torch.tensor([[0, 0]]), torch.tensor([[0, 1]]))


def test_tensor_delta_shape_dtype_and_values():
    a = torch.zeros(2, 3)
    b = a.clone(); b[1, 2] = 2
    row = tensor_delta(a, b)
    assert row["changed_elements"] == 1 and row["changed_rows"] == 1
    assert row["max_abs"] == 2
    assert not tensor_delta(a, a.double())["exact"]
    assert not tensor_delta(a, torch.zeros(3))["shape_matches"]


def test_opaque_metadata_and_numerical_records_remain_separate():
    assert opaque_paths({"a": {"kind": "repr", "value": "<object 0x123>"}}) == ["a"]
    assert opaque_paths({"a": {"kind": "torch", "sha256": "x"}}) == []


def test_field_difference_is_not_whole_file_boolean():
    a = {"mapping": {"pixels": {"kind": "torch", "sha256": "a"}}}
    b = {"mapping": {"pixels": {"kind": "torch", "sha256": "b"}}}
    assert record_differences(a, b)[0]["path"] == "mapping.pixels"


def test_trace_projection_does_not_erase_original_difference():
    def trace(time_hash):
        return {"events": [{"sequence": 0, "kind": "solver_input", "plan_index": 0,
                            "mapping": {"render_time": {"kind": "torch", "sha256": time_hash}},
                            "mapping_sha256": time_hash}]}
    row = trace_comparison(trace("a"), trace("b"))
    assert row["events_differing_by_kind"] == {"solver_input": 1}
    assert row["differences_excluding_render_time_and_derived_mapping_hash"] == 0


def test_missing_event_is_not_silently_zipped():
    a = {"events": [{"sequence": 0, "plan_index": 0, "kind": "solver_input"}]}
    b = {"events": []}
    assert trace_comparison(a, b)["missing_event_count"] == 1


def test_episode_flips_do_not_mean_all_outcomes_changed():
    a = {"num_eval": 50, "metrics": {"episode_successes": [True] * 50}}
    b = {"num_eval": 50, "metrics": {"episode_successes": [False] + [True] * 49}}
    row = outcome_comparison(a, b)
    assert row["changed_episode_count"] == 1 and row["lost_success_indices"] == [0]


def test_nonfinite_costs_rejected():
    with pytest.raises(ValueError):
        boundary_rows(torch.tensor([[float("nan"), 1., 2.]]), 1)


def test_nonfinite_metadata_is_explicit_and_not_a_false_pair_difference():
    a = {"placeholder": float("nan"), "positive": float("inf")}
    b = {"placeholder": float("nan"), "positive": float("inf")}
    assert record_differences(a, b) == []
    safe = json.loads(json.dumps(json_safe(a), allow_nan=False))
    assert safe["placeholder"] == {"kind": "nonfinite_scalar", "value": "nan"}
    b["positive"] = float("-inf")
    assert record_differences(a, b)[0]["path"] == "positive"
