"""CPU analysis adapter: unchanged estimator, authenticated combined R4 ledger."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from dtv_success_cost.common import *
from dtv_success_cost.worker import namespace
from dtv_success_cost_r4.common import recovery_gate,output_root
from dtv_success_cost_r4.accept import accept_grid
from dtv_success_cost.analysis import analyze

def analysis(c,run,output):
    unique={spec['dataset']:spec for spec in c['models'].values()}
    for spec in unique.values():
        if sha(spec['dataset'])!=spec['dataset_sha256']:raise RuntimeError('dataset whole-file final readback changed')
    records,receipt=accept_grid(c,run)
    report=analyze(records,c['analysis'])
    report['worker_setup_and_authentication']={j['id']:load(output_root(run,j)/j['id']/'WORKER.json') for j in c['jobs']}
    if len(json.dumps(report,separators=(',',':')).encode())+1000000>c['analysis_bytes']:
        raise RuntimeError('full analysis output reservation')
    write(output/'REPORT.json',report);write(output/'ACCEPTANCE.json',receipt);seal(output,'analysis')

def main():
    started=time.monotonic()
    p=argparse.ArgumentParser();p.add_argument('--approval',type=Path,required=True);p.add_argument('--recovery-approval',type=Path,required=True)
    p.add_argument('--job',choices=['analysis'],required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--child',action='store_true');a=p.parse_args()
    c,r=recovery_gate(a.recovery_approval)
    if a.approval.resolve()!=Path(r['worker_approval']).resolve():raise RuntimeError('original worker capability routing changed')
    namespace(c,a)
    if os.environ.get('SLURM_JOB_NAME')!='dtveff1-analysis' or not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('CPU analysis allocation identity')
    if not a.child:
        if a.output.exists():raise RuntimeError('exclusive analysis namespace; never repeat/overwrite')
        a.output.mkdir(parents=True)
        from dtv_efficiency_r1.deadline import supervise
        command=[sys.executable,'-m','dtv_success_cost_r4.analysis_entry','--child','--approval',str(a.approval),
                 '--recovery-approval',str(a.recovery_approval),'--job','analysis','--output',str(a.output),'--run',str(a.run)]
        result=supervise(command,a.output,work_seconds=7140,started=started)
        if result['status']!='child_exited' or result['child_exit_code']!=0:raise SystemExit(1)
        (a.output/'SEAL.json').rename(a.output/'CHILD-SEAL.json');seal(a.output,'analysis');return
    try:analysis(c,a.run,a.output)
    except Exception as e:
        if not (a.output/'FAILURE.json').exists():write(a.output/'FAILURE.json',dict(error=repr(e),automatic_retry=False))
        raise
if __name__=='__main__':main()
