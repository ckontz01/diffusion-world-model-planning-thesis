import json
from .common import DOC,RUN,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    r=ssh('RUN='+repr(RUN)+'\n'+'''
import json,pathlib,subprocess
r=pathlib.Path(RUN);controls={}
for p in sorted((r/'controls').glob('*.json')):
 if p.name.startswith(('SBATCH-','SUBMISSION-','RELEASE-','SUBMIT-')) or p.name=='DAG-DISPATCH.json':controls[p.name]=json.loads(p.read_text())
known=controls.get('SUBMISSION-ERROR.json',{}).get('known_job_ids',{})
queue=subprocess.check_output(['squeue','-u',str(__import__('os').getuid()),'-h','-o','%i|%j|%T|%R'],universal_newlines=True,timeout=10)
rows=[line for line in queue.splitlines() if 'wm-a2-v4-' in line]
acct=''
if known:acct=subprocess.check_output(['sacct','-X','-n','-P','-j',','.join(known.values()),'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
print(json.dumps({'controls':controls,'known_exact_job_ids':known,'current_study_queue':rows,'scheduler':acct,'task_directories':[p.name for p in (r/'tasks').iterdir()],'scientific_results_read':False}))
''')
    write_new(DOC/'campaign/SUBMISSION-RECONCILIATION-001.json',r);print(json.dumps(r,indent=2))

if __name__=='__main__':main()
