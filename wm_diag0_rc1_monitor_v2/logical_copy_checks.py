"""Synthetic maximal healthy snapshot roundtrip and all-copy receipt bounds."""
import ast,base64,copy,json,tempfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .compact import encode_record,decode_record,write_compact,canonical,failure,CAPTURE_PREFIX
from wm_diag0_rc1_completion_v1.compact import compact_payload,GRID_HASH
from wm_diag0_preflight_v1.preserve import digest


def main():
    for p in Path(__file__).parent.glob('*.py'):
        text=p.read_text();ast.parse(text,feature_version=(3,6))
        if any(s.rstrip()!=s for s in text.splitlines()):raise ValueError('prepublication whitespace guard')
    for name,receipt,module in (('compact-before-logical-copy-001.json','ARTIFICIAL-001.json','compact.py'),
                                ('publication-before-final-guard-001.json','ARTIFICIAL-002.json','publication.py')):
        pre=json.loads((DOC/'source-preimages'/name).read_text());old=json.loads((DOC/receipt).read_text())
        want={'bytes':pre['bytes'],'sha256':pre['sha256']}
        assert digest(base64.b64decode(pre['base64'],validate=True))==want
        assert old['sources'][module]==want
    rows=[];tasks={}
    for i in range(124):
        raw=str(500000+i);seal={'bytes':1,'sha256':'b'*64}
        rows.append('317180_'+str(i)+'|'+raw+'|COMPLETED|0:0|3600|4|gpu09\n')
        tasks[str(i)]={'STARTED':{'array_job_id':'317180','index':i,'contract':GRID_HASH,'job_id':raw},
                       'ACCEPTED':{'accepted':True,'contract_sha256':GRID_HASH,'output_seal':seal},
                       'RESULT':{'status':'ACCEPTED','job_id':raw,'output_seal':seal}}
    o={'dispatch':{'array_job_id':'317180','indices':124,'contract_sha256':GRID_HASH,'automatic_retries':0,
                   'allocation_seconds_each':3600,'grid_dispatched_after_all_four_gates':True},
       'scheduler':''.join(rows),'queue':'','queue_diagnostic':{'returncode':0,'stderr':'','invalid_live_queue_id_authenticated_by_complete_terminal_history':True},
       'tasks':tasks,'accepted_grid_parents':124,'active_process_records':[],'STOP':None,
       'full_future_GPU_reservation':449783,'CPU_before_analysis':1436,'quality_choices_outcomes_or_predictions_read':False}
    full=compact_payload(o);packed=encode_record(full)
    assert decode_record(packed)==full and len(canonical(packed))+1<=10000
    bad=copy.deepcopy(packed);bad['scheduler_rows'][0][4]='1'
    try:decode_record(bad)
    except ValueError:pass
    else:raise AssertionError('changed scheduler field rejected by complete original identity')
    bad=copy.deepcopy(packed);bad['accepted_indices_bitmask_hex']='0x0'
    try:decode_record(bad)
    except ValueError:pass
    else:raise AssertionError('changed accepted-index set rejected')
    with tempfile.TemporaryDirectory(prefix='wmrc1-compact-receipt-') as tmp:
        path=Path(tmp)/'receipt.json';write_compact(path,packed)
        assert decode_record(json.loads(path.read_text()))==full
        try:write_compact(path,packed)
        except FileExistsError:pass
        else:raise AssertionError('exclusive receipt must not overwrite')
    f=failure(255,b'x'*16000,b'y'*16000,'NONZERO_TRANSPORT_OR_REMOTE_NO_CAUSE_ASSUMED')
    assert CAPTURE_PREFIX==2048 and len(json.dumps(f,sort_keys=True,indent=2).encode())+1<=8000
    per_copy=3072+1024+1024+10000
    assert 4*per_copy==60480 and 4*per_copy<=65536
    assert (ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/LOCAL-RESUMEOBS003.started.json').stat().st_size<3072
    result={'status':'ARTIFICIAL_MONITOR_LOGICAL_COPY_AND_SOURCE_GUARDS_PASSED',
            'sources':{p.name:identity(p) for p in Path(__file__).parent.glob('*.py')},
            'checks':['exact full124terminal worst-allocation snapshot roundtrip','every original scheduler field reconstructed',
                      'complete original canonical record identity','changed scheduler/index mask rejected',
                      'exclusive native ordinary-temp serialized receipt','preserved exact older tested source preimages',
                      'all new source AST3.6/no trailing whitespace'],
            'success_receipt_limit':10000,'failure_receipt_limit':8000,'capture_prefix_each':2048,
            'logical_receipt_copies_reserved':4,'all_copy_check_reservation':60480,'authority_max_all_copy_check_bytes':65536,
            'synthetic_maximal_success_actual_bytes':len(canonical(packed))+1,
            'actual_cluster_or_designated_SSD_accessed':False,'external_processes_launched':0,
            'research_calls':0,'underlying_transport_cause_diagnosed':False,'final_gate_ready':False}
    write_new(DOC/'ARTIFICIAL-003.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('sources','checks')}))


if __name__=='__main__':main()
