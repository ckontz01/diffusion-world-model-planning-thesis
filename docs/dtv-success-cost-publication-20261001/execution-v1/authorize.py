"""Create separate operational authority; never change the scientific closure."""
import hashlib,json,time
from pathlib import Path
from dtv_success_cost.common import ROOT,DOC,load,sha,write
from dtv_success_cost.package import files
from dtv_success_cost.preserve import verify_archive,volume

HERE=Path(__file__).resolve().parent
INSTRUCTION=Path('C:/Users/Chris/.codex/attachments/af83d7d2-1d3a-4306-9c5c-792506c79651/Pasted text.txt')
EXPECTED=dict(publication='b5380b4b29ac9a94ad97da5f617bec4d78c8178e',package='3826f23ccf5ad33479943d819f04c293cccbc79a62bed4d03e3ad7134dd82b04',bindings='bc3b36c71362f17238ddb9a6fcd04846c0fafac488b41b26f6be2e74eb598866',cohort='27bf5ff45108242dfffb90c35ea083bb3bfe2f7a55542303c517dffbf96380b1',export='31b997e7628b424f7b36fc084f4622c4e1526a9a1db2137e3684ec6f8466de97')

def copy_bytes(path,data):
    with path.open('xb') as f:f.write(data)

def main():
    if (HERE/'AUTHORIZATION.json').exists():raise RuntimeError('authority already created; no regeneration')
    for key,name in [('package','PACKAGE-MANIFEST.json'),('bindings','BINDINGS.json'),('cohort','COHORT.json')]:
        if sha(DOC/name)!=EXPECTED[key]:raise RuntimeError('approved immutable binding mismatch')
    manifest=load(DOC/'PACKAGE-MANIFEST.json')
    if manifest['files']!=files():raise RuntimeError('frozen package changed')
    if load(DOC/'EXECUTION-APPROVAL.json')['execute'] is not False:raise RuntimeError('false template changed')
    backup=load(DOC/'SSD-BACKUP.json');archive=Path(backup['archive']);ssd=volume()
    if archive.stat().st_size!=19415040 or sha(archive)!=EXPECTED['export']:raise RuntimeError('SSD export bytes mismatch')
    rows=manifest['files']+[dict(path='PACKAGE-MANIFEST.json',bytes=(DOC/'PACKAGE-MANIFEST.json').stat().st_size,sha256=EXPECTED['package'])]
    if verify_archive(archive,rows)!=445:raise RuntimeError('SSD export member scope')
    instruction=INSTRUCTION.read_bytes()
    for value in EXPECTED.values():
        if value.encode() not in instruction:raise RuntimeError('instruction lacks exact approved identity')
    copy_bytes(HERE/'AUTHORIZATION-INSTRUCTION.txt',instruction)
    prior=ROOT/'docs/local-goal-source-replication-publication-20260920/execution-v6/AUTHORIZATION-PROVENANCE.md'
    copy_bytes(HERE/'DELEGATION-PROVENANCE.txt',prior.read_bytes())
    root='/lustreFS/data/superworld/ckontzias/thesis'
    source=root+'/snapshots/dtv-success-cost-20261001-'+EXPECTED['package'][:16]
    control=root+'/staging/dtv-success-cost-20261001-'+EXPECTED['package'][:16]
    run=root+'/experiments/dtv-success-cost-20261001/run-'+EXPECTED['bindings'][:16]
    keys=dict(study='DTV-EFF1',execute=True,research_execution_authorized=True,package_sha256=EXPECTED['package'],bindings_sha256=EXPECTED['bindings'],cohort_sha256=EXPECTED['cohort'],source_role='DTV-EFF1-P2-320-per-task')
    authority=dict(**keys,authorization_basis='Exact user-supplied execution direction under the standing delegation; not a newly obtained direct user signature',instruction_sha256=sha(HERE/'AUTHORIZATION-INSTRUCTION.txt'),delegation_provenance_sha256=sha(HERE/'DELEGATION-PROVENANCE.txt'),browser_origin_reverified_this_turn=False,publication=EXPECTED['publication'],source_export_sha256=EXPECTED['export'],source=source,control=control,run=run,created_unix=time.time(),no_automatic_retry=True,no_automation=True,limits=dict(successful_tasks=2882,gpu_workers=2880,episodes=23040,gpu_allocation_seconds=864000,cpu_stage_allocation_wall_seconds=14400,serial_gpu=1,cpus=4,ram_bytes=8589934592,worker_bytes=1000000,worker_logs_bytes=100000,source_bytes=20000000,control_bytes=100000000,analysis_bytes=40000000,live_bytes=4000000000,archive_bytes=4200000000,inclusive_bytes=13000000000))
    write(HERE/'AUTHORIZATION.json',authority)
    approval=dict(**keys,authorization_record=control+'/AUTHORIZATION.json',authorization_sha256=sha(HERE/'AUTHORIZATION.json'))
    write(HERE/'EXECUTION-APPROVAL.json',approval)
    local=dict(approval,authorization_record=str(HERE/'AUTHORIZATION.json'))
    write(HERE/'EXECUTION-APPROVAL-WINDOWS.json',local)
    identity=dict(source=source,control=control,run=run,control_python=root+'/envs/hi-lewm-artifact-py311-cu121-swm006/bin/python',**{k+'_sha256':v for k,v in EXPECTED.items() if k!='publication'},publication=EXPECTED['publication'],authority_sha256=sha(HERE/'AUTHORIZATION.json'),enabled_approval_sha256=sha(HERE/'EXECUTION-APPROVAL.json'),windows_approval_sha256=sha(HERE/'EXECUTION-APPROVAL-WINDOWS.json'),instruction_sha256=sha(HERE/'AUTHORIZATION-INSTRUCTION.txt'),export_bytes=19415040,export_members=445,archive=str(archive))
    write(HERE/'IDENTITIES.json',identity)
    write(HERE/'SSD-PRELAUNCH.json',dict(volume=ssd,archive_sha256=EXPECTED['export'],bytes=19415040,members=445,whole_and_every_member_verified=True,new_backup_cycle=False,observed_unix=time.time()))
    print(json.dumps(identity))

if __name__=='__main__':main()
