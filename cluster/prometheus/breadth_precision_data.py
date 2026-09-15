"""Approved-future collection glue. Same backend/decoder/physical verification."""
from pathlib import Path
import time
import numpy as np
import breadth_precision_contract as p
import candidate_value_contract as ct
import candidate_value_learning as c
from candidate_value_data import read_npz,write_npz,coverage,checked_decoded_bank
from candidate_value_data import validate_saved_trajectory,validate_candidate_delivery


def record(manifest,ref,h,role):
    allowed = p.allocation()[role]
    p.require(ref in allowed and h in (75,150), 'Exact source role')
    row=manifest['records'][str(ref)];f=Path(row['file'])
    p.require(f.name=='reference-%05d.npz'%ref and p.sha(f)==row['sha256'],'Pinned permitted record')
    z=read_npz(f);start=z['initial_request'];goal=z['states'][h]
    p.require(start.shape==goal.shape==(7,), 'Original start/goal fields')
    return dict(state=start,goal_state=goal,proprio=start[[0,1,5,6]]),row['environment_seed']


def original(ref,h,with_prefix=False):
    """Use accepted seals; authenticate consumed old members, not re-audit old traces."""
    a=ct.allocation()['train'];p.require(ref in a,'Original training only')
    directory=p.OLD_RUN/('train-%d'%(a.index(ref)*2+(h==150)))
    request_path=p.OLD_RUN/'BACKUP-REQUEST-train.json'
    p.require(p.sha(request_path)==p.TRAIN_REQUEST_SHA,'Accepted old training request')
    request=ct.json_read(request_path)
    p.require(p.sha(directory/'sha256.txt')==request['seals'][directory.name], 'Accepted old seal')
    seals={n:d for d,n in (line.split('  ',1) for line in (directory/'sha256.txt').read_text().splitlines())}
    consumed={}
    def member(name):
        path=ct.child(directory,name);p.require(p.sha(path)==seals[name],'Old consumed member')
        consumed[str(path)]=seals[name];return path
    r=ct.json_read(member('REPORT.json'))
    p.require((r['reference'],r['horizon'],r['source_sha256'],r['capsule_sha256'])==
              (ref,h,p.OLD_SOURCE_SHA,p.OLD_CAPSULE_SHA),'Accepted old identity')
    banks={b['anchor']:read_npz(member('bank-%d.npz'%b['anchor'])) for b in r['banks'] if b['available']}
    prefix=read_npz(member('prefix.npz')) if with_prefix else None
    return r,banks,prefix,consumed


def equal_bank(actual,expected):
    p.require(set(actual)==set(expected),'Candidate bank schema changed')
    for key in expected: np.testing.assert_array_equal(actual[key],expected[key],err_msg=key)


def collect(backend,rec,env_seed,ref,h,kind,out,old_input=None):
    out=Path(out);began=time.monotonic();entries=[];steps=0;consumed={}
    prefix_seed=c.seed('prefix',ref,h)
    if kind=='precision':
        p.require(old_input is not None,'C must reuse accepted banks')
        old_report,banks,prefix,consumed=old_input
        sources=old_report['banks'];draws=(2,3)
        ct.json_write(out/'ORIGINAL-INPUTS.json',consumed)
    else:
        p.require(kind in ('breadth','evaluation') and old_input is None,'Registered collection kind')
        run=backend.episode(rec,h,prefix_seed,env_seed,bank_times=c.anchors(h))
        prefix,banks=run['trace'],run['banks'];draws=(0,1) if kind=='breadth' else (0,1,2,3)
        write_npz(out/'prefix.npz',**prefix);validate_saved_trajectory(read_npz(out/'prefix.npz'),rec,h)
        ct.json_write(out/'prefix-calls.json',run['calls']);steps+=len(prefix['actions'])
        sources=[dict(anchor=t,available=t in banks) for t in c.anchors(h)]
    for src in sources:
        t=src['anchor']
        if not src['available']:
            p.require(len(prefix['actions'])<=t and prefix['flags'][-1].any(),'Unavailable terminal anchor')
            entries.append(dict(anchor=t,available=False,reason='prefix_native_terminal'));continue
        bank=banks[t];sample=p.sampling(bank['immediate'],bank['continuation'],ref,h,t)
        cov=coverage(bank,sample)
        if kind=='precision': p.require(cov==src['coverage'],'C sampled indices/collisions/coverage changed')
        else: write_npz(out/('bank-%d.npz'%t),**bank)
        decoded=checked_decoded_bank(bank)
        entry=dict(anchor=t,available=True,coverage=cov,labels=[],new_draws=list(draws),
                   final_budget_no_stochastic_tail=t==2*h-15,bank_reused=kind=='precision')
        streams={};labels={}
        for candidate in sample['indices']:
            for d in draws:
                seed=p.tail_seed(ref,h,t,d)
                branch=backend.episode(rec,h,prefix_seed,env_seed,forced=(t,candidate),tail_seed=seed)
                trace=branch['trace'];equal_bank(branch['banks'][t],bank)
                for key in ('actions','states','dynamics','flags'):
                    np.testing.assert_array_equal(trace[key][:t],prefix[key][:t])
                np.testing.assert_array_equal(trace['initial'],prefix['initial'])
                state=branch['tail_state'];p.require(state['seed']==seed,'Tail draw identity')
                pair=(state['proposal'],state['gmm'])
                if d in streams:p.require(streams[d]==pair,'Candidate-coupled tail streams')
                streams[d]=pair
                target=c.success_target(trace['flags'][t:,0],trace['flags'][t:,1],remaining=2*h-t)
                name='trace-%d-%d-%d.npz'%(t,candidate,d);write_npz(out/name,**trace)
                saved=read_npz(out/name)
                validate_saved_trajectory(saved,rec,h,anchor=t,target=target)
                validate_candidate_delivery(saved,decoded,t,candidate)
                ct.json_write(out/(name+'.calls.json'),branch['calls'])
                entry['labels'].append(dict(candidate=candidate,draw=d,target=target,tail=state,trace_file=name))
                labels[candidate,d]=target['success'];steps+=len(trace['actions'])
        p.require(len(set(streams.values()))==len(draws),'Distinct actual stream states')
        if kind=='precision':
            for label in src['labels']:
                p.require(label['tail']['seed']==p.tail_seed(ref,h,t,label['draw']),'Original draw scope')
                p.require((label['tail']['proposal'],label['tail']['gmm']) not in streams.values(),'New stream collided with original')
                labels[label['candidate'],label['draw']]=label['target']['success']
        if t==2*h-15:
            for candidate in sample['indices']:
                vals=[v for (i,_),v in labels.items() if i==candidate]
                p.require(len(set(vals))==1,'Final-budget draw discrepancy; no stochastic tail exists')
        entries.append(entry)
    backend.assert_frozen()
    return dict(reference=ref,horizon=h,banks=entries,primitive_steps=steps,
                standalone_prefix_executed=kind!='precision',new_outcomes=sum(len(b.get('labels',[])) for b in entries),
                original_banks_not_replaced=True,independent_saved_artifact_checks=True,
                wall_seconds=time.monotonic()-began,provenance=backend.provenance)


def unpack(r,banks,draws):
    result=[]
    for slot,b in enumerate(r['banks']):
        if not b['available']:continue
        t=b['anchor'];z=banks[t];ids=b['coverage']['indices']
        p.require(len(ids)==len(set(ids))==8,'Eight original indices')
        y=np.full((8,len(draws)),-1,np.int64)
        for label in b['labels']:
            i,d=ids.index(label['candidate']),draws.index(label['draw'])
            p.require(y[i,d]==-1 and label['target']['success'] in (0,1),'Unique binary labels')
            y[i,d]=label['target']['success']
        p.require(np.isin(y,(0,1)).all(),'Complete candidate/draw grid')
        base=ids.index(int(z['continuation_index']))
        result.append(dict(reference=r['reference'],horizon=r['horizon'],anchor=t,slot=slot,x=z['x'][ids],y=y,
            ids=ids,base=base,continuation_index=ids[base],continuation=-z['continuation'][ids],immediate=-z['immediate'][ids]))
    return result


def datasets(run,stage,source_sha):
    """Existing/new saved-data readers; no environment or world-model invocation."""
    a=p.allocation();run=Path(run)
    def new(kind,role,draws):
        rows=[]
        for index in range(2*len(a[role])):
            spec=p.task(kind,index);directory=run/('%s-%d'%(kind,index));r=ct.verify_seal(directory)
            p.require((r['kind'],r['index'],r['reference'],r['horizon'],r['new_source_sha256'])==
                      (kind,index,spec['reference'],spec['h'],source_sha),'New stage identity')
            banks={b['anchor']:read_npz(directory/('bank-%d.npz'%b['anchor'])) for b in r['banks'] if b['available']}
            rows.extend(unpack(r,banks,draws))
        return rows
    if stage=='evaluation':return new('evaluation','evaluation',[0,1,2,3])
    p.require(stage=='training','No unrelated dataset role')
    A=[];C=[]
    for ref in a['original_train']:
        for h in (75,150):
            r,banks,_,_=original(ref,h)
            A.extend(unpack(r,banks,[0,1]))
            index=a['original_train'].index(ref)*2+(h==150)
            extra=ct.verify_seal(run/('precision-%d'%index))
            p.require((extra['kind'],extra['index'],extra['reference'],extra['horizon'],extra['new_source_sha256'])==
                      ('precision',index,ref,h,source_sha),'Precision source identity')
            p.require(len(r['banks'])==len(extra['banks'])==4,'Exact C anchor grid')
            merged=dict(r,banks=[])
            for old_b,new_b in zip(r['banks'],extra['banks']):
                p.require((old_b['anchor'],old_b['available'])==(new_b['anchor'],new_b['available']),'C availability changed')
                if old_b['available']:
                    p.require(old_b['coverage']==new_b['coverage'],'C bank coverage identity')
                    merged['banks'].append(dict(old_b,labels=old_b['labels']+new_b['labels']))
                else:merged['banks'].append(old_b)
            p.require(len(merged['banks'])==4,'Complete anchor grid')
            C.extend(unpack(merged,banks,[0,1,2,3]))
    B=A+new('breadth','extra_train',[0,1])
    p.require(len(A)==len(C)==709 and sum(x['y'].size for x in A)==11344,'Accepted A/C bank counts')
    return dict(A=A,B=B,C=C)
