from acid_alternative_diagnostics.analyze_sensitivity import expected_keys


def test_frozen_sensitivity_matrix_has_105_runs_per_task():
    keys = expected_keys()
    assert len(keys) == 315
    assert sum(key[0] == "pusht" for key in keys) == 105
