"""Read-only exact final CPU dispatch/control observation; no result payloads."""
import ast,json,sys
from .common import DOC,identity
from .transport_v2 import call

CODE=r'''
import hashlib,json,subprocess,sys,time
from pathlib import Path
d=json.load(sys.stdin);cp=Path(d['contract_path']);raw=cp.read_bytes()
if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=d['contract']:raise ValueError('exact frozen contract')
c=json.loads(raw);ops=Path(c['rc1_final']['operational_root']);dispatch=json.loads((ops/'submission/DISPATCH.json').read_text())
if dispatch['contract']!=d['contract'] or dispatch['staged_members']!=c['staged_members']:raise ValueError('actual exact dispatch')
job=dispatch['job_id']
if not job.isdigit():raise ValueError('exact numeric dispatch')
accounting=subprocess.check_output(['sacct','-X','-n','-P','-j',job,'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=10)
rows=[x.split('|') for x in accounting.splitlines() if x]
if len(rows)!=1 or len(rows[0])!=7 or rows[0][:2]!=[job,job]:raise ValueError('one exact final CPU accounting row')
names=['ENTRY-VERIFIED.json','PHASE-analysis.json','PHASE-independent_acceptance.json','PHASE-archive.json','ANALYSIS-CLOSED.json','CPU-PHASES-COMPLETE.json','SUPERVISOR-CLOSED.json','CPU-FAILED.json']
controls={}
for name in names:
 p=ops/'cpu/controls'/name
 if not p.exists():continue
 if p.is_symlink() or not p.is_file() or p.stat().st_size>200000:raise ValueError('bounded ordinary technical control')
 b=p.read_bytes();v=json.loads(b);r={'identity':{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}}
 for k in ('status','phase','job_id','error','traceback'):
  if k in v:r[k]=v[k]
 controls[name]=r
diagnostic=None
if rows[0][2] not in ('RUNNING','PENDING','COMPLETED'):
 p=ops/'cpu/supervisor.log'
 if p.exists():
  if p.is_symlink() or not p.is_file() or p.stat().st_size>64000:raise ValueError('bounded native supervisor technical log')
  diagnostic=p.read_text()
print(json.dumps({'status':'EXACT_FINAL_CPU_TECHNICAL_OBSERVATION','captured_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'job_id':job,'contract':d['contract'],'scheduler_raw':accounting,'controls':controls,'native_supervisor_diagnostic':diagnostic,'scientific_values_read':False}))
'''

def main():
    label=sys.argv[1]
    cp=DOC/'FINAL-CONTRACT-002.json';c=json.loads(cp.read_text())
    ast.parse(CODE,feature_version=(3,6))
    result=call(label,CODE,{'contract_path':c['rc1_final']['run']+'/source/FINAL-CONTRACT.json','contract':identity(cp)},seconds=25)
    print(json.dumps(result))

if __name__=='__main__':main()
