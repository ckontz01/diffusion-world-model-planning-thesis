"""Exact original scientific command, separately versioned supervisor repair."""
import hashlib,json,os,signal,sys,time,traceback
from pathlib import Path
from .common import OLD,RUN,GRID_HASH,INDICES,closed_indices,sampled_bytes

def stop_owned(proc):
    # Every child is created by the original Popen(start_new_session=True).
    # Clean its group even if the leader already exited; never preexisting PIDs.
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    if proc.poll() is None:proc.wait(timeout=1.5)

def repaired_source(raw):
    edits=[("result['error']=repr(exc)","result['error']=repr(exc);result['traceback']=traceback.format_exc()[-12000:]"),
           ("if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()","if proc is not None:stop_owned(proc)")]
    for before,after in edits:
        if raw.count(before)!=(2 if before.startswith('if proc') else 1):raise ValueError('exact reviewed original supervisor preimage')
        raw=raw.replace(before,after)
    return raw

def entry(root,expected):
    from wm_diag0_rc1_grid_v1.common import identity,gates
    cp=root/'source/GRID-CONTRACT.json';c=json.loads(cp.read_text());r=closed_indices(c)
    if identity(cp)['sha256']!=expected or root!=Path(RUN):raise ValueError('new immutable recovery contract')
    index=int(os.environ['SLURM_ARRAY_TASK_ID'])
    if index not in INDICES or os.uname().nodename not in ('gpu09','gpu09.cluster'):raise ValueError('only failed66/unstarted67-123 on gpu09')
    old=Path(OLD)
    if identity(old/'source/GRID-CONTRACT.json')['sha256']!=GRID_HASH:raise ValueError('old frozen contract intact')
    for name,want in r['old_failure_controls'].items():
        if identity(old/name)!=want:raise ValueError('preserve original failure and STOP')
    if index>=67 and (old/'tasks'/('grid-'+str(index))).exists():raise ValueError('never repeat a started old parent')
    # Actual compute-node namespace, before any scientific child. A recycled
    # PID with different ticks is not the recorded failed supervisor.
    p=Path('/proc')/str(r['old_PID'])/'stat'
    if p.exists() and p.read_text().rsplit(')',1)[1].split()[19]==r['old_start_ticks']:raise RuntimeError('recorded old supervisor still exists; no signal/no launch')
    gates(c)
    return c

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];c=entry(root,expected)
    from wm_diag0_rc1_grid_v1.common import identity
    path=root/'source/wm_diag0_rc1_grid_v1/supervisor.py'
    if identity(path)!=c['staged_members']['wm_diag0_rc1_grid_v1/supervisor.py']:raise ValueError('original supervisor retained verbatim')
    scope={'__name__':'recovery_original_supervisor','__package__':'wm_diag0_rc1_grid_v1','__file__':str(path)}
    exec(compile(repaired_source(path.read_text()),str(path)+'[reviewed-recovery-wrapper]','exec'),scope)
    scope.update(size=sampled_bytes,stop_owned=stop_owned,traceback=traceback)
    return scope['main']()

if __name__=='__main__':sys.exit(main())
