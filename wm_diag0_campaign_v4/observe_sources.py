"""One bounded exact-dispatch source observation; technical metadata only."""
import json,sys
from .common import DOC,SOURCE_RUN,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('new exclusive label')
    result=ssh('RUN='+repr(SOURCE_RUN)+'\n'+'''
import hashlib,json,pathlib,subprocess
r=pathlib.Path(RUN);d=json.loads((r/'controls/DISPATCH-source.json').read_text());job=d['job_id']
if not job.isdigit():raise ValueError('exact dispatch ID')
queue=subprocess.run(['squeue','-h','-j',job,'-o','%i|%T|%M|%N|%R'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
acct=subprocess.run(['sacct','-X','-n','-P','-j',job,'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,ReqMem,NodeList'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=15)
rows={};errors={}
for p in sorted((r/'tasks').glob('*/controls/RESULT.json')):
 body=json.loads(p.read_text());rows[p.parents[1].name]=body
 if body['status']!='ACCEPTED':
  log=p.parents[1]/'logs/worker.log'
  if log.is_file():errors[p.parents[1].name]=log.read_text(errors='replace')[-12000:]
stop=json.loads((r/'controls/STOP.json').read_text()) if (r/'controls/STOP.json').exists() else None
print(json.dumps({'dispatch':d,'queue':queue.stdout,'queue_returncode':queue.returncode,'scheduler':acct.stdout,'scheduler_returncode':acct.returncode,'tasks':rows,'STOP':stop,'failed_worker_stderr':errors,'scientific_aggregates_read':False,'model_outputs_read':False}))
''')
    write_new(DOC/'source-import-r1'/('OBSERVATION-'+label+'.json'),result)
    print(json.dumps({'dispatch':result['dispatch'],'queue':result['queue'],'scheduler':result['scheduler'],
                      'completed_tasks':len(result['tasks']),'STOP':result['STOP'],'failed_worker_stderr':result['failed_worker_stderr']},indent=2))

if __name__=='__main__':main()
