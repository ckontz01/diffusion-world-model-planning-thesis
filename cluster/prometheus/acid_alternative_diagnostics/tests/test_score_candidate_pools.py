import argparse
from pathlib import Path

import pytest
import torch
from acid_alternative_diagnostics.score_candidate_pools import (
    expand_pool_tensor,
    parse_scorer_spec,
)


def test_parse_scorer_spec_keeps_path_tail():
    label, arm, path = parse_scorer_spec("d-6101=diffusion=/tmp/a=b.pt")
    assert label == "d-6101"
    assert arm == "diffusion"
    assert path == Path("/tmp/a=b.pt")


def test_parse_scorer_spec_rejects_unknown_arm():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_scorer_spec("x=unknown=/tmp/a.pt")


def test_expand_pool_tensor_repeats_only_candidate_dimension():
    value = torch.arange(6).reshape(2, 3)
    expanded = expand_pool_tensor(value, 4, torch.device("cpu"))
    assert expanded.shape == (1, 4, 2, 3)
    assert torch.equal(expanded[0, 3], value)
