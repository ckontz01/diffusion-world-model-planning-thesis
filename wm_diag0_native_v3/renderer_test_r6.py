"""Artificial 4x4 software-render test only, inside unchanged image."""
import json
from .common import DOC,RUN,write_new
from .transport import ssh
from wm_diag0_preflight_v1.common import SIF,VENV

TOY='''import ctypes,hashlib,json
from OpenGL import GL,osmesa
ctx=osmesa.OSMesaCreateContextExt(GL.GL_RGBA,24,8,0,None)
if not ctx:raise RuntimeError('OSMesa context unavailable')
buf=(ctypes.c_ubyte*64)()
try:
 if not osmesa.OSMesaMakeCurrent(ctx,buf,GL.GL_UNSIGNED_BYTE,4,4):raise RuntimeError('software context failed')
 GL.glClearColor(.2,.4,.6,1.);GL.glClear(GL.GL_COLOR_BUFFER_BIT);GL.glFinish()
 renderer=GL.glGetString(GL.GL_RENDERER).decode()
 if not any(n in renderer.lower() for n in ('llvmpipe','softpipe')):raise RuntimeError('software renderer required')
 if bytes(buf)!=bytes([51,102,153,255])*16:raise RuntimeError('artificial pixel equality')
 print(json.dumps({'status':'ARTIFICIAL_SOFTWARE_RENDER_PASSED','renderer':renderer,'pixels_sha256':hashlib.sha256(bytes(buf)).hexdigest(),'pixels':16,'models':0,'simulators':0,'gpu_requests':0}))
finally:osmesa.OSMesaDestroyContext(ctx)'''

def main():
    code='RUN='+repr(RUN)+'\nSIF='+repr(SIF)+'\nVENV='+repr(VENV)+'\nTOY='+repr(TOY)+'\n'+'''
import json,os,pathlib,subprocess
root=pathlib.Path(RUN);temp=root/'renderer-test-r6-tmp';temp.mkdir(exist_ok=False)
env=dict(os.environ)
for k in list(env):
 if k.startswith(('APPTAINERENV_','SINGULARITYENV_')):del env[k]
for k,v in {'LD_LIBRARY_PATH':'/renderer:/opt/conda/lib:/.singularity.d/libs','PYTHONPATH':'','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','MUJOCO_GL':'osmesa','PYOPENGL_PLATFORM':'osmesa','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe','LP_NUM_THREADS':'4','OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','CUDA_VISIBLE_DEVICES':'','HOME':'/tmp'}.items():env['APPTAINERENV_'+k]=v
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
p=subprocess.run(['apptainer','exec','--containall','--cleanenv','--no-home','--bind',str(root/'renderer-r6')+':/renderer:ro','--bind',str(temp)+':/tmp:rw','--bind',VENV+':'+VENV+':ro',SIF,VENV+'/bin/python','-B','-c',TOY],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=35)
r={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'runtime_or_host_modified':False}
with (root/'controls/RENDERER-R6-TEST.json').open('x') as f:json.dump(r,f,sort_keys=True)
print(json.dumps(r))
'''
    result=ssh(code);write_new(DOC/'RENDERER-R6-TEST-001.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
