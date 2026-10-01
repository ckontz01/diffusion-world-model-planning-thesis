"""Exclusive small R4 source export and verified authority copy."""
import argparse
import json
import shutil
import time
from pathlib import Path
from dtv_success_cost.common import ROOT,DOC,load,write,sha
from dtv_success_cost.preserve import make_archive,volume
HERE=ROOT/'docs/dtv-success-cost-publication-20261001/recovery-r4'
EXCLUDED={'PACKAGE-MANIFEST.json','AUTHORIZATION.json','EXECUTION-APPROVAL.json','IDENTITIES.json','SSD-BACKUP.json','PUBLICATION.json'}
def files():
    paths=list((ROOT/'dtv_success_cost_r4').glob('*.py'))+[p for p in HERE.iterdir() if p.is_file() and p.name not in EXCLUDED and not p.name.startswith(('STAGE-','LAUNCH-','OBSERVATION-'))]
    return [dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(paths)]
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','authorize','backup','identify']);a=p.parse_args();manifest=HERE/'PACKAGE-MANIFEST.json'
    if a.mode=='authorize':
        m=load(manifest)
        if m['files']!=files():raise RuntimeError('frozen source changed')
        old=load(HERE.parent/'recovery-r3/IDENTITIES.json');digest=sha(manifest);prefix=digest[:16]
        base='/lustreFS/data/superworld/ckontzias/thesis';suffix='dtv-success-cost-control-r4-20261001-'+prefix
        source=base+'/snapshots/'+suffix;control=base+'/staging/'+suffix
        authority=dict(study='DTV-EFF1-R4',execute=True,authorization_basis='Direct current user instruction: FIX IT AND RESUME; finite diagnosed PushT coordinate round-trip verification recovery',
            created_unix=time.time(),instruction_sha256=sha(HERE/'AUTHORIZATION-INSTRUCTION.txt'),recovery_manifest_sha256=digest,
            lineage_sha256=sha(HERE/'LINEAGE.json'),bindings_sha256=old['bindings_sha256'],cohort_sha256=old['cohort_sha256'],
            original_package_sha256=old['package_sha256'],source_role='DTV-EFF1-P2-320-per-task',scientific_source=old['source'],
            recovery_source=source,recovery_control=control,original_control=old['control'],r1_source=old['r1_source'],r1_control=old['r1_control'],r2_source=old['r2_source'],r2_control=old['r2_control'],r3_source=old['recovery_source'],r3_control=old['recovery_control'],run=old['run'],
            worker_approval=old['control']+'/EXECUTION-APPROVAL.json',worker_approval_sha256=old['enabled_approval_sha256'],
            remaining_gpu_workers=2853,remaining_cpu_analysis=1,replacement_allowance=1,replacement_task='pusht-3819-6101',failed_allocation='312950',
            carried_gpu_seconds=1622,carried_cpu_seconds=178,expected_logical_tasks=2882,expected_attempts=2885,scientific_changes=False,resource_expansion=False,
            automatic_retry=False,no_automation=True,
            limits=dict(gpu_seconds=864000,cpu_seconds=14400,full_gpu_reservation_with_carry=857522,full_cpu_reservation_with_carry=7378,
                        serial_gpu=1,cpus=4,ram_bytes=8*1024**3,source_bytes=20000000,control_bytes=100000000,live_bytes=4000000000,archive_bytes=4200000000,inclusive_bytes=13000000000),
            preparation=dict(previous_accounted_and_reserved_seconds=7530.894,reservation_seconds=1800,total_reserved_seconds=9330.894,
                             actual_suites_seconds=sum(load(p)['wall_seconds'] for p in HERE.glob('TEST-*.json')),cpus=4,ram_bytes=8*1024**3,new_artifact_bytes=100000000))
        write(HERE/'AUTHORIZATION.json',authority)
        write(HERE/'EXECUTION-APPROVAL.json',dict(authority,authorization_record=control+'/AUTHORIZATION.json',authorization_sha256=sha(HERE/'AUTHORIZATION.json')))
        print(json.dumps(dict(manifest_sha256=digest,authorization_sha256=sha(HERE/'AUTHORIZATION.json'),approval_sha256=sha(HERE/'EXECUTION-APPROVAL.json'))));return
    if a.mode=='identify':
        old=load(HERE.parent/'recovery-r3/IDENTITIES.json');authority=load(HERE/'AUTHORIZATION.json');backup=load(HERE/'SSD-BACKUP.json')
        if backup['status']!='verified' or not backup['whole_and_every_member_verified']:raise RuntimeError('required new-package backup not verified')
        identity=dict(old,r1_source=old['r1_source'],r1_control=old['r1_control'],r2_source=old['r2_source'],r2_control=old['r2_control'],r3_source=old['recovery_source'],r3_control=old['recovery_control'],
            recovery_source=authority['recovery_source'],recovery_control=authority['recovery_control'],recovery_manifest_sha256=sha(manifest),
            recovery_authorization_sha256=sha(HERE/'AUTHORIZATION.json'),recovery_approval_sha256=sha(HERE/'EXECUTION-APPROVAL.json'),
            recovery_archive=backup['archive'],recovery_export_bytes=backup['bytes'],recovery_export_members=backup['members'],recovery_export_sha256=backup['sha256'],terminal_rows=load(HERE/'LINEAGE.json')['terminal_rows'])
        write(HERE/'IDENTITIES.json',identity);print(json.dumps(identity));return
    if a.mode=='freeze':
        test=load(sorted(HERE.glob('TEST-*.json'))[-1])
        if test['errors'] or test['failures'] or test['tests']<90:raise RuntimeError('complete artificial acceptance required')
        original=load(DOC/'PACKAGE-MANIFEST.json')
        if any(sha(ROOT/r['path'])!=r['sha256'] for r in original['files']):raise RuntimeError('original scientific closure changed')
        for label in ('recovery-r1','recovery-r2','recovery-r3'):
            for row in load(HERE.parent/label/'PACKAGE-MANIFEST.json')['files']:
                if sha(ROOT/row['path'])!=row['sha256']:raise RuntimeError('executed historical recovery source changed')
        write(HERE/'SCIENTIFIC-CLOSURE-READBACK.json',dict(manifest_sha256=sha(DOC/'PACKAGE-MANIFEST.json'),members=len(original['files']),all_raw_member_hashes_verified=True,original_scientific_files_edited=False))
        write(HERE/'EXECUTION-APPROVAL-TEMPLATE.json',dict(study='DTV-EFF1-R4',execute=False))
        rows=files()
        if sum(r['bytes'] for r in rows)>500000:raise RuntimeError('small recovery closure cap')
        write(manifest,dict(study='DTV-EFF1-R4',scientific_changes=False,research_execution=False,files=rows))
        print(json.dumps(dict(manifest_sha256=sha(manifest),files=len(rows),bytes=sum(r['bytes'] for r in rows))));return
    v=volume();m=load(manifest)
    if m['files']!=files():raise RuntimeError('frozen recovery changed')
    destination=Path('D:/THESIS-BACKUPS/dtv-success-cost-20261001/recovery-r4')/('package-'+sha(manifest)[:16])
    if destination.exists():raise RuntimeError('R4 small backup already attempted; no duplicate/overwrite')
    destination.mkdir(parents=True);started=time.perf_counter()
    rows=[dict(r,source=str(ROOT/r['path'])) for r in m['files']]
    rows.append(dict(path='PACKAGE-MANIFEST.json',source=str(manifest),bytes=manifest.stat().st_size,sha256=sha(manifest)))
    info=make_archive(destination/'package.tar',rows)
    copies=[]
    for name in ('PACKAGE-MANIFEST.json','AUTHORIZATION.json','EXECUTION-APPROVAL.json'):
        source=HERE/name;target=destination/name;shutil.copyfile(source,target)
        if sha(source)!=sha(target) or source.stat().st_size!=target.stat().st_size:raise RuntimeError('R4 authority copy differs')
        copies.append(dict(path=name,bytes=target.stat().st_size,sha256=sha(target)))
    receipt=dict(status='verified',study='DTV-EFF1-R4',archive=str(destination/'package.tar'),**info,
                 copies=copies,manifest_sha256=sha(manifest),volume=v,whole_and_every_member_verified=True,
                 wall_seconds=time.perf_counter()-started,new_small_package_only=True,historical_archives_transferred=False)
    write(destination/'VERIFIED.json',receipt);write(HERE/'SSD-BACKUP.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
