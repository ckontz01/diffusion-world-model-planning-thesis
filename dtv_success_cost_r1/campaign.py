"""Control-only R1 continuation. Original workers and scientific settings unchanged."""
import argparse
import json
import os
import re
import time
import subprocess
from pathlib import Path
from dtv_success_cost.common import *
from dtv_success_cost.campaign import commands as original_commands, footprint
from dtv_efficiency_r1.campaign import LIVE, TERMINAL, ControlFault, invoke
from dtv_success_cost_r1.common import recovery_gate, verify_resolution, RECOVERY

def pending_placeholder(job,row,state):
    if row[1]!='allocation' or state!='PENDING' or row[3:5]!=['0:0','0']:return False
    if job['gpu']:return row[6] in ('gpu09','')
    # CPU grace is limited to the declared remaining analysis stage.
    return job['id']=='analysis' and row[5]=='' and (row[6]=='' or re.fullmatch(r'[a-zA-Z][a-zA-Z0-9.-]*',row[6]) is not None)

def dispatch(job,append,charges,call=invoke,clock=time.monotonic,sleep=time.sleep,check=lambda:None):
    append(dict(event='submission_intent',task=job['id']))
    try:r=call(job['command'],30)
    except subprocess.TimeoutExpired as e:
        append(dict(event='submission_response',task=job['id'],error=repr(e),ambiguous=True));raise ControlFault('ambiguous submission; preserve and reconcile, never repeat',dict(charges))
    append(dict(event='submission_response',task=job['id'],stdout=r.stdout,stderr=r.stderr,returncode=r.returncode))
    allocation=r.stdout.strip().split(';')[0]
    if r.returncode or not allocation.isdigit():raise ControlFault('ambiguous submission, no retry',dict(charges))
    began=clock();seen=False;placeholder=0
    append(dict(event='submitted',task=job['id'],allocation_id=allocation))
    while True:
        check()
        try:r=call(['sacct','-n','-P','-X','-j',allocation,'--format=JobIDRaw,JobName%200,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'],10)
        except subprocess.TimeoutExpired as e:
            append(dict(event='scheduler',allocation_id=allocation,error=repr(e)));raise ControlFault('unresolved scheduler timeout',dict(charges))
        append(dict(event='scheduler',allocation_id=allocation,stdout=r.stdout,stderr=r.stderr,returncode=r.returncode))
        if r.returncode:raise ControlFault('unresolved scheduler command failure',dict(charges))
        rows=[s.split('|') for s in r.stdout.splitlines() if s.strip()]
        if not rows:
            if seen or clock()-began>=60:raise ControlFault('bounded initial accounting visibility exhausted',dict(charges))
            sleep(min(5,60-(clock()-began)));continue
        if len(rows)!=1:raise ControlFault('unexpected accounting rows',dict(charges))
        row=rows[0]
        if row[-1]=='':row.pop()
        if len(row)!=7 or row[0]!=allocation:raise ControlFault('wrong allocation identity',dict(charges))
        state=row[2].split()[0]
        # Bounded incomplete CPU/GPU placeholder only; the raw response is preserved.
        if pending_placeholder(job,row,state):
            placeholder+=1
            if placeholder>8 or clock()-began>=60:raise ControlFault('pending identity grace exhausted',dict(charges))
            sleep(5);continue
        if state in TERMINAL:
            if not row[4].isdigit():raise ControlFault('invalid terminal charge',dict(charges))
            elapsed=int(row[4]);kind='gpu' if job['gpu'] else 'cpu';charges[kind]+=elapsed
            terminal=dict(event='terminal',task=job['id'],allocation_id=allocation,state=state,exit=row[3],elapsed_seconds=elapsed,charges=dict(charges),node=row[6],resources=row[5]);append(terminal)
            # Charge genuine terminal work before rejecting conflicting metadata.
            if row[1]!='dtveff1-'+job['id'] or state!='COMPLETED' or row[3]!='0:0' or elapsed>job['wall_seconds']:raise ControlFault('terminal fault charged and preserved',dict(charges))
            if job['gpu'] and (row[6] not in ('gpu09','gpu09.cluster') or 'gres/gpu=1' not in row[5]):raise ControlFault('wrong hardware/allocation charged',dict(charges))
            resources=dict(x.split('=',1) for x in row[5].split(',') if '=' in x)
            if job['gpu'] and resources.get('gres/gpu')!='1':raise ControlFault('wrong GPU allocation cardinality charged',dict(charges))
            if not job['gpu'] and 'gres/gpu' in row[5]:raise ControlFault('analysis unexpectedly used GPU',dict(charges))
            return terminal
        if row[1]!='dtveff1-'+job['id'] or state not in LIVE:raise ControlFault('nonterminal identity/state fault',dict(charges))
        if not seen and clock()-began>60:raise ControlFault('initial visibility deadline exceeded',dict(charges))
        seen=True;sleep(5)

def commands(c,worker_approval,recovery_approval,run):
    jobs=original_commands(c,worker_approval,run)[1:]
    analysis=jobs[-1]
    body=analysis['command'][-1]
    body=body.replace('PYTHONPATH='+str(ROOT),'PYTHONPATH='+str(RECOVERY)+':'+str(ROOT))
    body=body.replace('-m dtv_success_cost.worker','-m dtv_success_cost_r1.analysis_entry')
    body+=' --recovery-approval='+__import__('shlex').quote(str(recovery_approval))
    analysis['command'][-1]=body
    return jobs

def begin(run,resolution):
    location=Path(run)/'recovery-r1'
    if (location/'STARTED.json').exists() or (location/'DISPATCH-R1.jsonl').exists():
        raise RuntimeError('R1 already started/ambiguous; successful or live tasks are never repeated')
    # Even a never-started adapter cannot repeat an unexplained existing output.
    c=load(DOC/'BINDINGS.json')
    if any((Path(run)/identity).exists() for identity in [j['id'] for j in c['jobs']]+['analysis']):
        raise RuntimeError('remaining task has existing evidence; reconcile rather than submit')
    write(location/'STARTED.json',dict(unix=time.time(),carried_allocation='312920',cpu_seconds=178,
                                     resolution_sha256=sha(resolution),automatic_retry=False))

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',type=Path,required=True);p.add_argument('--submit',action='store_true');a=p.parse_args()
    c,r=recovery_gate(a.approval);run=run_namespace(c);location=run/'recovery-r1'
    jobs=commands(c,Path(r['worker_approval']),a.approval,run)
    if not a.submit:
        print(json.dumps(dict(execute=False,remaining_tasks=len(jobs),carried_cpu_seconds=178,
                              first_command=jobs[0]['command'],analysis_command=jobs[-1]['command'])));return
    verify_resolution(run,r);begin(run,location/'STOP-RESOLUTION.json');charges=dict(gpu=0,cpu=178)
    def append(row):
        row=dict(row,recorded_unix=time.time())
        with (location/'DISPATCH-R1.jsonl').open('a') as f:
            f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
        if (location/'DISPATCH-R1.jsonl').stat().st_size>c['control_bytes']:raise RuntimeError('control cap; retained')
    append(dict(event='carried_preflight_accepted',task='preflight',allocation_id='312920',elapsed_seconds=178,
                seal_sha256=sha(run/'preflight/SEAL.json'),resolution_sha256=sha(location/'STOP-RESOLUTION.json'),
                original_dispatch_accepted=False))
    try:
        for i,j in enumerate(jobs):
            verify_resolution(run,r)
            footprint(c,run,jobs[i:])
            if charges['gpu']+sum(v['wall_seconds'] for v in jobs[i:] if v['gpu'])>c['gpu_seconds'] or charges['cpu']+sum(v['wall_seconds'] for v in jobs[i:] if not v['gpu'])>c['cpu_seconds']:
                raise RuntimeError('unchanged full-future compute reservation exhausted')
            terminal=dispatch(j,append,charges,check=lambda:footprint(c,run,jobs[i+1:]))
            from dtv_success_cost.accept import accept_worker
            if j['gpu']:accept_worker(c,j,run,terminal['allocation_id'])
            else:
                read_seal(run/j['id'],j['id'])
                if sum(p.stat().st_size for p in (run/j['id']).rglob('*') if p.is_file())>j['output_bytes']:
                    raise RuntimeError('complete CPU-stage output cap')
            append(dict(event='accepted',task=j['id'],seal_sha256=sha(run/j['id']/'SEAL.json')))
            if i==8:append(dict(event='technical_tranche_passed',included_workers=9,included_episodes=72,scientific_selection=False))
        from dtv_success_cost_r1.accept import accounting
        write(run/'COMPUTE-COMPLETE.json',dict(**accounting(run,c,True),bindings_sha256=sha(DOC/'BINDINGS.json'),lineage='R1'))
    except Exception as e:
        write(location/'STOP-R1.json',dict(error=repr(e),charges=charges,automatic_retry=False));raise
if __name__=='__main__':main()

