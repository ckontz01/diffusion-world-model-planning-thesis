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
    r.require([x['job'] for x in ctx.baseline['failed_rows']]==['304589','304591'] and [x['seconds'] for x in ctx.baseline['failed_rows']]==[0,8],'Historical charged failures changed')
    return r.storage_check(ctx,finished)

def preserve_failed_output(ctx):
    failed=ctx.run/'fit-pair1-joint';historic=ctx.run/'recovery-history/r1/fit-pair1-joint'
    r.require(failed.is_dir() and {p.name for p in failed.iterdir()}=={'FAILURE.json'} and r.sha(failed/'FAILURE.json')==ctx.baseline['inventory']['run/fit-pair1-joint/FAILURE.json']['sha256'],'Exact failed output for preservation')
    r.require(not historic.exists() and not historic.parent.exists(),'Exclusive failed-output history')
    historic.parent.mkdir(parents=True);failed.rename(historic)
    r.write(ctx.control/'FAILED-OUTPUT-RELOCATION.json',dict(unix=time.time(),source=str(failed),destination=str(historic),sha256=r.sha(historic/'FAILURE.json'),preserved=True))

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);a=p.parse_args();ctx=r.Context(a.approval)
    r.baseline(ctx,exact_run=True);r.guard(ctx)
    r.require(not (ctx.run/'submissions-r2').exists(),'Exclusive continuation submissions')
    r.require(not any((ctx.run/j['key']).exists() for j in ctx.jobs[1:]),'No existing successful task may repeat')
    preserve_failed_output(ctx)
    (ctx.run/'submissions-r2').mkdir()
    r.write(ctx.control/'HISTORICAL-RESOLUTION.json',dict(unix=time.time(),instruction=r.sha(r.ROOT/'INSTRUCTION.txt'),approval=ctx.approval_sha,prior_stops=[ctx.baseline['original_stop_sha256'],ctx.baseline['r1_stop_sha256']],failed_jobs=['304589','304591'],replacement_key='fit-pair1-joint',prior_attempts=2,new_attempts_max=8197,total_attempts_max=8199,prior_gpu_seconds=0,prior_cpu_seconds=8,science_changed=False))
    d.campaign(ctx.auth,ctx.control,Scheduler(ctx),accept=lambda j,row:accepted(ctx,j,row),reuse=lambda:r.c.verify_seal(ctx.run/'reused'),freeze=lambda:models.freeze(ctx.run,r.SCIENCE),gate=lambda:accept.gate(ctx.run,ctx.jobs),storage_check=lambda done:reserve_with_prior(ctx,done))

if __name__=='__main__':main()
