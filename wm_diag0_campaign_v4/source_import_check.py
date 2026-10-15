"""Check only repaired native import closure, no research constructor calls."""
import json
from .common import DOC,SOURCE_RUN,write_new
from wm_diag0_native_v3.transport import ssh
from wm_diag0_preflight_v1.common import SIF,VENV

def main():
    test='CONTRACT='+repr(SOURCE_RUN+'/source/CONTRACT.json')+'\n'+'''
import json,torch
from pathlib import Path
from stable_worldmodel.envs.pusht.env import PushT
from stable_worldmodel.envs.dmcontrol.reacher import ReacherDMControlWrapper
from stable_worldmodel.envs.pusht.expert_policy import WeakPolicy
from stable_worldmodel.policy import RandomPolicy
from wm_diag0_native_v3.runtime import verify_imports
c=json.loads(Path(CONTRACT).read_text());files=verify_imports(c,Path(CONTRACT).parent)
if torch.cuda.is_initialized():raise RuntimeError('unexpected GPU initialization')
print(json.dumps({'status':'NATIVE_IMPORTS_AUTHENTICATED','runtime_files':len(files),'simulators':0,'resets':0,'models_loaded':0,'GPU_initialized':False}))
'''
    code='RUN='+repr(SOURCE_RUN)+'\nSIF='+repr(SIF)+'\nVENV='+repr(VENV)+'\nTEST='+repr(test)+'\n'+'''
import json,os,pathlib,subprocess
r=pathlib.Path(RUN);t=r/'import-check-tmp';t.mkdir(exist_ok=False)
env=dict(os.environ)
for k in list(env):
 if k.startswith(('APPTAINERENV_','SINGULARITYENV_')):del env[k]
for k,v in {'PYTHONPATH':str(r/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','LD_LIBRARY_PATH':'/renderer:/opt/conda/lib:/.singularity.d/libs','MUJOCO_GL':'osmesa','PYOPENGL_PLATFORM':'osmesa','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe','LP_NUM_THREADS':'4','OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','CUDA_VISIBLE_DEVICES':'','SDL_VIDEODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1','MPLCONFIGDIR':'/tmp/mpl','XDG_CACHE_HOME':'/tmp/cache','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}.items():env['APPTAINERENV_'+k]=v
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
cmd=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',str(r/'source')]
for bind in (str(r/'source')+':'+str(r/'source')+':ro',str(r/'controls')+':'+str(r/'controls')+':ro','/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/native-v3/renderer-r6:/renderer:ro',str(t)+':/tmp:rw',VENV+':'+VENV+':ro'):cmd+=['--bind',bind]
cmd+=[SIF,VENV+'/bin/python','-B','-c',TEST]
p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=35)
row={'returncode':p.returncode,'stdout':p.stdout[-12000:],'stderr':p.stderr[-16000:],'models_loaded':0,'simulators':0,'resets':0}
with (r/'controls/NATIVE-IMPORT-CHECK.json').open('x') as f:json.dump(row,f,sort_keys=True)
print(json.dumps(row))
'''
    r=ssh(code);write_new(DOC/'source-import-r1/NATIVE-IMPORT-CHECK-001.json',r);print(json.dumps(r,indent=2))

if __name__=='__main__':main()
