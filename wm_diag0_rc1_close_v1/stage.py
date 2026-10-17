"""Exact once-only held CPU dispatch after native publication/SSD and fresh gates."""
import ast,base64,hashlib,json
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .freeze import additions
from .transport_v2 import call

CODE=r'''
import base64,hashlib,json,os,shlex,stat,subprocess,sys,time
from pathlib import Path
data=json.load(sys.stdin);raw=base64.b64decode(data['contract']);expected=data['contract_identity'];c=json.loads(raw);f=c['rc1_final']
if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=expected:raise ValueError('externally reviewed final contract')
layout=json.loads(base64.b64decode(data['new_source']['final_evidence/PRESERVATION-LAYOUT-001.json']))['layout']
root=Path(layout['final_run']);ops=Path(layout['operational_root']);old=Path(c['run'])
if root.exists():raise FileExistsError('own final root already exists: reconcile, never duplicate allocation')
if layout['study_base']!=str(old.parent) or root.name!='campaign-v4-rc1-final-v2':raise ValueError('exact owned final root')
publication=data['publication']
if publication['contract']!=expected or publication['source_commit']!=publication['remote_full_hash'] or publication['publication_anchor']!=f['publication_anchor']:raise ValueError('native published/fullremote/SSD external source gate')
root.mkdir()
for directory in ('source','tasks/analysis-0/controls','tasks/analysis-0/logs','tasks/analysis-0/tmp','fixtures'):(root/directory).mkdir(parents=True,exist_ok=False)
for directory in ('submission','cpu/controls','cpu/tmp-archive','archive','postarchive/controls','sidecars'):(ops/directory).mkdir(parents=True,exist_ok=False)
for name,want in c['staged_members'].items():
 p=root/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name in data['new_source']:
  payload=base64.b64decode(data['new_source'][name])
  if {'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}!=want:raise ValueError('new published source bytes')
  with p.open('xb') as out:out.write(payload)
 else:
  original=old/'source'/name
  if original.is_symlink() or not original.is_file():raise ValueError('original regular source retained')
  h=hashlib.sha256(original.read_bytes()).hexdigest()
  if {'bytes':original.stat().st_size,'sha256':h}!=want:raise ValueError('original executed source byte changed')
  os.link(str(original),str(p))
 p.chmod(0o444)
with (root/'source/FINAL-CONTRACT.json').open('xb') as out:out.write(raw)
(root/'source/FINAL-CONTRACT.json').chmod(0o444)
# Retain all NEW integration failures/partials/snapshots as opaque evidence in
# the complete owned-final archive root, while keeping original ops copies too.
fixture_bytes=0;fixture_files=0
for name in ('review-source-001','review-source-002','tests'):
 original=ops/name
 if not original.is_dir() or original.is_symlink():raise ValueError('exact retained new integration evidence root')
 stack=[original]
 while stack:
  directory=stack.pop()
  with os.scandir(str(directory)) as stream:entries=list(stream)
  for entry in entries:
   s=entry.stat(follow_symlinks=False);p=Path(entry.path);destination=root/'fixtures'/name/p.relative_to(original)
   if stat.S_ISDIR(s.st_mode):stack.append(p)
   elif stat.S_ISREG(s.st_mode):
    fixture_files+=1;fixture_bytes+=s.st_size
    if fixture_files>2000 or fixture_bytes>5000000:raise ValueError('finite complete new fixture copies')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with p.open('rb') as source,destination.open('xb') as target:
     while True:
      b=source.read(1048576)
      if not b:break
      target.write(b)
    destination.chmod(0o444)
   else:raise ValueError('no fixture alias/special member omitted')
alloc=base64.b64decode(data['new_source']['final_evidence/ALL-ALLOCATIONS-TERMINAL.json'])
with (root/'tasks/analysis-0/controls/ALL-ALLOCATIONS-TERMINAL.json').open('xb') as out:out.write(alloc)
for p in sorted((root/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(root/'source').chmod(0o555)
sys.path.insert(0,str(root/'source'))
from wm_diag0_rc1_close_v1.entry_v2 import authenticate_inputs
from wm_diag0_rc1_final_v2.archive_v2 import canonical
proof=authenticate_inputs(root/'source/FINAL-CONTRACT.json',expected,layout,time.monotonic()+260)
def write(name,value):
 b=canonical(value)
 if len(b)>200000:raise ValueError('bounded external stage control')
 with (ops/'submission'/name).open('xb') as out:out.write(b);out.flush();os.fsync(out.fileno())
write('PREFLIGHT.json',{'proof':proof,'publication':publication,'retained_fixture_logical_bytes':fixture_bytes,'retained_fixture_files':fixture_files})
script='#!/bin/bash\nset -euo pipefail\numask 077\nexport PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" NVIDIA_VISIBLE_DEVICES=void\nexport OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4\ncd '+shlex.quote(str(root/'source'))+'\nexec python3 -B -m wm_diag0_rc1_close_v1.driver_v2 '+shlex.quote(str(root/'source/FINAL-CONTRACT.json'))+' '+shlex.quote(canonical(expected).decode())+'\n'
write('SBATCH-REQUEST.json',{'script_sha256':hashlib.sha256(script.encode()).hexdigest(),'contract':expected,'GPU_requested':0,'seconds':3600,'CPUs':4,'RAM_bytes':8589934592,'automatic_retry':False})
args=['sbatch','--parsable','--hold','--no-requeue','--account=superworld','--job-name=wm-a2-rc1-final-v2','--partition=defq','--qos=normal',
 '--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--time=60','--chdir='+str(root/'source'),
 '--output='+str(ops/'cpu/supervisor.log'),'--error='+str(ops/'cpu/supervisor.log')]
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('saved CPU submission failure; no automatic retry')
job=p.stdout.strip().split(';')[0]
if not job.isdigit():raise ValueError('ambiguous submission response: never repeat')
actual=subprocess.check_output(['scontrol','show','job','-o',job],universal_newlines=True,timeout=10)
fields=dict(x.split('=',1) for x in actual.split() if '=' in x)
if fields.get('JobState')!='PENDING' or fields.get('NumCPUs')!='4' or fields.get('NumTasks')!='1' or fields.get('TimeLimit')!='01:00:00' or fields.get('Partition')!='defq' or fields.get('WorkDir')!=str(root/'source'):raise PermissionError('actual held CPU request mismatch; retain held job')
if fields.get('MinMemoryNode') not in ('8G','8192M') or 'gpu' in fields.get('TresPerNode','').lower() or 'gres/gpu' in fields.get('ReqTRES','').lower():raise PermissionError('actual held memory/noGPU request mismatch')
dispatch={'job_id':job,'contract':expected,'staged_members':c['staged_members'],'publication':f['publication_anchor'],
 'source_commit':publication['source_commit'],'source_SSD_whole':publication['whole'],'held_scheduler_record':actual,
 'GPU_requested':0,'CPU_seconds':3600,'automatic_retry':False,'retained_fixture_bytes':fixture_bytes}
write('DISPATCH.json',dispatch)
release=subprocess.run(['scontrol','release',job],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE.json',{'job_id':job,'returncode':release.returncode,'stdout':release.stdout,'stderr':release.stderr})
if release.returncode:raise RuntimeError('held job release outcome retained; do not resubmit')
print(json.dumps({'status':'EXACT_FROZEN_CPU_ONLY_FINAL_JOB_DISPATCHED','job_id':job,'contract':expected,'source_commit':publication['source_commit'],
 'actual_analysis_or_final_SSD_acceptance_claimed':False,'scientific_values_read_by_parent':False,'retained_fixture_logical_bytes':fixture_bytes}))
'''

def main():
    from wm_diag0_preflight_v1.preserve import volume
    pub=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if pub['status']!='FINALIZER_SOURCE_PUBLISHED_FULL_REMOTE_AND_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_VERIFIED' or identity(pub['archive'])!=pub['whole']:raise ValueError('actual native source SSD package')
    volume();cpath=DOC/'FINAL-CONTRACT.json'
    if identity(cpath)!=pub['contract']:raise ValueError('exact published source contract')
    review=json.loads((DOC/'REVIEW-001.json').read_text());new=additions()
    for name,raw in new.items():
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=review['new_members'][name]:raise ValueError('published source member changed before stage')
    ast.parse(CODE,feature_version=(3,6))
    compact_pub={k:pub[k] for k in ('status','source_commit','remote_full_hash','contract','whole','publication_anchor','volume')}
    z=call('STAGE001',CODE,{'contract':base64.b64encode(cpath.read_bytes()).decode(),'contract_identity':pub['contract'],
        'new_source':{n:base64.b64encode(raw).decode() for n,raw in new.items()},'publication':compact_pub},seconds=345)
    print(json.dumps(z))
if __name__=='__main__':main()
