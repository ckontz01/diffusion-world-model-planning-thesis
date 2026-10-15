"""Bound existing runtime files and inspect technical sources without imports."""
import json
from .common import DOC, RUN, PRIOR, write_new
from wm_diag0_preflight_v1.common import SITE, SIF, VENV
from wm_diag0_preflight_v1.transport import ssh

def main():
    code = 'RUN='+repr(RUN)+'\nPRIOR='+repr(PRIOR)+'\nSITE='+repr(SITE)+'\nVENV='+repr(VENV)+'\nSIF='+repr(SIF)+'\n'+'''
import hashlib,json,os,pathlib,subprocess,time
root=pathlib.Path(RUN)
root.mkdir(exist_ok=False)
for n in ('controls','source','logs','tasks','tmp'): (root/n).mkdir()
members={}; total=0; links={}
for p in sorted(pathlib.Path(VENV).rglob('*')):
 if p.is_symlink():
  links[str(p.relative_to(VENV))]=os.readlink(str(p)); continue
 if not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc': continue
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 size=p.stat().st_size; total+=size
 members[str(p.relative_to(VENV))]={'bytes':size,'sha256':h.hexdigest()}
 if len(members)>60000 or total>2200000000: raise RuntimeError('existing runtime inventory bound')
body={'root':VENV,'members':members,'symlinks':links,'bytes':total,'installed_or_modified':False}
raw=json.dumps(body,sort_keys=True,indent=2).encode()
if len(raw)>12000000: raise ValueError('metadata reservation')
with (root/'controls/RUNTIME-MANIFEST.json').open('xb') as f: f.write(raw)
texts={}
for name in ('dm_control/rl/control.py','dm_control/mujoco/engine.py','dm_control/suite/reacher.py','dm_control/suite/base.py','pymunk/space.py'):
 p=pathlib.Path(SITE)/name
 if p.is_file(): texts[name]=p.read_text()
queue=subprocess.check_output(['squeue','-u',str(os.getuid()),'-h','-o','%i|%j|%T'],universal_newlines=True)
print(json.dumps({'runtime_manifest':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'runtime_bytes':total,'runtime_members':len(members),'symlinks':links,'technical_source':texts,'own_study_queue':[r for r in queue.splitlines() if 'wm-a2-' in r],'prior_dispatch':json.loads((pathlib.Path(PRIOR)/'controls/DISPATCH.json').read_text()),'run':RUN}))
'''
    result=ssh(code, timeout=120)
    write_new(DOC/'RUNTIME-INVENTORY-001.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='technical_source'},indent=2))

if __name__=='__main__': main()
