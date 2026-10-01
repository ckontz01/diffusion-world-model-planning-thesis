"""Serial finite R2 continuation; preserve successes and the failed allocation."""
import argparse,json,os,shlex,time
from dtv_success_cost.common import *
from dtv_success_cost.campaign import commands as original_commands,footprint as original_footprint
from dtv_success_cost_r1.campaign import dispatch,ControlFault
from dtv_success_cost_r2.common import *
from dtv_success_cost_r2.render import ENV,VENDOR,verify_evidence

def commands(c,worker_approval,recovery_approval,run,r1_source):
    jobs=original_commands(c,worker_approval,run)[4:]
    for j in jobs:
        body=j['command'][-1]
        body=body.replace(shlex.quote('PYTHONPATH='+str(ROOT)),shlex.quote('PYTHONPATH='+str(RECOVERY)+':'+str(r1_source)+':'+str(ROOT)))
        module='worker' if j['gpu'] else 'analysis_entry'
        body=body.replace('-m dtv_success_cost.worker','-m dtv_success_cost_r2.'+module)
        body+=' --recovery-approval='+shlex.quote(str(recovery_approval))
        if j['gpu']:
            output=PurePosixPath((location(run)/'workers'/j['id']).as_posix())
            old_output=PurePosixPath((Path(run)/j['id']).as_posix())
            body=body.replace('--output '+shlex.quote(str(old_output)),'--output '+shlex.quote(str(output)))
            flags=dict(ENV,__EGL_VENDOR_LIBRARY_FILENAMES=str(VENDOR))
            body=body.replace(' env ',' env '+shlex.join([k+'='+v for k,v in flags.items()])+' ',1)
            j['command']=[('--output='+str(output)+'.out') if x.startswith('--output=') else
                          ('--error='+str(output)+'.err') if x.startswith('--error=') else x for x in j['command']]
        j['command'][-1]=body
    return jobs

def reservations(c,charges,jobs):
    value={kind:charges[kind]+sum(j['wall_seconds'] for j in jobs if j['gpu']==(kind=='gpu')) for kind in ('gpu','cpu')}
    if value['gpu']>c['gpu_seconds'] or value['cpu']>c['cpu_seconds']:
        raise RuntimeError('full remaining cumulative compute reservation exhausted')
    return value

def footprint(c,run,remaining,r):
    original_footprint(c,run,remaining)
    def size(root):return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())
    if sum(size(r[k]) for k in ('scientific_source','r1_source','recovery_source'))>c['source_bytes']:
        raise RuntimeError('all retained source cap')
    if sum(size(r[k]) for k in ('original_control','r1_control','recovery_control'))>c['control_bytes']:
        raise RuntimeError('all retained control cap')
    for j in c['jobs'][3:]:
        out=location(run)/'workers'/j['id']
        if sum(p.stat().st_size for p in (Path(str(out)+'.out'),Path(str(out)+'.err')) if p.exists())>j['log_bytes']:
            raise RuntimeError('retained R2 worker log cap')

def begin(run,c):
    target=location(run)
    if (target/'STARTED.json').exists() or (target/'DISPATCH-R2.jsonl').exists() or (target/'workers').exists():
        raise RuntimeError('R2 already started/ambiguous; never repeat')
    if any((Path(run)/j['id']).exists() for j in c['jobs'][4:]) or (Path(run)/'analysis').exists():
        raise RuntimeError('unexplained remaining evidence; reconcile before any submission')
    write(target/'STARTED.json',dict(unix=time.time(),gpu_carried_seconds=174,cpu_carried_seconds=178,
                                     successful_tasks_recomputed=False,allowed_replacements=1,automatic_retry=False))
    (target/'workers').mkdir()

def gate_record(i):
    return dict(event='technical_tranche_passed',included_workers=9,included_episodes=72,
                carried_workers=3,new_workers=6,scientific_selection=False) if i==5 else None

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',type=Path,required=True);p.add_argument('--submit',action='store_true');a=p.parse_args()
    c,r=recovery_gate(a.approval);run=run_namespace(c);target=location(run)
    jobs=commands(c,Path(r['worker_approval']),a.approval,run,Path(r['r1_source']))
    charges=dict(gpu=174,cpu=178);full=reservations(c,charges,jobs)
    if not a.submit:
        print(json.dumps(dict(execute=False,remaining_tasks=len(jobs),full_reservations=full,first_command=jobs[0]['command'],analysis_command=jobs[-1]['command'])));return
    verify_resolution(run,r);begin(run,c)
    def append(row):
        row=dict(row,recorded_unix=time.time())
        with (target/'DISPATCH-R2.jsonl').open('a') as f:f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
        if (target/'DISPATCH-R2.jsonl').stat().st_size>c['control_bytes']:raise RuntimeError('retained control ledger cap')
    append(dict(event='carried_history_accepted',gpu_seconds=174,cpu_seconds=178,allocations=['312920']+CARRIED_IDS,
                failed_allocation=FAILED_ID,lineage_sha256=sha(LINEAGE),resolution_sha256=sha(target/'STOP-RESOLUTION.json')))
    try:
        for i,j in enumerate(jobs):
            verify_resolution(run,r);footprint(c,run,jobs[i:],r);reservations(c,charges,jobs[i:])
            terminal=dispatch(j,append,charges,check=lambda:footprint(c,run,jobs[i+1:],r))
            from dtv_success_cost.accept import accept_worker
            if j['gpu']:
                root=output_root(run,j);verify_evidence(root/j['id']);accept_worker(c,j,root,terminal['allocation_id'])
                directory=root/j['id']
            else:
                directory=run/'analysis';read_seal(directory,'analysis')
                if sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())>j['output_bytes']:raise RuntimeError('complete analysis cap')
            append(dict(event='accepted',task=j['id'],seal_sha256=sha(directory/'SEAL.json')))
            gate=gate_record(i)
            if gate:append(gate)
        from dtv_success_cost_r2.accept import accounting
        receipt=accounting(run,c,True)
        if receipt['unique_tasks']!=2882 or receipt['actual_attempts']!=2883:raise RuntimeError('full logical/attempt cardinality')
        write(run/'COMPUTE-COMPLETE.json',dict(**receipt,bindings_sha256=sha(DOC/'BINDINGS.json')))
    except Exception as e:
        write(target/'STOP-R2.json',dict(error=repr(e),charges=charges,automatic_retry=False));raise
if __name__=='__main__':main()
