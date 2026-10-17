"""New synthetic recovery mapping/139-attempt tests, no old suite or study read."""
import ast,copy,json,time
from pathlib import Path
from .recovery_suppliers_v1 import *
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,identity,write_new,CAPS,charge

def main():
    rc=ROOT/'docs/world-model-diagnostic-rc1-recovery-r1-20261016';c=json.loads((rc/'GRID-CONTRACT.json').read_text())
    old={str(i):str(400000+i) for i in range(67)};old['66']='317411';new={str(i):str(500000+i) for i in range(66,124)}
    wants=expected_starts(c,old,new);lines=[]
    for key,(raw,state,exitcode,n) in OLD_ALLOCATED.items():lines.append('|'.join([key,raw,state,exitcode,str(n),'4','gpu09']))
    for key,w in wants.items():lines.append('|'.join([key,w['job_id'],'FAILED' if key=='317180_66' else 'COMPLETED','125:0' if key=='317180_66' else '0:0','79' if key=='317180_66' else '1','4','gpu09']))
    for key in set(OLD_UNALLOCATED)|{'317180_[67-123%1]'}:lines.append('|'.join([key,'399999','CANCELLED by 1201','0:0','0','4','None assigned']))
    raw='\n'.join(lines)+'\n';answer=terminal_ledger(c,raw,old,new)
    assert answer['allocated_attempts']==139 and answer['original_newer_start_controls']==128
    locations=[]
    for setting in range(4):
        for index in range(1,32):
            location,_=parent_location(c,setting,index);locations.append(str(location))
    assert len(set(locations))==124 and sum(x.startswith(OLD+'/') for x in locations)==66 and sum(x.startswith(RUN+'/') for x in locations)==58
    for bad in (raw+'\n'+lines[0],raw.replace('317180_66|317411|FAILED|125:0|79','317180_66|317411|COMPLETED|0:0|79'),raw.replace('317441_66|500066|COMPLETED','317441_66|500066|RUNNING'),raw.replace('317441_123|500123|COMPLETED|0:0|1|4|gpu09\n',''),raw.replace('317180_[67-123%1]|399999|CANCELLED by 1201|0:0|0','317180_[67-123%1]|399999|CANCELLED by 1201|0:0|1')):
        try:terminal_ledger(c,bad,old,new)
        except ValueError:pass
        else:raise AssertionError('incomplete/changed/live/duplicate allocation accepted')
    for args in ((True,1),(0,True),(4,0),(0,32)):
        try:parent_location(c,*args)
        except ValueError:pass
        else:raise AssertionError('fixed nonboolean parent identity')
    source={p.name:identity(p) for p in [Path(__file__),Path(__file__).with_name('recovery_suppliers_v1.py')]}
    for name in source:ast.parse((Path(__file__).parent/name).read_text(),feature_version=(3,6))
    # Authenticate the saved interrupted start chain locally as part of this
    # NEW metadata test; the prior15s diagnostic timed out and is not retried.
    unknown=json.loads((DOC/'LOCAL-RECOVERYOBS016.json').read_text())
    assert identity(DOC/'LOCAL-RECOVERYOBS016.started.json')==unknown['original_started']
    assert identity(rc/'OBSERVER016.started.json')==unknown['child_started']
    assert unknown['charged_seconds']==30 and unknown['returncode'] is None and unknown['elapsed_seconds'] is None
    bundle=[]
    for directory in ('wm_diag0_rc1_completion_v1','docs/world-model-diagnostic-rc1-completion-budget-v1-20261016','wm_diag0_rc1_final_v2','docs/world-model-diagnostic-rc1-final-v2-20261016','wm_diag0_rc1_monitor_v2','docs/world-model-diagnostic-rc1-monitor-v2-20261016'):
        for p in (ROOT/directory).rglob('*'):
            if not p.is_file():continue
            n=p.name
            if n.startswith(('OBSERVE-R','RECONCILE-R','LOCAL-RESUMEOBS','LOCAL-HUMANOBS','LOCAL-INVESTOBS','LOCAL-RECOVERY')) or n=='CONTINUATION-014.txt':continue
            bundle.append(p)
    measured=sum(p.stat().st_size for p in bundle)
    if measured+12000>4500000:raise ValueError('actual old nonmonitor source/docs plus finite new compact receipts exceeds existing prospective bound')
    z={'status':'NEW_RECOVERY139_LEDGER_AND124_PARENT_MAPPING_SYNTHETIC_TESTS_PASSED','sources':source,'synthetic_allocations':139,'synthetic_started_controls':128,'ordinary_parents':124,'preserved_original_suppliers':66,'recovery_suppliers':58,
       'source_only_unfrozen_unpublished':True,'old_nonmonitor_bundle_bytes_before_compact_receipts':measured,'new_compact_receipt_allowance':12000,'R016_unknown_outcome_full30_authenticated_not_retried':True,
       'old_OBSINTERRUPT016_timeout_preserved_no_cause_inference':True,'research_WSL_SSH_scheduler_SSD_or_scientific_payload_calls':0,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-RECOVERY-SUPPLIERS-001.json',z);print(json.dumps(z))

if __name__=='__main__':main()
