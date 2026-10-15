"""Terminal allocation/supplier accounting before the single finite recovery."""
import json
from .common import DOC,OLD,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    code='OLD='+repr(OLD)+'\n'+'''
import hashlib,json,pathlib,subprocess
r=pathlib.Path(OLD);d=json.loads((r/'controls/DISPATCH-source.json').read_text())
if d['job_id']!='317041':raise ValueError('exact dispatched source array')
q=subprocess.run(['squeue','-h','-j','317041','-o','%i|%T'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
queue=q.stdout
if q.returncode and 'Invalid job id specified' not in q.stderr:raise RuntimeError('scheduler observation unavailable')
acct=subprocess.check_output(['sacct','-X','-n','-P','-j','317041','--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
if queue.strip():raise RuntimeError('wait/reconcile every live allocation before repair')
rows=[line.split('|') for line in acct.splitlines() if line.strip()]
actual=[x for x in rows if x[2] in ('COMPLETED','FAILED')]
if len(actual)!=61:raise ValueError('exact61 actual source allocations')
if len([x for x in actual if x[2]=='COMPLETED' and x[3]=='0:0'])!=60:raise ValueError('exact60 successful suppliers')
failed=[x for x in actual if x[2]=='FAILED']
if len(failed)!=1 or failed[0][:5]!=['317041_60','317102','FAILED','1:0','13']:raise ValueError('single diagnosed failure')
if len(rows)!=62 or not any(x[0]=='317041_[61-119%1]' and x[2].startswith('CANCELLED') and x[4]=='0' for x in rows):raise ValueError('all59 unstarted/cancelled tasks must be reconciled')
charge=sum(int(x[4]) for x in actual)
def ident(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
suppliers={}
for i in range(60):
 key='pusht-'+str(i).zfill(3);task=r/'tasks'/key;result=json.loads((task/'controls/RESULT.json').read_text())
 if result['status']!='ACCEPTED' or not result['acceptance']['available']:raise ValueError('successful source membership')
 manifest=task/'output/MEMBERS.json'
 if ident(manifest)!=result['acceptance']['seal']:raise ValueError('accepted supplier seal')
 suppliers[key]={'job_id':result['job_id'],'output_seal':result['acceptance']['seal'],'result_identity':ident(task/'controls/RESULT.json')}
task=r/'tasks/reacher-000';partial={}
for name in ('pixels','actions','coordinates','labels'):
 p=task/'output/evidence'/(name+'.npy')
 if not p.is_file():raise ValueError('missing successful partial before writer error')
 partial['evidence/'+name+'.npy']=ident(p)
 import ast,struct
 with p.open('rb') as f:
  if f.read(8)!=b'\\x93NUMPY\\x01\\x00':raise ValueError('safe original array header')
  length=struct.unpack('<H',f.read(2))[0];header=ast.literal_eval(f.read(length).decode('latin1'))
 expected={'pixels':(45,224,224,3),'actions':(44,2),'coordinates':(45,2),'labels':(45,2)}[name]
 if header['shape']!=expected or header['fortran_order']:raise ValueError('complete original trajectory partial')
if any((task/'output'/name).exists() for name in ('MEMBERS.json','record.json','evidence/audits.json')):raise ValueError('do not overwrite/duplicate potentially accepted work')
retained={}
for p in sorted(task.rglob('*')):
 if p.is_file() and not p.is_symlink():retained[str(p.relative_to(task))]=ident(p)
stop=json.loads((r/'controls/STOP.json').read_text())
print(json.dumps({'status':'ALL_ALLOCATIONS_TERMINAL_AND_RECONCILED','scheduler':acct,'own_queue':queue,'squeue_terminal_cache_status':q.stderr,'STOP':stop,'cpu_source_charged_seconds':charge,'CPU_total_with_preflight':17+charge,'CPU_full_future_after_recovery':9000,'CPU_total_charged_plus_full_future':17+charge+9000,'GPU_charged':0,'GPU_full_future':468000,'accepted_suppliers':suppliers,'failed_partial':partial,'failed_retained':retained,'failed_retained_bytes':sum(v['bytes'] for v in retained.values()),'failed_physical_work':{'world_resets':1,'controller_actions':44,'Reacher_dm_steps':88},'source_records_repeated_by_this_observation':0}))
'''
    result=ssh(code);write_new(DOC/'RECONCILIATION-001.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('accepted_suppliers','failed_retained','scheduler')},indent=2))

if __name__=='__main__':main()
