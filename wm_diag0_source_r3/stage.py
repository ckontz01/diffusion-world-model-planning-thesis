import base64,hashlib,json
from .common import ROOT,DOC,RUN,OLD,identity,write_new
from .build import additions
from .preserve import published
from wm_diag0_native_v3.transport import ssh

def main():
    published();raw=(DOC/'CONTRACT.json').read_bytes();expected=hashlib.sha256(raw).hexdigest()
    extra={n:base64.b64encode(b).decode() for n,b in additions().items()}
    payload=json.dumps({'contract':base64.b64encode(raw).decode(),'additions':extra}).encode()
    write_new(DOC/'STAGE-001.started.json',{'contract':expected,'run':RUN})
    code='RUN='+repr(RUN)+'\nOLD='+repr(OLD)+'\nEXPECTED='+repr(expected)+'\n'+'''
import base64,hashlib,json,os,pathlib,subprocess,sys
r=pathlib.Path(RUN);old=pathlib.Path(OLD);data=json.load(sys.stdin);b=base64.b64decode(data['contract']);c=json.loads(b)
if hashlib.sha256(b).hexdigest()!=EXPECTED:raise ValueError('contract bytes')
q=subprocess.run(['squeue','-h','-j','317041','-o','%i|%T'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
if q.stdout.strip() or (q.returncode and 'Invalid job id specified' not in q.stderr):raise RuntimeError('old allocation live/ambiguous')
if not (old/'controls/STOP.json').is_file():raise ValueError('original failure evidence missing')
r.mkdir(exist_ok=False)
for n in ('source','controls','tasks','logs','tmp'):(r/n).mkdir()
oldc=json.loads((old/'source/CONTRACT.json').read_text())
for name,x in c['staged_members'].items():
 p=r/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name in data['additions']:
  raw=base64.b64decode(data['additions'][name])
  if len(raw)!=x['bytes'] or hashlib.sha256(raw).hexdigest()!=x['sha256']:raise ValueError('exact new staged source')
  with p.open('xb') as f:f.write(raw)
  p.chmod(0o444)
 else:
  src=old/'source'/name
  if x!=oldc['staged_members'][name] or src.stat().st_size!=x['bytes'] or hashlib.sha256(src.read_bytes()).hexdigest()!=x['sha256']:raise ValueError('unchanged supplier source')
  os.link(str(src),str(p))
for name,x in c['source_recovery']['failed_partial'].items():
 p=pathlib.Path(c['source_recovery']['partial_supplier'])/name
 if p.is_symlink() or p.stat().st_size!=x['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']:raise ValueError('only four original partial inputs')
with (r/'source/CONTRACT.json').open('xb') as f:f.write(b)
(r/'source/CONTRACT.json').chmod(0o444)
os.link(str(old/'controls/RUNTIME-MANIFEST.json'),str(r/'controls/RUNTIME-MANIFEST.json'))
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
result={'status':'R3_SOURCE_STAGE_AUTHENTICATED','contract_sha256':EXPECTED,'source_members':len(c['staged_members']),'successful_outputs_copied_or_recomputed':0,'model_files_copied':0,'old_STOP_preserved':True}
with (r/'controls/STAGE-VERIFIED.json').open('x') as f:json.dump(result,f,sort_keys=True)
print(json.dumps(result))
'''
    result=ssh(code,payload=payload);write_new(DOC/'STAGE-001.json',result);print(json.dumps(result))

if __name__=='__main__':main()
