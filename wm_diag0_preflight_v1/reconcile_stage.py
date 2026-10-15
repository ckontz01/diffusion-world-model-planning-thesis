"""Read-only reconciliation of the failed bounded upload; no retry or mutation."""
import ast
import base64
import hashlib
import json
from wm_diag0_preflight_v1.common import DOC,ROOT,RUN,identity,write_new
from wm_diag0_preflight_v1.transport import ssh

def main():
    tree=ast.parse((ROOT/'wm_diag0_preflight_v1/deploy.py').read_text())
    raw=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('\nimport hashlib,json,os,pathlib,sys,time')][0]
    script='RUN='+repr(RUN)+'\nEXPECTED='+repr(identity(DOC/'CONTRACT.json')['sha256'])+'\n'+raw
    needle=base64.b64encode(script.encode()).decode()
    code='RUN='+repr(RUN)+'\nNEEDLE='+repr(needle)+'\n'+'''
import hashlib,json,pathlib,os,time
root=pathlib.Path(RUN); rows={}; active=[]
for p in sorted(root.rglob('*')):
 if p.is_file():
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(1048576),b''): h.update(b)
  rows[str(p.relative_to(root))]={'bytes':p.stat().st_size,'sha256':h.hexdigest(),'symlink':p.is_symlink()}
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit(): continue
 try:
  if p.stat().st_uid!=os.getuid(): continue
  cmd=(p/'cmdline').read_bytes()
  if NEEDLE.encode() in cmd:
   stat=(p/'stat').read_text(); fields=stat[stat.rfind(')')+2:].split()
   active.append({'pid':int(p.name),'start_ticks':int(fields[19]),'cmdline_sha256':hashlib.sha256(cmd).hexdigest()})
 except (IOError,OSError): pass
print(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'members':rows,'exact_upload_processes':active,'dispatch_exists':(root/'controls/DISPATCH.json').exists()}))
'''
    r=ssh(code); c=json.loads((DOC/'CONTRACT.json').read_text()); complete={}; partial={}
    for n,row in r['members'].items():
        key=n.removeprefix('source/')
        if n.startswith('source/') and key in c['staged_members']:
            (complete if {k:row[k] for k in ('bytes','sha256')}==c['staged_members'][key] else partial)[key]=row
    r.update(complete=complete,partial=partial,total_retained_bytes=sum(x['bytes'] for x in r['members'].values()))
    write_new(DOC/'STAGE-FAILURE-RECONCILIATION-001.json',r); print(json.dumps(r,indent=2))

if __name__=='__main__': main()
