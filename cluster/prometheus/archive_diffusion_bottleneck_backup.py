"""Single-file stage-0 backup with member-by-member canonical verification.

Avoids slow small-file extraction to NTFS. Never extracts the archive. Only
DONE metadata and checksum text are parsed; payload JSON/NPZ stays opaque.
"""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import tarfile
from diffusion_bottleneck import require,require_sha,sha256,write_report
from diffusion_bottleneck_traces import expected_tasks
from audit_diffusion_bottleneck_preservation import STUDY

def inventory(receipt):
    tasks=expected_tasks()
    require(receipt['all_passed'] is True and receipt['canonical_study']==str(STUDY),'Receipt identity')
    expected={}
    for task in tasks:
        key=f'stage-0/task-{task["task"]:04d}'
        row=receipt['shards'][key]
        expected[key+'/DONE.json']=row['done_sha256']
        expected[key+'/results/sha256.txt']=row['seal_sha256']
        expected[key+'/results/RESULT.json']=row['result_sha256']
        for i in range(task['begin'],task['end']):
            for h in (75,150):
                for ext in ('json','npz'):
                    expected[f'{key}/results/episode-{i:05d}-h{h}.{ext}']=None
    for name,item in receipt['compact_files'].items():expected['analysis-0/'+name]=item['sha256']
    # Historical verifier was independently pinned by both outcome checkers.
    expected['analysis-0/INDEPENDENT-VERIFICATION.json']='a0476199cbdeee6a04676a7dd86d4b17d1abfab6a2c1212833d8320a92bb5380'
    return expected

def pack(receipt,archive):
    require(not archive.exists(),'Existing archive')
    expected=inventory(receipt)
    with tarfile.open(archive,'x') as tar:
        for name in sorted(expected):
            path=STUDY/name
            require(path.is_file() and not path.is_symlink(),'Nonregular canonical member')
            tar.add(path,arcname=name,recursive=False)
    return {'archive_sha256':sha256(archive),'archive_bytes':archive.stat().st_size,'members':len(expected),
            'note':'Transport seal; per-member canonical verification is a separate required step'}

def verify(receipt,archive):
    expected=inventory(receipt);actual={};seals={};total=0
    with tarfile.open(archive,'r|') as tar:
        for member in tar:
            name=member.name
            require(member.isfile() and name in expected and name not in actual,'Unsafe/extra/duplicate archive member')
            require(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts,'Unsafe member path')
            stream=tar.extractfile(member);hasher=hashlib.sha256();parts=[]
            for block in iter(lambda:stream.read(1<<20),b''):
                hasher.update(block)
                if name.endswith('/sha256.txt'):parts.append(block)
            actual[name]=hasher.hexdigest();total+=member.size
            if expected[name] is not None:require(actual[name]==expected[name],'Canonical identity mismatch: '+name)
            if parts:seals[name]=b''.join(parts).decode('utf-8')
    require(set(actual)==set(expected),'Incomplete archive')
    for seal,text in seals.items():
        directory=str(PurePosixPath(seal).parent);seen=set()
        for line in text.splitlines():
            digest,name=line.split(maxsplit=1)
            require(name not in seen and '/' not in name and '\\' not in name,'Unsafe/duplicate sealed member')
            seen.add(name);require(actual.get(directory+'/'+name)==digest,'Payload mismatch: '+directory+'/'+name)
        require({n for n in actual if n.startswith(directory+'/') and n!=seal}=={directory+'/'+n for n in seen},'Incomplete member seal')
    return {'all_passed':True,'source_matched_shards':450,'members_verified':len(actual),
            'payload_bytes_verified':total,'archive_sha256':sha256(archive),
            'no_archive_extraction':True,'outcome_payloads_interpreted':False,
            'model_backup_verified':False,'reference_collection_backup_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['pack','verify'])
    p.add_argument('--receipt',type=Path,required=True);p.add_argument('--receipt-sha256',required=True)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();require_sha(a.receipt,a.receipt_sha256);require(not a.out.exists(),'Existing report')
    r=json.loads(a.receipt.read_text());result=pack(r,a.archive) if a.mode=='pack' else verify(r,a.archive)
    result['canonical_receipt_sha256']=a.receipt_sha256;result['program_sha256']=sha256(Path(__file__))
    write_report(a.out,result,(STUDY,));print(json.dumps(result),flush=True)
