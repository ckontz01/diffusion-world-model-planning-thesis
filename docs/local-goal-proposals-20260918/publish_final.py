"""Compact publication of the completed, externally verified aggregate only.

No model, physics, research-data preprocessing, new inferential rule, or
scientific reanalysis. Large original aggregate stays unchanged in the archive.
Supporting stage summaries describe actually executed stages, not a paired
common-state mechanism experiment. All original source effects are retained.
"""
import hashlib
import json
import statistics
import tarfile
from collections import Counter
from pathlib import Path

DOC=Path(__file__).resolve().parent
BACKUP=Path('D:/THESIS-BACKUPS/local-goal-proposals-20260918/run-b54a55b16bcb83a5')


def write(path,value):
    with path.open('x',encoding='utf8',newline='\n') as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')


def stage_summary(rows):
    stages=[s for r in rows for s in r['stages']]
    rounds=[v for s in stages for v in s['rounds']]
    first=[s['rounds'][0] for s in stages]
    last=[s['rounds'][-1] for s in stages]
    mean=statistics.mean
    return dict(episodes=len(rows),successes=sum(r['success'] for r in rows),
        physical_actions=sum(r['steps'] for r in rows),stages=len(stages),
        terminated=sum(bool(r['terminated']) for r in rows),truncated=sum(bool(r['truncated']) for r in rows),
        full_budget_episodes=sum(r['steps']==2*r['horizon'] for r in rows),
        first_chunk_success=sum(r['success']==1 and r['steps']<=15 for r in rows),
        final_budget_step_success=sum(r['success']==1 and r['steps']==2*r['horizon'] for r in rows),
        total_cost_calls=sum(s['cost_calls'] for s in stages),
        total_candidate_trajectories=sum(s['candidate_trajectories'] for s in stages),
        total_predicted_primitive_steps=sum(s['predicted_primitive_steps'] for s in stages),
        latency={key:dict(mean_seconds=mean(s[key] for s in stages),median_seconds=statistics.median(s[key] for s in stages),
                         total_seconds=sum(s[key] for s in stages)) for key in
                 ['seconds','proposal_seconds','encoding_seconds','generator_seconds','context_seconds','refinement_total_seconds','scoring_seconds']},
        physics_delivery_seconds=sum(r['physics_delivery_seconds'] for r in rows),
        first_bank_mean_minimum_cost=mean(v['minimum'][0] for v in first),
        last_population_mean_minimum_cost=mean(v['minimum'][0] for v in last),
        first_bank_mean_population_std=mean(v['population_std_mean'] for v in first),
        first_bank_mean_unique=mean(v['unique'][0] for v in first),
        all_rounds_mean_unique=mean(v['unique'][0] for v in rounds),
        projection_exceeded=sum(v['projection']['exceeded'] for v in rounds),
        projection_boundary=sum(v['projection']['boundary'] for v in rounds),
        projection_coordinates=sum(v['projection']['coordinates'] for v in rounds))


def main():
    verified=json.loads((BACKUP/'BACKUP-VERIFIED.json').read_text())
    request=json.loads((BACKUP/'BACKUP-REQUEST.json').read_text())
    assert verified['sha256']==request['sha256']=='24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd'
    assert verified['bytes']==request['bytes']==1734420480 and verified['files']==1733
    with tarfile.open(BACKUP/'final.tar','r:') as tar:
        def raw(name):
            data=tar.extractfile(name).read();meta=request['members'][name]
            assert len(data)==meta['bytes'] and hashlib.sha256(data).hexdigest()==meta['sha256']
            return data
        a=json.loads(raw('run/analysis/REPORT.json'))
        auth_raw=raw('new-control/FINAL-AUTHENTICATION-20260919.json')
        auth=json.loads(auth_raw)
        complete=json.loads(raw('run/COMPUTE-COMPLETE.json'))
        process=json.loads(raw('new-control/CONTROLLER-PROCESS.json'))
        failures={name:json.loads(raw(name)) for name in request['members']
                  if name.endswith('/FAILURE.json') and name.split('/')[0] in ['failed-run','prior-run','validation-run']}
    assert auth['verified'] and auth['successful_coordinates']==204 and len(a['rows'])==384
    assert len(a['source_effects'])==a['independent_units']==32
    rows=a['rows']; keys={(r['reference'],r['family'],r['horizon'],r['seed']) for r in rows}
    assert len(keys)==384 and all(r['failure'] is None for r in rows)
    for effect in a['source_effects']:
        for family in ['gmm','diffusion']:
            rr=[r for r in rows if (r['reference'],r['family'])==(effect['reference'],family)]
            assert len(rr)==6 and abs(sum(r['success'] for r in rr)/6-effect[family])<1e-12
    compact={k:v for k,v in a.items() if k not in ['rows','resources','ledger']}
    compact['rows']=[{k:v for k,v in r.items() if k!='stages'} for r in rows]
    compact['original_aggregate']=dict(archive_member='run/analysis/REPORT.json',**request['members']['run/analysis/REPORT.json'])
    compact['publication_note']='Compact projection; all 384 endpoint rows, six fits, 32 source effects and frozen aggregate statistics retained. Per-stage/round detail remains in unchanged archived original. No new endpoint or selection gate.'
    compact['supporting']=dict(weighting='Actual executed stages/coordinates; not primary source weighting and not paired common-state causality.',
        by_family={f:stage_summary([r for r in rows if r['family']==f]) for f in ['gmm','diffusion']})
    pair={(r['reference'],r['horizon'],r['seed']):{} for r in rows}
    for r in rows:pair[r['reference'],r['horizon'],r['seed']][r['family']]=r['success']
    compact['paired_outcome_counts']=dict(Counter('gmm%d_diffusion%d'%(p['gmm'],p['diffusion']) for p in pair.values()))
    compact['source_effect_sign_counts']=dict(positive=sum(r['diffusion_minus_gmm']>0 for r in a['source_effects']),
        zero=sum(r['diffusion_minus_gmm']==0 for r in a['source_effects']),negative=sum(r['diffusion_minus_gmm']<0 for r in a['source_effects']))
    workers=auth['workers'];grouped={}
    for kind in ['cache','fit','technical','evaluation','analysis']:
        rr=[r for r in workers if r['metadata']['task']['kind']==kind]
        grouped[kind]=dict(workers=len(rr),allocation_seconds=sum(r['allocation_seconds'] for r in rr),
            process_cpu_seconds=sum(r['metadata']['process_cpu_seconds'] for r in rr),
            worker_wall_seconds=sum(r['metadata']['wall_seconds'] for r in rr),
            peak_rss_bytes=max(r['metadata']['peak_rss_bytes'] for r in rr),
            peak_gpu_bytes=max(r['metadata'].get('peak_gpu_bytes',0) for r in rr),
            worker_bytes=sum(r['bytes'] for r in rr))
    accounting=dict(gpu_allocation_seconds=auth['gpu_allocation_seconds'],cpu_allocation_wall_seconds=auth['cpu_allocation_wall_seconds'],
        attempts=207,successful_coordinates=204,groups=grouped,historical_failure_technical_records=failures,
        failure_gpu_allocation_seconds=320,unique_updates=72000,unique_row_presentations=9216000,
        process_record=process,controller_launch_to_final_terminal_seconds=auth['analysis_recorded_terminal_unix']-process['unix'],
        controller_cpu_seconds=None,controller_peak_rss_bytes=None,
        controller_resource_note='Controller process CPU/RSS were not captured before exit; do not infer zero from Slurm TotalCPU placeholders.',
        archive_cpu_seconds=request['host_archive_cpu_seconds'],archive_wall_seconds=request['host_archive_seconds'],
        transfer_and_member_verification_wall_seconds=verified['seconds'],backup=verified,
        archive_prefixes=sorted({name.split('/')[0] for name in request['members']}),
        archived_member_bytes=sum(v['bytes'] for v in request['members'].values()),pre_archive_storage=auth['storage'])
    write(DOC/'FINAL-AGGREGATE-PROJECTION.json',compact)
    write(DOC/'FINAL-ACCOUNTING.json',accounting)
    with (DOC/'FINAL-AUTHENTICATION.json').open('xb') as f:f.write(auth_raw)
    for name in ['BACKUP-VERIFIED.json','BACKUP-REQUEST.json']:
        with (DOC/('FINAL-'+name)).open('xb') as f:f.write((BACKUP/name).read_bytes())
    lines=['# All 32 LGP1 source effects','',
           'Each percentage is the source mean across both horizons and all three fixed seeds. '+
           'Effects are diffusion minus GMM in percentage points. Already-exposed development only.','',
           '| Source | GMM success | Diffusion success | Difference (pp) |',
           '| ---: | ---: | ---: | ---: |']
    lines += [f"| {r['reference']} | {100*r['gmm']:.3f}% | {100*r['diffusion']:.3f}% | {100*r['diffusion_minus_gmm']:+.3f} |" for r in a['source_effects']]
    with (DOC/'FINAL-SOURCE-EFFECTS.md').open('x',encoding='utf8',newline='\n') as f:f.write('\n'.join(lines)+'\n')
    print(json.dumps(dict(primary=a['primary'],family_success=a['family_success'],supporting=compact['supporting'],
        paired=compact['paired_outcome_counts'],effect_signs=compact['source_effect_sign_counts'],accounting=accounting)))


if __name__=='__main__':main()
