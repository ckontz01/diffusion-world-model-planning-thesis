"""Existing WSL/bastion route only. No credentials, sudo, or environment repair."""
import base64
import json
import shlex
import subprocess
from wm_diag0_preflight_v1.common import DOC, REMOTE, SITE, SIF, RUN, write_new

def ssh(code, payload=None, timeout=90):
    encoded = base64.b64encode(code.encode()).decode()
    remote = 'timeout 75s python3 -B -c ' + shlex.quote('import base64;exec(base64.b64decode(' + repr(encoded) + '))')
    cmd = ['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout',str(timeout)+'s','ssh',
           '-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ConnectionAttempts=1','prometheus',remote]
    p = subprocess.run(cmd, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout+5)
    if p.returncode: raise RuntimeError('SSH operation failed: '+p.stderr.decode(errors='replace')+' '+p.stdout.decode(errors='replace')[:2000])
    if len(p.stdout) > 900000: raise ValueError('remote metadata output bound')
    return json.loads(p.stdout)

def inventory():
    code = '''
import hashlib,json,pathlib,subprocess,zipfile,pickletools,time
site=pathlib.Path(SITE)
members={}
for package in ('stable_worldmodel','stable_pretraining'):
 for p in sorted((site/package).rglob('*')):
  if p.is_file() and p.suffix in ('.py','.xml','.json','.yaml','.yml'):
   if p.is_symlink(): raise RuntimeError('unexpected source symlink')
   raw=p.read_bytes(); members[str(p.relative_to(site))]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
if len(members)>3000 or sum(x['bytes'] for x in members.values())>15000000: raise RuntimeError('source inventory bound')
objects={}
for name,rel in [('pusht','pusht/lewm_hf_22b330c_object.ckpt'),('reacher','reacher/lewm_object.ckpt')]:
 p=pathlib.Path(REMOTE)/'data/stablewm'/rel
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 with zipfile.ZipFile(p) as z:
  data=[i for i in z.infolist() if i.filename.endswith('/data.pkl')]
  if len(data)!=1 or data[0].file_size>2000000: raise RuntimeError('pickle metadata bound')
  raw=z.read(data[0]); refs=set(); stack=0
  for op,arg,pos in pickletools.genops(raw):
   if op.name=='GLOBAL': refs.add(arg)
   if op.name=='STACK_GLOBAL': stack+=1
 objects[name]={'path':str(p),'bytes':p.stat().st_size,'sha256':h,'static_globals':sorted(refs),'unresolved_stack_globals':stack,'deserialized':False}
queue=subprocess.check_output(['squeue','-u',str(__import__('os').getuid()),'-h','-o','%i|%j|%T'],text=True)
print(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_members':members,'lewm':objects,'own_queue':queue,'new_run_already_exists':pathlib.Path(RUN).exists(),'prejepa_source':(site/'stable_worldmodel/wm/prejepa.py').read_text()}))
'''
    for name,value in [('SITE',SITE),('REMOTE',REMOTE),('RUN',RUN)]: code = name+'='+repr(value)+'\n'+code
    result=ssh(code)
    write_new(DOC/'CLUSTER-INVENTORY-001.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_members','prejepa_source')},indent=2))
    print('source members',len(result['source_members']))

if __name__ == '__main__': inventory()
