"""RC1 fork of original native acceptance: explicit retained-bank gate supplier only.
Original equations, selection firewall and endpoint checks unchanged.
"""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from wm_diag0.core import array_id,digest,FeatureContract
from wm_diag0_native_v3.store import authenticate,load_array
from wm_diag0_campaign_v4.readout import load as load_readout
from wm_diag0_native_v3.common import canonical,identity

def endpoint(task,state,goal):
    a,b=np.asarray(state,dtype=np.float64),np.asarray(goal,dtype=np.float64)
    if a.shape!=b.shape or not np.isfinite(a).all():raise ValueError('native endpoint evidence shape')
    if task=='reacher':return bool(np.all(np.abs(a-b)<.05))
    angle=abs(a[4]-b[4])%(2*np.pi)
    return bool(np.linalg.norm(a[:4]-b[:4])<20 and min(angle,2*np.pi-angle)<np.pi/9)

def margin(task,p,g):
    if task=='reacher':return np.max(abs(p-g)/.05,axis=-1)
    n=np.linalg.norm(p[:,4:6],axis=1,keepdims=True);m=np.linalg.norm(g[4:6])
    pa=np.divide(p[:,4:6],n,out=np.tile([1.,0.],(len(p),1)),where=n>1e-8)
    ga=g[4:6]/m if m>1e-8 else np.array([1.,0.])
    angular=np.abs(np.arctan2(pa[:,1]*ga[0]-pa[:,0]*ga[1],pa@ga))/(np.pi/9)
    return np.maximum(np.linalg.norm(p[:,:4]-g[:4],axis=1)/20,angular)

def events_check(events,task,goal,max_actions,source_audit):
    if not 1<=len(events)<=max_actions+1:raise ValueError('absolute native branch clock')
    for i,e in enumerate(events):
        if e['clock']!=i or e['native_clocks']['clock']!=20+i or e['native_clocks']['wrapper_elapsed']!=20+i:raise ValueError('replay/diagnostic/wrapper clock')
        if any(type(e[k]) is not bool for k in ('success','terminated','truncated')):raise ValueError('boolean endpoint flags')
        if e['success']!=endpoint(task,e['coordinates'],goal):raise ValueError('independent native endpoint disagreement')
        if i and e['success'] and not e['terminated']:raise ValueError('native success must terminate after actual step')
        if i<len(events)-1 and any(e[k] for k in ('success','terminated','truncated')):raise ValueError('post-stop physical step')
        if task=='reacher' and i:
            a=events[i-1]['native_clocks'];b=e['native_clocks'];delta=b['step_count']-a['step_count']
            if delta not in (1,2) or (delta==1 and not e['success']):raise ValueError('native action_repeat clock')
            if b['physics_time']<=a['physics_time']:raise ValueError('native physical time')
    if events[0]['audit']!=source_audit:raise ValueError('fresh source state after metadata-only goal installation')
    if len(events)<max_actions+1 and not any(events[-1][k] for k in ('success','terminated','truncated')):raise ValueError('premature branch stop')

def source(directory,seal,row):
    directory=Path(directory);authenticate(directory,seal,12_000_000)
    record=json.loads((directory/'record.json').read_text())
    if record['root']!=row or not record['available']:raise ValueError('accepted fixed source/goal')
    coords=load_array(directory/'evidence/coordinates.npy',(45,7 if row['task']=='pusht' else 2),['<f8'])
    history=load_array(directory/'selector/history.npy',(1,224,224,3),['|u1'])
    goal=load_array(directory/'selector/goal.npy',(224,224,3),['|u1'])
    return record,coords,history,goal

def accept(directory,seal,external,source_dir,source_seal,readout_dir,readout_seal,c,gpu=True):
    root=Path(directory);authenticate(root,seal,60_000_000)
    ext=json.loads(Path(external).read_text())
    if identity(root/'SELECTION.json')!=ext['seal']:raise ValueError('externally retained pre-evaluation seal')
    selected=json.loads((root/'SELECTION.json').read_text());row=selected['root'];task=row['task'];backbone=selected['backbone']
    for name,member in selected['members_before_evaluation'].items():
        if identity(root/name)!=member:raise ValueError('preselection member changed')
    n=len(selected['candidate_ids'])
    if not 1<=n<=16 or len(set(selected['candidate_ids']))!=n or selected['native_index']!=0:raise ValueError('fixed native/ragged bank')
    expected={'trace.npy','trace-costs.npy','actions.npy','native-elites.npy','native-mean.npy','native-indices.npy','predicted.npy','realized.npy','goal.npy','costs.npy','SELECTION.json','USAGE.json'}
    if selected['technical']:expected.add('PARITY.json')
    if selected.get('RC1_retained_bank_continuation'):expected.add('REUSE.json')
    for i in range(n):
        expected|={'oracle/'+str(i)+'/'+f for f in ('actions.npy','PREFIX.json','5.png','10.png','15.png','20.png','25.png')}
        for j in (0,1):expected|={'evaluation/'+str(i)+'-'+str(j)+'/'+f for f in ('actions.npy','BRANCH.json')}
    authenticate(root,seal,60_000_000,expected)
    record,coordinates,history,goal_rgb=source(source_dir,source_seal,row)
    rd=dict(selected['route']);rd['feature_shape']=tuple(rd['feature_shape']);rd['positions']=tuple(rd['positions']);contract=FeatureContract(**rd)
    if contract.history_length!=1 or contract.positions!=(5,10,15,20,25) or contract.feature_shape!=((192,) if backbone=='lewm' else (196,384)):raise ValueError('native layout/time contract')
    checkpoint=c['lewm'][task]['sha256'] if backbone=='lewm' else c['prior_members']['artifacts/'+task+'.pth']['sha256']
    if contract.checkpoint_sha256!=checkpoint:raise ValueError('checkpoint route')
    source_id=canonical({'root':row['root_id'],'source':array_id(history),'goal':array_id(goal_rgb),'route':contract.identity})
    if selected['source_id']!=source_id or selected['source_seal']!=source_seal:raise ValueError('source/goal identity')
    head=load_readout(SimpleNamespace(contract=contract,task=task,backbone=backbone),readout_dir,readout_seal)
    if head.identity!=selected['readout_id']:raise ValueError('fit-only readout identity')
    arrays={name:load_array(root/(name+'.npy'),shape,['<f4']) for name,shape in
            (('actions',(n,25,2)),('trace',(9000,25,2)),('trace-costs',(9000,)),('native-elites',(30,5,10)),('native-mean',(5,10)),
             ('predicted',(n,5,*contract.feature_shape)),('realized',(n,5,*contract.feature_shape)),('goal',contract.feature_shape))}
    indices=load_array(root/'native-indices.npy',(30,),['<i8'])
    costs=load_array(root/'costs.npy',(4,n),['<f8'])
    if np.any(indices<0) or np.any(indices>=300) or len(set(indices.tolist()))!=30:raise ValueError('native elite indices')
    stats=json.loads((Path(c['prior_source'])/('configs/'+task+'/swm_h5_norm_stats.json')).read_text());mean=np.array(stats['action_mean']);scale=np.array(stats['action_std'])
    def decode(a):
        x=a.reshape(*a.shape[:-2],25,2).copy();x*=scale;x+=mean;return x
    if not np.array_equal(decode(arrays['native-mean']),arrays['actions'][0]) or not np.array_equal(decode(arrays['native-elites']),arrays['trace'][8700+indices]):raise ValueError('native return/physical decoder proof')
    if not np.array_equal(np.sort(arrays['trace-costs'][8700+indices]),np.sort(arrays['trace-costs'][8700:])[:30]):raise ValueError('native top30 costs')
    if gpu:
        import torch
        m=torch.from_numpy(arrays['native-elites'])[None].cuda().mean(1)[0].cpu().numpy()
        if not np.array_equal(m,arrays['native-mean']):raise ValueError('native returned elite mean bits')
    seen={array_id(arrays['actions'][0])};unique=[]
    for i in sorted(range(9000),key=lambda i:(float(arrays['trace-costs'][i]),i)):
        key=array_id(arrays['trace'][i])
        if key not in seen:unique.append(i);seen.add(key)
    strong=unique[:7];rest=unique[7:];ranks=sorted(set(np.linspace(0,len(rest)-1,min(8,len(rest))).astype(int))) if rest else []
    picked=strong+[rest[i] for i in ranks]
    if n!=len(picked)+1 or not np.array_equal(arrays['actions'][1:],arrays['trace'][picked]):raise ValueError('independent fixed bank reconstruction')
    if [array_id(x) for x in arrays['actions']]!=selected['candidate_ids']:raise ValueError('candidate byte identity')
    traced=digest({'actions':array_id(arrays['trace']),'costs':array_id(arrays['trace-costs'].astype(np.float64))})
    bank_id=digest({'actions':selected['candidate_ids'],'native':0,'trace':traced})
    if selected['trace_digest']!=traced or selected['bank_id']!=bank_id:raise ValueError('independent trace/bank identity')
    sel=selected['selection']
    if (sel['bank_id'],sel['source_id'],sel['contract_id'],sel['goal_id'],sel['s1_id'])!=(bank_id,source_id,contract.identity,array_id(arrays['goal']),head.identity):raise ValueError('complete selection information binding')
    recomputed=[]
    for key in ('predicted','realized'):
        x=arrays[key][:,-1];g=arrays['goal']
        if gpu:
            import torch
            d=torch.from_numpy(x.copy()).cuda()-torch.from_numpy(g.copy()).cuda()
            s0=(d.pow(2).sum(-1) if backbone=='lewm' else d.pow(2).mean((1,2))).cpu().numpy().astype(np.float64)
        else:
            d=x-g;s0=(np.sum(d*d,axis=-1) if backbone=='lewm' else np.mean(d*d,axis=(1,2))).astype(np.float64)
        xp=(x.astype(np.float64).reshape(n,-1)-head.mean)/head.scale@head.weights+head.intercept
        gp=(((g.astype(np.float64).reshape(1,-1)-head.mean)/head.scale)@head.weights+head.intercept)[0]
        recomputed.extend([s0,margin(task,xp,gp)])
    recomputed=np.stack(recomputed)
    if gpu:
        if not np.array_equal(recomputed[[0,2]],costs[[0,2]]):raise ValueError('independent native S0 device bits')
    elif not np.allclose(recomputed[[0,2]],costs[[0,2]],rtol=2e-6,atol=2e-6):raise ValueError('independent CPU S0 check')
    if not np.allclose(recomputed[[1,3]],costs[[1,3]],rtol=1e-12,atol=1e-12):raise ValueError('independent fixed S1')
    choices=np.argmin(costs,axis=1)
    if choices.tolist()!=selected['selection']['choices'] or [array_id(v) for v in costs]!=selected['selection']['cost_ids']:raise ValueError('preselection choice/tie/cost identity')
    # Only after independent source/bank/readout/cost/selection authentication
    # may this validator open any evaluation outcome file.
    owner_ids={selected['goal_installation']['world_serial']};labels=[];reasons=[];initial=[]
    if selected['technical']:
        parity=json.loads((root/'PARITY.json').read_text())
        if parity['status']!='PASSED' or parity['restoration_worlds']!=2:raise ValueError('included first-setting technical gate')
        reused=selected.get('RC1_retained_bank_continuation',False)
        if reused:
            if task!='pusht' or backbone!='dinowm_noprop' or parity['additional_sequences']!=0 or not parity.get('amended_RC1_gate_reused'):raise ValueError('exact approved retained-bank parity supplier')
            from .reuse import validate_receipt
            validate_receipt(root/'REUSE.json',c,selected)
        elif parity['additional_sequences']!=2*n:raise ValueError('fresh included technical reference sequences')
        owner_ids|={x['goal']['world_serial'] for x in parity['restoration']}
        if len(owner_ids)!=3:raise ValueError('fresh technical/helper ownership')
    from PIL import Image
    for i in range(n):
        prefix=root/'oracle'/str(i);p=json.loads((prefix/'PREFIX.json').read_text());steps=p['actions']
        if type(steps) is not int or not 0<=steps<=25:raise ValueError('oracle prefix clock')
        pa=load_array(prefix/'actions.npy',(steps,2),['<f4'])
        if not np.array_equal(pa,arrays['actions'][i,:steps]):raise ValueError('oracle physical prefix')
        events_check(p['events'],task,coordinates[44],25,record['frames'][20]['audit'])
        for t in (5,10,15,20,25):
            with Image.open(prefix/(str(t)+'.png')) as image:
                if image.format!='PNG' or image.size!=(224,224) or image.mode!='RGB':raise ValueError('bounded native RGB sampling')
                pix=np.array(image)
            if array_id(pix)!=p['events'][min(t,steps)]['pixels']:raise ValueError('realized visual sampling/absorption')
        owner=p['goal_installation']['world_serial']
        if owner in owner_ids:raise ValueError('oracle world reused')
        owner_ids.add(owner);y=[];why=[]
        for draw in (0,1):
            branch=root/'evaluation'/(str(i)+'-'+str(draw));b=json.loads((branch/'BRANCH.json').read_text());elapsed=b['elapsed']
            ba=load_array(branch/'actions.npy',(elapsed,2),['<f4'])
            if not 0<=elapsed<=50 or b['replay_steps']!=20 or b['draw_seed']!=selected['evaluation_draws'][draw]:raise ValueError('absolute budget/draw/replay binding')
            if not np.array_equal(ba[:min(25,elapsed)],arrays['actions'][i,:min(25,elapsed)]):raise ValueError('evaluation same candidate prefix')
            if b['tail_replans']!=int(elapsed>25):raise ValueError('one branch-owned native replan')
            events_check(b['events'],task,coordinates[44],50,record['frames'][20]['audit'])
            last=b['events'][-1]
            reason='success' if last['success'] else 'truncated' if last['truncated'] else 'terminal_failure' if last['terminated'] else 'budget_failure'
            if b['reason']!=reason:raise ValueError('independent native termination reason')
            upto=min(25,elapsed)
            if b['events'][:upto+1]!=p['events'][:upto+1]:raise ValueError('fresh native replay action-consequence/observation equality')
            owner=b['goal_installation']['world_serial']
            if owner in owner_ids:raise ValueError('evaluation/tail world reused')
            owner_ids.add(owner);y.append(int(b['events'][-1]['success']));why.append(b['reason'])
        labels.append(y);reasons.append(why);initial.append(p['events'][0]['success'])
    if len(set(initial))!=1 or len(owner_ids)!=1+3*n+(2 if selected['technical'] else 0):raise ValueError('initial success/world ownership')
    return {'accepted':True,'root_id':row['root_id'],'task':task,'backbone':backbone,'source_id':source_id,'candidate_count':n,
            'selection_seal':ext['seal'],'output_seal':seal,'initial_success':bool(initial[0]),
            'choices':choices.tolist(),'outcomes':labels,'reasons':reasons,'native_index':0,
            'technical':selected['technical'],'worlds':len(owner_ids),'native_endpoints_independently_checked':True}


