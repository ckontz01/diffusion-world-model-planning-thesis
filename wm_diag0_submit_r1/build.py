import hashlib,json
from .common import DOC,BASE,ROOT,SOURCE_COMMIT,identity,write_new

def main():
    r=json.loads((BASE/'campaign/SUBMISSION-RECONCILIATION-001.json').read_text());q=json.loads((BASE/'campaign/QOS-DIAGNOSIS-001.json').read_text())
    if r['known_exact_job_ids'] or r['current_study_queue'] or r['task_directories'] or 'DAG-DISPATCH.json' in r['controls']:raise ValueError('every ambiguous/live/accepted allocation must be reconciled before action')
    if r['controls']['SBATCH-readout-RESPONSE.json']['stderr']!='sbatch: error: Batch job submission failed: Invalid qos specification\n':raise ValueError('exact diagnosed nonallocation fault')
    if q['user']!='ckontzias' or q['own_associations']['returncode'] or q['partition']['returncode']:raise ValueError('existing configured scheduler route only')
    rows=[x.split('|') for x in q['own_associations']['stdout'].splitlines()]
    if not any(x[0]=='ckontzias' and 'normal-a6000' in x[3].split(',') for x in rows) or 'AllowQos=normal-a6000,' not in q['partition']['stdout']:raise ValueError('no new account/QOS/security authority')
    c={'repair':'explicit already-authorized normal-a6000 GPU QOS instead of incompatible default normal',
       'source_commit_unchanged':SOURCE_COMMIT,'scientific_contract':identity(BASE/'campaign/CONTRACT.json'),
       'new_submission_attempts_max':1,'research_tasks_recomputed':0,'GPU_seconds_previously_allocated':0,
       'CPU_charged_before':1436,'CPU_full_future':5400,'CPU_cap':13800,'GPU_full_future':468000,'GPU_cap':468000,
       'account_or_permission_changes':False,'QOS_GPU':'normal-a6000','QOS_CPU':'existing normal default',
       'old_failure_evidence_preserved':True,'reconciliation':identity(BASE/'campaign/SUBMISSION-RECONCILIATION-001.json'),
       'qos_diagnosis':identity(BASE/'campaign/QOS-DIAGNOSIS-001.json'),'preparation':'covered by native-v3 full2000s charge; no refund or duplicate charge'}
    write_new(DOC/'CONTRACT.json',c);print(json.dumps(c))

if __name__=='__main__':main()
