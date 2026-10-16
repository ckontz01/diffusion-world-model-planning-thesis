"""Artificial return-code/pipe-data decoder checks, ZERO external processes."""
import ast,hashlib,json
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .compact import failure,interpret,program,PROGRAM_SHA,GRID_HASH


def main():
    for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text(),feature_version=(3,6))
    assert hashlib.sha256(program().encode()).hexdigest()==PROGRAM_SHA
    for code in (1,124,137,255):
        z,e=interpret(code,b'',b'')
        assert z is None and e['transport_returncode']==code and not e['research_failure_inferred']
        assert e['captured']['stderr']['bytes']==0 and not e['automatic_retry']
    z,e=interpret(255,b'local transport message',b'synthetic existing route unavailable')
    assert e['captured']['stdout']['bytes']==23
    import base64
    assert base64.b64decode(e['captured']['stderr']['retained_prefix_base64'])==b'synthetic existing route unavailable'
    e=failure(None,b'partial',b'','NATIVE_TRANSPORT_TIMEOUT_NO_RESEARCH_INFERENCE')
    assert e['transport_returncode'] is None and not e['research_failure_inferred']
    assert interpret(0,b'not JSON',b'')[1]['failure_kind']=='INVALID_COMPACT_TECHNICAL_METADATA_STOP'
    z,e=interpret(0,json.dumps({'dispatch':{'array_job_id':'317180','contract_sha256':GRID_HASH,'indices':124},
                       'scientific_values_or_quality_or_aggregates_inspected':False,
                       'research_jobs_or_controllers_changed':False,'status':'SYNTHETIC_TEST_ONLY'}).encode(),b'')
    assert e is None and z['status']=='SYNTHETIC_TEST_ONLY'
    for row in (dict(z,scientific_values_or_quality_or_aggregates_inspected=True),dict(z,research_jobs_or_controllers_changed=True)):
        assert interpret(0,json.dumps(row).encode(),b'')[1] is not None
    big=failure(1,b'x'*16001,b'y'*16001,'SYNTHETIC_BOUND')
    assert big['captured']['stdout']['truncated'] and len(json.dumps(big).encode())<50000
    failed=ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/LOCAL-RESUMEOBS003.json'
    actual=json.loads(failed.read_text())
    if actual['status']!='CHILD_NONZERO' or 'bounded observation unavailable, not inferred research failure:' not in actual['stdout']:raise ValueError('exact preserved monitor failure')
    result={'status':'ARTIFICIAL_MONITOR_DIAGNOSTIC_WRAPPER_PASSED',
            'sources':{p.name:identity(p) for p in Path(__file__).parent.glob('*.py')},
            'unchanged_observer_program_sha256':PROGRAM_SHA,'preserved_failed_observation':identity(failed),
            'checks':['integer return codes including empty stderr preserved','bounded stdout/stderr prefix bytes and whole hashes',
                      'timeout distinguished without research inference','invalid metadata fail closed',
                      'exact program digest unchanged','no scientific or research-mutation schema accepted'],
            'actual_cluster_or_SSD_accessed':False,'external_processes_launched':0,'research_calls':0,
            'R003_retried':False,'underlying_transport_cause_diagnosed':False,'final_gate_ready':False}
    DOC.mkdir(exist_ok=True);write_new(DOC/'ARTIFICIAL-001.json',result)
    print(json.dumps({'status':result['status'],'research_calls':0,'underlying_transport_cause_diagnosed':False}))


if __name__=='__main__':main()
