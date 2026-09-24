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
    r.require([x['job'] for x in ctx.baseline['rows']]==['304589','304591','304593'] and [x['seconds'] for x in ctx.baseline['rows']]==[0,8,11],'Historical charges and successful fit changed')
    return r.storage_check(ctx,finished)

def accept_existing(ctx):
    key='fit-pair1-joint';root=ctx.run/key
    r.c.verify_seal(root,ctx.jobs[0])
    r.require(r.sha(root/'SEAL.json')==ctx.baseline['fit_seal_sha256'],'R2 fit seal changed')
    technical=r.read(root/'TECHNICAL.json')
    r.require(technical['passed'] is True and technical['job']=='304593' and technical['seed']==94411 and technical['updates']==192 and technical['recovery_approval']==r.sha(ctx.r2_control/'EXECUTION-APPROVAL.json'),'Exact R2 successful fit')
    r.require(r.read(ctx.run/'submissions-r2'/(key+'.json'))['job']=='304593','Exact R2 supplier')
    receipt=dict(unix=time.time(),key=key,job='304593',seal=ctx.baseline['fit_seal_sha256'],technical=r.sha(root/'TECHNICAL.json'),approval=ctx.approval_sha,prior_audit=r.sha(r.ROOT/'BASELINE-TRANSPORT.json'),recomputed=False)
    r.write(ctx.control/'ACCEPTED-EXISTING.json',receipt)

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);a=p.parse_args();ctx=r.Context(a.approval)
    r.baseline(ctx,exact_run=True);r.guard(ctx)
    r.require(not (ctx.run/'submissions-r3').exists(),'Exclusive continuation submissions')
    r.require(not any((ctx.run/j['key']).exists() for j in ctx.jobs[1:]),'No existing successful task may repeat')
    accept_existing(ctx)
    (ctx.run/'submissions-r3').mkdir()
    r.write(ctx.control/'HISTORICAL-RESOLUTION.json',dict(unix=time.time(),instruction=r.sha(r.ROOT/'INSTRUCTION.txt'),approval=ctx.approval_sha,prior_stops=[ctx.baseline['original_stop_sha256'],ctx.baseline['r1_stop_sha256'],ctx.baseline['r2_stop_sha256']],prior_jobs=['304589','304591','304593'],carried_success='fit-pair1-joint',prior_attempts=3,new_attempts_max=8196,total_attempts_max=8199,prior_gpu_seconds=0,prior_cpu_seconds=19,science_changed=False))
    d.campaign(ctx.auth,ctx.control,Scheduler(ctx),jobs=ctx.jobs[1:],accept=lambda j,row:accepted(ctx,j,row),reuse=lambda:r.c.verify_seal(ctx.run/'reused'),freeze=lambda:models.freeze(ctx.run,r.SCIENCE),gate=lambda:accept.gate(ctx.run,ctx.jobs),storage_check=lambda done:reserve_with_prior(ctx,done))

if __name__=='__main__':main()
