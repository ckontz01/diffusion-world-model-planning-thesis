"""Composite source lineage acceptance; one bounded observation per invocation."""
import json,sys
from .common import ROOT,DOC,write_new
from wm_diag0_source_r3.common import RUN as SOURCES,OLD
from wm_diag0_native_v3.transport import ssh

def main():
    mode,label=sys.argv[1:3]
    if mode not in ('observe','gate') or not label.isalnum():raise ValueError('exclusive bounded source operation')
    cbytes=(ROOT/'docs/world-model-diagnostic-a2-source-r3-20261015/CONTRACT.json').read_bytes()
    code='RUN='+repr(SOURCES)+'\nOLD='+repr(OLD)+'\nMODE='+repr(mode)+'\n'+'''
import hashlib,json,pathlib,subprocess,sys
r=pathlib.Path(RUN);old=pathlib.Path(OLD);c=json.load(sys.stdin)
d=json.loads((r/'controls/DISPATCH-source.json').read_text());job=d['job_id']
if not job.isdigit() or d['contract_sha256']!=hashlib.sha256((r/'source/CONTRACT.json').read_bytes()).hexdigest():raise ValueError('exact source dispatch/contract')
q=subprocess.run(['squeue','-h','-j',job,'-o','%i|%T|%M|%N|%R'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
if q.returncode and 'Invalid job id specified' not in q.stderr:raise RuntimeError('scheduler unavailable')
a=subprocess.check_output(['sacct','-X','-n','-P','-j',job,'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
tasks={};errors={}
for p in sorted((r/'tasks').glob('*/controls/RESULT.json')):
 t=json.loads(p.read_text());tasks[p.parents[1].name]=t
 if t['status']!='ACCEPTED':errors[p.parents[1].name]=(p.parents[1]/'logs/worker.log').read_text(errors='replace')[-16000:]
stop=json.loads((r/'controls/STOP.json').read_text()) if (r/'controls/STOP.json').exists() else None
result={'status':'SOURCE_PROGRESS','job_id':job,'queue':q.stdout,'scheduler':a,'accepted_tasks':sum(x['status']=='ACCEPTED' for x in tasks.values()),'STOP':stop,'failed_worker_stderr':errors,'scientific_aggregates_read':False}
if MODE=='gate':
 if q.stdout.strip() or stop:raise RuntimeError('sources active/stopped: no campaign gate')
 rows=[x.split('|') for x in a.splitlines() if x.strip()]
 if len(rows)!=60 or {x[0] for x in rows}!={job+'_'+str(i) for i in range(60,120)} or any(x[2]!='COMPLETED' or x[3]!='0:0' or x[5]!='4' for x in rows):raise ValueError('all60 new allocations must be successful and reconciled')
 olda=subprocess.check_output(['sacct','-X','-n','-P','-j','317041','--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
 oldrows=[x.split('|') for x in olda.splitlines() if x.strip()]
 oldcharge=sum(int(x[4]) for x in oldrows)
 if oldcharge!=678 or len(oldrows)!=62:raise ValueError('original failure-inclusive source allocation accounting')
 charge=oldcharge+sum(int(x[4]) for x in rows)
 if charge>7200 or 17+charge+5400>13800:raise ValueError('full future CPU reserve')
 sys.path.insert(0,str(r/'source'))
 from wm_diag0_native_v3.source_accept import accept,ident
 plan=json.loads((r/'source/ROOT-PLAN.json').read_text());seals={};proofs=[]
 for row in plan['roots']:
  key=row['task']+'-'+str(row['root_index']).zfill(3);supplier=old if row['task']=='pusht' else r;t=supplier/'tasks'/key
  ctl=json.loads((t/'controls/RESULT.json').read_text())
  if ctl['status']!='ACCEPTED' or not ctl['acceptance']['available']:raise ValueError('fixed required source window')
  if row['task']=='pusht' and ident(t/'controls/RESULT.json')!=c['source_recovery']['accepted_suppliers'][key]['result_identity']:raise ValueError('unchanged successful old supplier')
  proof=accept(t/'output',ctl['acceptance']['seal'],row)
  if not proof['available']:raise ValueError('required source window unavailable')
  seals[key]=proof['seal'];proofs.append(proof)
 original=json.loads((r/'tasks/reacher-000/controls/ORIGINAL-PARTIAL-BYTE-IDENTITY.json').read_text())
 if original['all_four_original_arrays_bit_identical'] is not True or original['members']!=c['source_recovery']['failed_partial']:raise ValueError('same-seed retry original-byte parity')
 result={'status':'ALL120_SOURCE_WINDOWS_INDEPENDENTLY_ACCEPTED','source_seals':seals,'roots':proofs,'source_run':RUN,
  'source_runs':{'pusht':OLD,'reacher':RUN},'exact_source_job_ids':['317041',job],'scheduler_original':olda,'scheduler_recovery':a,
  'cpu_source_allocation_seconds':charge,'cpu_total_with_preflight':17+charge,'cpu_full_future_after_source':5400,
  'gpu_full_future_original_cap':468000,'source_contract':ident(r/'source/CONTRACT.json'),'scientific_aggregates_read':False,
  'failed_replacement_attempts':1,'original_failed_partials_unchanged':True,'original_array_parity':original}
 with (r/'controls/ALL-SOURCES-ACCEPTED.json').open('x') as f:json.dump(result,f,sort_keys=True)
print(json.dumps(result))
'''
    r=ssh(code,payload=cbytes);write_new(DOC/('SOURCE-'+mode.upper()+'-'+label+'.json'),r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_seals','roots','scheduler_original','scheduler_recovery')},indent=2))

if __name__=='__main__':main()
