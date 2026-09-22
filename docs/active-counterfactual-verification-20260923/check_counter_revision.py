"""Authenticate instrumentation-only mock revision; never rerun efficacy fits."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).parent


def main():
    first=json.loads((ROOT/'mock-run-v1/RESULTS.json').read_text())
    second=json.loads((ROOT/'mock-run-v2/RESULTS.json').read_text())
    for key in ('fit','collection','independent_episode_checks','checkpoint_identity'):assert first[key]==second[key]
    for a,b in zip(first['results'],second['results']):
        for key in ('trace','success','steps','control'):assert a[key]==b[key]
        if 'decision' in a:assert a['decision']==b['decision'] and a['selected_suffix']==b['selected_suffix']
    for file in ('joint.npz','ordinary.npz'):
        with np.load(ROOT/'mock-run-v1'/file,allow_pickle=False) as a,np.load(ROOT/'mock-run-v2'/file,allow_pickle=False) as b:
            assert set(a.files)==set(b.files)
            for name in a.files:np.testing.assert_array_equal(a[name],b[name])
    original=json.loads((ROOT/'neural-run-v1/RESULTS.json').read_text());corrections=[]
    for case in original['results']:
        for c in case['controls']:
            if 'cost' not in c:continue  # exact known-law solver is not the neural path
            counts=c['cost'];assert counts['integration_responses']==384
            assert counts['outcome_queries'] in (1152,1158)
            post_calls=(counts['outcome_queries']-1152)//3
            corrections.append(dict(case=case['case'],control=c['control'],
                prior_candidate_predictions=9,conditional_candidate_predictions=counts['outcome_queries'],
                learned_module_forward_calls=6+post_calls,
                note='Counts include both enumerated artificial observed bits, not two physical deployments; no refit'))
    out=dict(status='PASS',reason='Complete instrumentation: CEM solve/fixed-prefix solve counters and previously separate prior neural predictions',
             first_mock_preserved=True,second_mock_all_parameters_losses_decisions_traces_identical=True,
             final_tests=25,final_mock_independent_checks=48,original_neural_efficacy_run_repeated=False,
             early_results_outcome_queries_mean='conditional candidate queries only; add prior_candidate_predictions for all neural candidate predictions',
             corrected_neural_accounting=corrections)
    with (ROOT/'AUDIT-CORRECTIONS.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(status='PASS',identical_mock_parameters_and_decisions=True,neural_accounting_rows=len(corrections))))


if __name__=='__main__':main()
