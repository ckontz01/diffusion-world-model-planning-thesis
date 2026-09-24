"""One finite continuation: preserve one failure and run the original grid once."""
import r1 as r
import argparse
import subprocess
import time
import campaign_r1 as d
import acceptance_r1 as accept
import scheduler
import models

def command(ctx,j):
    cmd=d.command(j,ctx.worker_approval,ctx.run)
    original_script=str(r.c.ROOT/'run_worker.sh');idx=cmd.index(original_script)
    cmd=cmd[:idx]+[str(r.ROOT/'run_worker.sh'),str(r.ROOT),str(ctx.control/'EXECUTION-APPROVAL.json'),str(r.c.ROOT),str(ctx.worker_approval),str(ctx.run),j['key'],str(j['gpu'])]
    for flag,suffix in (('--output=','.slurm.out'),('--error=','.slurm.err')):
        i=next(i for i,x in enumerate(cmd) if x.startswith(flag))
        cmd[i]=flag+str(r.slurm_log(ctx.run,j['key'],suffix))
    return cmd

class Scheduler(d.RealScheduler):
    def __init__(self,ctx):super().__init__(ctx.control,ctx.worker_approval,ctx.run);self.ctx=ctx
    def submit(self,spec):
        cmd=command(self.ctx,spec)
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            result=dict(command=cmd,stdout=p.stdout,stderr=p.stderr,returncode=p.returncode)
        except subprocess.TimeoutExpired as e:result=dict(command=cmd,stdout=str(e.stdout or ''),stderr=str(e.stderr or ''),returncode=124)
        r.write(self.control/(spec['key']+'.SUBMIT.json'),result)
        value=result['stdout'].strip()
        r.require(result['returncode']==0 and value.isdigit(),'AMBIGUOUS R1 submission; no retry')
        return value

def accepted(ctx,j,row):
    result=accept.worker(ctx.run,j,row,r.SCIENCE,r.APPROVAL)
    t=r.read(ctx.run/j['key']/'TECHNICAL.json')
    r.require(t['recovery_approval']==ctx.approval_sha,'Recovery worker binding')
    return result

def reserve_with_prior(ctx,finished):
    r.guard(ctx)
    # The authenticated historical failure is0 elapsed seconds, but remains attempt1.
    r.require(ctx.baseline['failed_row']['seconds']==0 and ctx.baseline['failed_row']['job']=='304589','Historical charged failure changed')
    return r.storage_check(ctx,finished)

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);a=p.parse_args();ctx=r.Context(a.approval)
    r.baseline(ctx,exact_run=True);r.guard(ctx)
    r.require(not (ctx.run/'submissions-r1').exists(),'Exclusive continuation submissions')
    r.require(not any((ctx.run/j['key']).exists() for j in ctx.jobs),'No existing task may repeat')
    (ctx.run/'submissions-r1').mkdir()
    r.write(ctx.control/'HISTORICAL-RESOLUTION.json',dict(unix=time.time(),instruction=r.sha(r.ROOT/'INSTRUCTION.txt'),approval=ctx.approval_sha,prior_stop=ctx.baseline['stop_sha256'],failed_job='304589',replacement_key='fit-pair1-joint',prior_attempts=1,new_attempts_max=8197,total_attempts_max=8198,prior_gpu_seconds=0,prior_cpu_seconds=0,science_changed=False))
    d.campaign(ctx.auth,ctx.control,Scheduler(ctx),accept=lambda j,row:accepted(ctx,j,row),reuse=lambda:r.c.verify_seal(ctx.run/'reused'),freeze=lambda:models.freeze(ctx.run,r.SCIENCE),gate=lambda:accept.gate(ctx.run,ctx.jobs),storage_check=lambda done:reserve_with_prior(ctx,done))

if __name__=='__main__':main()
