"""Recovery-aware final metadata, SOURCE ONLY; no analysis/launch entry.

Resolve accepted logical parents without repeating them, and reconcile every
allocated success/failure before a FUTURE independently authenticated CPU stage.
This library does not query a scheduler or load any scientific result payload.
"""
import hashlib,json
from pathlib import Path
from .archive_v2 import check_time,canonical
from .terminal_binding_v1 import check_started,TECH,TECH_CONTRACT,TECH_RAW
from .evidence_auth_v1 import bound_json
from wm_diag0_rc1_final_v1.ledger import OLD_ALLOCATED,OLD_UNALLOCATED
from wm_diag0_rc1_recovery_r1.common import OLD,RUN,GRID_HASH,closed_indices

RECOVERY_HASH='4c4c9dbc36302d6089389ea411bfa92dca560849620b5718c52c293fd8554df3'

def parent_location(c,setting,root_index):
    closed_indices(c)
    if type(setting) is not int or not 0<=setting<4 or type(root_index) is not int or not 0<=root_index<32:raise ValueError('exact fixed four cells/32 roots')
    if root_index==0:
        supplier=c['rc1_grid']['technical_suppliers'][str(setting)]
        return Path(supplier['run'])/'tasks'/('technical-'+str(setting)),supplier
    index=setting*31+root_index-1
    return Path(OLD if index<66 else RUN)/'tasks'/('grid-'+str(index)),None

def expected_starts(c,old_raw,recovery_raw):
    closed_indices(c)
    if not isinstance(old_raw,dict) or set(old_raw)!={str(i) for i in range(67)} or not isinstance(recovery_raw,dict) or set(recovery_raw)!={str(i) for i in range(66,124)}:raise ValueError('all67 original including failure, all58 recovery raw IDs')
    values=list(old_raw.values())+list(recovery_raw.values())
    if any(not isinstance(x,str) or not x.isdigit() for x in values) or len(set(values))!=125:raise ValueError('unique literal allocated raw IDs')
    if old_raw['66']!='317411':raise ValueError('actual failed old allocation retained')
    result={}
    for i in (1,2,3):result['317177_'+str(i)]={'path':TECH+'/tasks/technical-'+str(i)+'/controls/STARTED.json','job_id':TECH_RAW[str(i)],'array_job_id':'317177','setting':i,'contract':TECH_CONTRACT['sha256']}
    for dispatch,root,rows,contract in [('317180',OLD,old_raw,GRID_HASH),('317441',RUN,recovery_raw,RECOVERY_HASH)]:
        for key,raw in rows.items():
            index=int(key);result[dispatch+'_'+key]={'path':root+'/tasks/grid-'+key+'/controls/STARTED.json','job_id':raw,'array_job_id':dispatch,'setting':index//31,'index':index,'contract':contract}
    if len(result)!=128:raise ValueError('all128 original newer STARTED controls, plus11 exact old allocations')
    return result

def terminal_ledger(c,raw,old_raw,recovery_raw):
    wants=expected_starts(c,old_raw,recovery_raw)
    if not isinstance(raw,str) or len(raw.encode())>64000:raise ValueError('bounded exact scheduler text')
    expected=dict(OLD_ALLOCATED)
    for logical,w in wants.items():expected[logical]=(w['job_id'],'FAILED' if logical=='317180_66' else 'COMPLETED','125:0' if logical=='317180_66' else '0:0',79 if logical=='317180_66' else None)
    placeholders=set(OLD_UNALLOCATED)|{'317180_[67-123%1]'};found={};allocated=set();seconds=0
    for line in raw.splitlines():
        if not line:continue
        x=line.split('|')
        if len(x)!=7:raise ValueError('exact seven scheduler columns')
        logical,actual,state,exitcode,elapsed,cpus,node=x
        if logical in found or not actual.isdigit() or cpus!='4' or not elapsed.isdigit():raise ValueError('duplicate or invalid exact scheduler metadata')
        found[logical]=x;elapsed=int(elapsed)
        if logical in placeholders:
            if state.split()[0]!='CANCELLED' or elapsed or node!='None assigned' or exitcode!='0:0':raise ValueError('unallocated retained placeholders only')
            continue
        if logical not in expected:raise ValueError('unexpected allocated task cannot be omitted')
        eraw,estate,eexit,etime=expected[logical]
        if actual!=eraw or state!=estate or exitcode!=eexit or node not in ('gpu09','gpu09.cluster') or actual in allocated or not 0<elapsed<=3600 or etime is not None and elapsed!=etime:raise ValueError('exact terminal success/failure/time/raw binding')
        allocated.add(actual);seconds+=elapsed
    if set(found)!=set(expected)|placeholders or len(allocated)!=139 or seconds>468000:raise ValueError('all139 terminal allocated attempts, failures retained and total GPU cap')
    return {'status':'ALL139_RECOVERY_INCLUSIVE_GPU_ATTEMPTS_RECONCILED','allocated_attempts':139,'GPU_charged_seconds':seconds,'GPU_cap':468000,
            'original_failed66_retained_and_charged':True,'original_accepted_grid_parents':66,'recovery_accepted_grid_parents':58,
            'original_newer_start_controls':128,'older_immutable_allocated_attempts':11,'unallocated_placeholders':sorted(placeholders),'CPU_full_future_seconds':6836,'all_scheduler_rows':found}

def authenticate_terminal(c,receipt,expected,deadline):
    body=bound_json(receipt,expected,200000,deadline)
    if set(body)!={'scheduler','old_grid_raw_ids','recovery_grid_raw_ids','started_controls','reconciled'}:raise ValueError('exact externally bound complete terminal receipt')
    wants=expected_starts(c,body['old_grid_raw_ids'],body['recovery_grid_raw_ids'])
    result=terminal_ledger(c,body['scheduler'],body['old_grid_raw_ids'],body['recovery_grid_raw_ids'])
    if canonical(result)!=canonical(body['reconciled']) or set(body['started_controls'])!=set(wants):raise ValueError('independent ledger and all original start identities')
    for logical,want in wants.items():
        check_time(deadline);check_started(bound_json(Path(want['path']),body['started_controls'][logical],4000,deadline),want)
    check_time(deadline)
    return {'status':'ALL139_TERMINAL_AND128_STARTED_CONTROLS_AUTHENTICATED_NOT_FINAL_GATE','allocated_attempts':139,'GPU_charged_seconds':result['GPU_charged_seconds'],
            'started_control_commitment':hashlib.sha256(canonical(body['started_controls'])).hexdigest(),'scientific_payloads_read':False,'scheduler_queries':0,'final_gate_ready':False}
