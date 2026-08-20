import numpy as np
from acid_alternative_diagnostics.aggregate_mechanism_audits import (
    stratified_bootstrap,
)


def test_mechanism_bootstrap_equal_weights_tasks_and_is_reproducible():
    values = {
        "pusht": np.ones((3, 4)),
        "reacher": np.zeros((3, 5)),
        "cube": np.full((3, 6), 0.5),
    }
    first = stratified_bootstrap(values, seed=7, repetitions=100)
    second = stratified_bootstrap(values, seed=7, repetitions=100)
    assert first == second
    assert first["estimate"] == 0.5
