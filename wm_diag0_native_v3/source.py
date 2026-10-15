"""One predeclared source attempt; no outcomes or collection-policy selection."""
import json
import os
import sys
from pathlib import Path
import numpy as np
from .common import canonical, identity, write_new
from .world import NativeWorld, plain, rng_state
from wm_diag0.core import array_id

def save_array(path,a):
    a=np.asarray(a)
    if a.dtype.hasobject or not np.isfinite(a).all(): raise ValueError('numeric arrays only')
    with Path(path).open('xb') as f: np.save(f,a,allow_pickle=False)

def collect(row,output):
    output=Path(output); output.mkdir(exist_ok=False)
    for n in ('evidence','selector','training'): (output/n).mkdir()
    world=None; frames=[]; pixels=[]; actions=[]; coordinates=[]; labels=[]; audits=[]
    result={'root':row,'domain':'native','status':'FAILED','controller_actions':0,'available':False,
            'direct_snapshot_restoration_used':False,'research_models_loaded':0}
    try:
        world=NativeWorld(row); pix=world.reset(); get_action,policy=world.collector()
        result['origin']=world.configuration()
        initial_collector_rng=rng_state(policy.rng) if row['task']=='pusht' else rng_state(world.env.action_space.np_random)
        for i in range(45):
            audit=world.audit(); audits.append(audit)
            pixels.append(pix); coordinates.append(world.coordinates()); labels.append(world.labels())
            frames.append({'pixels':array_id(pix),'coordinates':array_id(coordinates[-1]),'audit':canonical(audit),
                           'success':bool(world.success),'terminated':bool(world.terminated),'truncated':bool(world.truncated)})
            if i==44 or world.stopped: break
            action=get_action()
            if not world.env.action_space.contains(action): raise ValueError('native collector action bounds/dtype')
            actions.append(action); pix=world.step(action)
        result.update(status='COLLECTED',available=len(actions)==44,controller_actions=len(actions),
                      reason='complete' if len(actions)==44 else 'unavailable_window_no_replacement',
                      collector={'class':type(policy).__module__+'.'+type(policy).__name__,'seed':row['seeds']['collector'],'initial_rng':initial_collector_rng})
        if row['task']=='pusht': result['collector']['final_rng']=rng_state(policy.rng)
        else: result['collector']['final_rng']=rng_state(world.env.action_space.np_random)
    except BaseException as exc: result['error']=repr(exc)
    finally:
        if world is not None: world.close()
        if pixels:
            for name,a in (('pixels',np.stack(pixels)),('coordinates',np.stack(coordinates)),('labels',np.stack(labels)),
                           ('actions',np.stack(actions) if actions else np.empty((0,2),dtype=np.float32))):
                save_array(output/'evidence'/(name+'.npy'),a)
            write_new(output/'evidence/audits.json',audits)
            if result['available']:
                save_array(output/'selector/history.npy',np.stack([pixels[20]]))
                save_array(output/'selector/goal.npy',pixels[44])
                if row['role']!='diagnostic':
                    idx=row['readout_frame_indices']
                    save_array(output/'training/pixels.npy',np.stack([pixels[i] for i in idx]))
                    save_array(output/'training/labels.npy',np.stack([labels[i] for i in idx]))
        result['frames']=frames
        write_new(output/'record.json',result)
        members={str(p.relative_to(output)):identity(p) for p in sorted(output.rglob('*')) if p.is_file()}
        if sum(r['bytes'] for r in members.values())>11_900_000: raise ValueError('12 MB source output bound')
        write_new(output/'MEMBERS.json',members)
        print(json.dumps({'root_id':row['root_id'],'status':result['status'],'available':result['available'],
                          'actions':len(actions),'members_sha256':identity(output/'MEMBERS.json')['sha256']}))
    return result['status']=='COLLECTED'

def main():
    contract=Path(sys.argv[1]); index=int(sys.argv[2]); out=Path(sys.argv[3])
    c=json.loads(contract.read_text()); plan=json.loads((contract.parent/'ROOT-PLAN.json').read_text())
    if identity(contract.parent/'ROOT-PLAN.json')['sha256']!=c['root_plan_sha256']: raise ValueError('frozen root plan')
    if not 0<=index<120: raise ValueError('one of 120 attempts')
    return 0 if collect(plan['roots'][index],out) else 1

if __name__=='__main__': sys.exit(main())
