"""Narrow, read-only recovery of exposed historical metadata and executed code.

Never imports torch, deserializes checkpoints, or opens research payloads.
"""
import base64
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/dtv-efficiency-20260930/evidence'
REMOTE = r'''
import base64, hashlib, json, pathlib, time
R=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis')
patterns=[]
for task,job,capture,component,episode in [('pusht',296631,297055,297060,297061),('reacher',296650,297114,297119,297163),('cube',296669,297079,297084,297085)]:
 for arm,offset in [('acid',0),('diffusion',3),('forward',6)]:
  for i in range(3): patterns.append(f'results/acid-alternative/scorers/{task}/{arm}/true/seed-{6101+i}-job-{job}-{offset+i}/summary.json')
 patterns += [f'results/acid-alternative/latency/{task}/cuda-components/multi/job-{component}/summary.json',f'results/acid-alternative/latency/{task}/end-to-end-episode/job-{episode}/summary.json',f'results/acid-alternative/diagnostics/{task}/d1-b0-candidate-pools/planner-seed-7101-job-{capture}/manifest.json']
 patterns += [f'results/acid-alternative/v3-d2/stage-a/{task}/capture/*/manifest.json',f'results/acid-alternative/v3-d2/stage-a/{task}/shared-score/job-297538-*/manifest.json',f'results/acid-alternative/v3-d2/stage-a/{task}/frozen-scores/job-297564-*/manifest.json']
 patterns += [f'results/acid-alternative/e6d-allgate-controls/closed-loop/{task}/*/job-297690-*/summary.json']
patterns += ['results/acid-alternative/v3-d2/stage-a/analysis/job-297565/summary.json','results/acid-alternative/e6d-allgate-controls/analysis/job-297691/summary.json','results/acid-alternative/analysis/d1/sensitivity/job-297131/summary.json']
sources=['acid-alternative-core-v1-3074081ea1ebadd9','acid-alternative-core-v1-52acea39e4a1f6da','acid-alternative-diagnostics-v1-2a55d07d912bf1b6','acid-alternative-diagnostics-v1-53065f818adf09b3','acid-alt-v3-d2-875a9cbc19dba78d','acid-alt-v3-d2-2c8f890c31e9f5bf']
for source in sources:
 patterns.append(f'snapshots/{source}/SOURCE-MANIFEST.sha256')
 for name in ['acid_alternative/costs.py','acid_alternative/models.py','acid_alternative/evaluate_matched.py','acid_alternative/train_transition_scorer.py','acid_alternative/task_registry.py','acid_alternative/action_standardization.py','acid_alternative/io_utils.py','acid_alternative_diagnostics/benchmark_latency.py','acid_alternative_diagnostics/benchmark_episode_latency.py','acid_alternative_diagnostics/score_candidate_pools.py','acid_alternative_diagnostics/capture_candidate_pools.py','score_acid_alt_d2_task.py','run_acid_alt_v3_d2_score.slurm','run_acid_alt_v3_core_score.slurm']:
  p=R/'snapshots'/source/name
  if p.is_file(): patterns.append(str(p.relative_to(R)))
files=[]; missing=[]; seen=set(); total=0
for pattern in patterns:
 matches=sorted(R.glob(pattern))
 if not matches: missing.append(pattern)
 for p in matches:
  if p in seen: continue
  seen.add(p)
  if p.stat().st_size>2000000: raise RuntimeError('oversized metadata '+str(p))
  data=p.read_bytes(); total+=len(data)
  if total>20000000: raise RuntimeError('recovery byte cap')
  files.append(dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),data=base64.b64encode(data).decode()))
print(json.dumps(dict(observed_unix=time.time(),files=files,missing=missing,bytes=total)))
'''

def main():
    if OUT.exists():
        raise RuntimeError('exclusive evidence destination already exists')
    start = time.monotonic()
    result = subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus','python3.9 -'], input=REMOTE.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    receipt=json.loads(result.stdout)
    OUT.mkdir(parents=True)
    for record in receipt['files']:
        data=base64.b64decode(record.pop('data'))
        if hashlib.sha256(data).hexdigest()!=record['sha256']: raise RuntimeError('transport hash mismatch')
        p=OUT/record['path']; p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f: f.write(data)
    receipt['local_wall_seconds']=time.monotonic()-start
    receipt['checkpoint_deserialization']=False
    receipt['new_payload_access']=False
    (OUT/'RECOVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'},indent=2))
    print('recovered_files',len(receipt['files']))

if __name__=='__main__': main()
