"""Remove diagnosed unused metadata lookup; preserve original failed reader."""
import json
from .common import DOC,OLD,identity,write_new
from .transport import call
from .manifest import CODE as ORIGINAL

UNUSED1="   index=s*31+ri-1;run=c['rc1_recovery']['original_grid_run'] if 'rc1_recovery' in c and index<66 else None\n"
UNUSED2="   root=c['rc1_grid_recovery']['original_run'] if 'rc1_grid_recovery' in c else None\n"
if ORIGINAL.count(UNUSED1)!=1 or ORIGINAL.count(UNUSED2)!=1:raise ValueError('exact saved failed helper preimage')
CODE=ORIGINAL.replace(UNUSED1,'   index=s*31+ri-1\n').replace(UNUSED2,'')

def main():
    failure=json.loads((DOC/'INPUTMETA001.failure.json').read_text())
    if failure['returncode']!=1 or "KeyError: 'original_grid_run'" not in failure['stderr'] or failure['stdout']:raise ValueError('saved exact pre-result metadata failure')
    write_new(DOC/'INPUTMETA001-DISPOSITION.json',{'status':'DIAGNOSED_UNUSED_METADATA_KEY_LOOKUP_REMOVED_IN_SEPARATE_V2','failure':identity(DOC/'INPUTMETA001.failure.json'),
        'original_source':identity(DOC.parent.parent/'wm_diag1_saved_v1/manifest.py'),'new_source':identity(__file__),'scientific_array_schema_modified':False,'new_numeric_derived_results_computed':False,'old_receipts_and_source_preserved':True})
    activation=json.loads((DOC/'ACTIVATION.json').read_text());c=json.loads((OLD/'FINAL-CONTRACT-002.json').read_text())
    value=call('INPUTMETA002',CODE,{'contract_path':c['rc1_final']['run']+'/source/FINAL-CONTRACT.json','anchors':activation['completed_anchors'],'completed_publication':activation['completed_publication']},seconds=65)
    write_new(DOC/'INPUT-MANIFEST.json',value)
    print(json.dumps({'status':value['status'],'parents':len(value['parents']),'input_manifest':identity(DOC/'INPUT-MANIFEST.json'),'required_bytes':value['required_saved_bytes_streamed_in_one_parent_at_a_time']}))

if __name__=='__main__':main()
