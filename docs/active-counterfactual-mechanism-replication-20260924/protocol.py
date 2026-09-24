"""Executable preparation contract: exact grid, reservations and dry-run tasks.

--freeze writes proposal artifacts; --check validates them; --task KEY emits
an exact job specification. --execute ALWAYS refuses. This is a ready-to-review
scientific protocol, not a newly authorized or deployed cluster controller.
"""
import base
import argparse, json
from planned_analysis import ARMS, NAMES, sensitivity

PAIRS=((94011,94012),(94411,94412),(94421,94422))

def build(eligibility):
    refs=eligibility['selected_references']; assert len(refs)==len(set(refs))==512
    seed_tasks=[dict(pair=i,joint_seed=j,ordinary_seed=o,joint_key=f'fit-pair{i}-joint',ordinary_key=f'fit-pair{i}-ordinary') for i,(j,o) in enumerate(PAIRS)]
    grid=[]
    for pair in seed_tasks[1:]:
        for kind in ('joint','ordinary'):
            grid.append(dict(key=pair[kind+'_key'],stage='fitting',kind=kind,pair=pair['pair'],
                             seed=pair[kind+'_seed'],updates=192,whole_source_batch=64,shuffle_seed=94013,
                             cpus=4,ram_gib=8,gpu=0,seconds=7200,work_seconds=7140,byte_cap=100_000_000,
                             dependencies=['authenticated-acv0-fit-dataset','authenticated-acv0-validation-dataset']+([pair['joint_key']] if kind=='ordinary' else [])))
    # Each source has16 ACTUAL executions:5x3 learned cells +1 seed-independent early.
    cells=[(p,a) for p in range(3) for a in ARMS]+[(None,'early-replan')]
    for position,ref in enumerate(refs):
        rotated=cells[position%16:]+cells[:position%16]
        for pair,arm in rotated:
            grid.append(dict(key=f'evaluate-{ref}-{arm}'+('' if pair is None else f'-pair{pair}'),
                             stage='evaluation',reference=ref,role='mechanism_evaluation',pair=pair,control=arm,
                             cpus=4,ram_gib=24,gpu=1,seconds=300,work_seconds=240,byte_cap=2_000_000,
                             max_episodes=1,max_steps=150,dependencies=['ALL-MODELS-FROZEN','EXECUTION-APPROVAL'],
                             source_key=eligibility['records'][str(ref)]['source_key']))
    grid.append(dict(key='analysis',stage='analysis',cpus=4,ram_gib=8,gpu=0,seconds=7200,work_seconds=7140,
                     byte_cap=100_000_000,dependencies=['ALL-8192-EPISODES-ACCEPTED']))
    assert len(grid)==8197 and sum(j['gpu'] for j in grid)==8192
    contract=dict(status='PREPARATION_ONLY_EXECUTION_DISABLED',authorized=False,
        namespace='active-counterfactual-mechanism-replication-v1',original_result_commit='5d8666754ad8aa0507730f86cf3ee6caa32c105a',
        seed_pairs=seed_tasks,original_pair_reused=True,new_fits=4,new_collection_jobs=0,
        old_final32_in_primary=False,source_count=512,unique_outcomes=8192,unique_tasks=8197,
        learned_arms=list(ARMS),external_seed_independent_arm='early-replan',baseline_repetitions=1,
        primary_mechanism_contrasts=list(NAMES[:2]),other_prespecified_contrasts=list(NAMES[2:]),
        family=list(NAMES),familywise_alpha=.05,bootstrap_seed=94431,bootstrap_samples=10000,
        training=dict(fit_sources=64,validation_sources=16,update_count=192,batch_sources=64,
                      learning_rate=.001,betas=[.9,.999],epsilon=1e-8,gradient_norm_cap=5,weight_decay=0,
                      shuffle_seed=94013,checkpoint='final192 only',early_stopping=False,model_selection=False,
                      preprocessing='identical authenticated fit64-only statistics; no recomputation from evaluation'),
        pairing=dict(planner_seed=[94041,'reference_index','absolute_clock'],tree_seed=[94001,'prefix-content-hash32'],
                     response_integration_seed=94021,response_samples_per_prefix=128,
                     environment_seed='exact registry environment_seed, identical across16 cells of a source',
                     tree_check='exact candidate actions/predicted features across learned arms and model seeds',
                     seeds_are_not_independent_sources=True),
        resources=dict(gpu_type='NVIDIA RTX 6000 Ada Generation',node='gpu09',gpu_concurrency=1,
                       gpu_allocation_seconds=2457600,cpu_stage_allocation_seconds=36000,
                       cpu_core_seconds_reservation=144000,gpu_job_seconds=300,gpu_job_cpus=4,gpu_job_ram_gib=24,
                       cpu_job_seconds=7200,cpu_job_cpus=4,cpu_job_ram_gib=8,
                       evaluation_output_bytes=16384000000,source_models_control_analysis_bytes=1000000000,
                       live_bytes=18000000000,archive_bytes=18500000000,inclusive_bytes=80000000000,
                       required_ssd_free_bytes=40000000000,archive_wall_seconds=7200,archive_cpus=4,archive_ram_gib=8,
                       transfer_attempts=1,transfer_wall_seconds=14400,stream_bytes_cap=18500000000,
                       preservation_host_seconds=28800,postpreservation_reporting_cpu_seconds=7200),
        attempts=dict(max_gpu_allocations=8192,max_cpu_allocations=5,automatic_retry=False,requeue=False,
                      failure_rule='fail-stop, preserve/account all attempts; no replacement or budget extension in this proposal'),
        storage_policy='Reserve all remaining worker caps plus tar headers and both live/archive/SSD partial or final, retained partials and <=1GB reused input/provenance allowance; never delete old artifacts to fit.',
        stopping='No interim efficacy inspection or optional stopping. Stop on any unresolved task/seal/hardware/identity/accounting/resource fault. Terminal prefix is normal. Poor outcomes are not faults.',
        execution_gate='Separate explicit execution authorization + immutable new source/input/model/grid/approval hashes + backed-up small package; no current launch capability.',
        sensitivity=sensitivity())
    return contract,grid

def validate(c,g,e):
    expected,grid=build(e)
    assert c==expected and g==grid
    assert c['authorized'] is False
    assert sum(x['seconds'] for x in g if x['gpu'])==c['resources']['gpu_allocation_seconds']
    assert sum(x['seconds'] for x in g if not x['gpu'])==c['resources']['cpu_stage_allocation_seconds']
    assert len({x['key'] for x in g})==len(g)
    final=set(base.read(base.OLD/'DATA-ROLES-PROPOSED.json')['proposed_roles']['final_development'])
    assert not final & set(e['selected_references'])
    for ref in e['selected_references']:
        rows=[x for x in g if x.get('reference')==ref]
        assert len(rows)==16 and sum(x['control']=='early-replan' for x in rows)==1
    return dict(valid=True,execution_enabled=False,tasks=len(g),sources=512,outcomes=8192,
                gpu_hours=c['resources']['gpu_allocation_seconds']/3600,cpu_stage_hours=10)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--freeze',action='store_true');p.add_argument('--check',action='store_true')
    p.add_argument('--task'); p.add_argument('--execute',action='store_true');a=p.parse_args()
    if a.execute: raise PermissionError('Preparation only: no research execution authorized or launched')
    e=base.read(base.HERE/'ELIGIBILITY.json'); c,g=build(e)
    if a.freeze:
        base.write(base.HERE/'PROTOCOL.json',c);base.write(base.HERE/'GRID.json',g)
        base.write(base.HERE/'SENSITIVITY.json',sensitivity())
    if a.check:
        print(json.dumps(validate(base.read(base.HERE/'PROTOCOL.json'),base.read(base.HERE/'GRID.json'),e)))
    if a.task: print(json.dumps(next(j for j in g if j['key']==a.task),indent=2))
    if not (a.freeze or a.check or a.task): p.error('Choose --freeze, --check or --task')

if __name__=='__main__': main()
