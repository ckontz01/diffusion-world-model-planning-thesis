from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parents[2]/'docs/active-counterfactual-verification-20260923/bindings-r1'
sys.path.insert(0,str(PACKAGE))
import common as c
receipt=c.read(HERE/'PRIOR-RECONCILIATION.json');assert receipt['returncode']==0
c.write(PACKAGE/'PRIOR-ATTEMPT.json',c.json.loads(receipt['stdout']))
raw=(HERE/'RECOVERY-INSTRUCTION.txt').read_bytes()
with (PACKAGE/'RECOVERY-INSTRUCTION.txt').open('xb') as f:f.write(raw)
c.write(PACKAGE/'GRID.json',c.grid())
c.write(PACKAGE/'RECOVERY-CONTRACT.json',{
 'authority':'User-supplied selected reasoning direction under standing delegation; not a fresh direct user signature',
 'instruction_sha256':c.sha(PACKAGE/'RECOVERY-INSTRUCTION.txt'),
 'prior_attempt_sha256':c.sha(PACKAGE/'PRIOR-ATTEMPT.json'),
 'reviewed_fault_commit':'64ebad6d881680ec54973b9b38b18a6999b24212',
 'old_implementation_commit':'5d382ddf294ee711d21e137091c59fe3a57a05df',
 'old_source_manifest':'5630b222e8a88d0eaa45408876929724734d1f992afa657131ac770fb0400fa9',
 'old_approval_sha256':'7ea5f67225ee1bff091e705e7515a4ed8f3589694e6093f1c2e7c607d27a6a88',
 'old_grid_sha256':'f9b4986c9f674122c253cff9aaf802e8d4b181180553d0e5643c0c92bb175a2a',
 'new_grid_sha256':c.digest(c.grid()),'inputs_sha256':c.sha(PACKAGE/'INPUT-BINDINGS.json'),
 'roles_sha256':c.sha(c.BASE/'DATA-ROLES-PROPOSED.json'),
 'failed_job':'304189','failed_task':'collect-fit-490','prior_gpu_seconds':23,'prior_cpu_stage_seconds':0,
 'replacement_task':'collect-fit-490','replacement_attempt':2,'hard_seconds':1740,'work_seconds':1620,
 'expected_device_name':'NVIDIA RTX 6000 Ada Generation','visible_gpus':1,
 'partition':'a6000','qos':'normal-a6000','account':'superworld',
 'max_campaign_attempts':340,'new_attempts':339,'successful_unique_tasks':339,
 'max_authorized_replacements':1,'automatic_retry_count':0,'initial_gpu_maximum':220763,
 'caps':c.caps(),'preparation_caps':{'wall_seconds':7200,'cpu_threads':4,'ram_bytes':8*1024**3,'output_bytes':250000000},
 'old_failed_artifacts_and_copies_counted':True,'scientific_changes':False})
print('Prepared exact prior/instruction/grid bindings; no allocation.')
