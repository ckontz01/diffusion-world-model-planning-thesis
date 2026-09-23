"""Contract fixtures only. No simulator import, no efficacy scenarios/search."""
import common as c
import contextlib
import types
import numpy as np
from bridge import NativeEpisode


def bf16(x):
    a=np.array(x,np.float32,copy=True); bits=a.view(np.uint32)
    bits[:]=(bits+np.uint32(0x7fff)+((bits>>16)&1))&np.uint32(0xffff0000)
    return a


class Tensor:
    def __init__(self,a,dtype=None):self.a=np.asarray(a);self.dtype=dtype or self.a.dtype
    @property
    def shape(self):return self.a.shape
    def __getitem__(self,k):return Tensor(self.a[k],self.dtype)
    def float(self):return Tensor(self.a.astype(np.float32))
    def max(self):return self.a.max()
    def reshape(self,*shape):return Tensor(self.a.reshape(*shape),self.dtype)
    def permute(self,*axes):return Tensor(self.a.transpose(*axes),self.dtype)
    def expand(self,*shape):return Tensor(np.broadcast_to(self.a,shape),self.dtype)
    def detach(self):return self
    def cpu(self):return self
    def numpy(self):return self.a
    def to(self,dtype):return Tensor(bf16(self.a) if dtype=='bfloat16' else self.a.astype(dtype),dtype)
    def __sub__(self,x):return Tensor(self.a-(x.a if isinstance(x,Tensor) else x))
    def __truediv__(self,x):return Tensor(self.a/(x.a if isinstance(x,Tensor) else x))


class FakeTorch:
    bfloat16='bfloat16'
    no_grad=staticmethod(contextlib.nullcontext)
    @staticmethod
    def as_tensor(x,device=None,dtype=None):
        c.require(device=='artificial-cpu','Mock must not allocate real GPU')
        return Tensor(x).to(dtype) if dtype else Tensor(x)
    @staticmethod
    def interpolate(x,*,size,mode,align_corners):
        c.require(x.shape==(1,3,224,224) and size==(224,224) and mode=='bilinear' and align_corners is False,'Exact image interface')
        return x
    nn=types.SimpleNamespace(functional=types.SimpleNamespace())
FakeTorch.nn.functional.interpolate=FakeTorch.interpolate


class FakeLeWM:
    def encode(self,info):
        c.require(info['pixels'].shape==(1,1,3,224,224) and info['pixels'].dtype=='bfloat16','BF16 pixels')
        value=float(info['pixels'].a.mean())
        return {'emb':Tensor(bf16((np.arange(192,dtype=np.float32)*.001+value)[None,None]),'bfloat16')}
    def rollout(self,info,actions):
        c.require(actions.dtype=='bfloat16' and actions.shape[0]==1 and actions.shape[2:]==(3,10),'BF16 action/time interface')
        n=actions.shape[1];c.require(info['pixels'].shape==(1,n,1,3,224,224),'One observed frame')
        z=[info['emb'].a[0,:,0].copy()]
        for t in range(3):z.append(bf16(z[-1]+actions.a[0,:,t].mean(-1)[:,None]*.001))
        return {'predicted_emb':Tensor(np.stack(z,1)[None],'bfloat16')}


class VectorWorld:
    """Artificial implementation of inspected World interface, not physics."""
    def __init__(self,success_at=None,t0_at_goal=False):
        self.success_at=success_at;self.t0=t0_at_goal;self.num_envs=1;self.clock=0;self.closed=False
        self.native=types.SimpleNamespace()
        for name in ('agent','block'):
            setattr(self.native,name,types.SimpleNamespace(position=[0.,0.],velocity=[0.,0.],angle=0.,angular_velocity=0.,force=[0.,0.],torque=0.))
        self.native.space=types.SimpleNamespace(damping=1.)
        for key,value in dict(dt=.01,control_hz=10.,k_p=100.,k_v=20.,action_scale=100.,n_contact_points=0.).items():setattr(self.native,key,value)
        self.native._get_obs=lambda:self.state.copy()
        self.envs=types.SimpleNamespace(envs=[types.SimpleNamespace(unwrapped=self.native)],step=self.step)

    def reset(self,record,seed):
        self.record=record;self.state=np.asarray(record['state']).copy();self.native.goal_state=np.asarray(record['goal_state']).copy()
        self.info(None)
    def info(self,action):
        self.native.agent.position=self.state[:2].tolist();self.native.agent.velocity=self.state[5:7].tolist()
        self.native.block.position=self.state[2:4].tolist();self.native.block.angle=float(self.state[4])
        image=np.full((224,224,3),(self.clock%230)+10,np.uint8)
        goal=np.full((224,224,3),245,np.uint8)
        self.infos={'state':self.state[None,None].copy(),'proprio':self.state[[0,1,5,6]][None,None].copy(),
                    'pixels':image[None,None],'goal':goal[None,None],'step_idx':np.array([[self.clock]]),
                    'action':np.zeros((1,1,2),np.float32) if action is None else action[None,None].copy()}
    def step(self,a):
        c.require(not self.closed and self.clock<150,'Fresh artificial lifecycle')
        self.clock+=1
        self.state[:2]+=a[0].astype(np.float64)*.01
        if self.t0 and self.clock==1:self.state[:4]=100.
        if self.clock==self.success_at:self.state=self.native.goal_state.copy()
        self.info(a[0]);success=(np.linalg.norm(self.state[:4]-self.native.goal_state[:4])<20)
        return {},0,np.array([success]),np.array([False]),self.infos
    def close(self):self.closed=True


def factory(backend,success_at=None,t0=False,owned=None):
    initial=np.zeros(7);goal=np.array([100.,100.,100.,100.,0,0,0])
    if t0:goal=initial.copy()
    def make():
        world=VectorWorld(success_at,t0)
        if owned is not None:owned.append(world)
        return NativeEpisode(world,backend,{'state':initial.copy(),'goal_state':goal.copy()},94031,
                             lambda w,records,seed:w.reset(records[0],seed))
    return make


def d192_fixture(role,ids):
    """Worst-case four-prefix/four-suffix batch. Random arrays, not efficacy data."""
    rng=np.random.default_rng(194011 if role=='fit' else 194012);n=len(ids)*4
    return {'x':rng.normal(size=(n,996)),'a':rng.normal(size=(n,4,212)),
            'r':rng.normal(size=(n,192)),'y':rng.integers(0,2,size=(n,4)).astype(float),
            'mask':np.ones((n,4),bool),'terminal':np.full(n,2),
            'source_ids':np.repeat(np.array(list(map(str,ids))),4),'roles':np.full(n,role)}
