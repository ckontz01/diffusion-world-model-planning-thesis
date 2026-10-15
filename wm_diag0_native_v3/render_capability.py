"""No-simulator readback of installed CPU rendering libraries in pinned image."""
import json
from .common import DOC,write_new
from wm_diag0_preflight_v1.common import SIF,VENV
from wm_diag0_preflight_v1.transport import ssh

def main():
    script="import ctypes.util,json; print(json.dumps({n:ctypes.util.find_library(n) for n in ('OSMesa','EGL','GL','glfw')}))"
    code='SIF='+repr(SIF)+'\nVENV='+repr(VENV)+'\nSCRIPT='+repr(script)+'\n'+'''
import subprocess,json
p=subprocess.run(['apptainer','exec','--containall','--cleanenv','--no-home','--bind',VENV+':'+VENV+':ro',SIF,VENV+'/bin/python','-B','-c',SCRIPT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=35)
print(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'simulators':0,'models':0,'gpu_requests':0}))
'''
    result=ssh(code); write_new(DOC/'RENDER-CAPABILITY-001.json',result); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
