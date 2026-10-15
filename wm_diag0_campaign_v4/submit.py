"""One finite serial GPU DAG; exact dispatch before releasing held jobs."""
import json
from .common import DOC,RUN,identity,write_new
from .small import published
from wm_diag0_native_v3.transport import ssh

def specification():
    return [('readout',4,1800,'a6000','gpu09',True,None),('technical',4,3600,'a6000','gpu09',True,'readout'),
            ('grid',124,3600,'a6000','gpu09',True,'technical'),('analysis',1,3600,'defq',None,False,'grid')]

def main():
    published('campaign');expected=identity(DOC/'campaign/CONTRACT.json')['sha256']
    write_new(DOC/'campaign/SUBMIT-001.started.json',{'contract':expected,'GPU_tasks':132,'CPU_analysis_tasks':1,'no_requeue':True})
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\nSPEC='+repr(specification())+'\n'+'''
import hashlib,json,os,pathlib,subprocess,time
r=pathlib.Path(RUN);control=r/'controls'
def write(n,x):
 with (control/n).open('x') as f:json.dump(x,f,sort_keys=True)
if any((control/n).exists() for n in ('DAG-DISPATCH.json','SUBMIT-STARTED.json','STOP.json')):raise RuntimeError('existing/ambiguous campaign; never duplicate')
c=json.loads((r/'source/CONTRACT.json').read_text())
if hashlib.sha256((r/'source/CONTRACT.json').read_bytes()).hexdigest()!=EXPECTED or not c['conditional_dispatch_ready']:raise ValueError('exact conditional campaign contract')
test=json.loads((control/'IMPORT-CHECK.json').read_text())
if test['returncode'] or json.loads(test['stdout'])['status']!='ALL_CAMPAIGN_IMPORTS_AUTHENTICATED':raise ValueError('all native source imports must pass')
if json.loads((control/'STAGE-VERIFIED.json').read_text())['contract_sha256']!=EXPECTED:raise ValueError('source stage acceptance')
queue=subprocess.check_output(['squeue','-u',str(os.getuid()),'-h','-o','%i|%j|%T'],universal_newlines=True,timeout=10)
if any('wm-a2-' in line for line in queue.splitlines()):raise RuntimeError('existing study allocation; no overlap')
write('SUBMIT-STARTED.json',{'contract_sha256':EXPECTED,'time':time.time(),'GPU_full_future':468000,'CPU_charged_before':c['cpu_charged_before'],'CPU_full_future':5400})
jobs={}
try:
 for phase,count,seconds,partition,node,gpu,dependency in SPEC:
  script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),'exec python3 -B -m wm_diag0_campaign_v4.supervisor '+RUN+' '+EXPECTED+' '+phase,''])
  args=['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-v4-'+phase,'--partition='+partition,'--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--time='+str(seconds//60),'--chdir='+str(r/'source'),'--output='+str(r/'logs'/(phase+'-%A_%a.log')),'--error='+str(r/'logs'/(phase+'-%A_%a.log'))]
  if count>1:args+=['--array=0-'+str(count-1)+'%1']
  if node:args+=['--nodelist='+node]
  if gpu:args+=['--gres=gpu:1']
  if dependency:args+=['--dependency=afterok:'+jobs[dependency]]
  p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
  write('SBATCH-'+phase+'-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'args':args})
  if p.returncode:raise RuntimeError('submission failed; preserve held dispatches, never blind retry')
  jid=p.stdout.strip().split(';')[0]
  if not jid.isdigit():raise RuntimeError('ambiguous submission; no automatic retry')
  jobs[phase]=jid
 dag={'jobs':jobs,'contract_sha256':EXPECTED,'stage_counts':c['stage_counts'],'maximum_simultaneous_GPU_tasks':1,'GPUs_per_task':1,'node':'gpu09','GPU_full_future_seconds':468000,'CPU_full_future_seconds':5400,'CPU_charged_before':c['cpu_charged_before'],'source_job_ids':['317041','317103'],'technical_gates_included_not_extra_pilots':True,'automatic_replacements':0}
 write('DAG-DISPATCH.json',dag)
 for phase,jid in jobs.items():
  p=subprocess.run(['scontrol','release',jid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
  write('RELEASE-'+phase+'-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
  if p.returncode:raise RuntimeError('partial release; reconcile exact dispatch, do not resubmit')
 print(json.dumps(dag))
except BaseException as e:
 write('SUBMISSION-ERROR.json',{'error':repr(e),'known_job_ids':jobs,'no_repeated_submission':True})
 for phase,jid in jobs.items():
  p=subprocess.run(['scancel','--state=PENDING',jid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=5)
  write('SUBMISSION-CANCEL-'+phase+'.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 raise
'''
    r=ssh(code);write_new(DOC/'campaign/DAG-DISPATCH-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
