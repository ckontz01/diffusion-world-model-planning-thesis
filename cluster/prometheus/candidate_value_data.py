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


def checked_decoded_bank(bank):
    """Recompute delivery-space actions from pinned decoder coefficients."""
    from verify_diffusion_branch import independent_decode
    pins=ct.json_read(Path(__file__).with_name('INDEPENDENT-PINNED-INPUTS.json'))['action_decoder']
    planner=bank['planner_actions'];saved=bank['decoded_actions']
    ct.require(planner.shape==saved.shape==(64,15,2) and planner.dtype==saved.dtype==np.float32
               and np.isfinite(planner).all() and np.isfinite(saved).all(),'Saved bank action shape/dtype')
    decoded=independent_decode(planner.reshape(-1,2),pins['scale'],pins['mean']).reshape(64,15,2)
    np.testing.assert_array_equal(saved,decoded)
    ct.require((np.abs(decoded)<=1).all(),'Decoded bank action bounds; no clipping')
    return decoded


def validate_saved_trajectory(trace,record,h,*,anchor=0,target=None):
    """Independent saved-state check, not a flag-only target reduction.

    The authenticated selected record supplies the goal. Historical physical()
    reconstructs EACH post-action success with the combined four-coordinate
    norm <20 and circular angle <pi/9, then compares every saved success flag.
    No threshold normalization/tolerance change or repair of stored values.
    """
    from single_anchor_ranking import physical,ATOL
    actions=trace['actions'];states=trace['states'];flags=trace['flags'];n=len(states)
    ct.require(h in (75,150) and 0<=anchor<2*h and anchor%15==0,'Saved episode coordinate')
    ct.require(actions.shape==(n,2) and actions.dtype==np.float32 and np.isfinite(actions).all()
               and (np.abs(actions)<=1).all(),'Saved action count/dtype/bounds')
    ct.require(trace['dynamics'].shape==(n,10) and np.isfinite(trace['dynamics']).all(),'Saved dynamics count')
    np.testing.assert_allclose(trace['initial'],record['state'],rtol=0,atol=ATOL)
    physical(states,flags,record['goal_state'],2*h)
    # The unchanged World has a native 300-step limit; H75 can stop at its
    # 150-step budget without a native truncated flag. An early truncation is
    # not a legitimate shortcut for an incomplete trajectory.
    ct.require(not flags[:,1].any() or n==300,'Unexpected early native truncation')
    ct.require(n>anchor and not flags[:anchor].any(),'Unavailable saved intervention')
    distance=np.sqrt(np.sum((states[anchor:,:4]-record['goal_state'][:4])**2,axis=1))
    angle=np.abs(states[anchor:,4]-record['goal_state'][4]);angle=np.minimum(angle,2*np.pi-angle)
    reconstructed=(distance<20)&(angle<np.pi/9)
    expected=c.success_target(reconstructed,flags[anchor:,1],remaining=2*h-anchor)
    if target is not None:ct.require(target==expected,'Saved target differs from physical reconstruction')
    return expected


def validate_candidate_delivery(trace,decoded,anchor,candidate):
    ct.require(isinstance(candidate,(int,np.integer)) and 0<=candidate<64,'Saved candidate index')
    n=min(15,len(trace['actions'])-anchor)
    ct.require(n>0,'No delivered candidate action')
    if n<15:ct.require(trace['flags'][-1].any(),'Short chunk without legitimate terminal flag')
    np.testing.assert_array_equal(trace['actions'][anchor:anchor+n],decoded[candidate,:n])


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
    validate_saved_trajectory(read_npz(out/'prefix.npz'),record,h)
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
        decoded=checked_decoded_bank(read_npz(out/('bank-%d.npz'%t)))
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
                saved=read_npz(out/name)
                validate_saved_trajectory(saved,record,h,anchor=t,target=target)
                validate_candidate_delivery(saved,decoded,t,candidate)
                ct.json_write(out/(name+'.calls.json'),branch['calls'])
                entry['labels'].append(dict(candidate=candidate,draw=draw,target=target,
                                            tail=states,trace_file=name))
                steps+=len(trace['actions'])
        ct.require(stream_hashes[0]!=stream_hashes[1],'Non-distinct actual tail generator states')
        banks.append(entry)
    backend.assert_frozen()
    return dict(reference=reference,horizon=h,banks=banks,primitive_steps=steps,
                independent_saved_artifact_checks=True,
                wall_seconds=time.monotonic()-began,provenance=backend.provenance)


def validated_banks(run,role,source_sha,capsule_sha,capsule):
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
        record,_=load_record(capsule,ref,h,role)
        ct.require([b['anchor'] for b in r['banks']]==list(c.anchors(h)),'Anchor grid')
        prefix=read_npz(p/'prefix.npz')
        validate_saved_trajectory(prefix,record,h)
        steps=len(prefix['actions'])
        for b in r['banks']:
            t=b['anchor']
            if not b['available']:
                ct.require(len(prefix['actions'])<=t and prefix['flags'][-1].any(),'Unavailable anchor reason')
                continue
            bank=read_npz(p/('bank-%d.npz'%t))
            decoded=checked_decoded_bank(bank)
            sampled=c.sample_bank(bank['immediate'],bank['continuation'],reference=ref,h=h,t=t)
            ct.require(b['coverage']==coverage(bank,sampled),'Sampling/coverage changed')
            ids=sampled['indices'];ys=np.empty((8,2),np.int64);seen=set()
            stream_hashes={}
            ct.require(len(b['labels'])==16,'Exact 8 x 2 labels')
            for row in b['labels']:
                i,j=row['candidate'],row['draw'];ct.require((i,j) not in seen and i in ids and j in (0,1),'Label grid')
                seen.add((i,j));trace=read_npz(ct.child(p,row['trace_file']))
                expected=validate_saved_trajectory(trace,record,h,anchor=t,target=row['target'])
                validate_candidate_delivery(trace,decoded,t,i)
                steps+=len(trace['actions'])
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
        ct.require(steps==r['primitive_steps'],'Saved aggregate action count')


def training_table(run,source_sha,capsule_sha,capsule):
    xs=[];ys=[];keys=[]
    for ref,h,t,bank,ids,y in validated_banks(run,'train',source_sha,capsule_sha,capsule):
        for k,i in enumerate(ids):
            for j in (0,1):
                xs.append(bank['x'][i]);ys.append(y[k,j]);keys.append((ref,h,t,i,j))
    return np.asarray(xs,np.float32),np.asarray(ys,np.float32),keys
