"""Sealed collection format and selected-record-only input/label validation."""
import time
from pathlib import Path
import numpy as np
import candidate_value_learning as c
import candidate_value_contract as ct


def write_npz(path,**arrays):
    with Path(path).open('xb') as f:np.savez_compressed(f,**arrays)


def read_npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def load_record(capsule,reference,h,role):
    ct.require(reference in ct.allocation()[role] and 0<=reference<1600,'Input role boundary')
    row=capsule['records'][str(reference)];p=Path(row['file'])
    ct.require(ct.sha(p)==row['sha256'],'Selected input bytes')
    z=read_npz(p)
    initial=z['initial_request'];goal=z['states'][h]
    ct.require(initial.shape==goal.shape==(7,),'Input shape')
    return dict(state=initial,goal_state=goal,proprio=initial[[0,1,5,6]]),row['environment_seed']


def coverage(bank,sampled):
    from candidate_value_runtime import array_sha
    a=bank['decoded_actions'];ids=sampled['indices']
    hashes=[array_sha(x) for x in a]
    rounded=np.round(a*1e4).astype(np.int64).reshape(64,-1)
    return {**sampled,'chunk_sha256':hashes,'unique_physical_chunks':len(set(hashes)),
            'raw_chunk_sha256':[array_sha(x) for x in bank['raw_actions']],
            'chunk_identity_space':'actual float32 decoded delivery actions',
            'sampled_unique_physical_chunks':len({hashes[i] for i in ids}),
            'rounded_unique':len(np.unique(rounded,axis=0)),
            'collision_rule':'retain distinct sampled indices; never replace duplicate action values',
            'immediate_ranks':np.argsort(np.argsort(bank['immediate'],kind='stable'),kind='stable')[ids].tolist(),
            'continuation_ranks':np.argsort(np.argsort(bank['continuation'],kind='stable'),kind='stable')[ids].tolist()}


def collect(backend,record,environment_seed,reference,h,out):
    """Shared orchestration for production and synthetic integration tests."""
    out=Path(out);began=time.monotonic();banks=[];steps=0
    prefix_seed=c.seed('prefix',reference,h)
    prefix=backend.episode(record,h,prefix_seed,environment_seed,bank_times=c.anchors(h))
    write_npz(out/'prefix.npz',**prefix['trace'])
    ct.json_write(out/'prefix-calls.json',prefix['calls'])
    steps+=len(prefix['trace']['actions'])
    for t in c.anchors(h):
        if t not in prefix['banks']:
            ct.require(len(prefix['trace']['actions'])<=t and prefix['trace']['flags'][-1].any(),
                       'Missing live anchor')
            banks.append(dict(anchor=t,available=False,reason='prefix_native_terminal',
                              prefix_steps=len(prefix['trace']['actions'])))
            continue
        bank=prefix['banks'][t]
        sample=c.sample_bank(bank['immediate'],bank['continuation'],reference=reference,h=h,t=t)
        write_npz(out/('bank-%d.npz'%t),**bank)
        entry=dict(anchor=t,available=True,coverage=coverage(bank,sample),labels=[])
        streams=ct.tail_seeds(reference,h,t);ct.require(streams[0]!=streams[1],'Tail seed collision')
        stream_hashes={}
        for candidate in sample['indices']:
            for draw,stream in enumerate(streams):
                branch=backend.episode(record,h,prefix_seed,environment_seed,forced=(t,candidate),tail_seed=stream)
                trace=branch['trace'];other=branch['banks'][t]
                for key in bank:
                    np.testing.assert_array_equal(other[key],bank[key])
                for key in ('actions','states','dynamics','flags'):
                    np.testing.assert_array_equal(trace[key][:t],prefix['trace'][key][:t])
                np.testing.assert_array_equal(trace['initial'],prefix['trace']['initial'])
                ct.require(branch['tail_state']['seed']==stream,'Tail seed identity')
                states=branch['tail_state']
                pair=(states['proposal'],states['gmm'])
                if draw in stream_hashes:ct.require(pair==stream_hashes[draw],'Common streams across candidates')
                stream_hashes[draw]=pair
                target=c.success_target(trace['flags'][t:,0],trace['flags'][t:,1],remaining=2*h-t)
                name='trace-%d-%d-%d.npz'%(t,candidate,draw)
                write_npz(out/name,**trace)
                ct.json_write(out/(name+'.calls.json'),branch['calls'])
                entry['labels'].append(dict(candidate=candidate,draw=draw,target=target,
                                            tail=states,trace_file=name))
                steps+=len(trace['actions'])
        ct.require(stream_hashes[0]!=stream_hashes[1],'Non-distinct actual tail generator states')
        banks.append(entry)
    backend.assert_frozen()
    return dict(reference=reference,horizon=h,banks=banks,primitive_steps=steps,
                wall_seconds=time.monotonic()-began,provenance=backend.provenance)


def validated_banks(run,role,source_sha,capsule_sha):
    """Authentication before any outcome interpretation; no closed-loop role."""
    ct.require(role in ('train','validation'),'No closed-loop outcome labels')
    jobs=[ct.task(role,i) for i in range(len(ct.allocation()[role])*2)]
    reports=[]
    # Validate EVERY job seal/identity before parsing numerical arrays/labels.
    for job in jobs:
        p=Path(run)/('%s-%d'%(role,job['index']))
        r=ct.check_report(p,role,job['index'],source_sha,capsule_sha)
        ct.require((r['reference'],r['horizon'])==(job['reference'],job['h']),'Job source/horizon')
        reports.append((p,r))
    for p,r in reports:
        ref,h=r['reference'],r['horizon']
        ct.require([b['anchor'] for b in r['banks']]==list(c.anchors(h)),'Anchor grid')
        prefix=read_npz(p/'prefix.npz')
        for b in r['banks']:
            t=b['anchor']
            if not b['available']:
                ct.require(len(prefix['actions'])<=t and prefix['flags'][-1].any(),'Unavailable anchor reason')
                continue
            bank=read_npz(p/('bank-%d.npz'%t))
            sampled=c.sample_bank(bank['immediate'],bank['continuation'],reference=ref,h=h,t=t)
            ct.require(b['coverage']==coverage(bank,sampled),'Sampling/coverage changed')
            ids=sampled['indices'];ys=np.empty((8,2),np.int64);seen=set()
            stream_hashes={}
            ct.require(len(b['labels'])==16,'Exact 8 x 2 labels')
            for row in b['labels']:
                i,j=row['candidate'],row['draw'];ct.require((i,j) not in seen and i in ids and j in (0,1),'Label grid')
                seen.add((i,j));trace=read_npz(ct.child(p,row['trace_file']))
                expected=c.success_target(trace['flags'][t:,0],trace['flags'][t:,1],remaining=2*h-t)
                ct.require(expected==row['target'] and row['tail']['seed']==ct.tail_seeds(ref,h,t)[j],'Label/RNG identity')
                for key in ('actions','states','dynamics','flags'):
                    np.testing.assert_array_equal(trace[key][:t],prefix[key][:t])
                np.testing.assert_array_equal(trace['initial'],prefix['initial'])
                pair=(row['tail']['proposal'],row['tail']['gmm'])
                if j in stream_hashes:ct.require(pair==stream_hashes[j],'Candidate-coupled streams')
                stream_hashes[j]=pair
                ys[ids.index(i),j]=expected['success']
            ct.require(stream_hashes[0]!=stream_hashes[1],'Actual paired stream distinction')
            yield ref,h,t,bank,ids,ys


def training_table(run,source_sha,capsule_sha):
    xs=[];ys=[];keys=[]
    for ref,h,t,bank,ids,y in validated_banks(run,'train',source_sha,capsule_sha):
        for k,i in enumerate(ids):
            for j in (0,1):
                xs.append(bank['x'][i]);ys.append(y[k,j]);keys.append((ref,h,t,i,j))
    return np.asarray(xs,np.float32),np.asarray(ys,np.float32),keys
