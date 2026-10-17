"""Bind terminal GPU accounting to all127 actual new STARTED controls.

No scheduler query, submission, research payload read or allocation authority.
The future frozen stage binds the complete receipt identity externally. Its
reconciled flag alone is never sufficient: originals are reauthenticated here.
The eleven older allocated attempts remain exact immutable ledger constants.
"""
import hashlib,math
from pathlib import Path
from .archive_v2 import canonical,check_time
from .evidence_auth_v1 import bound_json
from .preservation_layout_v1 import GRID
from wm_diag0_rc1_final_v1.ledger import reconcile

RUN='/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/campaign-v4-rc1-grid-v1'
TECH=RUN.replace('campaign-v4-rc1-grid-v1','campaign-v4-rc1-technical-v1')
TECH_CONTRACT={'bytes':151647,'sha256':'101cd417d9a823a559a29d3813887ad17f721b450ce4f21d267b597e4ef788fd'}
TECH_RAW={'1':'317178','2':'317179','3':'317177'}


def expected_starts(c,body):
    if c['run']!=RUN or c['rc1_grid']['technical_run']!=TECH or canonical(c['rc1_grid']['technical_contract'])!=canonical(TECH_CONTRACT):
        raise ValueError('exact frozen actual grid/technical lineage')
    if body.get('grid_dispatch')!='317180' or body.get('technical_raw_ids')!=TECH_RAW:
        raise ValueError('actual dispatch and all three accepted technical raw IDs')
    raw=body.get('grid_raw_ids')
    if not isinstance(raw,dict) or set(raw)!={str(i) for i in range(124)} or any(not isinstance(x,str) or not x.isdigit() for x in raw.values()):
        raise ValueError('all124 exact noncoerced raw-ID strings')
    out={}
    for i in (1,2,3):
        out['317177_'+str(i)]={'path':TECH+'/tasks/technical-'+str(i)+'/controls/STARTED.json',
            'job_id':TECH_RAW[str(i)],'array_job_id':'317177','setting':i,'contract':TECH_CONTRACT['sha256']}
    for i in range(124):
        out['317180_'+str(i)]={'path':RUN+'/tasks/grid-'+str(i)+'/controls/STARTED.json',
            'job_id':raw[str(i)],'array_job_id':'317180','setting':i//31,'index':i,'contract':GRID['sha256']}
    return out


def check_started(record,want):
    fields=(set(want)-{'path'})|{'PID','start_ticks','node','time'}
    if not isinstance(record,dict) or set(record)!=fields:raise ValueError('complete exact original STARTED schema')
    for k,v in want.items():
        if k!='path' and canonical(record[k])!=canonical(v):raise ValueError('STARTED raw/index/setting/source identity changed')
    if type(record['PID']) is not int or record['PID']<=0 or not isinstance(record['start_ticks'],str) or not record['start_ticks'].isdigit():
        raise ValueError('original nonboolean PID and literal start ticks')
    if record['node'] not in ('gpu09','gpu09.cluster') or type(record['time']) not in (int,float) or not math.isfinite(record['time']) or record['time']<=0:
        raise ValueError('original compute-node/time metadata')


def check_terminal(c,body,load_started,deadline):
    """load_started is reviewed bound_json adapter, never artifact-supplied code."""
    if set(body)!={'grid_dispatch','scheduler','technical_raw_ids','grid_raw_ids','reconciled','started_controls'}:
        raise ValueError('exact failure-inclusive receipt schema')
    wants=expected_starts(c,body);starts=body['started_controls']
    if not isinstance(starts,dict) or set(starts)!=set(wants):raise ValueError('every127 original STARTED control required')
    if not isinstance(body['scheduler'],str) or len(body['scheduler'].encode())>64000:raise ValueError('bounded exact scheduler metadata')
    accounting=reconcile(body['scheduler'],'317180',{int(k):v for k,v in TECH_RAW.items()},
                         {int(k):v for k,v in body['grid_raw_ids'].items()})
    if canonical(accounting)!=canonical(body['reconciled']):raise ValueError('independent138 failure-inclusive terminal accounting disagreement')
    for logical,want in sorted(wants.items()):
        check_time(deadline);check_started(load_started(want['path'],starts[logical],deadline),want)
    raw=canonical(starts);check_time(deadline)
    return {'status':'ALL138_GPU_TERMINAL_ROWS_AND127_NEW_ORIGINAL_START_CONTROLS_BOUND',
            'allocated_attempts':138,'original_start_controls_authenticated':127,
            'older_exact_allocated_attempts_bound_by_immutable_ledger':11,
            'GPU_charged_seconds':accounting['GPU_charged_seconds'],
            'complete_start_identity_map':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
            'scheduler_queries':0,'scientific_payloads_read':False,'final_gate_ready':False}


def authenticate_terminal(c,receipt,expected,deadline):
    body=bound_json(receipt,expected,200000,deadline)
    def read_start(path,want,end):return bound_json(Path(path),want,4000,end)
    return check_terminal(c,body,read_start,deadline)
