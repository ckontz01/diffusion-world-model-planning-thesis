"""Local-only disposition of retained R006 diagnostic bytes; never retry WSL."""
import ast,base64,hashlib,json
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,identity,write_new

FAILURE={'bytes':1791,'sha256':'8dfe3f32ec206fa837575a5dda582f94fe05c64190a9d956da34eff738cff171'}


def main():
    p=DOC/'OBSERVE-R006.failure.json'
    if identity(p)!=FAILURE:raise ValueError('exact new retained failure, never a repeated observation')
    z=json.loads(p.read_text());local=json.loads((DOC/'LOCAL-RESUMEOBS006.json').read_text())
    if z['dispatch']!='317180' or z['transport_returncode']!=4294967295 or z['research_failure_inferred'] is not False or local['status']!='CHILD_NONZERO' or local['charged_seconds']!=30:
        raise ValueError('exact transport/local receipt chain')
    stdout=z['captured']['stdout'];raw=base64.b64decode(stdout['retained_prefix_base64'],validate=True)
    if stdout['truncated'] or len(raw)!=stdout['bytes'] or hashlib.sha256(raw).hexdigest()!=stdout['sha256']:raise ValueError('complete exact retained stdout bytes')
    message=raw.decode('utf-16-le',errors='strict')
    disk='D:\\WSL\\Thesis-Ubuntu\\ext4.vhdx'
    if disk not in message or 'Wsl/Service/CreateInstance/MountDisk/ERROR_PATH_NOT_FOUND' not in message or 'Failed to attach disk' not in message:
        raise ValueError('do not infer a different cause from unknown output')
    err=z['captured']['stderr']
    if err['bytes']!=0 or err['sha256']!=hashlib.sha256(b'').hexdigest():raise ValueError('exact retained empty stderr')
    ast.parse(Path(__file__).read_text(),feature_version=(3,6))
    result={'status':'LOCAL_WSL_CONFIGURED_DISK_PATH_UNAVAILABLE_NO_RESEARCH_FAILURE_INFERENCE',
        'source':identity(__file__),'evidence':{'failure':FAILURE,'local':identity(DOC/'LOCAL-RESUMEOBS006.json'),
            'started':identity(DOC/'OBSERVE-R006.started.json')},
        'retained_stdout_encoding':'utf-16-le','retained_stdout_bytes':len(raw),'retained_stdout_sha256':stdout['sha256'],
        'configured_disk_path_reported_by_WSL':disk,'error_code':'Wsl/Service/CreateInstance/MountDisk/ERROR_PATH_NOT_FOUND',
        'diagnosed_scope':'saved WSL attachment error only; reason disk/path unavailable not determined',
        'current_cluster_health':'UNVERIFIED','older_R003_cause_retrospectively_inferred':False,
        'cluster_or_research_fault_inferred':False,'research_jobs_or_controllers_changed':False,
        'WSL_disk_path_or_configuration_changed':False,'automatic_retry':False,
        'next_remote_observation':'new exclusive R007 or later at a scheduled wake ONLY after the existing configured disk path is available; never retry R006',
        'required_human_action':'restore access to the existing configured disk/path, or direct how to proceed; do not recreate/migrate/change WSL automatically',
        'same_monitor_remains_active':'quiet while unchanged local blocker; no new monitor or sleeping loop',
        'new_network_WSL_cluster_SSD_or_research_calls':0,'scientific_values_read':False,'final_gate_ready':False}
    target=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/TRANSPORT-PATH-BLOCKER-007.json'
    write_new(target,result,limit=12000)
    print(json.dumps({'status':result['status'],'required_human_action':result['required_human_action'],'new_cluster_queries':0}))


if __name__=='__main__':main()
