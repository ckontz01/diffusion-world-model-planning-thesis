"""Fixed additional-28 dispatch; scheduler/size metadata only until sealed completion."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

REFS=(1269,582,525,722,567,716,630,1066,1074,1565,70,867,221,905,1287,621,428,288,1488,757,641,855,1280,420,860,98,886,432,181,783,706,989)
LIMIT_SECONDS=7200
JOB_SECONDS=300
LIMIT_BYTES=1_000_000_000
RESERVE_BYTES=64_000_000
PRIOR_ALLOCATION_SECONDS=11  # Preserved pre-model packaging failure301003.

def require(ok,msg):
    if not ok:raise RuntimeError(msg)

def allowed(seconds,size):
    return 0<=seconds<=LIMIT_SECONDS-JOB_SECONDS and 0<=size<=LIMIT_BYTES-RESERVE_BYTES

def size_bytes(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())

def command(*args):
    return subprocess.check_output(args,universal_newlines=True).strip()

def main(src,run,audit):
    require(not (run/'DISPATCH.jsonl').exists(),'Refuse controller restart/duplicate dispatch')
    run.mkdir(exist_ok=True)
    namespace='diffusion-bottleneck-v1|development-selection|2026-09-13'
    selected=sorted(range(1600),key=lambda i:(hashlib.sha256(f'{namespace}|{i}'.encode()).hexdigest(),i))[:32]
    require(tuple(selected)==REFS,'Selection differs')
    elapsed=PRIOR_ALLOCATION_SECONDS;jobs=[]
    with (run/'DISPATCH.jsonl').open('x',buffering=1) as log:
        def record(event,**kw):
            log.write(json.dumps({'event':event,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw},sort_keys=True)+'\n')
        record('prior_allocation_charged',job_id='301003',seconds=PRIOR_ALLOCATION_SECONDS)
        for index in range(8,64):
            size=size_bytes(run)
            require(allowed(elapsed,size),'Cost/storage reservation exhausted; stop without dispatch')
            jid=command('sbatch','--parsable','--account=superworld','--partition=a6000','--qos=normal-a6000',
                '--cpus-per-task=4','--mem=24G','--gres=gpu:1','--time=00:05:00',
                '--job-name=bottleneck-extension',f'--output={run}/slurm-%j.out',f'--error={run}/slurm-%j.err',
                str(src/'cluster/prometheus/run_diffusion_bottleneck_extension.sh'),str(src),str(run),str(audit),str(index))
            require(jid.isdigit(),'Ambiguous submission; stop and inspect, never retry')
            record('submitted',job_id=jid,index=index,reference=REFS[index//2],repeat=index%2,
                   completed_allocation_seconds=elapsed,bytes_before=size)
            jobs.append(jid)
            while True:
                time.sleep(15)
                current=size_bytes(run)
                if current>LIMIT_BYTES:
                    command('scancel',jid);record('storage_stop',job_id=jid,bytes=current)
                    raise RuntimeError('Storage watermark exceeded; exact current job cancelled')
                status=command('sacct','-X','-n','-P','-j',jid,'--format=JobID,State,ExitCode,ElapsedRaw')
                rows=[x.split('|') for x in status.splitlines() if x.split('|')[0]==jid]
                require(len(rows)<=1,'Ambiguous scheduler identity')
                if not rows:continue
                _,state,code,seconds=rows[0][:4]
                if state in ('PENDING','RUNNING','CONFIGURING','COMPLETING','SUSPENDED'):continue
                record('terminal',job_id=jid,state=state,exit_code=code,elapsed_seconds=int(seconds),bytes=current)
                require(state=='COMPLETED' and code=='0:0','Failed exact job '+jid+'; no further dispatch')
                elapsed+=int(seconds)
                require(elapsed<=LIMIT_SECONDS,'Aggregate allocation cap exceeded')
                break
        record('complete',jobs=jobs,completed_allocation_seconds=elapsed,bytes=size_bytes(run))
    with (run/'DISPATCH-COMPLETE.json').open('x') as f:
        json.dump({'all_56_completed':True,'job_ids':jobs,'allocation_seconds':elapsed,
                   'bytes':size_bytes(run),'new_reference_count':28,'reuse_reference_count':4},f,sort_keys=True,indent=2)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('src','run','audit'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();main(a.src,a.run,a.audit)
