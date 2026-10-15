"""Exactly one88-frame/5-predictor RC1 gate; no fitting/CEM/physics."""
import json,sys,time
from pathlib import Path
import numpy as np
import torch
from wm_diag0.core import array_id
from wm_diag0_native_v3.store import authenticate,load_array,save_array,seal
from wm_diag0_native_v3.runtime import verify_imports
from wm_diag0_numerical_v3.metrics import compare
from wm_diag0_numerical_v3.bank import retained
from wm_diag0_numerical_v3.worker import tensor_versions
from .common import COMMON,CONTEXT,EXPECTED_GATE_USAGE,REPRESENTATION,identity,write_new,canonical
from .models import PointwiseAdapter
from .decision import timing,decision

def cpu(t):return t.detach().float().cpu().numpy()

def role(adapter,pixels):
    routes=[]
    for repeat in range(2):
        one=np.stack([cpu(adapter.encode_tensor(pixels[i:i+1]))[0] for i in COMMON])
        five=cpu(adapter.encode_tensor(pixels[COMMON]));eight=cpu(adapter.encode_tensor(pixels[CONTEXT]))
        routes.append({'1':one,'5':five,'8':eight})
    loc=[CONTEXT.index(i) for i in COMMON]
    comparisons={}
    for i,r in enumerate(routes):
        for key,a,b in [('1v5',r['1'],r['5']),('1v8',r['1'],r['8'][loc]),('5v8',r['5'],r['8'][loc])]:comparisons[str(i)+'-'+key]=compare(a,b)
    return {'comparisons':comparisons,'repeats':{k:compare(routes[0][k],routes[1][k]) for k in ('1','5','8')},
            'input_ids':{str(i):array_id(pixels[i]) for i in CONTEXT}},routes[0]['1']

def reference(adapter,pixels,common_features,c,out,prior):
    from .reference import PointwiseRGBReference
    bank,physical=retained(c)
    q=prior['conditional'];v3=Path(c['rc1']['V3_run'])/'tasks/numerical-validation/output'
    authenticate(v3,c['rc1']['V3_output_seal'],26_000_000,{'predicted.npy','goal.npy','VALIDATION.json'})
    predicted=load_array(v3/'predicted.npy',(16,5,196,384),['<f4'],25_000_000)
    goal=load_array(v3/'goal.npy',(196,384),['<f4'],400_000)
    if canonical(adapter.original_contract.__dict__)!=canonical(q['route']):raise ValueError('unchanged original planning representation')
    if array_id(predicted)!=q['predicted_id'] or array_id(goal)!=q['goal_id'] or bank.identity!=q['bank_id'] or [x.identity for x in bank.candidates]!=q['candidate_ids']:
        raise ValueError('authenticated V3 bank/forecast/goal identity')
    if array_id(pixels[20:21])!=q['source_RGB_id'] or array_id(pixels[44])!=q['goal_RGB_id']:raise ValueError('unchanged RGB supplier')
    source_exact=array_id(common_features[0][None,None])==q['source_cache']['left_id']
    goal_exact=array_id(common_features[-1])==q['goal_id']
    source=adapter.pixels(pixels[20:21])[None]
    actions=torch.from_numpy(adapter.normalized(physical)).to(adapter.device)
    ref=PointwiseRGBReference(adapter.model)
    with adapter.autocast():
        native,_=ref.rollout({'visual':source.expand(16,-1,-1,-1,-1),
                             'proprio':torch.zeros(16,1,1,device=adapter.device)},actions)
    forecast=cpu(native['visual'][:,1:])
    terminal=cpu((native['visual'][:,-1].float()-torch.as_tensor(goal,device=adapter.device)).pow(2).mean((1,2))[None])
    save_array(out/'reference.npy',forecast)
    return {'forecast':compare(predicted,forecast),'source_binding_exact':source_exact,'goal_binding_exact':goal_exact,
      'terminal_cost_identity_exact':array_id(terminal)==q['terminal_cost']['left_id'],
      'terminal_cost_id':array_id(terminal),'source_cache_id':array_id(common_features[0][None,None]),
      'goal_id':array_id(goal),'pointwise_goal_id':array_id(common_features[-1]),'source_RGB_id':q['source_RGB_id'],'goal_RGB_id':q['goal_RGB_id'],
      'bank_id':bank.identity,'candidate_ids':q['candidate_ids'],'V3_output_seal':c['rc1']['V3_output_seal'],
      'production_forecast_supplier_id':array_id(predicted),'reference_boundary_calls':ref.boundary_calls,
      'representation':REPRESENTATION,'old_route':q['route'],'amended_route':adapter.contract.__dict__,
      'reused_not_newly_computed':True,'CEM_repeated':False}

@torch.inference_mode()
def main():
    root=Path(sys.argv[1]);cp=root/'source/RC1-CONTRACT.json';c=json.loads(cp.read_text());expected=sys.argv[2]
    if identity(cp)['sha256']!=expected or not c['rc1']['gate_authorized'] or c['gpu_stages_authorized']:
        raise ValueError('exact gate-only frozen contract')
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0) not in c['allowed_gpu_names']:raise ValueError('exact one GPU')
    for n,x in c['prior_members'].items():
        if identity(Path(c['prior_source'])/n)!=x:raise ValueError('original input/model/config identity')
    sa=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(sa)!=c['source_acceptance']:raise ValueError('accepted source authority')
    acceptance=json.loads(sa.read_text())
    v3=Path(c['rc1']['V3_run'])/'tasks/numerical-validation/output/VALIDATION.json'
    if identity(v3)!=c['rc1']['V3_report']:raise ValueError('V3 authenticated report')
    prior=json.loads(v3.read_text());out=root/'tasks/rc1-gate/output'
    report={'roles':{},'timing':{},'source_seals':{},'contract_sha256':expected,'representation':REPRESENTATION,
      'rtol':2**-6,'atol':2**-8,'tolerances_changed':False,'efficacy_inspected':False,
      'old_uncached_PushT':'FAILED','old_uncached_Reacher':'UNTESTED','campaign_resumed':False}
    usage={k:0 for k in EXPECTED_GATE_USAGE}
    for task in ('pusht','reacher'):
        directory=Path(c['source_runs'][task])/('tasks/'+task+'-000/output');source_seal=acceptance['source_seals'][task+'-000']
        authenticate(directory,source_seal,12_000_000)
        pixels=load_array(directory/'evidence/pixels.npy',(45,224,224,3),['|u1'])
        if not np.array_equal(load_array(directory/'selector/history.npy'),pixels[20:21]) or not np.array_equal(load_array(directory/'selector/goal.npy'),pixels[44]):raise ValueError('fixed20/44source')
        report['source_seals'][task]=source_seal
        torch.cuda.synchronize();began=time.monotonic()
        with torch.inference_mode(False):adapter=PointwiseAdapter(task,'dinowm_noprop',root/'source',c)
        torch.cuda.synchronize();load_seconds=time.monotonic()-began
        usage['predictor_bundle_loads']+=1;usage['restricted_encoder_loads']+=1
        verify_imports(c,root/'source');before=tensor_versions(adapter.model)
        report['roles'][task],features=role(adapter,pixels)
        report['timing'][task]=timing(load_seconds,adapter.single_image_seconds.copy())
        if task=='pusht':
            report['reference']=reference(adapter,pixels,features,c,out,prior)
            usage['cost_reforecast_API_operations']+=1;usage['terminal_score_reductions']+=1
        if tensor_versions(adapter.model)!=before:raise ValueError('frozen inference state changed')
        for k,x in adapter.actual.items():usage[k]+=x
        for h in adapter.hooks:h.remove()
        del adapter;torch.cuda.empty_cache()
    if usage!=EXPECTED_GATE_USAGE:raise ValueError('actual hooked usage mismatch '+repr(usage))
    report.update(actual_usage=usage,**decision(report))
    report['status']='RC1_GATE_PASSED_PENDING_PRO' if report['all_RC1_checks_passed'] else 'RC1_GATE_FAILED_CAMPAIGN_STOPPED'
    verify_imports(c,root/'source');write_new(out/'RC1-GATE.json',report)
    external=seal(out,26_000_000);write_new(root/'tasks/rc1-gate/controls/OUTPUT-SEAL.json',external)
    print(json.dumps({'status':report['status'],'actual_usage':usage,'output_seal':external}))

if __name__=='__main__':main()
