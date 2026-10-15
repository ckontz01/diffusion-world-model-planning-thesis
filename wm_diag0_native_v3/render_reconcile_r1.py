"""Preserve failed discovery; inspect existing software-renderer files only."""
import json
from .common import DOC,RUN,write_new
from wm_diag0_preflight_v1.common import SIF,VENV
from wm_diag0_preflight_v1.transport import ssh

def main():
    script='''import ctypes,glob,json,os
rows={}
for pat in ('/usr/lib/x86_64-linux-gnu/libOSMesa*','/usr/lib/x86_64-linux-gnu/libEGL*','/usr/lib/x86_64-linux-gnu/libGL*','/usr/lib64/libOSMesa*','/opt/conda/lib/libOSMesa*','/opt/conda/lib/libEGL*','/opt/conda/lib/libGL*'):
 for p in glob.glob(pat):
  if not os.path.isfile(p): continue
  try: ctypes.CDLL(p); status='LOAD_OK'
  except OSError as e: status=str(e)
  rows[p]={'bytes':os.stat(p).st_size,'load':status,'realpath':os.path.realpath(p)}
print(json.dumps(rows))'''
    code='RUN='+repr(RUN)+'\nSIF='+repr(SIF)+'\nVENV='+repr(VENV)+'\nSCRIPT='+repr(script)+'\n'+'''
import glob,hashlib,json,os,pathlib,subprocess
manifest=json.loads((pathlib.Path(RUN)/'controls/RUNTIME-MANIFEST.json').read_text())
inside=[k for k in manifest['members'] if any(x in k.lower() for x in ('osmesa','libegl.','libgl.','libglx.','swrast','libglfw.'))]
host={}
for pat in ('/usr/lib64/libOSMesa*','/usr/lib64/libEGL*','/usr/lib64/libGL*','/usr/lib/x86_64-linux-gnu/libOSMesa*','/usr/lib/x86_64-linux-gnu/libEGL*','/usr/lib/x86_64-linux-gnu/libGL*'):
 for name in glob.glob(pat):
  p=pathlib.Path(name)
  if p.is_file(): host[name]={'bytes':p.stat().st_size,'realpath':str(p.resolve())}
p=subprocess.run(['apptainer','exec','--containall','--cleanenv','--no-home','--bind',VENV+':'+VENV+':ro',SIF,VENV+'/bin/python','-B','-c',SCRIPT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=35)
print(json.dumps({'existing_venv_renderer_candidates':inside,'host_renderer_candidates':host,'container':{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr},'library_files_copied':0,'environment_modified':False,'simulators':0,'gpu_requests':0}))
'''
    result=ssh(code);write_new(DOC/'RENDER-RECONCILIATION-001.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__': main()
