"""One-use serial dispatch. Ambiguity/failure is terminal; no retry/resume path."""
import argparse,json,subprocess,time
from pathlib import Path
import lgp1_contract as c
from lgp1_verify import task as verify_task

class Controller:
    def __init__(self,specs,scheduler,record,bytes_used,check,freeze,source_bytes=0):
        self.specs=specs;self.scheduler=scheduler;self.record=record;self.bytes_used=bytes_used
        self.check=check;self.freeze=freeze;self.source_bytes=source_bytes
        self.gpu=self.cpu=0;self.started=False;self.completed=[]
    def run(self):
        c.require(not self.started,'No automatic restart/resumption');self.started=True
        for i,spec in enumerate(self.specs):
            c.require(self.bytes_used()+self.source_bytes<c.CAPS['worker_bytes']+c.CAPS['control_bytes'],'Storage stop')
            c.require(self.gpu+sum(t['seconds'] for t in self.specs[i:] if t['gpu'])<=c.CAPS['gpu_seconds'],'GPU reservation cap')
            c.require(self.cpu+sum(t['seconds'] for t in self.specs[i:] if not t['gpu'])<=c.CAPS['cpu_seconds'],'CPU reservation cap')
            if spec['kind']=='technical' and not any(x['task']['kind']=='technical' for x in self.completed):
                self.freeze('models',self.completed)
            if spec['kind']=='analysis': self.freeze('evaluation',self.completed)
            # Claim written BEFORE submission. Any exception after this point
            # permanently consumes this controller; unresolved reservation remains.
            self.record(dict(event='claim',task=spec,reserved_seconds=spec['seconds']))
            try: job=self.scheduler.submit(spec)
            except BaseException as e:
                self.record(dict(event='ambiguous_submission',task=spec,reserved_seconds=spec['seconds'],error=str(e)))
                raise RuntimeError('Submission ambiguous; reconcile manually, never retry') from e
            self.record(dict(event='submitted',task=spec,job=job))
            try: terminal=self.scheduler.wait(job,spec)
            except BaseException as e:
                self.record(dict(event='unresolved_live_or_terminal',task=spec,job=job,reserved_seconds=spec['seconds'],error=str(e)))
                raise
            seconds=int(terminal['seconds'])
            if spec['gpu']: self.gpu+=seconds
            else: self.cpu+=seconds
            row=dict(event='terminal',task=spec,job=job,**terminal,gpu_seconds=self.gpu,cpu_seconds=self.cpu)
            self.record(row);self.completed.append(row)
            c.require(seconds<=spec['seconds'] and self.gpu<=c.CAPS['gpu_seconds'] and self.cpu<=c.CAPS['cpu_seconds'],'Resource overrun')
            c.require(terminal['state']=='COMPLETED' and terminal['exit_code']=='0:0','Technical failure; preserved; no retry')
            self.check(spec)
        return dict(jobs=len(self.completed),gpu_seconds=self.gpu,cpu_seconds=self.cpu,completed=self.completed)

class Slurm:
    def __init__(self,source,approval,run): self.source,self.approval,self.root=source,approval,run
    def submit(self,spec):
        args=['sbatch','--parsable','--no-requeue','--account=superworld','--cpus-per-task=4',
              '--mem='+('24G' if spec['gpu'] else '8G'),'--time='+str((spec['seconds']+59)//60),
              '--partition='+('a6000' if spec['gpu'] else 'defq'),'--qos='+('normal-a6000' if spec['gpu'] else 'normal'),
              '--job-name=lgp1-'+spec['name'],'--output='+str(self.root/('slurm-'+spec['name']+'-%j.out')),
              '--error='+str(self.root/('slurm-'+spec['name']+'-%j.err'))]
        if spec['gpu']: args+=['--gres=gpu:1']
        args += [str(self.source/'cluster/prometheus/run_lgp1.sh'),str(self.source),str(self.approval),str(self.root),spec['name']]
        result=subprocess.run(args,text=True,capture_output=True,timeout=60)
        c.require(result.returncode==0 and result.stdout.strip().split(';')[0].isdigit(),'Unknown sbatch outcome: '+result.stderr)
        return result.stdout.strip().split(';')[0]
    def wait(self,job,spec):
        active={'PENDING','RUNNING','CONFIGURING','COMPLETING','SUSPENDED','RESIZING'}
        while True:
            text=subprocess.check_output(['sacct','-X','-n','-P','-j',job,
                '--format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,TotalCPU'],text=True)
            lines=[x.split('|') for x in text.splitlines() if x.strip() and x.split('|')[0]==job]
            if not lines: time.sleep(30);continue
            c.require(len(lines)==1,'Ambiguous scheduler rows');r=lines[0]
            if r[1] in active: time.sleep(30);continue
            gpu=('gres/gpu=' in r[5]);c.require(gpu==spec['gpu'] and int(r[4])==4,'Allocation CPU/GPU mismatch')
            return dict(state=r[1],exit_code=r[2],seconds=int(r[3]),alloc_cpus=int(r[4]),alloc_tres=r[5],total_cpu=r[6])

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--approval',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    approved=c.authorize(a.source,a.approval)
    c.require(a.run.parent.resolve()==c.ROOT/'experiments/local-goal-proposals-20260918' and
              a.run.name=='run-'+approved['source_sha256'][:16],'Exclusive namespace')
    recovery=approved.get('recovery')
    if not recovery:c.require(not a.run.parent.exists(),'Prior study namespace exists; no prior attempt/recovery permitted')
    else:
        prior=Path(recovery['failed-run'])
        c.require(set(a.run.parent.iterdir())=={prior},'Only preserved failed run may exist')
        c.require(not a.run.exists(),'No repeated recovery namespace')
        c.require(c.sha(prior/'DISPATCH.jsonl')==recovery['ledger_sha256'] and
                  c.sha(prior/'cache/sha256.txt')==recovery['failure_seal_sha256'],'Failed-attempt identity')
        c.verify(prior/'cache')
        prior_rows=[json.loads(line) for line in (prior/'DISPATCH.jsonl').read_text().splitlines()]
        terminals=[r for r in prior_rows if r['event']=='terminal']
        c.require(len(prior_rows)==3 and len(terminals)==1 and terminals[0]['job']=='301977' and
                  terminals[0]['state']=='FAILED' and terminals[0]['seconds']==46,'Exact terminal failure')
        observed=subprocess.check_output(['sacct','-X','-n','-P','-j','301977',
                    '--format=JobID,State,ExitCode,ElapsedRaw'],text=True).strip().split('|')
        c.require(observed[:4]==['301977','FAILED','1:0','46'],'Fresh failed-job reconciliation')
        process=c.read(Path(recovery['failed-control'])/'CONTROLLER-PROCESS.json')
        c.require(not Path('/proc',str(process['pid'])).exists(),'Prior controller must be absent')
    old=subprocess.check_output(['sacct','-X','-n','-P','--starttime=2026-09-18','--format=JobName'],text=True)
    attempts=[x.split('|')[0] for x in old.splitlines() if x.startswith('lgp1-')]
    c.require(attempts==['lgp1-cache'] if recovery else not attempts,'Unexpected prior Slurm attempt')
    a.run.mkdir(parents=True,exist_ok=False)
    c.write(a.run/'APPROVAL.json',approved)
    specs=c.grid(c.read(a.source/c.DOC/'DATA-ROLES.json')['development_reference_indices'],
                 recovery['cache_seconds'] if recovery else 14400)
    def record(row):
        row['unix']=time.time()
        with (a.run/'DISPATCH.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();__import__('os').fsync(f.fileno())
    def freeze(stage,completed):
        if stage=='models':
            fits=[s for s in specs if s['kind']=='fit'];c.require(len(completed)==7,'Cache+six fits before freeze')
            for s in fits:verify_task(a.run/s['name'],s)
            c.write(a.run/'PRE-EVALUATION-FREEZE.json',dict(unix=time.time(),
                models={s['name']:c.sha(a.run/s['name']/'model.pt') for s in fits},
                seals={s['name']:c.sha(a.run/s['name']/'sha256.txt') for s in fits}))
        else:
            c.require(len(completed)==203,'Complete GPU chain before aggregate')
            c.write(a.run/'PRE-ANALYSIS-ACCOUNTING.json',dict(jobs=completed,prior_failure=recovery))
    def bytes_used():
        sizes=c.storage(a.source,a.run)
        return sizes['worker_bytes']+sizes['source_control_log_bytes']-c.size(a.source)
    controller=Controller(specs,Slurm(a.source,a.run/'APPROVAL.json',a.run),record,bytes_used,
                          lambda s:verify_task(a.run/s['name'],s),freeze,c.size(a.source))
    if recovery:
        controller.gpu=recovery['prior_gpu_seconds'];controller.cpu=recovery['prior_cpu_seconds']
        c.write(a.run/'PRIOR-FAILURE-ACCOUNTING.json',recovery)
    try:
        final=controller.run();final['storage']=c.storage(a.source,a.run);final['remote_bytes_before_archive']=c.size(a.run)+c.size(a.source)
        final['prior_failure']=recovery
        final['attempts_including_prior']=len(controller.completed)+(1 if recovery else 0)
        final['remote_bytes_before_archive']=final['storage']['total_remote_bytes']
        c.write(a.run/'COMPUTE-COMPLETE.json',final)
    except BaseException as e:
        c.write(a.run/'STOP.json',dict(error=str(e),gpu_seconds=controller.gpu,cpu_seconds=controller.cpu,
            no_retry=True,preserved_attempts=len(controller.completed)));raise

if __name__=='__main__': main()
