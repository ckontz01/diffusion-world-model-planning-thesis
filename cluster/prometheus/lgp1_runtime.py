"""Shared frozen backend plus fresh-state policy binding, no legacy evaluator."""
from collections import deque
from pathlib import Path
import sys,time
import numpy as np
import torch
from local_goal_proposals import lowdim_from_state,stage_clock,stream_seed
from local_goal_models import sample
from lgp1_tensor import affine,project,cem
import lgp1_contract as c

class FrozenBackend:
    def __init__(self,lock):
        for key in ('lewm','generator'):
            c.require(c.sha(lock[key])==lock['files'][lock[key]],'Frozen checkpoint identity: '+key)
        import stable_worldmodel  # Preserve installed simulator before SAGE import.
        from independent_pusht_runtime import official_lewm_pickle_aliases
        official_type,_=official_lewm_pickle_aliases()
        sys.path.append(lock['sage'])
        from sage.runtime.lewm import load_lewm,image_batch_to_lewm
        from sage.models.subgoal import load_subgoal_prior
        self.image_transform=image_batch_to_lewm;self.device=torch.device('cuda')
        self.lewm=load_lewm(lock['lewm'],self.device,bf16=True)
        c.require(type(self.lewm) is official_type,'Pinned official LeWM runtime type')
        self.generator,self.generator_stats,_=load_subgoal_prior(lock['generator'],self.device)
        c.require(self.generator_stats['lowdim_keys']==['state','proprio'],'Generator lowdim ordering')
        self.generator.eval().requires_grad_(False)
        self.mean=np.array(lock['decoder']['mean'],np.float64);self.std=np.array(lock['decoder']['scale'],np.float64)
    def pixels(self,frames):
        x=torch.as_tensor(np.asarray(frames),device=self.device)
        if x.shape[-1]==3: x=x.permute(0,3,1,2)
        c.require(x.ndim==4 and x.shape[1]==3,'Frame shape')
        return self.image_transform(x[None],224).to(torch.bfloat16)
    @torch.no_grad()
    def encode_frames(self,frames):
        return self.lewm.encode({'pixels':self.pixels(frames)})['emb'][0].float().cpu().numpy()
    @torch.no_grad()
    def generate(self,history,far,raw_state,remaining):
        tt=lambda x:torch.as_tensor(x,device=self.device,dtype=torch.float32)
        gs=self.generator_stats
        state=(tt(raw_state)-gs['lowdim_mean'].float())/gs['lowdim_std'].float()
        return self.generator(tt(history),tt(far),state,tt(remaining),torch.full_like(tt(remaining),15))['prediction'].float().cpu().numpy()
    @torch.no_grad()
    def cost_function(self,current_pixels,local):
        pixels=self.pixels(current_pixels[-1:])
        embedding=self.lewm.encode({'pixels':pixels})['emb'].detach()
        goal=torch.as_tensor(local,device=self.device,dtype=torch.bfloat16)
        def cost(bank):
            b,k=bank.shape[:2]
            info={'pixels':pixels[:,None].expand(b,k,*pixels.shape[1:]),
                  'goal':pixels[:,None].expand(b,k,*pixels.shape[1:]),
                  'emb':embedding[:,None].expand(b,k,*embedding.shape[1:]),
                  'goal_emb':goal[:,None],
                  'action':torch.zeros((b,k,1,10),device=self.device,dtype=torch.bfloat16)}
            return self.lewm.get_cost(info,bank.to(torch.bfloat16)).float()
        return cost

class Policy:
    def __init__(self,backend,model,stats,horizon,seed,reference,guard=lambda:None):
        self.backend=backend;self.model=model;self.stats=stats;self.horizon=horizon
        self.seed=seed;self.reference=reference;self.guard=guard
        self.planner=self;self.diagnostic_history=[];self._stage_index=0;self._action_buffer=deque()
        self.history=deque(maxlen=3);self.elapsed=0;self.terminal=False;self.env=None
    def set_env(self,env):
        if self.env is not None: raise RuntimeError('Policy already owned by an episode')
        self.env=env
    def finish(self): self.terminal=True;self._action_buffer.clear();self.history.clear()
    @torch.no_grad()
    def get_action(self,info):
        if self.terminal or self.elapsed>=2*self.horizon: raise RuntimeError('Post-terminal planning')
        self.guard()
        frame=np.asarray(info['pixels'])[0,-1].copy()
        if self.elapsed%5==0: self.history.append(frame)
        if not self._action_buffer:
            started=time.monotonic();remaining,physical=stage_clock(self.horizon,self.elapsed)
            frames=list(self.history);frames=[frames[0]]*(3-len(frames))+frames
            history=self.backend.encode_frames(np.stack(frames))[None]
            far=self.backend.encode_frames(np.asarray(info['goal'])[0,-1:])[None]
            encoding_seconds=time.monotonic()-started
            raw=lowdim_from_state(np.asarray(info['state'])[0,-1:])
            local=(far.copy() if remaining==15 else self.backend.generate(history,far,raw,np.array([remaining])))
            context_seconds=time.monotonic()-started
            device=next(self.model.parameters()).device
            tt=lambda x:torch.as_tensor(x,device=device,dtype=torch.float32)
            normalized=(raw-self.stats['lowdim_mean'])/self.stats['lowdim_std']
            inputs=tuple(tt(x) for x in (history,local,far,normalized,np.array([remaining])))
            proposal=torch.Generator(device=device).manual_seed(stream_seed((self.reference,self.horizon),self._stage_index,'proposal',self.seed))
            refinement=torch.Generator(device=device).manual_seed(stream_seed((self.reference,self.horizon),self._stage_index,'refinement',self.seed))
            if device.type=='cuda':torch.cuda.synchronize(device)
            proposal_start=time.monotonic()
            bank=sample(self.model,inputs,300,proposal)
            if device.type=='cuda':torch.cuda.synchronize(device)
            proposal_seconds=time.monotonic()-proposal_start
            bank=affine(bank,self.stats['action_mean'],self.stats['action_std'],self.backend.mean,self.backend.std)
            cost=self.backend.cost_function(np.stack(frames),local);cost_seconds=[0.]
            def measured_cost(x):
                if device.type=='cuda':torch.cuda.synchronize(device)
                tic=time.monotonic();value=cost(x)
                if device.type=='cuda':torch.cuda.synchronize(device)
                cost_seconds[0]+=time.monotonic()-tic
                return value
            refine_start=time.monotonic()
            actions,logs=cem(bank,measured_cost,generator=refinement,
                            project_fn=lambda x:project(x,self.backend.mean,self.backend.std))
            raw_actions=affine(actions,self.backend.mean,self.backend.std,[0,0],[1,1]).cpu().numpy().reshape(15,2)
            c.require(np.isfinite(raw_actions).all() and (abs(raw_actions)<=1).all(),'Invalid decoded action')
            self._action_buffer.extend(a[None].copy() for a in raw_actions)
            self.diagnostic_history.append(dict(stage=self._stage_index,elapsed=self.elapsed,remaining=remaining,
                physical_remaining=physical,final_goal=remaining==15,rounds=logs,
                seconds=time.monotonic()-started,
                context_seconds=context_seconds,proposal_seconds=proposal_seconds,
                encoding_seconds=encoding_seconds,generator_seconds=context_seconds-encoding_seconds,
                scoring_seconds=cost_seconds[0],refinement_total_seconds=time.monotonic()-refine_start,
                cost_calls=30,candidate_trajectories=9000,predicted_primitive_steps=135000,
                context_sha256=__import__('hashlib').sha256(b''.join(x.tobytes() for x in (history,local,far,raw))).hexdigest()))
            self._stage_index+=1
        self.elapsed+=1
        return self._action_buffer.popleft()
