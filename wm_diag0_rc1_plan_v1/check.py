"""Validate the final plan's conservative arithmetic and source identities."""
import json
from .inventory import DOC
from wm_diag0_native_v3.common import ROOT,identity,write_new

def main():
    r=json.loads((DOC/'LEDGER-001.json').read_text())
    text=(DOC/'FINAL-PLAN.md').read_text(encoding='utf8')
    s=r['storage'];live=s['live'];archive=live+500000000
    assert archive==13340451198<=14000000000 and s['inclusive_with_two_full_14GB_archives']==43715303510<=44000000000
    for number in ('12840451198','13340451198','43715303510','10409','11099','200558','190174','950760','63432','138377','143779','570742','1267900','126860','461248','6836'):
        assert number in text,number
    local=ROOT/'docs/world-model-diagnostic-a2-native-v3-20261015'
    elapsed=sum(json.loads(p.read_text())['elapsed_seconds'] for p in local.glob('LOCAL-*.json') if not p.name.endswith('.started.json'))
    assert elapsed+500+120<=1700
    row={'status':'FINAL_PLAN_METADATA_AND_ARITHMETIC_CHECKED_EXECUTION_DISABLED',
      'plan':identity(DOC/'FINAL-PLAN.md'),'base_ledger':identity(DOC/'LEDGER-001.json'),
      'archive_overhead_reservation_supersedes_100MB_comparison_bytes':500000000,
      'archive_full_future_bound_bytes':archive,'inclusive_bound_bytes':s['inclusive_with_two_full_14GB_archives'],
      'measured_continuation_seconds_before_this_check':elapsed,'implementation500_seconds_plus_plan120_fit_existing1700':True,
      'research_calls':0,'accepted_work_changed':False,'scientific_implementation':False,'campaign_resumed':False,
      'finite_operation_exceptions_pending_human':r['proposed_exceptions']}
    write_new(DOC/'PLAN-CHECK-002.json',row);print(json.dumps(row,indent=2))

if __name__=='__main__':main()
