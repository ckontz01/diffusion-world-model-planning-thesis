"""Canonical stage-0 byte receipt and authenticated off-cluster comparison.

Never deserializes models or reference trajectories. Run canonical mode inside
a CPU allocation. Transfer its receipt via strict-host-key SSH; local mode
requires that separately obtained receipt digest (not an untrusted local seal).
"""
import argparse
from pathlib import Path
from diffusion_bottleneck import checked_child, read_json, require, require_sha, sha256, write_report
from diffusion_bottleneck_traces import expected_tasks, sealed_stage
from verify_diffusion_backup import recheck_task

ROOT = Path('/lustreFS/data/superworld/ckontzias/thesis')
STUDY = ROOT/'experiments/independent-pusht/final-20260906-4a608e5'
SOURCE = ROOT/'snapshots/independent-pusht-4a608e5'

def seal_files(root, seal):
    seen = set()
    records = {}
    for line in seal.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        require(name not in seen, 'Duplicate seal entry')
        seen.add(name)
        file = checked_child(root, name)
        require_sha(file, digest)
        records[name] = {'sha256': digest, 'bytes': file.stat().st_size}
    require(bool(seen), 'Empty seal')
    return records

def canonical():
    files, lock = sealed_stage(STUDY)
    require_sha(SOURCE/'SOURCE-MANIFEST.sha256', lock['source_manifest_sha256'])
    source = seal_files(SOURCE, SOURCE/'SOURCE-MANIFEST.sha256')
    require_sha(SOURCE/'INDEPENDENT-PUSHT-PROTOCOL.md', lock['protocol_sha256'])
    require_sha(STUDY/'collection/COLLECTION.json', lock['collection_sha256'])
    pins = read_json(SOURCE/'INDEPENDENT-PINNED-INPUTS.json')
    models = {p['path']:p['sha256'] for p in pins['checkpoints']}
    models[str(ROOT/'data/stablewm/pusht/lewm_hf_22b330c_object.ckpt')] = pins['lewm_sha256']
    models[str(ROOT/'experiments/gdp-cem-e17/development-run-20260827-9fb5a8c2/models/pusht/final.pt')] = pins['adapter_sha256']
    sage = ROOT/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage'
    release = read_json(sage/'configs/checkpoints.json')
    for key in ('pusht_generator','pusht_action_prior'):
        p=ROOT/'experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988/checkpoints'/release[key]['filename']
        models[str(p)]=release[key]['sha256']
    for p,digest in models.items(): require_sha(Path(p),digest)
    shards={}
    for p,task in files:
        key=f'stage-0/task-{task["task"]:04d}'
        record={'path':key,'done_sha256':sha256(p.parent.parent/'DONE.json'),
                'result_sha256':sha256(p)}
        check=recheck_task(STUDY,key,record,task)
        shards[key]={**record,'seal_sha256':sha256(p.parent/'sha256.txt'),**check}
    compact=seal_files(STUDY/'analysis-0',STUDY/'analysis-0/sha256.txt')
    # Only exposed reference bytes are needed. No semantic NPZ read occurs here.
    collection=read_json(STUDY/'collection/COLLECTION.json')
    refs={}
    for i,ref in enumerate(collection['records'][:1600]):
        require(ref['index']==i,'Reference ordering')
        path=checked_child(STUDY/'collection',ref['file'])
        require_sha(path,ref['sha256'])
        refs[ref['file']]={'sha256':ref['sha256'],'bytes':path.stat().st_size}
    require(len(refs)==1600,'Exposed reference count')
    return {'all_passed':True,'canonical_study':str(STUDY),'input_lock':lock,
            'shards':shards,'source_files':source,'model_file_sha256':models,
            'compact_files':compact,'exposed_reference_files':refs,
            'unevaluated_reference_payloads_read_or_hashed':0,
            'model_deserializations':0,'protected_payload_reads':0,
            'scope':'Byte identities; separate from physical outcome interpretation'}

def local(local_study,receipt,digest):
    require_sha(receipt,digest)
    source=read_json(receipt)
    require(source['all_passed'] is True and source['canonical_study']==str(STUDY),'Wrong canonical receipt')
    tasks=expected_tasks()
    require(set(source['shards'])=={f'stage-0/task-{t["task"]:04d}' for t in tasks},'Receipt coverage')
    passed={}
    for task in tasks:
        key=f'stage-0/task-{task["task"]:04d}'
        record=source['shards'][key]
        require_sha(local_study/key/'results/sha256.txt',record['seal_sha256'])
        passed[key]=recheck_task(local_study,key,record,task)
    return {'all_passed':True,'canonical_receipt_sha256':digest,'local_study':str(local_study),
            'source_matched_shards':len(passed),
            'payload_bytes_rehashed':sum(v['payload_bytes_rehashed'] for v in passed.values()),
            'compact_backup_verified':False,'models_backup_verified':False,
            'reference_backup_verified':False,'protected_payload_reads':0}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['canonical','local'])
    p.add_argument('--local-study',type=Path);p.add_argument('--receipt',type=Path)
    p.add_argument('--receipt-sha256');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    roots=(STUDY,SOURCE) if a.mode=='canonical' else (a.local_study,a.receipt.parent)
    require(not a.out.exists(),'Output exists')
    for root in roots: require(root.resolve() not in a.out.resolve().parents,'Output inside input')
    report=canonical() if a.mode=='canonical' else local(a.local_study,a.receipt,a.receipt_sha256)
    report['program_sha256']=sha256(Path(__file__))
    write_report(a.out,report,roots)
    print('PASS '+a.mode+' '+sha256(a.out),flush=True)
