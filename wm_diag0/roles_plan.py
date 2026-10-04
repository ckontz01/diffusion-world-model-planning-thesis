"""Outcome-free BIND1 role/row proposal from immutable cohort metadata only."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/world-model-diagnostic-20261004'
COHORT_SHA='27bf5ff45108242dfffb90c35ea083bb3bfe2f7a55542303c517dffbf96380b1'
ROLE_SHA='62b06d8c3c5850904c49f3c774d462220ae5f06601b5d58f384636951523f578'

def authenticated_metadata(path, expected):
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:
        raise ValueError('Historical metadata identity changed; no implicit namespace override')
    return json.loads(data)

def propose():
    cohort=authenticated_metadata(ROOT/'docs/dtv-success-cost-20261001/COHORT.json',COHORT_SHA)
    reconciled=authenticated_metadata(ROOT/'docs/dtv-success-cost-20261001/ROLE-RECONCILIATION.json',ROLE_SHA)
    roles={'status':'PROPOSED_NOT_ALLOCATED','version':'bind1-v2','payload_reads':0,
           'rule':"SHA256(UTF8('wm-diag0-discovery-reuse-v2|TASK|PARENT|20261004')), then integer parent ID; lowercase TASK",
           'exposure':'Previously exposed, outcome-informed discovery; selection reads metadata only, not outcomes',
           'cohort_sha256':COHORT_SHA,'historical_role_sha256':ROLE_SHA,
           'reviewed_unexecuted_proposal':'history/preparation-v1/ROLE-PROPOSAL.json',
           'historical_publication':'cf216e5312ab32a7f7097a38d3f2396e34c2a37e',
           'unused_parent_allocation':False,'checkpoint_training_parent_overlap':'Unknown; not training-held-out confirmation'}
    rows={'domain':'metadata-only','status':'PROPOSED_NOT_ALLOCATED','payload_reads':0,'version':'bind1-v2','tasks':{}}
    pool={'status':'EXPOSED_METADATA_ONLY','payload_reads':0,'cohort_sha256':COHORT_SHA,'parents':{}}
    for task in ('pusht','reacher'):
        by_id={x['parent_id']:x for x in cohort[task]}
        if len(by_id)!=320 or any(x['partition']!='P2' or x['task']!=task for x in by_id.values()):
            raise ValueError('Canonical cohort namespace')
        if not set(by_id)<=set(reconciled[task]['eligible_parents']):
            raise ValueError('Conflicting historical role; no automatic override')
        ids=sorted(by_id,key=lambda p:(hashlib.sha256(f'wm-diag0-discovery-reuse-v2|{task}|{p}|20261004'.encode()).hexdigest(),p))
        pool['parents'][task]=sorted(by_id)
        roles[task]={'master_sha256':reconciled[task]['master_sha256'],'reused_pool_count':320,
                     'diagnostic':ids[:32],'fit':ids[32:48],'validation':ids[48:60],
                     'unused_eligible_preserved':len(set(reconciled[task]['eligible_parents'])-set(by_id))}
        entries=[]
        for role in ('diagnostic','fit','validation'):
            for parent in roles[task][role]:
                x=by_id[parent];length=x['parent_length']
                if length<31:raise ValueError('Insufficient length; no source substitution')
                offset=x['source_row']-x['start_step'];start=min(200,(length-25)//2)
                if offset<0 or start+24>=length or start<2:raise ValueError('Source/history rows')
                count={'diagnostic':0,'fit':16,'validation':8}[role]
                frames=[2+i*(length-3)//(count-1) for i in range(count)] if count else []
                if len(set(frames))!=count:raise ValueError('Insufficient unique readout rows')
                entries.append({'task':task,'role':role,'parent':parent,'partition':'P2','length':length,
                    'episode_offset':offset,'source_step':start,'goal_step':start+24,
                    'source_row':offset+start,'goal_row':offset+start+24,'replay_actions':start,
                    'readout_steps':frames,'readout_rows':[offset+s for s in frames],
                    'historical_cohort_source_index':x['source_index']})
        rows['tasks'][task]={'master_sha256':reconciled[task]['master_sha256'],
                            'offset_source':'Authenticated completed DTV cohort, source_row minus start_step; HDF5 schema remains unbound',
                            'entries':entries}
    return {'ROLE-PROPOSAL.json':roles,'SOURCE-ROWS-PROPOSED.json':rows,'EXPOSED-POOL-METADATA.json':pool}

if __name__=='__main__':print(json.dumps(propose(),sort_keys=True))
