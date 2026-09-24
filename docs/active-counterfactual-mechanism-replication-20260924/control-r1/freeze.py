"""Freeze and back up only the new small recovery package; no research submission."""
import r1 as r
import argparse
from pathlib import Path
import tarfile
import shutil
import time
from preserve import ssd,verify_tar
from transport import PUB

def contract():
    r.require(not (r.ROOT/'CONTRACT.json').exists(),'Exclusive contract')
    baseline=r.read(r.ROOT/'BASELINE.json')
    r.write(r.ROOT/'CONTRACT.json',dict(schema='ACVM1-R1-finite-recovery',instruction_sha256=r.sha(r.ROOT/'INSTRUCTION.txt'),authority='New direct user technical-repair and launch authorization; historical delegation records unchanged',baseline_sha256=r.sha(r.ROOT/'BASELINE.json'),science_manifest=r.SCIENCE,worker_approval=r.APPROVAL,grid=r.c.bindings()['grid'],roles=r.c.bindings()['ROLES.json'],model_reuse=r.c.bindings()['MODEL-REUSE.json'],old_failed_job='304589',old_failed_key='fit-pair1-joint',old_attempts=1,max_new_attempts=8197,max_total_attempts=8198,successful_logical_tasks=8197,evaluation_episodes=8192,replacement_attempts=1,never_submitted_tasks=8196,prior_gpu_seconds=baseline['prior_gpu_seconds'],prior_cpu_seconds=baseline['prior_cpu_seconds'],caps=r.c.caps(),local_test_wall_seconds=3600,local_threads=4,local_ram_gib=8,local_bytes=250000000,scientific_changes=False,no_automatic_retry_in_package=True))

def freeze():
    test=r.read(r.ROOT/'TEST-RECEIPT.json');r.require(test['passed'],'Integration required')
    for n,h in test['tested_sources'].items():r.require(r.sha(r.ROOT/n)==h,'Source changed after tests: '+n)
    rows=r.c.lines(r.ROOT/'TEST-ATTEMPTS.jsonl')
    r.require({x['label'] for x in rows if x['state']=='started'}=={x['label'] for x in rows if x['state']=='finished'},'Unreconciled local test')
    r.require(sum(x.get('wall_seconds',0) for x in rows)<=3600 and r.c.bytes_in(r.ROOT)<=250000000,'Preparation bounds')
    r.c.source_check()
    files={p.name:r.sha(p) for p in r.ROOT.iterdir() if p.is_file() and p.name not in ('SOURCE-MANIFEST.json',)}
    r.write(r.ROOT/'SOURCE-MANIFEST.json',dict(schema='ACVM1-control-r1-source',files=files,scientific_source_unchanged=r.SCIENCE))
    PUB.mkdir(exist_ok=False,parents=True)
    a=dict(schema='ACVM1-recovery-r1',authorized=True,instruction=(r.ROOT/'INSTRUCTION.txt').read_text(encoding='utf8'),binding=r.binding())
    r.write(PUB/'EXECUTION-APPROVAL.json',a)
    disabled=dict(a,authorized=False);r.write(PUB/'DISABLED-TEMPLATE.json',disabled)
    tar=PUB/'SOURCE-PACKAGE.tar'
    with tar.open('xb') as stream,tarfile.open(fileobj=stream,mode='w') as t:
        for p in sorted(r.ROOT.iterdir()):
            if p.is_file():t.add(p,arcname=p.name,recursive=False)
    r.require(tar.stat().st_size<=2000000,'Small recovery export cap')
    r.write(PUB/'FREEZE.json',dict(unix=time.time(),binding=r.binding(),approval=r.sha(PUB/'EXECUTION-APPROVAL.json'),package_sha256=r.sha(tar),package_bytes=tar.stat().st_size,test_receipt=r.sha(r.ROOT/'TEST-RECEIPT.json'),wall_seconds=sum(x.get('wall_seconds',0) for x in rows),peak_job_memory_bytes=max(x.get('peak_job_memory_bytes',0) for x in rows)))
    print(r.c.json.dumps(r.read(PUB/'FREEZE.json')))

def backup():
    volume=ssd();tar=PUB/'SOURCE-PACKAGE.tar';b=r.binding()
    dest=Path('D:/THESIS-BACKUPS/active-counterfactual-mechanism-replication-v1')/('recovery-r1-'+b['manifest'][:16]);dest.mkdir(exist_ok=False,parents=True)
    copied=dest/'SOURCE-PACKAGE.tar'
    with tar.open('rb') as src,copied.open('xb') as out:shutil.copyfileobj(src,out)
    expected={p.name:dict(bytes=p.stat().st_size,sha256=r.sha(p)) for p in r.ROOT.iterdir() if p.is_file()}
    verified=verify_tar(copied,expected)
    r.require(verified['sha256']==r.sha(tar) and verified['bytes']==tar.stat().st_size,'SSD whole source copy')
    for name in ('EXECUTION-APPROVAL.json','DISABLED-TEMPLATE.json','FREEZE.json'):
        with (PUB/name).open('rb') as src,(dest/name).open('xb') as out:shutil.copyfileobj(src,out)
        r.require(r.sha(PUB/name)==r.sha(dest/name),'SSD authority receipt copy')
    receipt=dict(unix=time.time(),volume=volume,ssd_path=str(copied),archive=verified,manifest=b['manifest'],approval=r.sha(dest/'EXECUTION-APPROVAL.json'))
    r.write(dest/'PACKAGE-VERIFIED.json',receipt);r.write(PUB/'PACKAGE-VERIFIED.json',receipt)
    print(r.c.json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['contract','freeze','backup']);a=p.parse_args()
    {'contract':contract,'freeze':freeze,'backup':backup}[a.operation]()
