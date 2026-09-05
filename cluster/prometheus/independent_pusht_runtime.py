"""Frozen E18 and released SAGE constructors in one pinned simulator runtime."""
import hashlib,json,os,random,sys
from copy import deepcopy
from pathlib import Path
import numpy as np
import torch
import stable_worldmodel as swm

ROOT=Path('/lustreFS/data/superworld/ckontzias/thesis')
SAGE=ROOT/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage'
CHECKPOINTS=ROOT/'experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988/checkpoints'
TRAIN=ROOT/'experiments/gdp-cem-e15/development-run-20260825-ebd6109b/training'
ADAPTER=ROOT/'experiments/gdp-cem-e17/development-run-20260827-9fb5a8c2/models/pusht'
LEWM=ROOT/'data/stablewm/pusht/lewm_hf_22b330c_object.ckpt'
ARMS=('vad_continuation','vad_greedy_300','diagonal_gaussian_continuation',
      'vad_greedy_576','direct_gmm_continuation','sage')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def deterministic(seed):
    os.environ['PUSHT_CPU_MULTINOMIAL']='1'
    random.seed(seed);np.random.seed(seed % 2**32);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)

def tensor_hash(modules):
    h=hashlib.sha256()
    for model in modules:
        for key,t in sorted(model.state_dict().items()):
            h.update(key.encode());h.update(str((tuple(t.shape),t.dtype)).encode())
            h.update(t.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()

class Decoder:
    def __init__(self,mean,scale): self.mean_=np.asarray(mean,np.float64);self.scale_=np.asarray(scale,np.float64)
    def inverse_transform(self,x):
        # sklearn StandardScaler in-place dtype semantics, including float32 roundoff.
        x=x.copy();x*=self.scale_;x+=self.mean_;return x
    def transform(self,x):
        x=x.copy();x-=self.mean_;x/=self.scale_;return x

def build(arm,train_seed):
    if arm not in ARMS or train_seed not in (7201,7202,7203):raise ValueError('unknown registered arm/seed')
    deterministic(32)
    device=torch.device('cuda')
    pins=json.loads(Path(__file__).with_name('INDEPENDENT-PINNED-INPUTS.json').read_text())
    assert sha(LEWM)==pins['lewm_sha256']
    if arm=='sage':
        # Add only after the shared installed simulator has been imported.
        sys.path.append(str(SAGE))
        from sage.eval import pusht as p
        release=json.loads((SAGE/'configs/checkpoints.json').read_text())
        def path(name):
            q=CHECKPOINTS/release[name]['filename'];assert sha(q)==release[name]['sha256'];return q
        generator,gs,_=p.load_subgoal_prior(path('pusht_generator'),device)
        prior,ps,_=p.load_action_prior(path('pusht_action_prior'),device)
        lewm=p.load_lewm(LEWM,device=device,bf16=True)
        decoder=p.ArrayNormalizer(ps['action_mean'].cpu().numpy(),ps['action_std'].cpu().numpy())
        def factory(horizon,seed):
            # New cost wrapper owns subgoal cache; shared frozen networks are not modified.
            model=p.SAGECostModel(lewm,generator,gs,prior,ps,goal_offset_steps=horizon,action_block=5,image_size=224).to(device).eval().requires_grad_(False)
            solver=p.PriorInitializedCEM(model,candidates=300,rounds=30,elites=30,seed=seed,device=device)
            policy=p.ScheduledPolicy(solver=solver,config=swm.PlanConfig(horizon=3,receding_horizon=3,action_block=5,warm_start=False),
                process={'action':decoder},transform={'pixels':p.image_transform(224,torch.bfloat16),'goal':p.image_transform(224,torch.bfloat16)},
                schedule_steps=[15]*(horizon//15),goal_offset_steps=horizon,history_length=3,frameskip=5)
            return policy
        modules=[lewm,generator,prior]
        provenance={'sage_commit':'8219029fd52e89157e05aebb998ab26f0ef46966',
          'checkpoints':{k:release[k] for k in ('pusht_generator','pusht_action_prior')},
          'runtime':'E18 swm006 common physical environment; released SAGE model, CEM and schedule code',
          'precision':'released SAGE BF16 LeWM, FP32 learned subgoal/action networks',
          'seed_block':'released one trained model; three evaluation seed blocks, not three SAGE training seeds',
          'post_horizon_schedule':'released SAGE remains at final local duration with remaining=max(H-elapsed,15), unlike unchanged E18 cycle restart'}
    else:
        from gdp_cem_e18_runtime import load_e15_proposer,E18ScheduledPolicy
        from gdp_cem_e18_inputs import load_e17_adapter
        from gdp_cem_e18_closed_loop import E18Planner
        from evaluate_gdp_cem_e18 import image_transform
        import gdp_cem_e18_specs as s
        model=swm.policy.AutoCostModel('pusht/lewm_hf_22b330c',cache_dir=ROOT/'data/stablewm').to(device).eval().requires_grad_(False)
        if hasattr(model,'interpolate_pos_encoding'):model.interpolate_pos_encoding=True
        family=s.family_for_arm(arm)
        selected=next(r for r in pins['checkpoints'] if r['family']==family and r['training_seed']==train_seed)
        assert sha(selected['path'])==selected['sha256']
        proposer,stats,pr=load_e15_proposer(TRAIN,task='pusht',condition=family,seed=train_seed,device=device)
        adapter=None
        if s.is_continuation_arm(arm):adapter,ar=load_e17_adapter(ADAPTER,task='pusht',device=device)
        decoder=Decoder(pins['action_decoder']['mean'],pins['action_decoder']['scale'])
        np.testing.assert_array_equal(decoder.mean_.astype(np.float32),stats.planner_action_mean.numpy())
        np.testing.assert_array_equal(decoder.scale_.astype(np.float32),stats.planner_action_std.numpy())
        def factory(horizon,seed):
            solver=E18Planner(model,arm=arm,statistics=stats,state_dim=7,primitive_action_dim=2,
              proposer=proposer,state_adapter=adapter,batch_size=1,proposal_seed=seed)
            return E18ScheduledPolicy(solver,schedule=s.schedule_for(horizon),environment_budget=2*horizon,
              state_key='state',process={'action':decoder},transform={'pixels':image_transform(224),'goal':image_transform(224)})
        modules=[model,proposer]+([adapter] if adapter is not None else [])
        provenance={'proposer':selected,'adapter_sha256':pins['adapter_sha256'] if adapter else None,
                    'precision':'unchanged E18 model precision','checkpoint_statistics':pins['statistics'],
                    'decoder':pins['action_decoder']}
    provenance.update(arm=arm,train_seed_block=train_seed,lewm_sha256=sha(LEWM),
       parameter_counts=[sum(p.numel() for p in m.parameters()) for m in modules])
    return factory,modules,provenance
