"""Prepared fail-stop serial dispatcher; researcher approval required to run.

Never run by tests. An interrupted/ambiguous submission requires manual diagnosis.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path
from single_anchor_ranking_host import REFS,check_approval,require,require_sha,verify_source,size_bytes

LIMIT_SECONDS=14400
JOB_SECONDS=900
LIMIT_BYTES=2_000_000_000
RESERVE_BYTES=64_000_000


def allowed(charged,size,outstanding=0):
    return (min(charged,size,outstanding)>=0 and
            charged+outstanding+JOB_SECONDS<=LIMIT_SECONDS and size+RESERVE_BYTES<=LIMIT_BYTES)


def command(*args):
    return subprocess.check_output(args,universal_newlines=True).strip()


def dispatch(src,run,approval,source_sha,protocol_sha):
    verify_source(src,source_sha)
    protocol=src/'docs/single-anchor-ranking-20260914/PROTOCOL.md'
    require_sha(protocol,protocol_sha);check_approval(approval,source_sha,protocol_sha)
    required=Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/single-anchor-ranking-20260914')
    require(required in run.resolve().parents and not run.exists(),'New isolated run root required')
    run.mkdir(parents=True,exist_ok=False)
    charged=0;jobs=[]
    with (run/'DISPATCH.jsonl').open('x',buffering=1) as log:
        def event(kind,**fields):log.write(json.dumps(dict(event=kind,**fields),sort_keys=True)+'\n')
        # First ref's two repeats are the bounded technical pilot, NOT extra cases.
        # Per-job runner assertions govern continuation; no partial outcomes read.
        for index in range(64):
            require(allowed(charged,size_bytes(run)),'Resource reservation exhausted')
            event('reserved',index=index,charged_seconds=charged,reserved_seconds=JOB_SECONDS)
            job=command('sbatch','--parsable','--account=superworld','--partition=a6000','--qos=normal-a6000',
                '--cpus-per-task=4','--mem=24G','--gres=gpu:1','--time=00:15:00',
                '--job-name=single-anchor-ranking',f'--output={run}/slurm-%j.out',f'--error={run}/slurm-%j.err',
                str(src/'cluster/prometheus/run_single_anchor_ranking.sh'),str(src),str(run),str(approval),
                source_sha,protocol_sha,str(index))
            require(job.isdigit(),'Ambiguous submission: stop, no retry')
            jobs.append(job);event('submitted',job=job,index=index,reference=REFS[index//2],repeat=index%2)
            while True:
                time.sleep(15)
                size=size_bytes(run)
                if size>LIMIT_BYTES:
                    command('scancel',job);event('storage_stop',job=job,bytes=size,reservation_seconds=JOB_SECONDS)
                    raise RuntimeError('Storage stop; retain full reservation pending final sacct charge')
                raw=command('sacct','-X','-n','-P','-j',job,'--format=JobID,State,ExitCode,ElapsedRaw')
                rows=[r.split('|') for r in raw.splitlines() if r.split('|')[0]==job]
                require(len(rows)<=1,'Ambiguous accounting; stop with active reservation')
                if not rows:continue
                _,state,code,seconds=rows[0][:4]
                if state in ('PENDING','RUNNING','CONFIGURING','COMPLETING','SUSPENDED'):continue
                charged+=int(seconds)
                event('terminal',job=job,state=state,code=code,seconds=int(seconds),charged_seconds=charged,bytes=size)
                require(state=='COMPLETED' and code=='0:0','Failed job charged; stop, no retry')
                require(charged<=LIMIT_SECONDS,'Aggregate cap exceeded')
                break
        with (run/'DISPATCH-COMPLETE.json').open('x') as f:
            json.dump(dict(all_64_completed=True,jobs=jobs,allocation_seconds=charged,bytes=size_bytes(run)),f,indent=2)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('src','run','approval'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source-sha',required=True);p.add_argument('--protocol-sha',required=True)
    a=p.parse_args();dispatch(a.src,a.run,a.approval,a.source_sha,a.protocol_sha)
