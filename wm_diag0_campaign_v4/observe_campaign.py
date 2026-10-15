"""One exact-dispatch bounded technical snapshot, never scientific outputs."""
import json,sys
from .common import DOC,RUN,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive observation label')
    r=ssh('RUN='+repr(RUN)+'\n'+'''
import json,pathlib,subprocess
r=pathlib.Path(RUN);d=json.loads((r/'controls/DAG-DISPATCH.json').read_text());jobs=list(d['jobs'].values())
if len(jobs)!=4 or not all(j.isdigit() for j in jobs):raise ValueError('exact four dispatch IDs')
q=subprocess.run(['squeue','-h','-j',','.join(jobs),'-o','%i|%j|%T|%M|%N|%R'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
a=subprocess.run(['sacct','-X','-n','-P','-j',','.join(jobs),'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,ReqMem,NodeList'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=15)
tasks={};errors={};gpu={}
for p in sorted((r/'tasks').glob('*/controls/RESULT.json')):
 row=json.loads(p.read_text());tasks[p.parents[1].name]=row
 if row['status']!='ACCEPTED':
  for name in ('worker.log','accept.log'):
   f=p.parents[1]/'logs'/name
   if f.is_file():errors[p.parents[1].name+'/'+name]=f.read_text(errors='replace')[-16000:]
for p in sorted((r/'tasks').glob('*/controls/RUNTIME-AND-GPU.json')):
 row=json.loads(p.read_text());gpu[p.parents[1].name]={k:row[k] for k in ('GPU','CUDA_visible_devices','torch','source_contract_sha256')}
stop=json.loads((r/'controls/STOP.json').read_text()) if (r/'controls/STOP.json').exists() else None
print(json.dumps({'dispatch':d,'queue':q.stdout,'queue_returncode':q.returncode,'scheduler':a.stdout,'scheduler_returncode':a.returncode,
 'tasks':tasks,'verified_GPU_metadata':gpu,'STOP':stop,'failed_stderr':errors,'scientific_aggregates_or_effects_read':False}))
''')
    write_new(DOC/'campaign'/('OBSERVATION-'+label+'.json'),r);print(json.dumps(r,indent=2))

if __name__=='__main__':main()
