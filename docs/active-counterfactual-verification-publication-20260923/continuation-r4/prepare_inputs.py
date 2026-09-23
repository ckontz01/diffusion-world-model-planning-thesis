"""Exclusive R4 binding derived only from authenticated technical evidence."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-verification-20260923/control-r4'
def put(name,value):
    with (ROOT/name).open('xb') as f:f.write(json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
receipt=json.loads((HERE/'BASELINE-CAPTURE.json').read_text())
assert receipt['returncode']==0
base=json.loads(receipt['stdout'])
assert base['successful_tasks']==37 and base['unsubmitted_tasks']==302 and base['gpu_seconds']==4862 and base['live_or_unknown_jobs']==0
fault=[v for v in base['r3_scheduler_observations'] if v['job']=='304237']
assert len(fault)==1 and fault[0]['stdout']=='304237|allocation|PENDING|0:0|0|0||gpu09||Unknown|superworld|\n'
put('BASELINE.json',base)
instruction='okay do scheduled checks every 2 hours, and if any TECHNICAL issues arise, I give you full permission to resolve them and resume the jobs. (do not of me to approve)'
with (ROOT/'INSTRUCTION.txt').open('xb') as f:f.write(instruction.encode())
contract=json.loads((ROOT.parent/'control-r3/CONTRACT.json').read_text())
contract.update(authority='Direct advance user monitoring and technical-recovery instruction, recorded at ace242ee5ea14af284401ad857fc3a49b30e1b58; this finite R4 corrects the observed R3 pending accounting placeholder only; no scientific changes',
 baseline_sha256=sha(ROOT/'BASELINE.json'),instruction_sha256=sha(ROOT/'INSTRUCTION.txt'),
 monitoring_authority_commit='ace242ee5ea14af284401ad857fc3a49b30e1b58',
 monitoring_authority_sha256=sha(HERE.parent/'continuation-r3/MONITORING-AUTHORIZATION.md'),
 initial_gpu_seconds=4862,initial_maximum_gpu_seconds=159062,new_allocations=302,existing_successful_tasks=37,
 blocked_new_submissions=[v['spec']['key'] for v in base['successful_rows']],
 historical_job_names={v['job']:v['job_name'] for v in base['allocations']},
 resolved_r3_stop_sha256=base['r3_stop_sha256'],r3_source_manifest=base['r3_binding']['control_manifest'],
 next_task='collect-fit-256',reviewed_status_commit='e379530fa86230827fa6f0be639de594bb76036d',
 finite_attempts='One new allocation for each of302 never-submitted logical tasks; zero new replacements; maximum340 campaign allocations including the original failed304189',
 status_placeholder_rule='Only exact captured twelve-field allocation/PENDING/0:0/0/0/empty/gpu09/empty/Unknown/superworld/empty row with exact submitted allocation ID and GPU task; counts against8-poll incomplete allowance, never terminal acceptance')
put('CONTRACT.json',contract)
print(json.dumps({'baseline_sha256':contract['baseline_sha256'],'existing':37,'new':302,'gpu_seconds':4862,'stop_r3_sha256':base['r3_stop_sha256']}))
