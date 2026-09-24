from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'docs/active-counterfactual-verification-20260923/finalization-r5'))
import transport5 as t
CODE=r'''
from pathlib import Path
import sys,time
b=CONFIG['binding'];root=Path(b['control_source'])/CONFIG['rel'];control=Path(b['control'])
sys.path.insert(0,str(root));import r5_core as r
ctx=r.Context(control/'EXECUTION-APPROVAL.json')
import finalize5
complete=finalize5.authenticate_complete(ctx)
assert not (ctx.run/'final-preservation').exists(),'Archive state must be reconciled, not overwritten'
records={p.relative_to(control).as_posix():{'bytes':p.stat().st_size,'sha256':r.sha(p)} for p in control.rglob('*') if p.is_file()}
print(json.dumps({'unix':time.time(),'archive_directory_exists':False,'science_tasks':339,'attempts':340,
 'gpu_seconds':complete['gpu_seconds'],'cpu_stage_seconds':complete['cpu_stage_seconds'],
 'r5_control_members':records,'completion_sha256':r.sha(ctx.run/'COMPUTE-COMPLETE.json'),
 'r5_approval_sha256':ctx.approval_sha,'r5_manifest':b['control_manifest'],'r5_binding':b,
 'scientific_payloads_decoded':0,'scheduler_calls':0,'new_jobs':0}))
'''
if __name__=='__main__':t.once('ARCHIVE-FAULT-RECONCILIATION',CODE)
