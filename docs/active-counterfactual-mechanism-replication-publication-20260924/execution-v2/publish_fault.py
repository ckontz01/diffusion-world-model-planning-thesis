"""Publish technical evidence without the unrelated site balance footer."""
import sys
from pathlib import Path
import datetime

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-mechanism-replication-20260924/runtime-v2'
sys.path.insert(0,str(ROOT))
import common as c

raw=HERE/'FAULT-RECONCILIATION.json'
transport=c.read(raw)
c.require(transport['returncode']==0,'Reconciliation must have succeeded')
e=c.json.loads(transport['stdout'])
c.require(e['independent_charges']['attempts']==1 and not e['independent_charges']['live_allocations'] and not e['independent_charges']['ambiguous_submissions'],'Exact finite stopped state')
c.require(e['control_records']['STOP.json'] and e['process']['exists'] is False,'Controller fail-stop confirmed')
for name,record in e['worker_logs'].items():
    if name.endswith('.slurm.out'):
        record.pop('text')
        record['publication_note']='Unrelated site account-balance footer omitted from publication only. Original bytes retained unchanged on cluster and in the local raw reconciliation receipt; hash/length preserved here.'
e['raw_local_receipt_sha256']=c.sha(raw)
e['observation_utc']=datetime.datetime.fromtimestamp(e['unix'],datetime.timezone.utc).isoformat()
e['automatic_retry']=False
e['research_task_successes']=0
e['technical_tranche']='NOT_REACHED; no evaluation submitted'
c.write(HERE/'FAULT-TECHNICAL.json',e)
summary={n:c.sha(HERE/n) for n in ('AUTHORIZATION.json','EXECUTION-APPROVAL.json','PRELAUNCH.json','PRELAUNCH-REMOTE.json','STAGE.json','STAGE-READBACK.json','LAUNCH.json','LAUNCH-OBSERVATION.json','FAULT-TECHNICAL.json')}
c.write(HERE/'RECEIPTS.json',dict(files=summary,source_manifest=c.sha(ROOT/'SOURCE-MANIFEST.json'),false_approval=c.sha(ROOT/'EXECUTION-APPROVAL.json'),source_export=c.sha(ROOT/'SOURCE-PACKAGE.tar'),raw_local_receipt=dict(path=raw.name,sha256=c.sha(raw),publication='not tracked; raw originals retained without deletion or rewrite'),no_retry=True))
print(c.json.dumps(dict(observation_utc=e['observation_utc'],approval=e['approval'],charges=e['independent_charges'],fault_receipt_sha256=c.sha(HERE/'FAULT-TECHNICAL.json'),receipts_sha256=c.sha(HERE/'RECEIPTS.json'))))
