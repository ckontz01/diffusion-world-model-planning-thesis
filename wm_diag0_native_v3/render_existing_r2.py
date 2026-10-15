"""Final bounded search of existing renderer executables/libraries, no installs."""
import json
import subprocess
from .common import DOC,REMOTE,write_new
from wm_diag0_preflight_v1.transport import ssh

def main():
    code='BASE='+repr(REMOTE)+'\n'+'''
import glob,json,os,pathlib,shutil,subprocess,time
rows={}; started=time.monotonic(); visited=0; truncated=False
for base in (BASE+'/envs','/opt/ohpc/pub/libs','/opt/apps'):
 if not os.path.isdir(base): continue
 for here,dirs,files in os.walk(base):
  visited+=1
  if visited>60000 or time.monotonic()-started>20: truncated=True; break
  dirs[:]=[n for n in dirs if n not in ('__pycache__','.git','include','tests','test','examples')]
  for name in files:
   if name.startswith('libOSMesa') or name in ('Xvfb','xvfb-run'):
    p=os.path.join(here,name); rows[p]={'bytes':os.stat(p).st_size,'realpath':os.path.realpath(p)}
 if truncated: break
system={n:shutil.which(n) for n in ('Xvfb','xvfb-run','Xorg')}
dri={p:{'bytes':os.stat(p).st_size,'realpath':os.path.realpath(p)} for pat in ('/usr/lib64/dri/swrast_dri.so','/usr/lib64/libLLVM*','/usr/lib/x86_64-linux-gnu/dri/swrast_dri.so') for p in glob.glob(pat) if os.path.isfile(p)}
print(json.dumps({'existing_renderer_files':rows,'executables':system,'software_dri':dri,'visited_directories':visited,'search_truncated':truncated,'elapsed_seconds':time.monotonic()-started,'installations':0,'simulators':0}))
'''
    result=ssh(code); write_new(DOC/'RENDER-EXISTING-CLUSTER-001.json',result)
    script="import glob,json,os,shutil; print(json.dumps({'existing_osmesa':{p:{'bytes':os.stat(p).st_size,'realpath':os.path.realpath(p)} for p in glob.glob('/usr/lib/x86_64-linux-gnu/libOSMesa*') if os.path.isfile(p)},'executables':{n:shutil.which(n) for n in ('Xvfb','xvfb-run')}}))"
    p=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','15s','python3','-B','-c',script],capture_output=True,text=True,timeout=20)
    result2={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'environment_modified':False}
    write_new(DOC/'RENDER-EXISTING-WSL-001.json',result2)
    print(json.dumps({'cluster':result,'existing_wsl':result2},indent=2))

if __name__=='__main__': main()
