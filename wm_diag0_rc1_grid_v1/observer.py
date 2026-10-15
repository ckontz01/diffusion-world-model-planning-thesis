"""Technical metadata only; one exact array snapshot and compute-node PID check."""
OBSERVE=r'''
import hashlib,json,pathlib,shlex,subprocess
r=pathlib.Path(RUN);d=json.loads((r/'controls/DISPATCH.json').read_text());jid=d['array_job_id'];c=json.loads((r/'source/GRID-CONTRACT.json').read_text())
if not jid.isdigit():raise ValueError('exact dispatch ID')
q=subprocess.check_output(['squeue','-h','-j',jid,'-o','%i|%T|%M|%N|%R'],universal_newlines=True,timeout=10)
a=subprocess.check_output(['sacct','-X','-n','-P','-j',jid,'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
def ident(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
tasks={};accepted=0;active=[]
for i in range(124):
 t=r/'tasks'/('grid-'+str(i))
 if not t.exists():continue
 z={}
 for n in ('STARTED','RESULT','WORKER-SUCCESS','ACCEPTED'):
  p=t/'controls'/(n+'.json')
  if p.exists():z[n]=json.loads(p.read_text())
 if 'ACCEPTED' in z:
  if ident(t/'output/MEMBERS.json')!=z['ACCEPTED']['output_seal'] or ident(t/'controls/ACCEPTED.json')!=z['RESULT']['acceptance_identity']:raise ValueError('accepted chain/seal changed')
  accepted+=1
 if 'STARTED' in z and 'RESULT' not in z:active.append(z['STARTED'])
 if 'RESULT' in z and z['RESULT']['status']=='FAILED':
  p=t/'logs/worker.log';z['stderr']=p.read_text(errors='replace')[-16000:] if p.exists() else ''
 tasks[str(i)]=z
if len(active)>1:raise ValueError('serial one-GPU invariant')
for s in active:
 code="import json,pathlib;p=pathlib.Path('/proc')/"+repr(str(s['PID']))+"/'stat';print(json.dumps({'PID_exists':p.exists(),'start_ticks_match':p.exists() and p.read_text().rsplit(')',1)[1].split()[19]=="+repr(str(s['start_ticks']))+"}))"
 try:
  p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5',s['node'],'python3 -B -c '+shlex.quote(code)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=8)
  s['node_verification']=json.loads(p.stdout) if p.returncode==0 else {'verification_unavailable_not_cluster_failure':True,'returncode':p.returncode}
 except subprocess.TimeoutExpired:s['node_verification']={'verification_unavailable_not_cluster_failure':True}
rows=[x.split('|') for x in a.splitlines() if x.strip()]
charged=sum(int(x[4]) for x in rows if x[6] in ('gpu09','gpu09.cluster') and x[2] not in ('PENDING','CONFIGURING'))
stop=json.loads((r/'controls/STOP.json').read_text()) if (r/'controls/STOP.json').exists() else None
print(json.dumps({'dispatch':d,'queue':q,'scheduler':a,'tasks':tasks,'accepted_grid_parents':accepted,'active_process_records':active,'STOP':stop,
 'GPU_all_attempts_including_live_elapsed':c['rc1_grid']['GPU_charged_before']+charged,'CPU_before_analysis':1436,'full_future_GPU_reservation':c['rc1_grid']['full_future_GPU_seconds'],
 'quality_choices_outcomes_or_predictions_read':False}))
'''
