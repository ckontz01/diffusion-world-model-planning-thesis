#!/usr/bin/env python3
"""Unit tests for the frozen E8D bootstrap and advancement rules."""

from __future__ import annotations

from pathlib import Path

import numpy as np

import analyze_gdp_cem_e8d_closed_loop as analysis


def record(equal: float, pusht: float, reacher: float, cube: float):
    return {
        "equal_task": {"estimate": equal},
        "per_task": {
            "pusht": {"estimate": pusht},
            "reacher": {"estimate": reacher},
            "cube": {"estimate": cube},
        },
    }


def main() -> None:
    for protected in ("d3", "C1", "i1"):
        try:
            analysis.e8d.reject_protected_path(Path("/tmp") / protected / "artifact")
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"E8D protected path was accepted: {protected}")
    for allowed in ("gdp-cem-e8d", "candidate3", "acid1"):
        analysis.e8d.reject_protected_path(Path("/tmp") / allowed / "artifact")

    indices = analysis.bootstrap_indices()
    vectors = {
        "pusht": np.ones(analysis.EVAL_COUNT),
        "reacher": np.zeros(analysis.EVAL_COUNT),
        "cube": np.tile((0.0, 1.0), analysis.EVAL_COUNT // 2),
    }
    summary = analysis.summarize(vectors, indices)
    if (
        summary["per_task"]["pusht"]["estimate"] != 1.0
        or summary["per_task"]["reacher"]["estimate"] != 0.0
        or summary["per_task"]["cube"]["estimate"] != 0.5
        or summary["equal_task"]["estimate"] != 0.5
    ):
        raise RuntimeError("E8D summary estimates differ")
    sign = analysis.exact_sign(np.asarray((1, 1, -1, 0), dtype=np.float64))
    if sign != {"positive": 2, "negative": 1, "ties": 1, "two_sided_p": 1.0}:
        raise RuntimeError("E8D exact sign test differs")

    contrasts = {
        "gadr_true_refresh_minus_acid": record(0.01, -0.10, 0.02, 0.11),
        "gadr_true_refresh_minus_b0": record(0.02, 0.01, 0.02, 0.03),
        "gadr_true_refresh_minus_gaussian_refresh": record(0.03, 0.01, 0.03, 0.05),
        "gadr_true_refresh_minus_gadr_shuffled_refresh": record(0.01, 0.02, -0.01, 0.02),
        "gadr_true_select_minus_acid": record(-0.05, -0.04, -0.05, -0.06),
        "gadr_true_select_minus_b0": record(0.01, 0.01, 0.01, 0.01),
        "gadr_true_select_minus_gaussian_select": record(0.01, 0.01, 0.01, 0.01),
        "gadr_true_select_minus_gadr_shuffled_select": record(0.01, 0.01, -0.01, 0.03),
    }
    refresh, selector = analysis.gate_results(contrasts)
    if not all(refresh.values()) or not all(selector.values()):
        raise RuntimeError("E8D inclusive-margin gate test failed")
    contrasts["gadr_true_refresh_minus_acid"] = record(0.0, -0.10, 0.02, 0.08)
    contrasts["gadr_true_select_minus_acid"] = record(-0.050001, -0.04, -0.05, -0.06)
    refresh, selector = analysis.gate_results(contrasts)
    if (
        refresh["1_true_refresh_above_acid_equal_task"]
        or not refresh["6_true_refresh_within_010_acid_each_task"]
        or selector["4_true_select_within_005_acid_equal_task"]
    ):
        raise RuntimeError("E8D strict/inclusive boundary test failed")
    print("E8D analyzer tests passed")


if __name__ == "__main__":
    main()
