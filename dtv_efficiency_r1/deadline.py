"""Outer-process deadline supervisor; nothing wraps the timed CUDA callable."""
import json,os,signal,subprocess,time
from pathlib import Path

class EvidenceList(list):
    """Journal completed records outside timers; interrupted tail stays intact."""
    def __init__(self,path):super().__init__();self.path=Path(path)
    def append(self,value):
        with self.path.open('a',encoding='utf-8') as f:
            f.write(json.dumps(value,separators=(',',':'))+'\n');f.flush()
        super().append(value)

def signal_group(process,force):
    if os.name=='posix':
        try:os.killpg(process.pid,signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:pass
    elif force:process.kill()
    else:process.terminate()

def supervise(command,output,work_seconds=720,started=None,termination_grace=5,kill_wait=5,env=None):
    """Bounded waits, not a guarantee of uninterruptible kernel/I/O cleanup."""
    started=time.monotonic() if started is None else started
    output=Path(output);deadline=started+work_seconds
    child_env=dict(os.environ if env is None else env)
    child_env.update(DTVEFF_START_MONOTONIC=str(started),DTVEFF_SUPERVISOR_PID=str(os.getpid()))
    if time.monotonic()>=deadline:
        record=dict(status='deadline_fault',fault='work_deadline',child_pid=None,child_exit_code=None,accounting_start_monotonic=started,work_deadline_seconds=work_seconds,elapsed_seconds=time.monotonic()-started,termination_sent=False,kill_sent=False,termination_grace_seconds=termination_grace,kill_wait_seconds=kill_wait,unresolved_process=False,cleanup_guaranteed=False,automatic_retry=False)
        with (output/'SUPERVISION.json').open('x') as f:json.dump(record,f,indent=2)
        with (output/'FAILURE.json').open('x') as f:json.dump(dict(error='deadline exhausted before child startup',automatic_retry=False),f)
        return record
    try:process=subprocess.Popen(command,env=child_env,start_new_session=os.name=='posix')
    except OSError as e:
        record=dict(status='startup_fault',fault='child_startup',error=repr(e),child_pid=None,child_exit_code=None,accounting_start_monotonic=started,work_deadline_seconds=work_seconds,elapsed_seconds=time.monotonic()-started,unresolved_process=False,cleanup_guaranteed=False,automatic_retry=False)
        with (output/'SUPERVISION.json').open('x') as f:json.dump(record,f,indent=2)
        with (output/'FAILURE.json').open('x') as f:json.dump(record,f,indent=2)
        return record
    fault=None;term=False;kill=False;unresolved=False
    try:
        process.wait(timeout=max(0,deadline-time.monotonic()))
    except subprocess.TimeoutExpired:
        fault='work_deadline';term=True;signal_group(process,False)
        try:process.wait(timeout=termination_grace)
        except subprocess.TimeoutExpired:
            kill=True;signal_group(process,True)
            try:process.wait(timeout=kill_wait)
            except subprocess.TimeoutExpired:unresolved=True
    record=dict(status='deadline_fault' if fault else 'child_exited',fault=fault,child_pid=process.pid,child_exit_code=process.poll(),accounting_start_monotonic=started,work_deadline_seconds=work_seconds,elapsed_seconds=time.monotonic()-started,termination_sent=term,kill_sent=kill,termination_grace_seconds=termination_grace,kill_wait_seconds=kill_wait,unresolved_process=unresolved,cleanup_guaranteed=False,automatic_retry=False)
    with (output/'SUPERVISION.json').open('x') as f:json.dump(record,f,indent=2)
    if fault:
        evidence={p.name:p.stat().st_size for p in output.iterdir() if p.is_file()}
        with (output/'DEADLINE-FAULT.json').open('x') as f:json.dump(dict(**record,retained_evidence_bytes=evidence),f,indent=2)
    if fault or process.poll()!=0:
        failure=output/'FAILURE.json'
        if not failure.exists():
            with failure.open('x') as f:json.dump(dict(error=fault or 'child_exit_nonzero',supervision='SUPERVISION.json',records_journal='RECORDS.jsonl',equivalence_journal='EQUIVALENCE.jsonl',automatic_retry=False),f,indent=2)
    return record
