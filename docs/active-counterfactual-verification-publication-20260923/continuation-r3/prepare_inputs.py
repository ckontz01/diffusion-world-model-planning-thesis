"""Generate new R3 technical bindings from the one read-only reconciliation."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-verification-20260923/control-r3'
def put(name,value):
    with (ROOT/name).open('xb') as f:f.write(json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
receipt=json.loads((HERE/'BASELINE-CAPTURE.json').read_text())
assert receipt['returncode']==0
base=json.loads(receipt['stdout'])
assert base['successful_tasks']==24 and base['unsubmitted_tasks']==315 and base['gpu_seconds']==3015 and base['live_or_unknown_jobs']==0
put('BASELINE.json',base)
with (ROOT/'INSTRUCTION.txt').open('xb') as f:f.write(b'FIX IT AND RESUME IT')
old=json.loads((ROOT.parent/'control-r2/CONTRACT.json').read_text())
for key in ('blocked_new_submission','existing_job','existing_worker_hashes','reviewed_fault_commit'):old.pop(key)
old.update(authority='Direct user instruction FIX IT AND RESUME IT, applied only to the reconciled R2 control-status fault; original scientific authorization and caps unchanged',
 baseline_sha256=sha(ROOT/'BASELINE.json'),instruction_sha256=sha(ROOT/'INSTRUCTION.txt'),
 initial_gpu_seconds=3015,initial_maximum_gpu_seconds=180615,new_allocations=315,existing_successful_tasks=24,
 blocked_new_submissions=[v['spec']['key'] for v in base['successful_rows']],
 historical_job_names={v['job']:v['job_name'] for v in base['allocations']},
 resolved_r2_stop_sha256=base['r2_stop_sha256'],r2_source_manifest=base['r2_binding']['control_manifest'],
 status_grace_polls=8,status_poll_seconds=15,status_log_bytes=10000000,
 next_task='collect-fit-505',reviewed_status_commit='f8c731d05ede1e0869d1912335122516911a32c2')
put('CONTRACT.json',old)
print(json.dumps({'baseline_sha256':old['baseline_sha256'],'existing':24,'new':315,'gpu_seconds':3015}))
