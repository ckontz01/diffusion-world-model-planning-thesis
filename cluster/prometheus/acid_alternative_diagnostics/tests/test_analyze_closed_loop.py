import numpy as np
from acid_alternative_diagnostics.analyze_closed_loop import (
    bootstrap_contrast,
    exact_paired_two_sided,
    parse_run,
    validate_task_set,
)


def test_parse_run_preserves_equals_in_path():
    task, arm, seed, path = parse_run("pusht=diffusion=6101=/tmp/a=b.json")
    assert (task, arm, seed) == ("pusht", "diffusion", 6101)
    assert path.as_posix() == "/tmp/a=b.json"


def test_exact_paired_test_counts_discordance():
    result = exact_paired_two_sided(np.array([1, 1, 0]), np.array([0, 1, 1]))
    assert result["first_wins"] == 1
    assert result["first_losses"] == 1
    assert result["two_sided_exact_p"] == 1.0


def test_cluster_bootstrap_retains_point_estimate_and_is_reproducible():
    values = {"pusht": np.ones((3, 4)), "cube": np.zeros((3, 5))}
    first = bootstrap_contrast(values, seed=9, repetitions=100)
    second = bootstrap_contrast(values, seed=9, repetitions=100)
    assert first == second
    assert first["estimate"] == 0.5


def test_confirmation_requires_full_frozen_task_suite():
    validate_task_set("development", {"pusht"})
    validate_task_set("confirmation", {"pusht", "reacher", "cube"})
    try:
        validate_task_set("confirmation", {"pusht"})
    except RuntimeError as error:
        assert "missing=['cube', 'reacher']" in str(error)
    else:
        raise AssertionError("partial confirmation task set was accepted")
