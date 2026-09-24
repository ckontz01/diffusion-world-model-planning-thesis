from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-verification-20260923/finalization-r5'
ROOT.mkdir(exist_ok=False)
def put(name,value):
    with (ROOT/name).open('xb') as f:f.write(json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
rec=json.loads((HERE/'BASELINE-CAPTURE.json').read_text());assert rec['returncode']==0
base=json.loads(rec['stdout']);assert (base['successful_tasks'],base['attempts'],base['gpu_seconds'],base['cpu_stage_seconds'],base['live_or_unknown_jobs'])==(339,340,19365,52,0)
put('BASELINE.json',base)
authority=HERE.parent/'continuation-r3/MONITORING-AUTHORIZATION.md'
instruction=(ROOT.parent/'control-r4/INSTRUCTION.txt').read_bytes()
with (ROOT/'INSTRUCTION.txt').open('xb') as f:f.write(instruction)
with (ROOT/'MONITORING-AUTHORIZATION.md').open('xb') as f:f.write(authority.read_bytes())
put('CONTRACT.json',dict(schema='ACV0-finalization-only-r5-contract',authority='Direct advance user technical-recovery authority recorded at ace242ee5ea14af284401ad857fc3a49b30e1b58; no fresh signature',
 authority_commit='ace242ee5ea14af284401ad857fc3a49b30e1b58',authority_sha256=sha(authority),instruction_sha256=sha(ROOT/'INSTRUCTION.txt'),baseline_sha256=sha(ROOT/'BASELINE.json'),
 research_root=base['r4_binding']['research_root'],run=base['r4_binding']['run'],r4_source=base['paths']['r4_source'],r4_control=base['paths']['r4_control'],
 r4_manifest=base['r4_binding']['control_manifest'],r4_approval_sha256='ea6c4de1774775c2188a541d370e277e3325c73491cc8f47eb58fcb946853885',
 r4_stop_sha256=base['r4_stop_sha256'],r4_rel='docs/active-counterfactual-verification-20260923/control-r4',
 successful_tasks=339,campaign_allocations=340,gpu_seconds=19365,cpu_stage_seconds=52,new_allocations=0,replacements=0,reanalysis=0,
 finalization_attempts=1,archive_attempts=1,transfer_attempts=1,automatic_retries=0,transport_envelope_bytes=8000000,
 source_models_control_analysis_cap=500000000,live_cap=2000000000,inclusive_cap=8000000000,
 preparation_wall_seconds=7200,preparation_ram_bytes=8589934592,preparation_threads=4,preparation_artifact_bytes=250000000))
print(json.dumps({'baseline_sha256':sha(ROOT/'BASELINE.json'),'stop_sha256':base['r4_stop_sha256'],'new_allocations':0}))
