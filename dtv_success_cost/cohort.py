"""Metadata-only parent-role reconciliation. No allocation or payload access."""
import csv
import hashlib
import json
import struct
from pathlib import Path
from dtv_success_cost.metadata import DOC

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
    with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f,delimiter='\t'))
def h64(s):return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8],'big')

def reconcile():
    result={}
    for task in ('pusht','reacher','cube'):
        master=DOC/'metadata/manifests/partitions'/ (task+'-v1')/'episodes-seed-20260728.tsv'
        source=rows(master);p2={int(r['episode_id']) for r in source if r['partition']=='P2' and int(r['episode_length'])>25}
        excluded=set();evidence=[]
        for base in (DOC/'metadata',DOC/'additional/metadata'):
            for p in sorted(base.rglob('*.tsv')):
                if ('/'+task+'/' not in p.as_posix()) or '/partitions/' in p.as_posix():continue
                data=rows(p)
                if data and 'episode_id' in data[0]:
                    ids={int(r['episode_id']) for r in data};excluded|=ids
                    evidence.append(dict(path=str(p.relative_to(DOC)).replace('\\','/'),sha256=sha(p),parent_ids=sorted(ids)))
        # A cancelled or invalidated controller does not erase a historical
        # source assignment. Authenticate the actual parent/global-row mapping,
        # rather than interpreting integer coincidence in another namespace.
        legacy_directory={'pusht':'manifests/acid-alternative-v1/pusht-invalidated-job-296413-unfiltered-task-paths',
                          'reacher':'manifests/quarantine/acid-alt-preparation-20260814/reacher-eval-v1-cancelled-job-296512'}.get(task)
        if legacy_directory:
            offsets={};total=0;lengths={}
            for r in source:
                parent=int(r['episode_id']);offsets[parent]=total;lengths[parent]=int(r['episode_length']);total+=lengths[parent]
            for p in sorted((DOC/'invalidated/metadata'/legacy_directory).glob('*.tsv')):
                data=rows(p);ids=set()
                for r in data:
                    parent=int(r['episode_id']);step=int(r['start_step'])
                    if parent not in offsets or offsets[parent]+step!=int(r['source_global_row']) or not 0<=step<lengths[parent]:raise RuntimeError('historical parent namespace requires reconciliation')
                    ids.add(parent)
                excluded|=ids;evidence.append(dict(path=p.relative_to(DOC).as_posix(),sha256=sha(p),parent_ids=sorted(ids),invalidated_or_cancelled_assignment_retained=True))
        if task=='pusht':
            legacy=DOC/'additional/metadata/data/stablewm/derived/candidate-pools/pusht-v1'
            ordered=sorted(p2,key=lambda i:h64(f'pusht_expert_train\0{20260728}\0p2_real_source_episode\0{i}'))
            for p in sorted(legacy.glob('*/manifest.json')):
                value=json.loads(p.read_text())
                if value['partition']!='P2':continue
                if 'source_episode_ids_sha256' in value.get('sampling',{}):
                    count=value['candidates_per_stratum'];ids=ordered[:2*count]
                    hashes=[hashlib.sha256(b''.join(struct.pack('<q',i) for i in ids[j*count:(j+1)*count])).hexdigest() for j in (0,1)]
                    if hashes!=value['sampling']['source_episode_ids_sha256']:raise RuntimeError('legacy parent identity reconstruction mismatch')
                else:
                    ids=[r['episode_id'] for r in value['query_selection']['queries']]
                excluded|=set(ids);evidence.append(dict(path=str(p.relative_to(DOC)).replace('\\','/'),sha256=sha(p),parent_ids=sorted(set(ids)),metadata_only=True))
        available=p2-excluded
        result[task]=dict(master_sha256=sha(master),p2_parent_count=len(p2),excluded_p2_count=len(p2&excluded),eligible_parent_count=len(available),eligible_parents=sorted(available),evidence=evidence,
                          non_p2_closed=True,payload_reads=0)
    return result

def main():
    value=reconcile()
    with (DOC/'ROLE-RECONCILIATION.json').open('x') as f:json.dump(value,f,indent=2)
    print(json.dumps({t:{k:r[k] for k in ('p2_parent_count','excluded_p2_count','eligible_parent_count')} for t,r in value.items()},indent=2))
if __name__=='__main__':main()
