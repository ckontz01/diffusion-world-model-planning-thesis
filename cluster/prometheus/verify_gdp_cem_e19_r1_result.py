"""Independently verify the small R1 evidence package without simulator access."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'e19-r1-evidence'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert sha(ROOT/'INITIAL-SOURCE-MANIFEST.sha256')=='2c5ea97ae66b1f4714bcd58f7a33d3b57bb9276df672f5023966bf96c6a33a67'
    manifest=ROOT/'CUBE-REPLACEMENT-SOURCE-MANIFEST.sha256'
    assert sha(manifest)=='549757ef959a79ba77de5a4ec2384edb71ab2639f72d265f66b7c1a64ebe7f6a'
    for line in manifest.read_text().splitlines():
        h,n=line.split(maxsplit=1); assert sha(ROOT.parent/n)==h
    p=ROOT/'R1-REVIEW.json'
    assert sha(p)=='1939a10896c5c019508b421278798f57cd1ac66649a70d25bab6748b01338fbe'
    assert (ROOT/'sha256.txt').read_text().strip()==sha(p)+'  R1-REVIEW.json'
    stimuli=ROOT/'STIMULI.json'
    assert sha(stimuli)=='45ac71f23c4ff96df15a7eb2c019456c7847bec4cae3582c57dbefb8f085848a'
    s=json.loads(stimuli.read_text()); x=json.loads(p.read_text())
    assert len(s['cases'])==5 and x['valid_processes']==20 and x['valid_post_restoration_steps']==300
    assert x['summary_sha256']=='8c243ee917315ae3c0eba9d06be6c29fb6f9c28f9d31859f6c6a880e465fcca2'
    assert x['decision']=='hold_confirmation_pending_restoration_contract_resolution'
    for key in ('new_planning','model_changes','protected_read','benchmark_table','historical_decisions_changed','confirmation_ready'):
        assert x[key] is False
    assert {(p['stack'],p['case']['case_id']) for p in x['pairs']}=={(st,c) for st in ('sage','e18') for c in range(5)}
    assert len(x['full_trace_inventory'])==20
    for pair in x['pairs']:
        case=pair['case']; assert case==s['cases'][case['case_id']]
        assert case['candidate_index']==(None if case['case_id']==2 else 1)
        assert case['action_source']==('saved historical planner output' if case['case_id']==2 else 'fixed diagnostic action stimulus')
        assert pair['action_repeat_exact'] and pair['stage_alignment_exact'] and pair['initial_supplied_state_repeat_exact']
        for r in pair['repeats']:
            assert r['steps']==15 and r['fixed_return_calls']==1 and r['stopped_at_cap']
            assert r['observation_probe_captured_state_unchanged'] and r['policy_vs_env']['exact']
            assert r['reset_kwargs']['seed'] is None and r['dataset_seed_columns']==[]
            assert x['full_trace_inventory'][r['trace_path']]==r['trace_sha256']
            if case['task']=='cube':
                assert r['reset_internal_steps']==2
                assert all(r['restoration'][key]['exact'] for key in ('qpos','qvel','target_pos','target_quat'))
        steps=[q for q in pair['comparisons'] if q['stage'].startswith('before_step:')]
        assert len(steps)==15 and all(not q.get('primitive_action') for q in steps)
    print('Verified: 5 stimuli, 20 valid traces, 300 post-restoration steps, identical paired actions, confirmation remains on hold.')
if __name__=='__main__': main()
