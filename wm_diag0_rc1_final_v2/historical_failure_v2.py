"""Diagnose exact preserved traceback frames, without assuming an expression.

V1 and its failed guard/start/charge remain unchanged. This is a separately
labelled read-only metadata diagnosis, not a research rerun or resumed analysis.
"""
import ast,base64,json,shlex,subprocess,sys
from .historical_failure_v1 import READ as V1
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new

PREFIX=V1.split("log=read(t/'logs/worker.log',1000000)",1)[0]
if PREFIX==V1:raise ValueError('exact preserved V1 pre-log source boundary')
READ=PREFIX+r'''
log=read(t/'logs/worker.log',1000000).decode('utf8',errors='strict')
frames=[]
for m in re.finditer(r'File "([^"\n]+)", line ([0-9]+), in ([^\n]+)\n[ \t]*([^\n]*)',log):
 frames.append({'file':m.group(1),'line':int(m.group(2)),'function':m.group(3),'expression':m.group(4)[:1000]})
if not frames or len(frames)>50:raise ValueError('bounded recorded traceback metadata required')
classes=[x.split(':',1)[0] for x in log.splitlines() if x.startswith(('AssertionError:','ValueError:','RuntimeError:','TypeError:'))]
if not classes or len(classes)>8:raise ValueError('recorded exception class metadata required')
print(json.dumps({'status':'PRESERVED_FAILURE_TRACEBACK_METADATA_DIAGNOSED_NOT_YET_ARITHMETIC_DISPOSITION',
 'job_id':'317171','array_job_id':'317164','frames':frames,'exception_classes':classes,
 'evidence':evidence,'scheduler_calls':0,'filesystem_mutations':0,'research_calls':0,
 'numerical_array_values_read_or_released':False,'scientific_outcomes_or_quality_read':False,
 'final_gate_ready':False},sort_keys=True))
'''


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive diagnosis label')
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    target=doc/('HISTORICAL-FAILURE-V2-'+label+'.json');started=doc/('HISTORICAL-FAILURE-V2-'+label+'.started.json')
    if target.exists() or started.exists():raise FileExistsError('no repeat/ambiguous diagnosis')
    failed=ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/LOCAL-HISTFAILUREAUTH001.json'
    f=json.loads(failed.read_text())
    if f['status']!='CHILD_NONZERO' or 'expected uncached numerical-reference traceback, not an assumed failure point' not in f['stdout']:raise ValueError('exact diagnosed metadata-guard rejection')
    ast.parse(READ,feature_version=(3,6))
    write_new(started,{'source':identity(__file__),'V1_preimage':identity(PathV1()),'original_failed_receipt':identity(failed),'scope':'stack frame metadata only, no assumed reference expression'})
    encoded=base64.b64encode(READ.encode()).decode()
    remote='timeout --kill-after=1s 15s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    cmd=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','20s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','ConnectionAttempts=1','prometheus',remote]
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=22)
    if p.returncode:raise RuntimeError('bounded traceback metadata unavailable; '+p.stderr.decode(errors='replace')[-2000:])
    if len(p.stdout)>16000:raise ValueError('bounded metadata stdout')
    z=json.loads(p.stdout);z['original_failed_receipt']=identity(failed)
    write_new(target,z,limit=20000);print(json.dumps(z))


def PathV1():
    from pathlib import Path
    return Path(__file__).parent/'historical_failure_v1.py'


if __name__=='__main__':main()
