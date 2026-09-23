from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parents[2]/'docs/active-counterfactual-verification-20260923/control-r2'
sys.path.insert(0,str(PACKAGE))
import r2_core as r
capture=r.read(HERE/'BASELINE-CAPTURE.json');assert capture['returncode']==0
base=r.json.loads(capture['stdout']);r.write(PACKAGE/'BASELINE.json',base)
old=PACKAGE.parent/'bindings-r1'
r.write(PACKAGE/'CONTRACT.json',{
 'authority':'Explicit user-supplied reasoning instruction under standing delegation; not a fresh direct user signature',
 'reviewed_fault_commit':'4b74a58c3c5f382c2c8075f309e89cebf602d95e',
 'instruction_sha256':r.sha(PACKAGE/'INSTRUCTION.txt'),'baseline_sha256':r.sha(PACKAGE/'BASELINE.json'),
 'research_root':'/lustreFS/data/superworld/ckontzias/thesis','scientific_source':base['paths']['source'],
 'scientific_rel':'docs/active-counterfactual-verification-20260923/bindings-r1',
 'scientific_manifest':r.SCIENCE_MANIFEST,'worker_approval_sha256':r.WORKER_APPROVAL,
 'worker_approval_path':base['paths']['control']+'/EXECUTION-APPROVAL.json','run':base['paths']['run'],
 'grid_sha256':r.digest(r.read(old/'GRID.json')),'input_sha256':r.sha(old/'INPUT-BINDINGS.json'),
 'roles_sha256':r.sha(old.parent/'DATA-ROLES-PROPOSED.json'),'resolved_stop_sha256':r.STOP_SHA,
 'hostname_pairs':[list(pair) for pair in r.PAIRS],'device_name':r.DEVICE,'existing_job':'304193',
 'existing_worker_hashes':r.EXISTING_HASHES,'blocked_new_submission':'collect-fit-490',
 'initial_gpu_seconds':103,'initial_cpu_stage_seconds':0,'initial_maximum_gpu_seconds':219103,
 'new_allocations':338,'total_campaign_allocations':340,'successful_unique_tasks':339,
 'historical_failed_allocations':1,'previously_authorized_replacements':1,'new_replacements_authorized':0,'automatic_retries':0,
 'caps':r.read(old/'RECOVERY-CONTRACT.json')['caps'],
 'preparation_caps':{'wall_seconds':7200,'cpu_threads':4,'ram_bytes':8*1024**3,'new_artifact_bytes':250000000}})
print(r.json.dumps({'scheduler_rows':base['scheduler_rows'],'baseline_members':len(base['inventory']),
 'baseline_sha256':r.sha(PACKAGE/'BASELINE.json'),'instruction_sha256':r.sha(PACKAGE/'INSTRUCTION.txt')}))
