"""One read-only saved-data pass; NumPy/pure S0 only, no research-model imports."""
import ast,hashlib,json,math,os,sys,time,traceback
from pathlib import Path
import numpy as np
from .common import canonical,identity,read_bound,json_bound,write_new,ordinary,check_time,SETTINGS
from .numerics import decompose,clock_summary,paired_bootstraps
from wm_diag0.core import array_id

def array(path,want,header):
    p=ordinary(Path(path));before=p.stat()
    if want['bytes']>50000000 or identity(p)!=want:raise ValueError('required numeric input identity '+str(p))
    with p.open('rb') as f:
        if f.read(6)!=b'\x93NUMPY':raise ValueError('numeric NPY only')
        version=tuple(f.read(2));width=2 if version==(1,0) else 4 if version==(2,0) else 0
        if not width:raise ValueError('supported numeric format only')
        n=int.from_bytes(f.read(width),'little')
        if n>4096:raise ValueError('bounded non-executable numeric header')
        h=ast.literal_eval(f.read(n).decode('latin1'));dtype=np.dtype(h['descr'])
        if h['fortran_order'] or dtype.hasobject or dtype.str!=header['dtype'] or list(h['shape'])!=header['shape'] or math.prod(h['shape'])*dtype.itemsize+f.tell()!=want['bytes']:raise ValueError('scientific NPY schema cannot be reconciled')
    a=np.load(p,allow_pickle=False,max_header_size=4096)
    if not np.isfinite(a).all() or a.dtype.str!=header['dtype'] or list(a.shape)!=header['shape']:raise ValueError('finite accepted numeric schema')
    after=p.stat()
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('accepted numeric input changed during load')
    a.flags.writeable=False;return a

def describe(values):
    values=[float(v) for v in values if v is not None]
    if not values:return {'n':0,'mean':None,'median':None,'min':None,'max':None}
    if not np.isfinite(values).all():raise ValueError('finite descriptive population')
    return {'n':len(values),'mean':float(np.mean(values)),'median':float(np.median(values)),'min':min(values),'max':max(values)}
def summaries(rows):
    return {'energies':{k:describe(r['decomposition']['energies'][k] for r in rows) for k in ('total_mean_L2_squared','common_L2_squared','specific_mean_L2_squared','coordinate_MSE','common_per_coordinate','specific_per_coordinate','common_energy_fraction_not_failure_attribution')},
        'selected_pair_terms':{k:describe(r['decomposition']['pair_ordering'][k] for r in rows) for k in ('saved_relative_ordering_error','float64_relative_ordering_error','signed_goal_direction_difference','squared_error_difference','saved_minus_float64_relative_error')}}

def process_parent(meta,baseline,output,end):
    check_time(end);root=Path(meta['output']);required=meta['required_members'];parent=Path(meta['parent_path'])
    ctl=json_bound(parent/'controls/ACCEPTED.json',meta['accepted_control']);result=json_bound(parent/'controls/RESULT.json',meta['accepted_result'])
    if ctl['output_seal']!=meta['output_seal'] or ctl.get('accepted') is not True or result['status']!='ACCEPTED':raise ValueError('accepted supplier chain changed')
    members=json_bound(root/'MEMBERS.json',meta['output_seal'])
    if any(members.get(k)!=v for k,v in required.items()):raise ValueError('same accepted required subset, not a new whole-study audit')
    selected=json_bound(root/'SELECTION.json',required['SELECTION.json']);external=json_bound(parent/'controls/SELECTION-EXTERNAL.json',meta['external_selection'])
    if external['seal']!=required['SELECTION.json'] or selected['candidate_ids']!=meta['candidate_ids'] or selected['route']!=meta['route'] or selected['source_id']!=meta['source_id'] or selected['readout_id']!=meta['readout_id']:raise ValueError('exact accepted representation/source/head/candidates')
    if meta['backbone']=='dinowm_noprop' and meta['active_head']['role']!='RC1_pointwise_DINO':raise ValueError('no old batched DINO replacement')
    arrays={name:array(root/name,required[name],header) for name,header in meta['array_headers'].items()}
    if [array_id(a) for a in arrays['actions.npy']]!=meta['candidate_ids'] or array_id(arrays['goal.npy'])!=selected['selection']['goal_id']:raise ValueError('exact candidate action bytes and own goal')
    choices=selected['selection']['choices'];costs=arrays['costs.npy'];score_id=meta['route']['native_score_id']
    if score_id!=('terminal_sum' if meta['backbone']=='lewm' else 'terminal_mse'):raise ValueError('same original terminal S0 reduction')
    parts=decompose(arrays['predicted.npy'][:,-1],arrays['realized.npy'][:,-1],arrays['goal.npy'],costs,choices,score_id)
    seal={'root_id':meta['root_id'],'backbone':meta['backbone'],'candidate_ids':meta['candidate_ids'],'source_id':meta['source_id'],'output_seal':meta['output_seal'],
        'P0_index':parts['P0_index'],'O0_index':parts['O0_index'],'A_index':parts['A_index'],'B_index':parts['B_index'],
        'A_scores':parts['A_scores'],'B_scores':parts['B_scores'],'A_corrected_array_id':parts['A_corrected_array_id'],'B_corrected_array_id':parts['B_corrected_array_id'],
        'evaluation_outcomes_opened_before_new_selection_seal':False}
    selection_seal=write_new(output/'controls'/('SELECTORS-'+str(meta['setting'])+'-'+str(meta['root_index']).zfill(2)+'.json'),seal,limit=16000)
    # Both indices are immutable now. Only accepted recorded branches are joined.
    candidate_rows=[]
    for candidate,row in enumerate(parts.pop('candidates')):
        check_time(end);prefix=json_bound(root/('oracle/'+str(candidate)+'/PREFIX.json'),required['oracle/'+str(candidate)+'/PREFIX.json'],500000)
        prefix_summary=clock_summary(prefix,prefix=True);draws=[]
        for draw in (0,1):
            name='evaluation/'+str(candidate)+'-'+str(draw)+'/BRANCH.json';branch=json_bound(root/name,required[name],500000)
            clocks=clock_summary(branch)
            upto=min(25,branch['elapsed'])
            if branch['events'][:upto+1]!=prefix['events'][:upto+1] or branch['draw_seed']!=selected['evaluation_draws'][draw]:raise ValueError('saved exact prefix/draw identity')
            draws.append(clocks)
        candidate_rows.append(dict(row,candidate_id=meta['candidate_ids'][candidate],oracle_prefix=prefix_summary,evaluation_draws=draws,
            two_full_budget_outcomes=[int(x['success']) for x in draws],mean_success=sum(int(x['success']) for x in draws)/2))
    key=meta['task']+'|'+meta['backbone'];old=baseline['settings'][key];ri=meta['root_index']
    if old['parent_ids'][ri]!=meta['root_id'] or old['candidate_counts'][ri]!=meta['candidate_count'] or old['selected_indices'][ri]!=choices:raise ValueError('same completed original parent/bank/choices')
    for cell,index in enumerate(choices):
        if old['source_cells'][ri][cell]!=candidate_rows[index]['mean_success']:raise ValueError('accepted recorded outcomes disagree with immutable completed results')
    outcomes={}
    indices={'P0':parts['P0_index'],'O0':parts['O0_index'],'A':parts['A_index'],'B':parts['B_index'],'native':meta['native_index']}
    for name,index in indices.items():
        c=candidate_rows[index];draws=c['evaluation_draws']
        outcomes[name]={'index':index,'candidate_id':c['candidate_id'],'two_outcomes':c['two_full_budget_outcomes'],'mean':c['mean_success'],
            'prefix_success_mean':sum(x['phase']=='prefix_success' for x in draws)/2,'tail_success_mean':sum(x['phase']=='tail_success' for x in draws)/2,
            'draw_phases':[x['phase'] for x in draws],'oracle_terminal_feature_absorbed':c['oracle_prefix']['terminal_feature_post_stop_absorbed']}
    if old['native_parent'][ri]!=outcomes['native']['mean']:raise ValueError('native-return outcome remains separate and unchanged')
    delta=outcomes['O0']['mean']-outcomes['P0']['mean'];stratum='gain' if delta>0 else 'loss' if delta<0 else 'tie'
    if any(outcomes[k]['mean']!=outcomes[k]['prefix_success_mean']+outcomes[k]['tail_success_mean'] for k in outcomes):raise ValueError('disjoint recorded success phase identity')
    return {**{k:meta[k] for k in ('setting','task','backbone','root_index','root_id','candidate_count','candidate_ids','native_index','source_id','source_seal','route','readout_id','active_head','parent_path','output_seal')},
        'new_selector_seal_before_outcome_join':selection_seal,'decomposition':parts,'outcomes':outcomes,
        'original_O0_minus_P0':delta,'original_stratum':stratum,'candidates':candidate_rows}

def aggregate(rows,baseline):
    paired,draw_ids=paired_bootstraps(rows);settings={}
    for task,backbone in SETTINGS:
        key=task+'|'+backbone;group=[r for r in rows if r['task']==task and r['backbone']==backbone];old=baseline['settings'][key]
        phases={};transitions={}
        for name in ('P0','O0','A','B','native'):
            phases[name]={phase:sum(r['outcomes'][name]['draw_phases'].count(phase) for r in group) for phase in ('prefix_success','tail_success','failure')}
        for r in group:
            for x,y in zip(r['outcomes']['P0']['draw_phases'],r['outcomes']['O0']['draw_phases']):transitions[x+' -> '+y]=transitions.get(x+' -> '+y,0)+1
        phase_diffs={name:{kind:float(np.mean([r['outcomes'][name][kind]-r['outcomes']['P0'][kind] for r in group])) for kind in ('prefix_success_mean','tail_success_mean')} for name in ('O0','A','B')}
        for name in phase_diffs:
            total=sum(phase_diffs[name].values());expected=float(np.mean([r['outcomes'][name]['mean']-r['outcomes']['P0']['mean'] for r in group]))
            if abs(total-expected)>1e-12:raise ValueError('recorded prefix/tail absolute-difference identity')
        settings[key]={'n_physical_source_parents':32,'original_copied_not_reestimated':{'P0':old['cells']['P0'],'O0':old['cells']['O0'],'P0_ci95':old['cell_ci95']['P0'],'O0_ci95':old['cell_ci95']['O0'],'O0_minus_P0':old['contrasts']['O0-P0'],'native_reference':old['native_reference']},
            'new_diagnostic_selectors':paired[key],'original_choice_changes':sum(r['decomposition']['action_choice_changed'] for r in group),'original_outcome_changes':sum(r['original_O0_minus_P0']!=0 for r in group),
            'changed_choices_with_tied_outcomes':sum(r['decomposition']['action_choice_changed'] and r['original_O0_minus_P0']==0 for r in group),
            'all_parents':summaries(group),'original_gain_loss_tie_strata':{s:dict(n=len([r for r in group if r['original_stratum']==s]),**summaries([r for r in group if r['original_stratum']==s])) for s in ('gain','loss','tie')},
            'recorded_draw_phase_counts_not_independent_n':phases,'P0_to_O0_draw_phase_transitions':transitions,'absolute_success_difference_split_by_recorded_phase':phase_diffs,
            'oracle_absorbed_terminal_candidates':sum(c['oracle_prefix']['terminal_feature_post_stop_absorbed'] for r in group for c in r['candidates']),
            'all_oracle_candidates':sum(r['candidate_count'] for r in group),'P0_selected_absorbed_parents':sum(r['outcomes']['P0']['oracle_terminal_feature_absorbed'] for r in group),
            'O0_selected_absorbed_parents':sum(r['outcomes']['O0']['oracle_terminal_feature_absorbed'] for r in group)}
    return settings,draw_ids

def main():
    import resource
    began=time.monotonic();source=Path(sys.argv[1]);freeze_id=json.loads(sys.argv[2]);output=Path(sys.argv[3]);end=float(sys.argv[4])
    current=None
    try:
        freeze=json_bound(source/'FREEZE.json',freeze_id);check_time(end)
        if any(os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES','SLURM_JOB_GPUS','SLURM_STEP_GPUS')):raise PermissionError('no visible or allocated GPU')
        if not 0<len(os.sched_getaffinity(0))<=4:raise PermissionError('four CPU process placement')
        for name,want in freeze['members'].items():
            if identity(source/name)!=want:raise ValueError('frozen executed source/spec/input bytes changed '+name)
        manifest=json_bound(source/'INPUT-MANIFEST.json',freeze['members']['INPUT-MANIFEST.json'])
        if manifest['status']!='REQUIRED_ACCEPTED_INPUT_METADATA_AND_NUMERIC_HEADERS_FROZEN_NO_NEW_DERIVED_RESULTS':raise ValueError('fixed accepted saved evidence only')
        baseline=json_bound(manifest['completed_results']['path'],manifest['completed_results']['identity'])
        accepted=json_bound(manifest['completed_acceptance']['path'],manifest['completed_acceptance']['identity'])
        if len(accepted['parent_output_seals'])!=128 or len(manifest['parents'])!=128:raise ValueError('complete accepted cohort')
        output.mkdir(exist_ok=False);(output/'controls').mkdir();rows=[]
        for meta in manifest['parents']:
            current={'task':meta['task'],'backbone':meta['backbone'],'root_index':meta['root_index']}
            if accepted['parent_output_seals'].get(meta['root_id']+'|'+meta['backbone'])!=meta['output_seal']:raise ValueError('immutable final accepted supplier map')
            rows.append(process_parent(meta,baseline,output,end))
        settings,draw_ids=aggregate(rows,baseline);check_time(end)
        forbidden=('torch','mujoco','dm_control','pymunk','timm','h5py','PIL')
        if any(name.split('.')[0] in forbidden for name in sys.modules):raise PermissionError('research model/physics/image module imported')
        result={'study':'WM-DIAG1-SAVED','status':'ONE_COMPLETE_FIXED_SAVED_DATA_PASS','discovery_outcome_informed_not_confirmation':True,'freeze':freeze_id,
            'input_manifest':freeze['members']['INPUT-MANIFEST.json'],'original_publication':manifest['completed_publication'],'settings':settings,'parents':rows,
            'new_bootstrap_seed':20261017,'new_bootstrap_resamples':10000,'task_paired_resample_ids':draw_ids,'old_estimator_or_intervals_rerun':False,
            'new_selectors_are_privileged_not_deployable':True,'new_model_training_inference_physics_source_collection_GPU_calls':0,
            'all_physical_source_parents':64,'all_task_backbone_parent_evaluations':128,'original_published_time_position_MSE_reused_by_reference':manifest['completed_results'],
            'mechanism_and_unlaunched_proposal_require_complete_postpass_review':True}
        write_new(output/'DERIVED-RESULTS.json',result,limit=50000000)
        used=resource.getrusage(resource.RUSAGE_SELF)
        receipt={'status':'ONE_CPU_ONLY_SAVED_DATA_PASS_COMPLETED','elapsed_wall_seconds':time.monotonic()-began,'CPU_seconds':used.ru_utime+used.ru_stime,'peak_RSS_bytes':used.ru_maxrss*1024,
            'CPU_affinity':sorted(os.sched_getaffinity(0)),'NumPy':np.__version__,'python':sys.version,'thread_environment':{k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},
            'rows':128,'only_required_saved_bytes_authenticated':manifest['required_saved_bytes_streamed_in_one_parent_at_a_time'],'no_model_or_simulator_modules_imported':True,
            'source':identity(__file__),'freeze':freeze_id,'new_derived_result':identity(output/'DERIVED-RESULTS.json'),'no_latent_banks_persisted':True}
        write_new(output/'RESOURCE.json',receipt)
        members={p.relative_to(output).as_posix():identity(p) for p in output.rglob('*') if p.is_file()}
        if sum(x['bytes'] for x in members.values())>100000000:raise ValueError('compact outputs and controls aggregate cap')
        write_new(output/'MEMBERS.json',members)
        print(json.dumps({'status':receipt['status'],'output_seal':identity(output/'MEMBERS.json'),'rows':128,'new_model_or_physics_calls':0}))
    except BaseException as e:
        write_new(output.parent/'SAVED-DATA-STOP.json',{'status':'STOP_NO_AUTOMATIC_RETRY_NO_IMPUTATION','parent':current,'error':repr(e),'traceback':traceback.format_exc()[-16000:]})
        raise

if __name__=='__main__':main()
