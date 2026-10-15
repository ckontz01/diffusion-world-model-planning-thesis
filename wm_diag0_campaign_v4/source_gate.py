"""Reconcile all120 source allocations and independently authenticate windows."""
import json,subprocess,sys
from pathlib import Path
from wm_diag0_native_v3.source_accept import accept,ident

def gate(run,expected_job,write=False):
    root=Path(run);d=json.loads((root/'controls/DISPATCH-source.json').read_text())
    if d['job_id']!=expected_job or not expected_job.isdigit():raise ValueError('exact source dispatch')
    queue=subprocess.check_output(['squeue','-h','-j',expected_job,'-o','%i|%T'],universal_newlines=True,timeout=10)
    accounting=subprocess.check_output(['sacct','-X','-n','-P','-j',expected_job,'--format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS'],universal_newlines=True,timeout=15)
    if queue.strip():return {'status':'SOURCE_STILL_ACTIVE','exact_job_id':expected_job,'queue':queue,'scheduler':accounting}
    if (root/'controls/STOP.json').exists():return {'status':'SOURCE_STOP','STOP':json.loads((root/'controls/STOP.json').read_text()),'scheduler':accounting}
    rows=[line.split('|') for line in accounting.splitlines() if line.strip()]
    if len(rows)!=120 or {x[0] for x in rows}!={expected_job+'_'+str(i) for i in range(120)}:raise ValueError('every source allocation must be terminal and unambiguous')
    if any(x[1]!='COMPLETED' or x[2]!='0:0' or x[4]!='4' for x in rows):raise ValueError('source allocation failures require finite diagnosed recovery')
    charge=sum(int(x[3]) for x in rows)
    if charge>7200 or 17+charge+3600+1800>13800:raise ValueError('cumulative source+full future CPU reserve')
    plan=json.loads((root/'source/ROOT-PLAN.json').read_text());seals={};accepted=[]
    for row in plan['roots']:
        key=row['task']+'-'+str(row['root_index']).zfill(3);task=root/'tasks'/key
        control=json.loads((task/'controls/RESULT.json').read_text())
        if control['status']!='ACCEPTED' or not control['acceptance']['available']:raise ValueError('all required windows, no replacement')
        seal=control['acceptance']['seal'];proof=accept(task/'output',seal,row)
        if not proof['available']:raise ValueError('missing fixed source/goal')
        seals[key]=seal;accepted.append(proof)
    result={'status':'ALL120_SOURCE_WINDOWS_INDEPENDENTLY_ACCEPTED','exact_job_id':expected_job,'source_seals':seals,
            'cpu_source_allocation_seconds':charge,'cpu_total_with_preflight':17+charge,'cpu_full_future_after_source':5400,
            'gpu_full_future_original_cap':468000,'scheduler':accounting,'roots':accepted,'source_run':str(root),
            'source_contract':ident(root/'source/CONTRACT.json'),'scientific_aggregates_read':False}
    if write:
        with (root/'controls/ALL-SOURCES-ACCEPTED.json').open('x') as f:json.dump(result,f,sort_keys=True)
    return result

if __name__=='__main__':print(json.dumps(gate(sys.argv[1],sys.argv[2])))
