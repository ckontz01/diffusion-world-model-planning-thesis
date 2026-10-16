"""Fresh old-lineage reconciliation and full future recovery resource proof."""
import inspect as pyinspect,json,sys
from .common import *
from .transport import call

CODE=r'''
import hashlib,json,os,pathlib,stat,subprocess,sys,time
old=pathlib.Path(OLD)
def ident(p):
 s=p.lstat()
 if not stat.S_ISREG(s.st_mode):raise ValueError('ordinary opaque binding')
 h=hashlib.sha256();n=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
 return {'bytes':n,'sha256':h.hexdigest()}
def auth_output(task,seal):
 p=task/'output/MEMBERS.json'
 if ident(p)!=seal:raise ValueError('independent member manifest changed')
 members=json.loads(p.read_text())
 for n,x in members.items():
  q=pathlib.PurePosixPath(n)
  if q.is_absolute() or '..' in q.parts or ident(task/'output'/n)!=x:raise ValueError('whole/every accepted member changed')
 return len(members)
if ident(old/'source/GRID-CONTRACT.json')['sha256']!=GRID_HASH:raise ValueError('actual old grid contract')
c=json.loads((old/'source/GRID-CONTRACT.json').read_text())
args=['sacct','-X','-n','-P','--array','-j','317180','--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList']
p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=12)
if p.returncode:raise RuntimeError('exact old accounting unavailable '+p.stderr)
rows=[x.split('|') for x in p.stdout.splitlines() if x]
if len(rows)!=124 or {x[0] for x in rows}!={'317180_'+str(i) for i in range(124)}:raise ValueError('complete124 expanded terminal records')
table={int(x[0][7:]):x for x in rows};allocated=[];gpu=3383;controls={};members=0;usage={};physical={}
for i in range(124):
 x=table[i];state=x[2].split()[0]
 if x[5]!='4' or not x[4].isdigit():raise ValueError('exact CPU and allocation elapsed')
 if i<=66:
  if x[6] not in ('gpu09','gpu09.cluster') or not 0<int(x[4])<=3600:raise ValueError('old allocated identity')
  allocated.append(x[1]);gpu+=int(x[4]);t=old/'tasks'/('grid-'+str(i))
  s=json.loads((t/'controls/STARTED.json').read_text());rr=json.loads((t/'controls/RESULT.json').read_text())
  if s['job_id']!=x[1] or s['contract']!=GRID_HASH or rr['job_id']!=x[1]:raise ValueError('old raw/source/start/result binding')
  for name in ('STARTED','RESULT'):controls[str(i)+'/'+name]=ident(t/'controls'/(name+'.json'))
  if i<66:
   aa=json.loads((t/'controls/ACCEPTED.json').read_text())
   if x[2:4]!=['COMPLETED','0:0'] or rr['status']!='ACCEPTED' or aa['accepted'] is not True or ident(t/'controls/ACCEPTED.json')!=rr['acceptance_identity']:raise ValueError('all66 accepted independently')
   if aa['output_seal']!=rr['output_seal'] or aa['contract_sha256']!=GRID_HASH:raise ValueError('old output seal/source')
   members+=auth_output(t,aa['output_seal']);controls[str(i)+'/ACCEPTED']=ident(t/'controls/ACCEPTED.json')
   for key,value in aa['actual_usage'].items():usage[key]=usage.get(key,0)+value
   for key,value in aa['physical_resource_usage'].items():physical[key]=physical.get(key,0)+value
  elif x[2:4]!=['FAILED','125:0'] or rr['status']!='FAILED' or (t/'controls/ACCEPTED.json').exists():raise ValueError('original failed66 retained and not accepted')
 else:
  if state!='CANCELLED' or x[4]!='0' or x[6]!='None assigned' or (old/'tasks'/('grid-'+str(i))).exists():raise ValueError('only neverallocated67-123')
if len(set(allocated))!=67 or gpu!=45902:raise ValueError('all81 allocated attempts and45902GPU seconds')
q=subprocess.run(['squeue','-h','-j','317180','-o','%i|%T|%M|%N|%R'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=6)
if q.stdout.strip() or not (q.returncode==0 or q.returncode==1 and q.stderr.strip()=='slurm_load_jobs error: Invalid job id specified'):raise ValueError('old array must be fully terminal, not inferred')
# Full pregrid historical allocation rows, including all failures/placeholders.
p=subprocess.check_output(['sacct','-X','-n','-P','-j','317163,317164,317165,317166,317172,317173,317174,317175,317177','--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=12)
exec(HISTORY,globals());_,historical=all_before_grid(p)
if historical!=3383:raise ValueError('all14 historical charge unchanged')
for n,x in c['staged_members'].items():
 if ident(old/'source'/n)!=x:raise ValueError('original executed staged source changed')
for k,x in c['rc1_grid']['technical_suppliers'].items():
 t=pathlib.Path(x['run'])/'tasks'/('technical-'+k)
 if ident(t/'controls/ACCEPTED.json')!=x['acceptance_identity']:raise ValueError('four technical suppliers unchanged')
 members+=auth_output(t,x['output_seal'])
# Hash the full runtime regular members against the existing manifest; retain
# aliases as literals, do not follow their targets from the login environment.
manifest=pathlib.Path(c['recovery']['old_run'])/'controls/RUNTIME-MANIFEST.json'
if ident(manifest)!=c['runtime_manifest']:raise ValueError('runtime manifest authority')
runtime=json.loads(manifest.read_text())['members'];runtime_bytes=0
for n,x in runtime.items():
 if ident(pathlib.Path(c['venv'])/n)!=x:raise ValueError('runtime manifest member changed')
 runtime_bytes+=x['bytes']
if ident(pathlib.Path(c['sif']))['sha256']!=c['sif_sha256']:raise ValueError('SIF unchanged')
for x in c['lewm'].values():
 if ident(pathlib.Path(x['path']))!={k:x[k] for k in ('bytes','sha256')}:raise ValueError('LeWM model unchanged')
failure={n:ident(old/n) for n in ['controls/STOP.json','tasks/grid-66/controls/STARTED.json','tasks/grid-66/controls/RESULT.json','tasks/grid-66/controls/CANCEL-PENDING.json']}
# Whole current study, logical copies and literal aliases, no dedup discount.
logical=0;files=0;aliases=0;stack=[old.parent];children=sorted(x.name for x in old.parent.iterdir())
while stack:
 d=stack.pop()
 with os.scandir(str(d)) as scan:
  for e in scan:
   s=e.stat(follow_symlinks=False)
   if stat.S_ISDIR(s.st_mode):stack.append(pathlib.Path(e.path))
   elif stat.S_ISREG(s.st_mode):logical+=s.st_size;files+=1
   elif stat.S_ISLNK(s.st_mode):logical+=len(os.readlink(e.path).encode());aliases+=1
   else:raise ValueError('unexpected study special file')
source_copy=sum(x['bytes'] for x in c['staged_members'].values())+len((old/'source/GRID-CONTRACT.json').read_bytes())+400000
future=27*10000000+31*60000000+58*1000000+60000000+20000000+300000000+68000000+5000000+source_copy
live=logical+2100000000+3139002368+144694193+future
storage={'logical_current_study':logical,'regular_files':files,'literal_aliases':aliases,'children':children,'new_recovery_source_copy_max':source_copy,
 'live_full_future':live,'archive_full_future':live+500000000,'inclusive_full_future':live+28000000000+2874852312,'no_logical_copy_omission_or_dedup_discount':True}
if live>13500000000 or live+500000000>14000000000 or storage['inclusive_full_future']>44000000000:raise ValueError('full future storage exceeds unchanged overall caps')
z={'status':'OLD81_ATTEMPTS_RECONCILED_FOR_EXACT58_RECOVERY','old_contract_sha256':GRID_HASH,'scheduler':rows,'queue_returncode':q.returncode,'queue_stderr':q.stderr,
 'GPU_terminal':gpu,'GPU_full_future':gpu+58*3600,'allocated_before':81,'planned_total_attempts':139,'accepted_indices':list(range(66)),
 'old_failure_controls':failure,'old_PID':s['PID'] if False else 258808,'old_start_ticks':'9893980','accepted_control_commitment':hashlib.sha256(json.dumps(controls,sort_keys=True).encode()).hexdigest(),
 'accepted_members_hashed':members,'accepted_grid_actual_model_usage':usage,'accepted_grid_actual_physical_usage':physical,
 'runtime_manifest_members_hashed':len(runtime),'runtime_manifest_bytes_hashed':runtime_bytes,'runtime_whole_unmanifested_members_not_claimed':True,
 'storage':storage,'scientific_payloads_deserialized':False,'jobs_changed':False,'captured_epoch':time.time()}
print(json.dumps(z,sort_keys=True,separators=(',',':')))
'''

def main():
    from wm_diag0_rc1_grid_v1.scheduler import HISTORY
    if not Path('D:/WSL/Thesis-Ubuntu/ext4.vhdx').is_file():raise RuntimeError('existing WSL path unavailable; no retry or configuration change')
    auth=json.loads((DOC/'AUTHORITY-001.json').read_text())
    if auth['direct_human_instruction']!=HUMAN:raise ValueError('latest explicit human recovery authority')
    code='OLD='+repr(OLD)+'\nGRID_HASH='+repr(GRID_HASH)+'\nHISTORY='+repr(HISTORY)+'\n'+CODE
    z=call('BINDING001',code,seconds=190)
    if z['status']!='OLD81_ATTEMPTS_RECONCILED_FOR_EXACT58_RECOVERY':raise ValueError('complete technical reconciliation')
    print(json.dumps({'status':z['status'],'storage':z['storage'],'GPU_full_future':z['GPU_full_future'],'accepted_members_hashed':z['accepted_members_hashed']}))

if __name__=='__main__':main()
