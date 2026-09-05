"""Bounded fixed-exposed-input resource calibration; no episode evaluation."""
import argparse
from copy import deepcopy
import gc
import json
from pathlib import Path
import time
import numpy as np
import torch
from gdp_cem_e19_r3_arms import setup,E18_ARMS
from gdp_cem_e19_r3_validation import inputs
from check_e18_fresh_integration import module_hash
from pusht_fresh_initialization import register,reset_world
from e18_fresh_driver import computational_info
from gdp_cem_e18_closed_loop import E18Planner


@torch.inference_mode()
def run():
    import stable_worldmodel as swm
    case=inputs('e18')[0]  # exposed 8908/53; no prospective dataset reads
    output=[]
    for arm in E18_ARMS:
        started=time.perf_counter();make,template,modules,pins=setup('e18',arm)
        load_seconds=time.perf_counter()-started
        before=module_hash(modules);policy=make()
        world=swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,
                        correct_velocity_space=True)
        try:
            reset_world(world,[case['record']],seed=932)
            raw=computational_info(world.infos)
            for delta in (15,30,75,150):
                rows=[]
                for repeat in range(4):  # one warmup, three measured; all reported
                    solver=E18Planner(template.world_model,arm=arm,statistics=template.statistics,
                        state_dim=7,primitive_action_dim=2,proposer=template.proposer,
                        state_adapter=template.state_adapter,batch_size=1,proposal_seed=932+repeat)
                    solver.configure(action_space=world.envs.action_space,n_envs=1)
                    torch.cuda.synchronize();start=time.perf_counter()
                    prepared=policy._prepare_info(deepcopy(raw))
                    prepared={k:v.to(solver.device) if torch.is_tensor(v) else v for k,v in prepared.items()}
                    solver.solve(prepared,raw_state=torch.as_tensor(raw['state'][:,-1]).float(),
                                 delta_value=delta,tau_value=15)
                    torch.cuda.synchronize();elapsed=time.perf_counter()-start
                    d=solver.diagnostic_history[-1]
                    rows.append(dict(warmup=repeat==0,wall_seconds=elapsed,
                        timing={k:v for k,v in d.items() if k.endswith('_seconds')},
                        peak_allocated_bytes=torch.cuda.max_memory_allocated()))
                    del solver
                output.append(dict(arm=arm,delta=delta,tau=15,load_seconds=load_seconds,rows=rows,
                    checkpoint_pins=pins['checkpoints']))
            assert module_hash(modules)==before
        finally:world.close()
        del modules,template,policy,make;gc.collect();torch.cuda.empty_cache()
    return dict(kind='resource_calibration_not_efficacy',training_seed=7201,
        device=torch.cuda.get_device_name(),batch_size=1,exposed_record='8908/53 stored R1 endpoint',
        episode_executed=False,prospective_record_read=False,protected_data_read=False,
        model_tensors_unchanged=True,rows=output)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists();a.out.write_text(json.dumps(run(),indent=2,sort_keys=True)+'\n')
