from __future__ import annotations

import numpy as np

import gdp_cem_e15_specs as spec
from analyze_gdp_cem_e15_offline import (
    PRIMARY_METRICS,
    expected_cells,
    gmm_structural,
    manifest_scientific_label,
    scientific_label,
    vad_mechanism,
)


def fake_aggregates() -> dict[tuple[str, str, int], dict]:
    result = {}
    for task, condition, seed in expected_cells():
        base = {
            "vad": 1.0,
            "diagonal_gaussian": 2.0,
            "direct_gmm": 1.5,
            "vad_shuffled": 3.0,
            "vad_unconditional": 4.0,
        }[condition]
        metrics = {name: base for name in PRIMARY_METRICS}
        result[(task, condition, seed)] = {
            "equal_cell_mean": dict(metrics),
            "per_tau_equal_cell_mean": {
                str(tau): dict(metrics) for tau in spec.TAU_VALUES
            },
        }
    return result


def test_vad_gate_requires_every_seed_task_and_null_direction() -> None:
    aggregates = fake_aggregates()
    assert vad_mechanism(aggregates)["pass"] is True
    for tau in (15, 20):
        aggregates[("cube", "vad", 7202)]["per_tau_equal_cell_mean"][str(tau)][
            PRIMARY_METRICS[0]
        ] = 5.0
    result = vad_mechanism(aggregates)
    assert result["pass"] is False
    assert (
        result["seed_results"]["7202"]["per_task_two_of_three_durations"][
            "cube"
        ]["pass"]
        is False
    )


def test_gmm_structural_rule_accepts_balanced_used_modes() -> None:
    records = {}
    delta = np.repeat(
        np.asarray([value[0] for value in spec.DELTA_TAU_PAIRS], dtype=np.int64),
        spec.GMM_MODES,
    )
    tau = np.repeat(
        np.asarray([value[1] for value in spec.DELTA_TAU_PAIRS], dtype=np.int64),
        spec.GMM_MODES,
    )
    rows = len(delta)
    prior = np.full((rows, spec.GMM_MODES), 1.0 / spec.GMM_MODES)
    posterior = np.full_like(prior, 1.0e-6)
    posterior[np.arange(rows), np.arange(rows) % spec.GMM_MODES] = 1.0
    posterior /= posterior.sum(axis=1, keepdims=True)
    for task in spec.TASKS:
        for seed in spec.MODEL_SEEDS:
            records[(task, "direct_gmm", seed)] = {
                "delta": delta,
                "tau": tau,
                "gmm": {
                    "prior_probability": prior,
                    "posterior_probability": posterior,
                    "sampled_mode_fraction": prior,
                    "normalized_prior_entropy": np.ones(rows),
                    "effective_prior_modes": np.full(rows, spec.GMM_MODES),
                },
            }
    result = gmm_structural(records)
    assert result["pass"] is True
    assert all(
        bank["posterior_used_modes"] == spec.GMM_MODES
        for bank in result["banks"].values()
    )


def test_metric_and_manifest_scientific_labels_are_intentionally_distinct() -> None:
    assert scientific_label(1.0e-2) == "1e-2"
    assert manifest_scientific_label(1.0e-2) == "1e-02"
    assert scientific_label(5.0e-2) == "5e-2"
    assert manifest_scientific_label(1.0e-6) == "1e-06"
