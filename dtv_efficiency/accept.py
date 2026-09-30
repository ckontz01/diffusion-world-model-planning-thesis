"""Independent full-grid timing acceptance, then all-cell comparison (no selection)."""
import argparse,json
from pathlib import Path
from dtv_efficiency.profile import DOC,sha,ARMS,summary

def validate(run,c):
    events=[json.loads(x) for x in (run/'DISPATCH.jsonl').read_text().splitlines()]
    terminal=[e for e in events if e['event']=='terminal']
    if len(terminal)!=9 or len({e['allocation_id'] for e in terminal})!=9 or {e['task'] for e in terminal}!={j['id'] for j in c['jobs']}:raise RuntimeError('full-grid accounting mismatch')
    if any(e['state']!='COMPLETED' or e['exit']!='0:0' or e['elapsed_seconds']>800 for e in terminal) or sum(e['elapsed_seconds'] for e in terminal)>7200:raise RuntimeError('failure/cap; never omit')
    if any(e.get('node') not in ('gpu09','gpu09.cluster') or 'gres/gpu=1' not in e.get('allocated_resources','') for e in terminal):raise RuntimeError('allocation hardware identity mismatch')
    submitted=[e for e in events if e['event']=='submitted']
    if len(submitted)!=9 or {(e['task'],e['allocation_id']) for e in submitted}!={(e['task'],e['allocation_id']) for e in terminal}:raise RuntimeError('submission/terminal lineage mismatch')
    profiles=[]
    for job in c['jobs']:
        root=run/job['id'];seal=json.loads((root/'SEAL.json').read_text());profile_path=root/'PROFILE.json'
        if seal['profile_sha256']!=sha(profile_path) or seal['job']!=job['id']:raise RuntimeError('worker seal mismatch')
        value=json.loads(profile_path.read_text())
        if value['status']!='completed' or value['job']!=job['id'] or value['bindings_sha256']!=sha(DOC/'BINDINGS.json') or value['science_outcomes_computed']:raise RuntimeError('wrong worker contract')
        if value['gpu']!='NVIDIA RTX 6000 Ada Generation' or value['hostname'] not in ('gpu09','gpu09.cluster') or value['python']!='3.11.10' or value['torch']!='2.5.1+cu121' or value['rss_high_water_bytes']>c['ram_bytes']:raise RuntimeError('worker hardware/runtime/memory mismatch')
        if value['wall_seconds']>800:raise RuntimeError('worker wall ceiling')
        warm=[r for r in value['records'] if r.get('phase')=='warm']
        expected={(context,arm,level,block,rep) for context in (0,1) for arm in ARMS for level in ('A','B','C') if not (arm=='plain' and level=='A') for block in range(5) for rep in range(2)}
        observed=[(r['context'],r['arm'],r['level'],r['block'],r['repetition']) for r in warm]
        if len(observed)!=len(expected) or set(observed)!=expected:raise RuntimeError('missing/duplicate timing cell')
        if {(e['context'],e['arm']) for e in value['equivalence']}!={(i,a) for i in (0,1) for a in ARMS} or len(value['equivalence'])!=10 or any(e['index_equivalence'] is not True or e['rounds']!=30 for e in value['equivalence']) or sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>4000000:raise RuntimeError('audit or byte contract')
        offline=[r for r in value['records'] if r['level']=='A_offline_reconciliation']
        if len(offline)!=6 or {(r['arm'],r['repetition']) for r in offline}!={(a,i) for a in ('acid','forward','legacy_dtv') for i in range(2)} or any((r['candidate_sequences'],r['horizon_transitions'],r['transition_chunk'])!=(15000,75000,8192) for r in offline):raise RuntimeError('offline reconciliation workload differs')
        for r in warm+offline:
            for metric in ('gpu_event_ms','synchronized_wall_ms'):summary([r[metric]])
        allocation=next(e['allocation_id'] for e in terminal if e['task']==job['id'])
        if value['slurm_allocation_id']!=allocation:raise RuntimeError('worker/allocation identity mismatch')
        profiles.append(value)
    return profiles,terminal

def comparisons(profiles):
    result=[]
    for profile in profiles:
        for context in (0,1):
            for level in ('A','B','C'):
                for metric in ('gpu_event_ms','synchronized_wall_ms'):
                    rows=[r for r in profile['records'] if r.get('phase')=='warm' and r['context']==context and r['level']==level]
                    baseline=[r[metric] for r in rows if r['arm']=='acid'];acid=summary(baseline)['median']
                    for arm in ARMS:
                        if level=='A' and arm=='plain':continue
                        arm_rows=[r for r in rows if r['arm']==arm];s=summary([r[metric] for r in arm_rows])
                        saving=acid-s['median'];blocks=[]
                        for block in range(5):
                            av=summary([r[metric] for r in rows if r['arm']=='acid' and r['block']==block])['median']
                            tv=summary([r[metric] for r in arm_rows if r['block']==block])['median']
                            blocks.append((av-tv)/av)
                        result.append(dict(job=profile['job'],context=context,level=level,metric=metric,arm=arm,summary=s,acid_over_arm_ratio=acid/s['median'],absolute_ms_saved=saving,fraction_saved=saving/acid,block_fractions=blocks,utility_cell_pass=level=='C' and saving/acid>=.10 and sum(x>=.10 for x in blocks)>=4))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    c=json.loads((DOC/'BINDINGS.json').read_text());profiles,terminal=validate(args.run,c)
    cells=comparisons(profiles)
    screen={arm:all(r['utility_cell_pass'] for r in cells if r['arm']==arm and r['level']=='C' and r['metric']=='synchronized_wall_ms') for arm in ('legacy_dtv','d1_sigma025')}
    with args.output.open('x') as f:json.dump(dict(status='complete_fixed_grid',bindings_sha256=sha(DOC/'BINDINGS.json'),worker_profiles=[dict(job=j['id'],sha256=sha(args.run/j['id']/'PROFILE.json')) for j in c['jobs']],comparisons=cells,frozen_utility_screen=screen,allocation_seconds=sum(e['elapsed_seconds'] for e in terminal),models_promoted=False,next_stage_authorized=False,science_outcomes=False),f,indent=2)
if __name__=='__main__':main()
