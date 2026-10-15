import json
from .local import DOC,LEGACY_DOC
from wm_diag0_rc1_v1.common import identity,ROOT,write_new

def main():
    a=json.loads((DOC/'ROUTING.json').read_text());old=json.loads((LEGACY_DOC/'PREPARATION-ACTIVATION.json').read_text())
    if identity(LEGACY_DOC/'PREPARATION-ACTIVATION.json')!=a['original_activation_identity'] or sum(a['prospective_component_ceiling_seconds'].values())!=750:raise AssertionError('original funding/total identity')
    before=old['component_ceiling_seconds'];after=a['prospective_component_ceiling_seconds']
    if after['implementation_artificial_schema']!=before['implementation_artificial_schema']-180 or after['metadata_reconciliation_staging']!=before['metadata_reconciliation_staging']+180:raise AssertionError('exact prospective transfer')
    for k in ('cluster_artificial_interface','freeze_publication_SSD','fault_reserve'):
        if after[k]!=before[k]:raise AssertionError('other ceilings unchanged')
    rows=[json.loads(p.read_text()) for directory in (LEGACY_DOC,DOC) for p in directory.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    for k in after:
        if sum(x['elapsed_seconds'] for x in rows if x['component']==k)>after[k]:raise AssertionError('all historical actual charges fit')
    for p in (ROOT/'wm_diag0_rc1_prep_routing_v1').glob('*.py'):compile(p.read_bytes(),str(p),'exec')
    write_new(DOC/'TEST-001.json',{'status':'PASSED','same_measured_total_seconds':750,'original_sources_edited':False,'historic_receipts_relabelled':False,'new_charge':0,'research_calls':0})
    print(json.dumps({'status':'PROSPECTIVE_SAME_TOTAL_ROUTING_CHECKED','new_charge':0,'research_calls':0}))

if __name__=='__main__':main()
