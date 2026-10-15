"""The exact approved 78-frame/15-predictor numerical workload, once."""
import json,sys
from pathlib import Path
import numpy as np
import torch
from wm_diag0_campaign_v4.models import Adapter
from wm_diag0.core import array_id
from wm_diag0_native_v3.store import authenticate,load_array,save_array,seal
from wm_diag0_native_v3.runtime import verify_imports
from .common import identity,write_new,COMMON,CONTEXT,EXPECTED_USAGE
from .metrics import compare,decision
from .bank import retained

def cpu(t):return t.detach().float().cpu().numpy()

def instrument(adapter,usage):
    hooks=[]
    def hook(key):
        def count(module,args):
            usage[key]+=1
            if key=='visual_encoder_calls':usage['encoded_frames']+=int(args[0].shape[0])
        return count
    # Native encode_obs calls encoder.forward directly, bypassing Module hooks.
    # The pinned DINO prepare_tokens path calls patch_embed exactly once instead.
    hooks.append(adapter.model.encoder.model.patch_embed.register_forward_pre_hook(hook('visual_encoder_calls')))
    for name,key in [('proprio_encoder','proprio_encoder_calls'),
                     ('action_encoder','action_encoder_calls'),('predictor','predictor_calls')]:
        hooks.append(getattr(adapter.model,name).register_forward_pre_hook(hook(key)))
    return hooks

def tensor_versions(model):
    # Registered state plus the predictor's unregistered attention masks.
    out=[]
    for m in model.modules():
        for x in list(m.parameters(recurse=False))+list(m.buffers(recurse=False))+[v for v in vars(m).values() if torch.is_tensor(v)]:
            out.append((id(x),x._version,tuple(x.shape),str(x.dtype),str(x.device)))
    return out

def role(adapter,pixels):
    routes=[]
    for repeat in range(2):
        one=np.stack([cpu(adapter.encode_tensor(pixels[i:i+1]))[0] for i in COMMON])
        five=cpu(adapter.encode_tensor(pixels[COMMON]))
        eight=cpu(adapter.encode_tensor(pixels[CONTEXT]))
        routes.append({'1':one,'5':five,'8':eight})
    loc=[CONTEXT.index(i) for i in COMMON]; comparisons={}
    for i,r in enumerate(routes):
        for key,a,b in [('1v5',r['1'],r['5']),('1v8',r['1'],r['8'][loc]),('5v8',r['5'],r['8'][loc])]:
            comparisons[str(i)+'-'+key]=compare(a,b)
    return {'comparisons':comparisons,'repeats':{k:compare(routes[0][k],routes[1][k]) for k in ('1','5','8')},
            'input_ids':{str(i):array_id(pixels[i]) for i in CONTEXT}}

def conditional(adapter,pixels,c,output,usage):
    from .reference import CanonicalVisualReference
    bank,physical=retained(c)
    history=pixels[20:21];goal_rgb=pixels[44];wm=adapter.model
    source_pixels=adapter.pixels(history)[None]
    with adapter.autocast():
        canonical=wm.encode_obs({'visual':source_pixels,'proprio':torch.zeros(1,1,1,device=adapter.device)})['visual'].float()
        canonical_goal=wm.encode_obs({'visual':adapter.pixels(goal_rgb[None])[None],
                                    'proprio':torch.zeros(1,1,1,device=adapter.device)})['visual'][0,0].float()
    source_id=identity(Path(c['source_runs']['pusht'])/'tasks/pusht-000/output/MEMBERS.json')['sha256']
    predicted=adapter.predict(history,bank,source_id)
    goal=adapter.encode(goal_rgb[None])[0]
    if len(adapter.cache)!=1:raise ValueError('own fresh source cache')
    cached=next(iter(adapter.cache.values()))
    source_check=compare(cpu(cached),cpu(canonical));goal_check=compare(goal,cpu(canonical_goal))
    if not source_check['exact_bits'] or not goal_check['exact_bits']:raise ValueError('canonical supplier differs from actual production input')
    info=adapter.public_info(history,goal_rgb);n=16
    expanded={k:v[:,None].expand(1,n,*v.shape[1:]) for k,v in info.items()}
    z=torch.from_numpy(adapter.normalized(physical)).to(adapter.device)
    first=adapter.costs(dict(expanded),z[None])
    ref=CanonicalVisualReference(wm,canonical,source_pixels)
    with adapter.autocast():
        native,_=ref.rollout({'visual':source_pixels.expand(n,-1,-1,-1,-1),
                              'proprio':torch.zeros(n,1,1,device=adapter.device)},z)
    if ref.boundary_calls!=1:raise ValueError('one original reference rollout')
    # Each scalar reduction below is one of the three already approved paths.
    g=torch.as_tensor(goal,device=adapter.device)
    second=(native['visual'][:,-1].float()-g).pow(2).mean((1,2))[None]
    own=(torch.from_numpy(np.array(predicted.values[:,-1],copy=True)).to(adapter.device)-g).square().mean((1,2))
    usage['cost_reforecast_API_operations']+=adapter.cost_api_calls+1
    usage['terminal_score_reductions']+=3
    save_array(output/'predicted.npy',predicted.values);save_array(output/'goal.npy',goal)
    return {'source_cache':source_check,'goal':goal_check,'cached_cost':compare(cpu(first[0]),cpu(own)),
            'terminal_cost':compare(cpu(first),cpu(second)),
            'forecast':compare(predicted.values,cpu(native['visual'][:,1:])),
            'bank_id':bank.identity,'candidate_ids':[x.identity for x in bank.candidates],
            'predicted_id':array_id(predicted.values),'goal_id':array_id(goal),
            'source_RGB_id':array_id(history),'goal_RGB_id':array_id(goal_rgb),
            'route':adapter.contract.__dict__,'reference_encode_obs_calls':ref.boundary_calls,
            'scope':'conditional recurrence only; original uncached PushT FAILED / Reacher UNTESTED'}

@torch.inference_mode()
def main():
    root=Path(sys.argv[1]);cp=root/'source/VALIDATION-CONTRACT.json';c=json.loads(cp.read_text())
    if identity(cp)['sha256']!=sys.argv[2] or not c['numerical_validation_authorized'] or c['gpu_stages_authorized']:raise ValueError('exact validation-only authorization')
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0) not in c['allowed_gpu_names']:raise ValueError('exact single GPU')
    for name,row in c['prior_members'].items():
        if identity(Path(c['prior_source'])/name)!=row:raise ValueError('authenticated original source/models/config')
    sa=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(sa)!=c['source_acceptance']:raise ValueError('fixed accepted sources')
    acceptance=json.loads(sa.read_text());out=root/'tasks/numerical-validation/output'
    usage={k:0 for k in EXPECTED_USAGE};report={'roles':{},'contract_sha256':sys.argv[2],
        'rtol':2**-6,'atol':2**-8,'tolerances_changed':False,'production_changed':False,
        'old_uncached_PushT':'FAILED','old_uncached_Reacher':'UNTESTED',
        'campaign_resumption_authorized':False,'efficacy_or_readout_outputs_inspected':False,
        'GPU':torch.cuda.get_device_name(0),'torch':torch.__version__,'source_seals':{}}
    for task in ('pusht','reacher'):
        directory=Path(c['source_runs'][task])/('tasks/'+task+'-000/output')
        source_seal=acceptance['source_seals'][task+'-000'];authenticate(directory,source_seal,12_000_000)
        pixels=load_array(directory/'evidence/pixels.npy',(45,224,224,3),['|u1'])
        if not np.array_equal(load_array(directory/'selector/history.npy'),pixels[20:21]) or not np.array_equal(load_array(directory/'selector/goal.npy'),pixels[44]):raise ValueError('fixed source20/goal44')
        report['source_seals'][task]=source_seal
        # Keep state version counters available; all actual forwards remain inference-only.
        with torch.inference_mode(False):adapter=Adapter(task,'dinowm_noprop',root/'source',c)
        usage['predictor_bundle_loads']+=1;usage['restricted_encoder_loads']+=1
        verify_imports(c,root/'source');hooks=instrument(adapter,usage);before=tensor_versions(adapter.model)
        report['roles'][task]=role(adapter,pixels)
        if task=='pusht':report['conditional']=conditional(adapter,pixels,c,out,usage)
        if tensor_versions(adapter.model)!=before:raise ValueError('frozen module state mutation')
        for h in hooks:h.remove()
        del adapter
        torch.cuda.empty_cache()
    if usage!=EXPECTED_USAGE:raise ValueError('actual hooked workload differs: '+repr(usage))
    report.update(actual_usage=usage,**decision(report))
    report['status']='NUMERICAL_CHECKS_PASSED_PENDING_PRO' if report['all_numerical_checks_passed'] else 'NUMERICAL_GATE_FAILED_CAMPAIGN_STOPPED'
    verify_imports(c,root/'source')
    write_new(out/'VALIDATION.json',report)
    external=seal(out,26_000_000)
    write_new(root/'tasks/numerical-validation/controls/OUTPUT-SEAL.json',external)
    print(json.dumps({'status':report['status'],'actual_usage':usage,'output_seal':external}))

if __name__=='__main__':main()
