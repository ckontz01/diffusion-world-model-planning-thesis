"""Fresh exact-ID read-only reconciliation against preserved R2 identities."""
import json
from .common import DOC,R2,OLD,identity,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    raw=(R2/'RECONCILIATION-001.json').read_bytes()
    code='OLD='+repr(OLD)+'\n'+'''
import hashlib,json,pathlib,subprocess,sys,time
r=pathlib.Path(OLD);expected=json.load(sys.stdin)
def ident(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
d=json.loads((r/'controls/DISPATCH-source.json').read_text())
if d['job_id']!='317041':raise ValueError('original exact dispatch')
q=subprocess.run(['squeue','-h','-j','317041','-o','%i|%T'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
if q.stdout.strip() or (q.returncode and 'Invalid job id specified' not in q.stderr):raise RuntimeError('live/ambiguous old source allocation')
a=subprocess.check_output(['sacct','-X','-n','-P','-j','317041','--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
if a!=expected['scheduler']:raise ValueError('changed allocation accounting; reconcile before resumption')
if json.loads((r/'controls/STOP.json').read_text())!=expected['STOP']:raise ValueError('old STOP changed')
for key,x in expected['accepted_suppliers'].items():
 t=r/'tasks'/key
 if ident(t/'controls/RESULT.json')!=x['result_identity'] or ident(t/'output/MEMBERS.json')!=x['output_seal']:raise ValueError('successful supplier changed')
for name,x in expected['failed_retained'].items():
 p=r/'tasks/reacher-000'/name
 if p.is_symlink() or ident(p)!=x:raise ValueError('failed evidence changed')
queue=subprocess.check_output(['squeue','-u',str(__import__('os').getuid()),'-h','-o','%i|%j|%T'],universal_newlines=True,timeout=10)
if any('wm-a2-' in line for line in queue.splitlines()):raise RuntimeError('existing study job; no duplicate')
print(json.dumps({'status':'EXACT_OLD_ALLOCATIONS_AND_SUPPLIERS_UNCHANGED','time':time.time(),'CPU_charged':expected['CPU_total_with_preflight'],'CPU_with_full_future':expected['CPU_total_charged_plus_full_future'],'accepted_roots':60,'failed_jobs':1,'unstarted_cancelled_roots':59,'GPU_charged':0,'old_STOP_preserved':True,'scientific_aggregates_read':False}))
'''
    result=ssh(code,payload=raw);result['original_reconciliation']=identity(R2/'RECONCILIATION-001.json')
    write_new(DOC/'RECHECK-001.json',result);print(json.dumps(result))

if __name__=='__main__':main()
