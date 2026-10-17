"""Metadata-only exact portable/manifest forecast BEFORE real CPU allocation."""
import json
from .common import DOC,write_new
from .transport_v2 import call
CODE=r'''
import json,sys,time
from pathlib import Path
data=json.load(sys.stdin);sys.path[:0]=['/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015-rc1-preservation-v2/review-source-002','/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/campaign-v4-rc1-grid-recovery-r1/source']
from wm_diag0_rc1_final_v2.inventory_v3 import plan
from wm_diag0_rc1_final_v2.archive_v2 import canonical
layout=data['layout'];external={n:p for n,p in layout['root_paths'].items() if not n.startswith('study/')}
p=plan(layout['study_base'],layout['approved_children_before_final'],external,layout['approved_inert_alias_literals'])
portable={k:v for k,v in p.items() if k!='members'};rows={};manifest={};index=0
for name,row in sorted(p['members'].items()):
 if row['type']=='file':
  rows[name]={'type':'file','bytes':row['bytes'],'sha256':'0'*64};manifest[name]=dict(rows[name],payload='payload/'+str(index).zfill(6));index+=1
 else:rows[name]={'type':'symlink','target':row['target']};manifest[name]=rows[name]
portable['members']=rows
m={'schema':'WM-DIAG0-RC1-ARCHIVE-v2','binding':{'root_paths':{n:layout['root_paths'][n] for n in p['root_labels']},'final_contract_sha256':data['contract_sha256']},'root_labels':p['root_labels'],'members':manifest,
 'logical_payload_bytes_no_discounts':p['logical_payload_bytes_no_discounts'],'alias_policy':'metadata-only; never followed/extracted/executed','compression_or_hardlink_savings_assumed':False}
print(json.dumps({'status':'ACTUAL_METADATA_ONLY_PORTABLE_AND_MANIFEST_FORECAST','current_members':len(rows),'portable_bytes_before_owned_final':len(canonical(portable)),
 'manifest_bytes_before_owned_final':len(canonical(m)),'reserved_owned_final_metadata_addition':1000000,'existing_portable_cap':12000000,'format_manifest_cap':20000000,'scientific_values_read':False}))
'''
def main():
    layout=json.loads((DOC/'LAYOUT-001.json').read_text())['layout'];pub=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    result=call('FORECAST001',CODE,{'layout':layout,'contract_sha256':pub['contract']['sha256']},seconds=80)
    print(json.dumps(result))
if __name__=='__main__':main()
