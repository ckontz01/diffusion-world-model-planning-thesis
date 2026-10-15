"""Bind compiled native integrator multiplicities from accepted origin metadata."""
import json
from .common import DOC,write_new
from wm_diag0_source_r3.common import RUN,OLD
from wm_diag0_native_v3.transport import ssh

def main():
    code='RUN='+repr(RUN)+'\nOLD='+repr(OLD)+'\n'+'''
import hashlib,json,pathlib
r=pathlib.Path(RUN);old=pathlib.Path(OLD);accepted=json.loads((r/'controls/ALL-SOURCES-ACCEPTED.json').read_text());compiled={};values=set()
for i in range(60):
 key='reacher-'+str(i).zfill(3);out=r/'tasks'/key/'output';seal=accepted['source_seals'][key]
 if hashlib.sha256((out/'MEMBERS.json').read_bytes()).hexdigest()!=seal['sha256']:raise ValueError('accepted source origin seal')
 meta=json.loads((out/'record.json').read_text());o=meta['origin'];n=o['n_sub_steps']
 if type(n) is not int or n<=0 or o['action_repeat']!=2 or abs(o['physics_timestep']*n-o['dm_control_timestep'])>1e-12:raise ValueError('native compiled step multiplicity')
 values.add(n);compiled[key]={'n_sub_steps':n,'physics_timestep':o['physics_timestep'],'dm_control_timestep':o['dm_control_timestep'],'legacy_step':o['legacy_step'],'compiled_assets':o['compiled_assets']}
if len(values)!=1:raise ValueError('unanticipated varying compiled physics; no guess')
n=next(iter(values))
result={'status':'NATIVE_INTEGRATOR_MULTIPLICITIES_BOUND','reacher_dm_steps_max':386968,'reacher_mujoco_integrator_steps_max':386968*n,'n_sub_steps':n,
 'PushT_controller_steps_max':193440,'PushT_integrator_steps_per_controller_action':10,'PushT_reset_internal_integrator_steps_max':6400,
 'PushT_integrator_steps_including_reset_max':1940800,'origins':compiled,'scientific_results_read':False,'source_acceptance_sha256':hashlib.sha256((r/'controls/ALL-SOURCES-ACCEPTED.json').read_bytes()).hexdigest()}
with (r/'controls/COMPILED-PHYSICS-BOUND.json').open('x') as f:json.dump(result,f,sort_keys=True)
print(json.dumps(result))
'''
    r=ssh(code);write_new(DOC/'COMPILED-PHYSICS-BOUND-001.json',r)
    print(json.dumps({k:v for k,v in r.items() if k!='origins'}))

if __name__=='__main__':main()
