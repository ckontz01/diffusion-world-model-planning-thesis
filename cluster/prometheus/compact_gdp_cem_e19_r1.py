"""Produce a small review package from verified R1 traces and analysis."""
import argparse
import json
from pathlib import Path
from analyze_gdp_cem_e19_r1 import read,sha,stages,delta,core,differences,coverage

def compact_difference(rows):
    return [{k:v for k,v in row.items() if k in ('path','a_hash','b_hash','delta')} for row in rows]
def main():
    p=argparse.ArgumentParser(); p.add_argument('summary',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
    full=read(a.summary); pairs=[]
    for pair in full['pairs']:
        st=pair['stack']; cid=pair['case']['case_id']
        paths=[Path(q) for q in full['inventories'] if f'/{st}/case-{cid}/' in q]
        paths.sort(); ts=[read(q) for q in paths]
        assert len(ts)==2 and all(coverage(t) for t in ts)
        fs=[stages(t)['before_first_action#0'] for t in ts]
        records=[]
        for r,t,f in zip(pair['repeats'],ts,fs):
            records.append({k:v for k,v in r.items() if k!='dataset_endpoints'})
            records[-1].update(env_rng_seed=f['rng']['env_seed'],
                env_rng_state=f['rng']['env'],reset_internal_steps=t.get('reset_internal_step_count',0),
                dataset_seed_columns=[c for c in r['dataset_endpoints']['columns'] if 'seed' in c],
                dataset_load_args=r['dataset_endpoints']['args'],
                source_hashes=t['source_hashes'],action_scaler=t['action_scaler'],
                trace_path=str(paths[len(records)-1]),trace_sha256=sha(paths[len(records)-1]))
        comparisons=[]
        for row in pair['comparisons']:
            comparisons.append({'stage':row['stage'],**{k:compact_difference(v) for k,v in row.items() if k!='stage'},
                'core_physical_exact':not bool(row.get('core_physical'))})
        pairs.append(dict(case=pair['case'],stack=st,stage_alignment_exact=pair['stage_alignment_exact'],repeats=records,
            comparisons=comparisons,action_repeat_exact=pair['first_action_difference'] is None,
            first_step_observation_difference=pair['first_step_observation_difference']['stage'] if pair['first_step_observation_difference'] else None,
            initial_fresh_observation_delta=delta(fs[0]['fresh_observation'],fs[1]['fresh_observation']),
            initial_fresh_render_repeat_exact=fs[0]['fresh_render']==fs[1]['fresh_render'],
            initial_supplied_state_repeat_exact=fs[0]['supplied']['state' if cid<3 else 'observation']==fs[1]['supplied']['state' if cid<3 else 'observation']))
    payload=dict(kind='e19_r1_review_evidence',summary_path=str(a.summary),summary_sha256=sha(a.summary),
        full_trace_inventory=full['inventories'],pairs=pairs,valid_processes=20,valid_post_restoration_steps=300,
        initial_job=300297,cube_replacement_job=300298,superseded_cube_processes_preserved=8,
        new_planning=False,model_changes=False,protected_read=False,benchmark_table=False,
        historical_decisions_changed=False,confirmation_ready=False,
        decision='hold_confirmation_pending_restoration_contract_resolution',
        compact_source_sha256=sha(__file__),analyzer_source_sha256=full['analyzer_sha256'])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f: json.dump(payload,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
    with (a.output.parent/'sha256.txt').open('x') as f: f.write(sha(a.output)+'  '+a.output.name+'\n')
    print(sha(a.output),a.output.stat().st_size)
if __name__=='__main__': main()
