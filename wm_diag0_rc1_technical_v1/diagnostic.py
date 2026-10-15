"""Original source/oracle/evaluation protocol; explicit approved bank continuation."""
import json
from pathlib import Path
import numpy as np
import torch
from wm_diag0_campaign_v4.diagnostic import source_record,prefix,branch
from wm_diag0_campaign_v4.planning import solve,substream
from wm_diag0_campaign_v4.world import restore
from wm_diag0.core import Features,array_id,frozen,select_four
from wm_diag0_native_v3.store import PhaseAccess,save_array,seal
from .common import identity,write_new,canonical

def restorations(record,arrays):
    checks=[]
    for _ in range(2):
        w,r=restore(record,arrays)
        try:checks.append({'state':canonical(w.audit()),'pixels':array_id(w.pixels()),'goal':r})
        finally:w.close()
    if checks[0]['state']!=checks[1]['state'] or checks[0]['pixels']!=checks[1]['pixels'] or checks[0]['goal']['world_serial']==checks[1]['goal']['world_serial']:raise ValueError('two fresh restoration worlds')
    return checks

@torch.inference_mode()
def parity(adapter,record,arrays,bank,predicted,goal,reused):
    n=len(bank.candidates)
    if not reused:
        if adapter.backbone=='lewm':
            from wm_diag0_campaign_v4.diagnostic import parity as original
            return original(adapter,record,arrays,bank,predicted,goal)
        z=torch.from_numpy(adapter.normalized(np.stack([x.actions for x in bank.candidates]))).to(adapter.device)
        info=adapter.public_info(np.stack([arrays['pixels'][20]]),arrays['pixels'][44])
        expanded={k:v[:,None].expand(1,n,*v.shape[1:]) for k,v in info.items()}
        first=adapter.costs(dict(expanded),z[None])
        from .reference import NativePointwiseReference
        reference=NativePointwiseReference(adapter.model)
        with adapter.autocast():native,_=reference.rollout({'visual':info['pixels'].expand(n,-1,-1,-1,-1),'proprio':torch.zeros(n,1,1,device=adapter.device)},z)
        adapter.predictor_calls+=5;adapter.encoded_frames+=n;adapter.cost_api_calls+=1
        second=(native['visual'][:,-1].float()-torch.as_tensor(goal,device=adapter.device)).pow(2).mean((1,2))[None]
        own=(torch.from_numpy(np.array(predicted.values[:,-1],copy=True)).to(adapter.device)-torch.as_tensor(goal,device=adapter.device)).pow(2).mean((1,2))
        if not torch.equal(first[0],own):raise ValueError('native cached cost bits')
        torch.testing.assert_close(first,second,rtol=2**-6,atol=2**-8)
        torch.testing.assert_close(torch.from_numpy(np.array(predicted.values,copy=True)).to(adapter.device),native['visual'][:,1:].float(),rtol=2**-6,atol=2**-8)
    return {'status':'PASSED','additional_sequences':0 if reused else 2*n,'restoration_worlds':2,'restoration':restorations(record,arrays),
        'native_reference':'completed authenticated RC1 original-method reference supplier' if reused else 'original per-image encode_obs and inherited VWorldModel recurrence',
        'amended_RC1_gate_reused':bool(reused),'T':1,'history_size':3,'grouping':5,'chunk':100,
        'rtol':2**-6,'atol':2**-8,'training_encoder_checkout_verified':False,'unsaved_parent_reference_comparison_checked_in_memory':not reused}

def run(adapter,row,source_dir,source_seal,head,out,external,c,setting):
    out=Path(out);out.mkdir(exist_ok=False);record,arrays=source_record(source_dir,source_seal,row)
    helper,g=restore(record,arrays)
    try:history=np.stack([helper.pixels()]);goal=arrays['pixels'][44].copy()
    finally:helper.close()
    sid=canonical({'root':row['root_id'],'source':array_id(history),'goal':array_id(goal),'route':adapter.contract.identity})
    reused=setting==1
    if reused:
        from .reuse import obtain
        bank,predicted,gf=obtain(adapter,history,goal,c,out,sid)
    else:
        bank,trace,costs,proof=solve(adapter,history,goal,row['seeds']['bank_lewm' if adapter.backbone=='lewm' else 'bank_dino'],capture=True)
        for n,a in proof.items():save_array(out/('native-'+n+'.npy'),a)
        save_array(out/'trace.npy',trace);save_array(out/'trace-costs.npy',costs);save_array(out/'actions.npy',np.stack([x.actions for x in bank.candidates]))
        predicted=adapter.predict(history,bank,sid);gf=adapter.encode(goal[None])[0]
    write_new(out/'PARITY.json',parity(adapter,record,arrays,bank,predicted,gf,reused))
    oracle=out/'oracle';oracle.mkdir();real=[]
    for i,x in enumerate(bank.candidates):real.append(prefix(adapter,record,arrays,x.actions,oracle/str(i)))
    realized=Features(frozen(np.stack(real)),adapter.contract,bank.identity,sid,'realized')
    selection=select_four(bank,predicted,realized,gf,adapter.original_score,head)
    costs=np.stack([f(x,gf) for x,f in ((predicted,adapter.original_score),(predicted,head),(realized,adapter.original_score),(realized,head))])
    for n,x in (('predicted',predicted.values),('realized',realized.values),('goal',gf),('costs',costs)):save_array(out/(n+'.npy'),x)
    phases=PhaseAccess(out)
    pre={'root':row,'backbone':adapter.backbone,'route':adapter.contract.__dict__,'source_id':sid,'source_seal':source_seal,'readout_id':head.identity,
        'selection':selection.__dict__,'bank_id':bank.identity,'candidate_ids':[x.identity for x in bank.candidates],'native_index':0,
        'origins':[x.origin for x in bank.candidates],'trace_digest':bank.trace_digest,'members_before_evaluation':{str(p.relative_to(out)):identity(p) for p in out.rglob('*') if p.is_file()},
        'oracle_seed':row['seeds']['oracle'],'evaluation_draws':[substream(row['seeds'][k],adapter.backbone) for k in ('tail_1','tail_2')],
        'technical':True,'RC1_retained_bank_continuation':reused,'goal_installation':g}
    sealrow=phases.record_selection(pre);write_new(external,{'seal':sealrow,'root_id':row['root_id'],'backbone':adapter.backbone})
    if json.loads(Path(external).read_text())['seal']!=sealrow:raise ValueError('external preselection evidence')
    evaluation=phases.authorize_outcomes(sealrow);evaluation.mkdir()
    for i,x in enumerate(bank.candidates):
        for draw,k in enumerate(('tail_1','tail_2')):branch(adapter,record,arrays,x.actions,substream(row['seeds'][k],adapter.backbone),evaluation/(str(i)+'-'+str(draw)))
    write_new(out/'USAGE.json',{'predictor_calls':adapter.predictor_calls,'encoded_frames':adapter.encoded_frames,'cost_api_calls':adapter.cost_api_calls,
        'actual_module_usage':adapter.actual,'candidate_count':len(bank.candidates),'selection_seal':sealrow,'physics_worlds':3+3*len(bank.candidates),
        'initial_CEM_reused_not_recomputed':reused,'additional_reference_sequences_this_job':0 if reused else 2*len(bank.candidates)})
    return seal(out,59900000 if adapter.backbone=='dinowm_noprop' else 9900000)
