import numpy as np
import torch
from acid_alternative_diagnostics.capture_candidate_pools import (
    FinalPopulationRecorder,
    stack_info,
)


class DummyCost:
    def get_cost(self, info, candidates):
        return candidates.square().sum(dim=(-1, -2))


def test_recorder_retains_only_final_population_and_exact_elite_mean():
    recorder = FinalPopulationRecorder(DummyCost(), iterations=2, topk=1)
    info = {
        "pixels": torch.arange(12).reshape(1, 2, 2, 3),
        "ignored": np.asarray([["a", "b"]], dtype=object),
    }
    first = torch.ones(1, 2, 1, 1)
    second = torch.tensor([[[[2.0]], [[0.5]]]])
    recorder.get_cost(info, first)
    recorder.get_cost(info, second)
    assert recorder.call_count == 2
    assert len(recorder.candidates) == 1
    assert torch.equal(recorder.candidates[0], second[0])
    assert torch.equal(recorder.elite_means[0], torch.tensor([[0.5]]))
    assert set(recorder.info_tensors[0]) == {"pixels"}


def test_stack_info_requires_matching_keys_and_stacks_pool_axis():
    result = stack_info([{"x": torch.tensor([1, 2])}, {"x": torch.tensor([3, 4])}])
    assert torch.equal(result["x"], torch.tensor([[1, 2], [3, 4]]))
