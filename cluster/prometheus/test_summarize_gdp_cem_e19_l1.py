import pytest

from summarize_gdp_cem_e19_l1 import distribution, trace_stages


def test_stage_reduction_distinguishes_metadata_then_computation():
    def trace(metadata, later_pixels):
        return {'events': [
            {'kind': 'solver_input', 'plan_index': 0, 'sequence': 0,
             'mapping': {'pixels': 'same', 'id': metadata}},
            {'kind': 'solver_output', 'plan_index': 0, 'sequence': 1,
             'actions': 'same', 'costs': [float('nan')]},
            {'kind': 'solver_input', 'plan_index': 1, 'sequence': 2,
             'mapping': {'pixels': later_pixels}},
            {'kind': 'history_latents', 'plan_index': 1, 'sequence': 3,
             'input': later_pixels, 'output': later_pixels},
        ]}
    result = trace_stages(trace(1, 'a'), trace(2, 'b'))
    assert result['first_plan_recorded_computation_exact']
    assert result['per_plan'][0]['solver_input_changed_keys'] == ['id']
    assert result['first_observed_computation_difference_by_field']['history_latents.output']['plan_index'] == 1


def test_stage_reduction_rejects_unaligned_events():
    with pytest.raises(ValueError):
        trace_stages({'events': [{'kind': 'solver_input', 'plan_index': 0}]}, {'events': []})


def test_summary_reports_zero_replacements_in_denominator():
    assert distribution([0, 0, 1, 3]) == {'n': 4, 'min': 0, 'median': .5, 'mean': 1, 'max': 3}
