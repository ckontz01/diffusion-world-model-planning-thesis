"""All campaign class imports; zero checkpoint loads/forwards/physics/GPU."""
import json
from .common import DOC,RUN,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    test='RUN='+repr(RUN)+'\n'+'''
import json,sys,torch
from pathlib import Path
c=json.loads((Path(RUN)/'source/CONTRACT.json').read_text())
sys.path[:0]=[c['prior_source']+'/lewm',c['dino_source'],c['prior_source']+'/encoder']
from models.visual_world_model import VWorldModel
from models.vit import ViTPredictor,Attention
from models.proprio import ProprioceptiveEmbedding
from dinov2.models.vision_transformer import vit_small
from stable_worldmodel.solver.cem import CEMSolver
from stable_worldmodel.policy import PlanConfig
from stable_worldmodel.envs.pusht.env import PushT
from stable_worldmodel.envs.dmcontrol.reacher import ReacherDMControlWrapper
from wm_diag0_campaign_v4 import models,diagnostic,readout,accept,accept_readout,analysis,worker,validate_task
from wm_diag0_native_v3.runtime import verify_imports
checked=verify_imports(c,Path(RUN)/'source')
if torch.cuda.is_initialized():raise RuntimeError('unexpected CUDA initialization')
print(json.dumps({'status':'ALL_CAMPAIGN_IMPORTS_AUTHENTICATED','runtime_files':len(checked),'checkpoint_loads':0,'model_forwards':0,'simulators':0,'GPU_initialized':False}))
'''
    code='RUN='+repr(RUN)+'\nTEST='+repr(test)+'\n'+'''
import json,os,pathlib,subprocess
r=pathlib.Path(RUN);c=json.loads((r/'source/CONTRACT.json').read_text());t=r/'import-check-tmp';t.mkdir(exist_ok=False)
env=dict(os.environ)
for k in list(env):
 if k.startswith(('APPTAINERENV_','SINGULARITYENV_')):del env[k]
for k,v in {'PYTHONPATH':str(r/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','LD_LIBRARY_PATH':'/renderer:/opt/conda/lib:/.singularity.d/libs','MUJOCO_GL':'osmesa','PYOPENGL_PLATFORM':'osmesa','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe','LP_NUM_THREADS':'4','OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','CUDA_VISIBLE_DEVICES':'','SDL_VIDEODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1','MPLCONFIGDIR':'/tmp/mpl','XDG_CACHE_HOME':'/tmp/cache','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','XFORMERS_DISABLED':'1'}.items():env['APPTAINERENV_'+k]=v
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
cmd=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',str(r/'source')]
for bind in (str(r/'source')+':'+str(r/'source')+':ro',str(r/'controls')+':'+str(r/'controls')+':ro',c['prior_source']+':'+c['prior_source']+':ro',c['renderer_path']+':/renderer:ro',str(t)+':/tmp:rw',c['venv']+':'+c['venv']+':ro'):cmd+=['--bind',bind]
cmd+=[c['sif'],c['venv']+'/bin/python','-B','-c',TEST]
p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=45)
row={'returncode':p.returncode,'stdout':p.stdout[-12000:],'stderr':p.stderr[-20000:],'models_loaded':0,'simulators':0,'model_forwards':0}
with (r/'controls/IMPORT-CHECK.json').open('x') as f:json.dump(row,f,sort_keys=True)
print(json.dumps(row))
'''
    r=ssh(code);write_new(DOC/'campaign/IMPORT-CHECK-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
