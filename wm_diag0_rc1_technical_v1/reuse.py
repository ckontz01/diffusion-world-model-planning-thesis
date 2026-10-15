"""Dated exact retained-bank/forecast compatibility; zero new model forwards."""
import json,shutil,time
from pathlib import Path
import numpy as np
from wm_diag0.core import Features,array_id,frozen
from wm_diag0_native_v3.store import authenticate,load_array,save_array
from wm_diag0_numerical_v3.bank import retained
from .common import identity,write_new,canonical,REPRESENTATION

def gate(c):
    p=Path(c['rc1_technical']['gate_run'])/'tasks/rc1-gate/output'
    authenticate(p,c['rc1_technical']['gate_seal'],26_000_000,{'reference.npy','RC1-GATE.json'})
    if identity(p/'RC1-GATE.json')!=c['rc1_technical']['gate_report']:raise ValueError('accepted gate report identity')
    report=json.loads((p/'RC1-GATE.json').read_text())
    if not report['all_RC1_checks_passed'] or not report['reference']['source_binding_exact'] or not report['reference']['goal_binding_exact'] or not report['reference']['terminal_cost_identity_exact']:
        raise ValueError('exact numerical compatibility gate')
    return report

def validate_receipt(path,c,selected):
    r=json.loads(Path(path).read_text());g=gate(c)['reference']
    if r['status']!='AUTHENTICATED_REUSE_NOT_NEW_COMPUTATION' or r['gate_report']!=c['rc1_technical']['gate_report'] or r['bank_id']!=g['bank_id'] or r['candidate_ids']!=g['candidate_ids']:
        raise ValueError('dated exact supplier receipt')
    if r['representation']!=REPRESENTATION or r['source_RGB_id']!=g['source_RGB_id'] or r['goal_RGB_id']!=g['goal_RGB_id'] or r['production_forecast_supplier_id']!=g['production_forecast_supplier_id'] or r['goal_feature_id']!=g['goal_id']:
        raise ValueError('source/goal/forecast supplier identity')
    if canonical(selected['route'])!=canonical(g['amended_route']) or selected['bank_id']!=r['bank_id'] or selected['candidate_ids']!=r['candidate_ids']:
        raise ValueError('amended selection compatibility')
    if any(r[k] for k in ('new_CEM','new_production_forecast','new_reference_forward')):raise ValueError('no recomputation claim')
    old=Path(c['recovery']['old_run'])/'tasks/technical-1/output'
    for n,x in c['recovery']['partial'].items():
        if identity(old/n)!=x or identity(Path(path).parent/n)!=x:raise ValueError('retained trace and native return bytes')
    if array_id(load_array(Path(path).parent/'predicted.npy'))!=g['production_forecast_supplier_id'] or array_id(load_array(Path(path).parent/'goal.npy'))!=g['goal_id']:raise ValueError('retained forecast/goal bytes')
    from wm_diag0_native_v3.actions import normalize
    physical=load_array(Path(path).parent/'actions.npy',(16,25,2),['<f4'])
    stats=json.loads((Path(c['prior_source'])/'configs/pusht/swm_h5_norm_stats.json').read_text())
    if r['physical_actions_id']!=array_id(physical) or r['normalized_actions_id']!=array_id(normalize(physical,np.array(stats['action_mean']),np.array(stats['action_std']))):raise ValueError('physical/normalized action identity')

def obtain(adapter,history,goal,c,out,source_id):
    g=gate(c)['reference']
    if array_id(history)!=g['source_RGB_id'] or array_id(goal)!=g['goal_RGB_id'] or canonical(adapter.original_contract.__dict__)!=canonical(g['old_route']) or canonical(adapter.contract.__dict__)!=canonical(g['amended_route']):raise ValueError('unchanged E1 planning definition/raw source')
    bank,physical=retained(c)
    if bank.identity!=g['bank_id'] or [x.identity for x in bank.candidates]!=g['candidate_ids']:raise ValueError('retained exact bank')
    v3=Path(c['rc1']['V3_run'])/'tasks/numerical-validation/output'
    authenticate(v3,c['rc1']['V3_output_seal'],26_000_000,{'predicted.npy','goal.npy','VALIDATION.json'})
    pred=load_array(v3/'predicted.npy',(16,5,196,384),['<f4']);gf=load_array(v3/'goal.npy',(196,384),['<f4'])
    if array_id(pred)!=g['production_forecast_supplier_id'] or array_id(gf)!=g['goal_id']:raise ValueError('sealed production tensor identities')
    old=Path(c['recovery']['old_run'])/'tasks/technical-1/output'
    for n,x in c['recovery']['partial'].items():
        if identity(old/n)!=x or (out/n).exists():raise ValueError('exact exclusive partial copy')
        with (old/n).open('rb') as src,(out/n).open('xb') as dest:shutil.copyfileobj(src,dest,1048576)
        if identity(out/n)!=x:raise ValueError('exact copied native supplier bytes')
    r={'status':'AUTHENTICATED_REUSE_NOT_NEW_COMPUTATION','recorded_unix_time':time.time(),'representation':REPRESENTATION,
        'gate_report':c['rc1_technical']['gate_report'],'bank_id':bank.identity,'candidate_ids':g['candidate_ids'],
        'source_RGB_id':array_id(history),'goal_RGB_id':array_id(goal),'production_forecast_supplier_id':array_id(pred),'goal_feature_id':array_id(gf),
        'physical_actions_id':array_id(physical),'normalized_actions_id':array_id(adapter.normalized(physical)),
        'old_partial_members':c['recovery']['partial'],'V3_output_seal':c['rc1']['V3_output_seal'],
        'new_CEM':False,'new_production_forecast':False,'new_reference_forward':False,
        'model_config_runtime_binding':'exact frozen prior_members, runtime_manifest, SIF and original/amended route contracts',
        'original_failed_attempt_preserved':True,'original_uncached_PushT':'FAILED','amended_included_check_uses_completed_RC1_reference':True}
    write_new(out/'REUSE.json',r)
    return bank,Features(frozen(pred),adapter.contract,bank.identity,source_id,'predicted'),gf
