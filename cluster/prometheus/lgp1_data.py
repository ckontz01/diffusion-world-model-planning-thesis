"""Selected-data rules and authenticated, aligned shared cache construction."""
import csv,hashlib,heapq,json,time
from pathlib import Path
import numpy as np
import lgp1_contract as c

def select_rows(registry,excluded,quota):
    rows=[]
    for role in ('P1_train','P1_val'):
        episodes=[r for r in registry if r['p1_role']==role and int(r['episode_id']) not in excluded]
        for delta in range(15,151,15):
            def candidates():
                for ep in episodes:
                    e=int(ep['episode_id'])
                    for t in range(10,int(ep['episode_length'])-delta):
                        key=hashlib.sha256(f'lgp1|row|{role}|{delta}|{e}|{t}'.encode()).hexdigest()
                        yield key,e,t
            picked=heapq.nsmallest(quota[role],candidates())
            c.require(len(picked)==quota[role],'Insufficient eligible rows; no replacement')
            rows += [dict(role=role,episode=e,t=t,delta=delta) for _,e,t in picked]
    c.require(not {r['episode'] for r in rows if r['role']=='P1_train'} &
              {r['episode'] for r in rows if r['role']=='P1_val'},'Whole-source overlap')
    return rows

def aligned(reader,row):
    e,t,d=row['episode'],row['t'],row['delta']
    # Individual absolute rows avoid frameskip slicing ambiguities. All fifteen
    # actions and their source step IDs are checked before chronological packing.
    frames=reader(e,[t-10,t-5,t,t+d],['pixels','state','proprio'])
    actions=reader(e,list(range(t,t+15)),['action'])['action']
    state=np.asarray(frames['state'][2],np.float32)
    proprio=np.asarray(frames['proprio'][2],np.float32)
    c.require(state.shape==(7,) and np.array_equal(proprio,state[[0,1,5,6]]),'Recorded proprio/state mismatch')
    actions=np.asarray(actions,np.float32)
    c.require(actions.shape==(15,2) and np.isfinite(actions).all() and np.isfinite(state).all(),'Invalid data values')
    c.require((np.abs(actions)<=1).all(),'Recorded action support; no clipping/replacement')
    return frames['pixels'][:3],frames['pixels'][3:4],np.r_[state,proprio],actions.reshape(3,10)

def statistics(arrays,mask):
    c.require(mask.any(),'Empty fitting role')
    state=arrays['lowdim'][mask]; action=arrays['actions'][mask].reshape(-1,2)
    return {key+suffix:fn(x.astype(np.float64),axis=0).clip(1e-6,None).astype(np.float32)
            if suffix=='_std' else fn(x.astype(np.float64),axis=0).astype(np.float32)
            for key,x in [('lowdim',state),('action',action)]
            for suffix,fn in [('_mean',np.mean),('_std',np.std)]}

class LanceReader:
    def __init__(self,path,registry):
        import lance
        self.ds=lance.dataset(str(path))
        ids=self.ds.to_table(columns=['episode_idx','step_idx']).to_pydict()
        ep=np.asarray(ids['episode_idx']);step=np.asarray(ids['step_idx'])
        unique,starts,counts=np.unique(ep,return_index=True,return_counts=True)
        lookup={int(e):(int(s),int(n)) for e,s,n in zip(unique,starts,counts)}
        self.offset={};self.length={}
        for row in registry:
            e=int(row['episode_id']);start,n=lookup[e]
            c.require(n==int(row['episode_length']) and np.array_equal(step[start:start+n],np.arange(n)) and
                      (ep[start:start+n]==e).all(),'Lance episode chronology')
            self.offset[e]=start;self.length[e]=n
        self.allowed=set(self.offset)
    def __call__(self,e,steps,keys):
        c.require(e in self.allowed and all(0<=t<self.length[e] for t in steps),'Forbidden source slice')
        result=self.ds.take([self.offset[e]+t for t in steps],columns=['episode_idx','step_idx']+keys).to_pydict()
        c.require(result.pop('episode_idx')==[e]*len(steps) and result.pop('step_idx')==steps,'Row alignment')
        if 'pixels' in result:
            import torch
            from torchvision.io import decode_jpeg,ImageReadMode
            result['pixels']=np.stack([decode_jpeg(torch.frombuffer(bytearray(x),dtype=torch.uint8),
                                      mode=ImageReadMode.RGB).numpy() for x in result['pixels']])
        return {k:np.asarray(v) for k,v in result.items()}

def build_cache(source,out,backend,guard):
    lock=c.read(Path(source)/c.DOC/'INPUTS.json')
    # Verify accepted Lance tree bytes inside this charged allocation.
    for p in lock['lance_files']: c.require(c.sha(p)==lock['files'][p],'Lance transport bytes')
    with open(lock['registry']) as f: registry=list(csv.DictReader(f,delimiter='\t'))
    excluded=set(lock['excluded_episode_ids'])
    rows=select_rows(registry,excluded,{'P1_train':8000,'P1_val':800})
    c.write(out/'ROWS.json',rows)
    eligible=[r for r in registry if int(r['episode_id']) not in excluded]
    reader=LanceReader(lock['lance'],eligible)
    n=len(rows);shapes=dict(history=(n,3,192),local=(n,1,192),far=(n,1,192),lowdim=(n,11),actions=(n,3,10),remaining=(n,))
    arrays={k:np.lib.format.open_memmap(out/(k+'.npy'),mode='w+',dtype=np.float32,shape=shape) for k,shape in shapes.items()}
    began=time.monotonic()
    for i,row in enumerate(rows):
        guard()
        history,far,state,action=aligned(reader,row)
        hz,fz=backend.encode_frames(history),backend.encode_frames(far)
        goal=fz if row['delta']==15 else backend.generate(hz[None],fz[None],state[None],np.array([row['delta']]))[0]
        for key,value in dict(history=hz,far=fz,local=goal,lowdim=state,actions=action,remaining=row['delta']).items():
            c.require(np.isfinite(value).all() and np.shape(value)==shapes[key][1:],'Cache shape/finiteness')
            arrays[key][i]=value
        if i==255:
            elapsed=time.monotonic()-began
            c.require(elapsed+1.5*elapsed/256*(n-256)<13500,'Measured cache throughput cannot fit allocation')
    for x in arrays.values(): x.flush()
    stats=statistics(arrays,np.array([r['role']=='P1_train' for r in rows]))
    np.savez(out/'normalization.npz',**stats)
    return dict(rows=n,train_rows=80000,val_rows=8000,distinct={role:dict(
        episodes=len({r['episode'] for r in rows if r['role']==role}),
        windows=len({(r['episode'],r['t']) for r in rows if r['role']==role}))
        for role in ('P1_train','P1_val')},alignment='t-10,t-5,t;far=t+delta;actions=[t,t+15)',
        normalization='fitting rows only; frozen generator statistics remain separate')

def load_cache(cache):
    c.verify(cache)
    arrays={k:np.load(Path(cache)/(k+'.npy'),mmap_mode='r',allow_pickle=False)
            for k in ('history','local','far','lowdim','actions','remaining')}
    with np.load(Path(cache)/'normalization.npz',allow_pickle=False) as z: stats={k:z[k].copy() for k in z.files}
    rows=c.read(Path(cache)/'ROWS.json')
    return arrays,stats,rows
