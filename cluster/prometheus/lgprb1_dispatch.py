"""Single-use cluster-resident serial execution; fail closed, no restart path."""
import argparse,json,os,subprocess,time
from pathlib import Path
import lgprb1_contract as c
from lgp1_dispatch import Slurm as OldSlurm

class Slurm(OldSlurm):
    def submit(self,spec):
        args=['sbatch','--parsable','--no-requeue','--account=superworld','--cpus-per-task=4',
            '--mem='+('24G' if spec['gpu'] else '8G'),'--time='+str((spec['seconds']+59)//60),
            '--partition='+('a6000' if spec['gpu'] else 'defq'),'--qos='+('normal-a6000' if spec['gpu'] else 'normal'),
            '--job-name=lgprb1-'+spec['name'],'--output='+str(self.root/('slurm-'+spec['name']+'-%j.out')),
            '--error='+str(self.root/('slurm-'+spec['name']+'-%j.err'))]
        if spec['gpu']:args+=['--gres=gpu:1']
        args += [str(self.source/'cluster/prometheus/run_lgprb1.sh'),str(self.source),str(self.approval),str(self.root),spec['name']]
        r=subprocess.run(args,text=True,capture_output=True,timeout=60)
        c.require(r.returncode==0 and r.stdout.strip().split(';')[0].isdigit(),'Ambiguous sbatch; no retry: '+r.stderr)
        return r.stdout.strip().split(';')[0]

def execute(specs,scheduler,record,check,stage,bytes_check):
    completed=[];gpu=cpu=0
    for i,spec in enumerate(specs):
        bytes_check()
        c.require(gpu+sum(s['seconds'] for s in specs[i:] if s['gpu'])<=c.CAPS['gpu_seconds'] and
            cpu+sum(s['seconds'] for s in specs[i:] if not s['gpu'])<=c.CAPS['cpu_seconds'],'Full remaining reservations')
        if i==2:stage('compatibility',completed)
        if spec['kind']=='analysis':stage('analysis',completed)
        record(dict(event='claim',task=spec,reserved_seconds=spec['seconds']))
        try:job=scheduler.submit(spec)
        except BaseException:
            record(dict(event='submission_unresolved',task=spec));raise
        record(dict(event='submitted',job=job,task=spec))
        terminal=scheduler.wait(job,spec);seconds=int(terminal['seconds'])
        if spec['gpu']:gpu+=seconds
        else:cpu+=seconds
        row=dict(event='terminal',job=job,task=spec,**terminal,gpu_seconds=gpu,cpu_seconds=cpu)
        record(row);completed.append(row)
        c.require(seconds<=spec['seconds'] and terminal['state']=='COMPLETED' and terminal['exit_code']=='0:0','Failure preserved; no retry or changed case')
        check(spec)
    return dict(completed=completed,gpu_seconds=gpu,cpu_seconds=cpu,new_jobs=387,new_main_episodes=768,reused_main_episodes=384)

def main():
    began=time.monotonic();cpu_began=time.process_time()
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--approval',type=Path,required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    approval,specs=c.authorize(a.source,a.approval)
    c.require(a.run.parent.resolve()==c.ROOT/'experiments'/c.NAME and a.run.name=='run-'+approval['source_sha256'][:16],'Exact new namespace')
    c.require(not a.run.parent.exists(),'Prior attempt/namespace; no automatic recovery')
    old=subprocess.check_output(['sacct','-X','-n','-P','--starttime=2026-09-19','--format=JobName%100'],text=True)
    c.require(not any(s.startswith('lgprb1-') for s in old.splitlines()),'Prior allocation; stop for reconciliation')
    c.verify_reuse(a.source)
    a.run.mkdir(parents=True,exist_ok=False);c.write(a.run/'APPROVAL.json',approval)
    with (a.run/'PRE-EVALUATION-FREEZE.json').open('xb') as f:f.write((c.OLD_RUN/'PRE-EVALUATION-FREEZE.json').read_bytes())
    c.write(a.run/'REUSE-VERIFIED.json',dict(source_sha256=c.OLD_SOURCE_SHA,freeze_sha256=c.FREEZE_SHA,reused_episodes=384,unix=time.time()))
    c.write(a.run/'CONTROLLER-PROCESS.json',dict(pid=os.getpid(),unix=time.time(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]))
    def record(row):
        row['unix']=time.time()
        with (a.run/'DISPATCH.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    def check(spec):
        from lgprb1_analysis import task
        return task(a.run/spec['name'],spec)
    def stage(name,rows):
        if name=='compatibility':
            c.require(len(rows)==2,'Both families compatibility first')
            c.write(a.run/'COMPATIBILITY-PASSED.json',dict(unix=time.time(),seals={s['name']:c.sha(a.run/s['name']/'sha256.txt') for s in specs[:2]},scientific_selection=False))
        else:
            c.require(len(rows)==386,'All main and compatibility allocations')
            c.write(a.run/'PRE-ANALYSIS-ACCOUNTING.json',dict(jobs=rows,reused_30_rounds_charged_to='LGP1 historical record only',new_optimizer_updates=0))
    try:
        result=execute(specs,Slurm(a.source,a.run/'APPROVAL.json',a.run),record,check,stage,lambda:c.storage(a.source,a.run))
        result['storage']=c.storage(a.source,a.run)
        result.update(controller_wall_seconds=time.monotonic()-began,controller_cpu_seconds=time.process_time()-cpu_began)
        c.write(a.run/'COMPUTE-COMPLETE.json',result)
    except BaseException as e:
        c.write(a.run/'STOP.json',dict(error=str(e),automatic_retry=False,action='Preserve and reconcile all dispatched allocations and reservations.'));raise

if __name__=='__main__':main()
