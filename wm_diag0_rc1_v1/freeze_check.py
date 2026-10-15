"""Gate-specific source/schema checks, without real model execution."""
import ast,json
from pathlib import Path
from .common import DOC,ROOT,identity,write_new
from .operations import STAGE,OBSERVE,RECONCILE

def main():
    for p in (ROOT/'wm_diag0_rc1_v1').glob('*.py'):compile(p.read_bytes(),str(p),'exec')
    for source in (STAGE,OBSERVE,RECONCILE):ast.parse(source,feature_version=(3,6))
    supervisor=(ROOT/'wm_diag0_rc1_v1/supervisor.py').read_text()
    assert "('wm_diag0_rc1_v1.worker',120)" in supervisor and "('wm_diag0_rc1_v1.validate',175)" in supervisor
    assert "--hold" in STAGE and "r.mkdir(exist_ok=False)" in STAGE and "--no-requeue" in STAGE
    worker=(ROOT/'wm_diag0_rc1_v1/worker.py').read_text()
    assert 'adapter.original_contract' in worker and 'pointwise_goal_id' in worker
    for name in ('ARTIFICIAL-GATE-001.json','ARTIFICIAL-REFERENCE-001.json','RECONCILE-001.json'):
        assert (DOC/name).is_file()
    row={'status':'RC1_GATE_FREEZE_STATIC_BOUNDARIES_PASSED','research_calls':0,
      'source_members':{p.name:identity(p) for p in sorted((ROOT/'wm_diag0_rc1_v1').glob('*.py'))},
      'gated_future_fits_and_campaign_still_disabled':True}
    write_new(DOC/'FREEZE-CHECK-001.json',row);print(json.dumps({'status':row['status'],'members':len(row['source_members']),'research_calls':0}))

if __name__=='__main__':main()
