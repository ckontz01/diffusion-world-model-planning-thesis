"""One dated final funding activation; no refund/transfer of earlier ceilings."""
from decimal import Decimal
import json
from .runner import DOC
from wm_diag0_rc1_v1.common import ROOT,identity,write_new

def main():
    old=ROOT/'docs/world-model-diagnostic-rc1-v1-20261016/PREPARATION-ACTIVATION.json';a=json.loads(old.read_text())
    previous=Decimal(str(a['new_cumulative_nonrefundable_charge_seconds']));new=Decimal(str(a['remaining_unreserved_seconds']))
    if previous+new!=Decimal('14400') or new!=Decimal('45.89698539988'):raise ValueError('exact remaining original-cap balance')
    for p in (ROOT/'wm_diag0_rc1_ops_reserve_v1').glob('*.py'):compile(p.read_bytes(),str(p),'exec')
    write_new(DOC/'ACTIVATION.json',{'status':'LAST_UNRESERVED_PREPARATION_BALANCE_ACTIVATED_ONCE','authority':'original14400s preparation cap plus latest direct autonomous bounded iteration authority',
        'authority_identity':identity(ROOT/'docs/world-model-diagnostic-rc1-v1-20261016/AUTHORITY.json'),'previous_activation_identity':identity(old),
        'previous_nonrefundable_charge':float(previous),'new_nonrefundable_charge':float(new),'cumulative_nonrefundable_charge':14400,
        'original_preparation_cap':14400,'remaining_unreserved_seconds':0,'new_measured_seconds_ceiling':float(new),
        'previous_750s_envelope_and_all_component_ceilings_unchanged':True,'previous_charges_refunded_or_spent_twice':False,
        'CPU_threads':4,'RAM_bytes':8589934592,'scope':'exact current dispatch/control/scheduler observations and reviewed precise grid staging only; no model execution',
        'on_exhaustion':'stop affected preparation/metadata action and report; no additional grants or automatic resource expansion'})
    print(json.dumps({'status':'FINAL_PREPARATION_BALANCE_FROZEN','new_charge':float(new),'cumulative_charge':14400,'remaining_unreserved':0}))

if __name__=='__main__':main()
