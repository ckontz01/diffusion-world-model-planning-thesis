"""Native fixed-bank intervention job, preselection seal and independent worlds."""
import json
from pathlib import Path
import numpy as np
import torch
from .common import canonical,identity,write_new
from wm_diag0_native_v3.store import PhaseAccess,authenticate,load_array,save_array,seal
from .world import restore
from .planning import solve,substream
from wm_diag0.core import Features,array_id,frozen,native_terminal_score,select_four

def source_record(directory,expected,row):
    directory=Path(directory); authenticate(directory,expected,12_000_000)
    record=json.loads((directory/'record.json').read_text())
    if record['root']!=row or not record['available']: raise ValueError('accepted fixed native source')
    arrays={k:load_array(directory/'evidence'/(k+'.npy')) for k in ('pixels','actions','coordinates')}
    return record,arrays

def record_step(world,pix):
    audit=world.audit()
    clocks={k:audit[k] for k in ('clock','wrapper_elapsed','step_count','physics_time') if k in audit}
    return {'pixels':array_id(pix),'audit':canonical(audit),'native_clocks':clocks,'coordinates':world.coordinates().tolist(),
            'clock':world.clock-20,'success':bool(world.success),'terminated':bool(world.terminated),'truncated':bool(world.truncated)}

def prefix(adapter,record,arrays,actions,output):
    from PIL import Image
    world,goal_receipt=restore(record,arrays)
    sampled={}; events=[]; done=0
    try:
        pix=world.pixels(); events.append(record_step(world,pix))
        for i in range(25):
            if world.stopped: break
            pix=world.step(actions[i]); done+=1; events.append(record_step(world,pix))
            if done in (5,10,15,20,25): sampled[done]=np.array(pix,copy=True)
        if world.stopped:
            for i in (5,10,15,20,25):
                if i>done: sampled[i]=np.array(pix,copy=True)
        if set(sampled)!={5,10,15,20,25}: raise ValueError('realized native sampling clock')
        rgb=np.stack([sampled[t] for t in (5,10,15,20,25)])
        features=adapter.encode(rgb)
        output=Path(output); output.mkdir(exist_ok=False)
        for t,image in zip((5,10,15,20,25),rgb): Image.fromarray(image).save(output/(str(t)+'.png'))
        save_array(output/'actions.npy',actions[:done])
        write_new(output/'PREFIX.json',{'events':events,'goal_installation':goal_receipt,'actions':done,
                                      'sampling':[5,10,15,20,25],'absorbed_after_stop':world.stopped})
        return features
    finally: world.close()

def branch(adapter,record,arrays,actions,draw_seed,output):
    world,goal_receipt=restore(record,arrays)
    events=[]; taken=[]; tail=None
    try:
        pix=world.pixels(); events.append(record_step(world,pix))
        for t in range(50):
            if world.stopped: break
            if t<25: action=actions[t]
            else:
                if tail is None:
                    tail=solve(adapter,np.stack([pix]),arrays['pixels'][44],draw_seed)
                    if tail.shape!=(25,2): raise ValueError('one native tail at action25')
                action=tail[t-25]
            taken.append(np.array(action,copy=True)); pix=world.step(action); events.append(record_step(world,pix))
        output=Path(output); output.mkdir(exist_ok=False)
        save_array(output/'actions.npy',np.stack(taken) if taken else np.empty((0,2),dtype=actions.dtype))
        write_new(output/'BRANCH.json',{'events':events,'goal_installation':goal_receipt,'draw_seed':draw_seed,
                                     'elapsed':len(taken),'tail_replans':int(tail is not None),'replay_steps':20,
                                     'reason':'success' if world.success else 'truncated' if world.truncated else 'terminal_failure' if world.terminated else 'budget_failure'})
    finally: world.close()

@torch.inference_mode()
def parity(adapter,record,arrays,bank,predicted,goal_features):
    z=torch.from_numpy(adapter.normalized(np.stack([c.actions for c in bank.candidates]))).to(adapter.device)
    info=adapter.public_info(np.stack([arrays['pixels'][20]]),arrays['pixels'][44])
    n=len(bank.candidates)
    expanded={k:v[:,None].expand(1,n,*v.shape[1:]) for k,v in info.items()}
    if adapter.backbone=='lewm':
        adapter.predictor_calls+=10; adapter.encoded_frames+=4
        first=adapter.model.get_cost(dict(expanded),z[None])
        second=adapter.model.get_cost(dict(expanded),z[None])
    else:
        first=adapter.costs(dict(expanded),z[None])
        wm=adapter.model
        with adapter.autocast():
            obs={'visual':info['pixels'].expand(n,-1,-1,-1,-1),
                 'proprio':torch.zeros(n,1,1,device=adapter.device)}
            native,_=wm.rollout(obs,z)
        adapter.predictor_calls+=5; adapter.encoded_frames+=n
        second=(native['visual'][:,-1].float()-torch.as_tensor(goal_features,device=adapter.device)).pow(2).mean((1,2))[None]
    own=torch.from_numpy(predicted.values[:,-1]).to(adapter.device)-torch.as_tensor(goal_features,device=adapter.device)
    own=own.square().sum(-1) if adapter.backbone=='lewm' else own.square().mean((1,2))
    # Identical native floating-point operators are required to agree exactly.
    # A failure is retained; tolerance is never relaxed after seeing outputs.
    if not torch.equal(first[0],own): raise ValueError('native cached forecast/cost bits')
    if adapter.backbone=='lewm':
        if not torch.equal(first,second): raise ValueError('original LeWM cost bits')
    else:
        torch.testing.assert_close(first,second,rtol=2**-6,atol=2**-8)
        torch.testing.assert_close(torch.from_numpy(predicted.values).to(adapter.device),native['visual'][:,1:].float(),rtol=2**-6,atol=2**-8)
    checks=[]
    for _ in range(2):
        w,r=restore(record,arrays)
        try: checks.append({'state':canonical(w.audit()),'pixels':array_id(w.pixels()),'goal':r})
        finally: w.close()
    if checks[0]['state']!=checks[1]['state'] or checks[0]['pixels']!=checks[1]['pixels'] or checks[0]['goal']['world_serial']==checks[1]['goal']['world_serial']: raise ValueError('two fresh native restoration branches')
    return {'status':'PASSED','additional_sequences':2*n,'restoration_worlds':2,
            'native_reference':'original deserialized LeWM methods / pinned VWorldModel.rollout over original deserialized DINO components',
            'T':1,'history_size':3,'grouping':5,'chunk':100,'exact_cached_cost_bits':True,'uncached_BF16_reference_rtol':2**-6,'uncached_BF16_reference_atol':2**-8,
            'training_encoder_checkout_verified':False,'restoration':checks}

def run(adapter,row,source_dir,source_seal,readout,output,external_selection,technical):
    output=Path(output); output.mkdir(exist_ok=False)
    record,arrays=source_record(source_dir,source_seal,row)
    # The helper world establishes exact replay and metadata-only goal setting.
    helper,g=restore(record,arrays)
    try:
        history=np.stack([helper.pixels()]); goal=arrays['pixels'][44].copy()
    finally: helper.close()
    source_id=canonical({'root':row['root_id'],'source':array_id(history),'goal':array_id(goal),'route':adapter.contract.identity})
    bank,trace,trace_costs,proof=solve(adapter,history,goal,row['seeds']['bank_lewm' if adapter.backbone=='lewm' else 'bank_dino'],capture=True)
    for name,a in proof.items(): save_array(output/('native-'+name+'.npy'),a)
    save_array(output/'trace.npy',trace); save_array(output/'trace-costs.npy',trace_costs)
    save_array(output/'actions.npy',np.stack([c.actions for c in bank.candidates]))
    predicted=adapter.predict(history,bank,source_id); goal_features=adapter.encode(goal[None])[0]
    if technical: write_new(output/'PARITY.json',parity(adapter,record,arrays,bank,predicted,goal_features))
    oracle=output/'oracle'; oracle.mkdir()
    realized=[]
    for i,c in enumerate(bank.candidates): realized.append(prefix(adapter,record,arrays,c.actions,oracle/str(i)))
    realized=Features(frozen(np.stack(realized)),adapter.contract,bank.identity,source_id,'realized')
    selection=select_four(bank,predicted,realized,goal_features,adapter.original_score,readout)
    costs=np.stack([f(x,goal_features) for x,f in ((predicted,adapter.original_score),(predicted,readout),(realized,adapter.original_score),(realized,readout))])
    for name,x in (('predicted',predicted.values),('realized',realized.values),('goal',goal_features),('costs',costs)): save_array(output/(name+'.npy'),x)
    phases=PhaseAccess(output)
    sealrow={'root':row,'backbone':adapter.backbone,'route':adapter.contract.__dict__,'source_id':source_id,
             'source_seal':source_seal,'readout_id':readout.identity,'selection':selection.__dict__,
             'bank_id':bank.identity,'candidate_ids':[c.identity for c in bank.candidates],'native_index':0,
             'origins':[c.origin for c in bank.candidates],'trace_digest':bank.trace_digest,
             'members_before_evaluation':{str(p.relative_to(output)):identity(p) for p in output.rglob('*') if p.is_file()},
             'oracle_seed':row['seeds']['oracle'],'evaluation_draws':[substream(row['seeds'][k],adapter.backbone) for k in ('tail_1','tail_2')],
             'technical':technical,'goal_installation':g}
    expected=phases.record_selection(sealrow)
    write_new(external_selection,{'seal':expected,'root_id':row['root_id'],'backbone':adapter.backbone})
    if json.loads(Path(external_selection).read_text())['seal']!=expected: raise ValueError('external retained preselection seal')
    evaluation=phases.authorize_outcomes(expected); evaluation.mkdir()
    for i,c in enumerate(bank.candidates):
        for draw,k in enumerate(('tail_1','tail_2')):
            branch(adapter,record,arrays,c.actions,substream(row['seeds'][k],adapter.backbone),evaluation/(str(i)+'-'+str(draw)))
    write_new(output/'USAGE.json',{'predictor_calls':adapter.predictor_calls,'encoded_frames':adapter.encoded_frames,
                                 'candidate_count':len(bank.candidates),'selection_seal':expected,'physics_worlds':1+3*len(bank.candidates)+(2 if technical else 0)})
    return seal(output,59_900_000 if adapter.backbone=='dinowm_noprop' else 9_900_000)
