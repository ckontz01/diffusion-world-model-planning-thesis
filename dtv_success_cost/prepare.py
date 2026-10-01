"""Metadata-only exact cohort, grid, checkpoint and resource freeze generator."""
import hashlib
from dtv_success_cost.common import *
from dtv_success_cost.cohort import reconcile, rows, h64

def build():
    roles=reconcile(); cohort={}; jobs=[]
    old=load(ROOT/'docs/dtv-efficiency-20260930/BINDINGS.json')
    for task in TASKS:
        ordered=sorted(roles[task]['eligible_parents'], key=lambda i:hashlib.sha256(f'dtv-eff1|{task}|{i}|20261001'.encode()).hexdigest())[:N]
        if len(ordered)!=N: raise RuntimeError('legitimate source allocation unavailable')
        master=rows(DOC/f'metadata/manifests/partitions/{task}-v1/episodes-seed-20260728.tsv')
        offsets={}; total=0
        for r in master:
            offsets[int(r['episode_id'])]=total; total+=int(r['episode_length'])
        lengths={int(r['episode_id']):int(r['episode_length']) for r in master}
        cohort[task]=[dict(task=task, source_index=i, parent_id=p, start_step=(start:=h64(f'dtv-eff1-start|{task}|{p}|20261001')%(lengths[p]-24)),
                           goal_step=start+24, source_row=offsets[p]+start, goal_row=offsets[p]+start+24,
                           parent_length=lengths[p], partition='P2') for i,p in enumerate(ordered)]
    # First source from each task and all fixed blocks is the included technical tranche.
    for index in range(N):
        for task in TASKS:
            for block, seed in enumerate(SEEDS):
                source=cohort[task][index]
                jobs.append(dict(id=f'{task}-{source["parent_id"]}-{seed}', task=task, source_index=index, scorer_seed=seed,
                                 planner_seed=7101+block, environment_seed=h64(f'dtv-eff1-env|{task}|{source["parent_id"]}|{seed}')%(2**31-1),
                                 configs=list(CONFIGS[(index*3+block)%8:]+CONFIGS[:(index*3+block)%8]),
                                 wall_seconds=300, work_seconds=240, output_bytes=1000000, log_bytes=100000))
    models={}
    for j in old['jobs']:
        models[j['id']]=dict(task=j['task'], seed=j['scorer_seed'], models=j['models'], dataset=j['capture']['dataset'],
                            dataset_sha256=j['capture']['dataset_sha256'], world_checkpoint=j['capture']['world_model_checkpoint'],
                            world_sha256=j['capture']['world_model_checkpoint_sha256'],
                            decoder={k:v['planner_action_standardization'] for k,v in [(r['arm'],r) for r in j['offline_scores']['scorers']] if k in ('diffusion','acid','forward')})
    runtime={r['path']:r for r in old['runtime']+load(ROOT/'docs/dtv-efficiency-20260930/FINAL-RECOVERY.json')['model_runtime_sources']}
    for receipt in (load(DOC/'METADATA-RECEIPT.json'),load(DOC/'additional/METADATA-RECEIPT.json'),load(DOC/'native-dependency/METADATA-RECEIPT.json'),load(DOC/'native-base/METADATA-RECEIPT.json')):
        for r in receipt.get('files',[]):
            # Metadata receipt schema contains paths relative to the thesis remote root.
            path=r.get('remote_path',r.get('path',''))
            if path and not path.startswith('/') : path=str(REMOTE/path)
            if '/site-packages/' in path or '/src/hi-lewm/' in path: runtime[path]=dict(path=path,sha256=r['sha256'],bytes=r['bytes'])
    measured=load(ROOT/'docs/dtv-efficiency-20260930/evidence/AUTHENTICATED-BYTES.json')['records']
    preservation_inputs=[r for r in measured if r['kind'] in ('checkpoint','world_model')]
    c=dict(study='DTV-EFF1', execute=False, cohort=cohort, jobs=jobs, models=models, runtime=list(runtime.values()),
           role_inventory=load(DOC/'ROLE-INVENTORY.json')['files'],
           container=dict(path=str(REMOTE/'containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'),sha256='589af9b428527ae2d315fbd5eaf7ef991efb1aa7249e30a6d28e6731df40afb2'),
           historical_sources=[dict(path=str(REMOTE/'snapshots/acid-alternative-core-v1-52acea39e4a1f6da'),sha256='52acea39e4a1f6dadfa5d5be4ec6206a9aefb46159e5def7355a8575f0062f1d'),
                               dict(path=str(REMOTE/'snapshots/acid-alt-v3-d2-2c8f890c31e9f5bf'),sha256='2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea')],
           gpu_seconds=300*len(jobs),cpu_seconds=14400,analysis_bytes=40000000,control_bytes=100000000,
           live_bytes=4000000000,archive_bytes=4200000000,inclusive_bytes=13000000000,
           source_bytes=20000000,reused_model_bytes=sum(r['bytes'] for r in preservation_inputs),preservation_inputs=preservation_inputs,
           initial_tranche=9,physical_actions=len(jobs)*8*50,
           max_populations=len(jobs)*4*(30+28)*2,max_candidate_sequences=len(jobs)*4*(30+28)*2*300,
           max_predicted_transitions=len(jobs)*4*(30+28)*2*300*5,
           analysis=dict(bootstrap=10000,seed=20261001,comparisons=['acid30','acid28','forward30','plain30'],alpha=.05,
                         family_axes=2,family_scopes=4,family_size=32,noninferiority_margin=None))
    return c,roles

def main():
    c,roles=build()
    import sys
    if '--refresh-preparation' in sys.argv:
        if (DOC/'PACKAGE-MANIFEST.json').exists():raise RuntimeError('frozen package cannot be refreshed')
        for name in ('COHORT.json','BINDINGS.json','EXECUTION-APPROVAL.json'):
            p=DOC/name
            if p.exists():
                version=0
                while (DOC/(name+f'.preparation-v{version}')).exists():version+=1
                p.rename(DOC/(name+f'.preparation-v{version}'))
    write(DOC/'COHORT.json',c['cohort']);write(DOC/'BINDINGS.json',c)
    write(DOC/'EXECUTION-APPROVAL.json',dict(study='DTV-EFF1',execute=False,research_execution_authorized=False,source_role='DTV-EFF1-P2-320-per-task'))
    print(dict(workers=len(c['jobs']),episodes=len(c['jobs'])*8,gpu_seconds=c['gpu_seconds'],eligible={t:roles[t]['eligible_parent_count'] for t in TASKS}))
if __name__=='__main__':main()
