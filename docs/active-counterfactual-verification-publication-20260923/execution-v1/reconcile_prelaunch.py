"""One read-only namespace/scheduler reconciliation after local CreateProcess failure.

This is not a preflight retry or a launch. No runtime/checkpoint/reference load,
source transfer, approval mutation, controller start or sbatch call is made.
"""
import json
import subprocess
import time
import operate as o

CODE=r'''
import json,os,subprocess,time
from pathlib import Path
root='/lustreFS/data/superworld/ckontzias/thesis'
paths={'source':root+'/snapshots/active-counterfactual-verification-bindings-v1-bf3f4558f2cdfbca',
       'control':root+'/staging/active-counterfactual-verification-bindings-v1-bf3f4558f2cdfbca',
       'run':root+'/experiments/active-counterfactual-verification-pilot-v1/run-bf3f4558f2cdfbca'}
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
a=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--format=JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw,AllocTRES'],capture_output=True,text=True,timeout=30)
assert q.returncode==a.returncode==0,(q.stderr,a.stderr)
print(json.dumps({'unix':time.time(),'path_exists':{k:Path(v).exists() for k,v in paths.items()},'paths':paths,
 'active_acv0b1_rows':[v for v in q.stdout.splitlines() if 'acv0b1-' in v],
 'accounted_acv0b1_rows':[v for v in a.stdout.splitlines() if 'acv0b1-' in v],
 'scope':'Read-only exact namespace and scheduler reconciliation; no preflight retry or research action'}))
'''

if __name__=='__main__':
    path=o.HERE/'PRELAUNCH-RECONCILIATION.json'
    with path.open('xb') as f:
        start=time.time()
        try:
            p=subprocess.run(o.SSH+['python3.9','-B','-S','-'],input=CODE.encode(),capture_output=True,timeout=90)
            result={'start_unix':start,'end_unix':time.time(),'returncode':p.returncode,
                    'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')}
        except BaseException as e:result={'start_unix':start,'end_unix':time.time(),'returncode':125,'error':repr(e)}
        f.write(json.dumps(result,indent=2).encode()+b'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(result['returncode'])
