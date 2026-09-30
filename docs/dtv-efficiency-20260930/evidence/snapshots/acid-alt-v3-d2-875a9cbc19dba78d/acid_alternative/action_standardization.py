"""Strict planner-action standardizer provenance checks."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn import preprocessing


def validate_planner_action_standardizer(
    raw_actions: np.ndarray,
    actual_mean: np.ndarray,
    actual_scale: np.ndarray,
    expected_mean: np.ndarray,
    expected_scale: np.ndarray,
) -> dict[str, Any]:
    """Validate exact statistics or the documented legacy float32 fit.

    The released evaluator fits ``StandardScaler`` to the source HDF5 dtype.
    Early transition caches explicitly converted the same source values to
    float32 first. Compatibility is allowed only when the checkpoint values
    exactly reproduce a fresh float32 refit of the same source rows and the
    resulting difference remains within a small float32-rounding envelope.
    """

    values = np.asarray(raw_actions)
    if values.ndim != 2 or values.shape[1] == 0:
        raise RuntimeError("planner action column is not a nonempty matrix")
    usable = values[~np.isnan(values).any(axis=1)]
    if not len(usable) or not np.isfinite(usable).all():
        raise RuntimeError("planner action column has no finite usable rows")

    actual_mean = np.asarray(actual_mean, dtype=np.float64)
    actual_scale = np.asarray(actual_scale, dtype=np.float64)
    expected_mean = np.asarray(expected_mean, dtype=np.float64)
    expected_scale = np.asarray(expected_scale, dtype=np.float64)
    shape = (values.shape[1],)
    if any(
        array.shape != shape
        for array in (actual_mean, actual_scale, expected_mean, expected_scale)
    ):
        raise RuntimeError("planner action statistics have incompatible shapes")
    if not all(
        np.isfinite(array).all()
        for array in (actual_mean, actual_scale, expected_mean, expected_scale)
    ):
        raise RuntimeError("planner action statistics are non-finite")

    mean_difference = float(np.max(np.abs(actual_mean - expected_mean)))
    scale_difference = float(np.max(np.abs(actual_scale - expected_scale)))
    exact_mean = bool(np.array_equal(actual_mean, expected_mean))
    exact_scale = bool(np.array_equal(actual_scale, expected_scale))
    # Every registered planner action space is bounded to [-1, 1]. Keep this
    # an absolute four-epsilon envelope so a large-valued source cannot turn
    # the compatibility path into a permissive relative-tolerance check.
    tolerance = float(4.0 * np.finfo(np.float32).eps)

    legacy_mean_matches = False
    legacy_scale_matches = False
    if exact_mean and exact_scale:
        mode = "exact_source_dtype"
    else:
        float32_values = np.asarray(usable, dtype=np.float32)
        if not np.isfinite(float32_values).all():
            raise RuntimeError("float32 planner action compatibility is non-finite")
        legacy = preprocessing.StandardScaler().fit(float32_values)
        legacy_mean = np.asarray(legacy.mean_, dtype=np.float64)
        legacy_scale = np.asarray(legacy.scale_, dtype=np.float64)
        legacy_mean_matches = bool(np.array_equal(legacy_mean, expected_mean))
        legacy_scale_matches = bool(np.array_equal(legacy_scale, expected_scale))
        if not legacy_mean_matches:
            raise RuntimeError("planner action mean differs from scorer training")
        if not legacy_scale_matches:
            raise RuntimeError("planner action scale differs from scorer training")
        if mean_difference > tolerance or scale_difference > tolerance:
            raise RuntimeError(
                "legacy float32 planner action statistics exceed the rounding envelope"
            )
        mode = "exact_legacy_float32_refit"

    return {
        "status": "pass",
        "mode": mode,
        "source_action_dtype": str(values.dtype),
        "source_rows": int(len(values)),
        "usable_rows": int(len(usable)),
        "actual_mean": actual_mean.tolist(),
        "actual_scale": actual_scale.tolist(),
        "expected_mean": expected_mean.tolist(),
        "expected_scale": expected_scale.tolist(),
        "exact_source_dtype_match": {"mean": exact_mean, "scale": exact_scale},
        "exact_legacy_float32_refit_match": {
            "mean": legacy_mean_matches,
            "scale": legacy_scale_matches,
        },
        "maximum_absolute_difference": {
            "mean": mean_difference,
            "scale": scale_difference,
        },
        "float32_rounding_envelope": tolerance,
    }
