"""Independent Boolean-mask reaggregation of an authorized count-only report.

Re-read only the identifier projections named in the report. No output tables,
pixels, actions, model calls, selected manifests, or membership lists emitted.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np

ALLOWED_IDS={'episode_idx','episode_id','source_episode_id','target_episode_id','goal_episode_id'}
ALLOWED_TSV=set('episode_id episode_length partition eval_index shard_index start_step dataset_goal_step declared_goal_offset source_global_row goal_global_row selection_hash split base_index goal_horizon'.split())
def digest(ids):
    return hashlib.sha256(''.join(str(i)+'\n' for i in sorted(ids)).encode()).hexdigest()

def verify(root, report):
    raw=Path(report).read_bytes(); data=json.loads(raw)
    rp=root/'manifests/partitions/pusht-v1/episodes-seed-20260728.tsv'
    assert hashlib.sha256(rp.read_bytes()).hexdigest()==data['registry_sha256']
    with rp.open() as f: rows=list(csv.DictReader(f,delimiter='\t'))
    ids=[int(r['episode_id']) for r in rows]
    assert sorted(ids)==list(range(len(ids)))
    n=len(ids); groups={}; verified=0
    for source in data['metadata_sources']:
        p=Path(source['path']); members=set()
        if source.get('format')=='hdf5_identifier_projection':
            assert p.is_relative_to(root) and p.suffix=='.h5'
            keys=source['read_dataset_keys'];assert keys and set(keys)<=ALLOWED_IDS
            with h5py.File(p,'r') as f:
                for key in keys:
                    d=f[key];assert d.dtype.kind in 'iu'
                    found=set(int(i) for i in np.unique(d[...]))-{-1}
                    assert digest(found)==source['identifier_key_hashes'][key]
                    members.update(found)
            assert source['whole_hdf5_hashed'] is False
        elif source.get('format')=='membership_tsv':
            assert p.is_relative_to(root) and p.suffix=='.tsv'
            with p.open() as f:
                r=csv.reader(f,delimiter='\t');header=next(r)
                assert set(header)<=ALLOWED_TSV and header==source['fields']
                ix=header.index('episode_id')
                members={int(row[ix]) for row in r}
            assert hashlib.sha256(p.read_bytes()).hexdigest()==source['metadata_file_sha256']
        elif source['category']=='SAGE_paper_evaluated':
            for item in source['manifests']:
                q=Path(item['path']);assert q.is_relative_to(root)
                b=q.read_bytes();assert hashlib.sha256(b).hexdigest()==item['sha256']
                members.update(int(r['episode_id']) for r in json.loads(b)['records'])
        elif source['category']=='explicit_engineering':
            members={8908,201,627}
        else: raise ValueError('Unknown projection format')
        assert members and min(members)>=0 and max(members)<n
        assert len(members)==source['identifier_count'] and digest(members)==source['identifier_projection_sha256']
        mask=groups.setdefault(source['category'],np.zeros(n,dtype=bool));mask[list(members)]=True
        verified+=1
    results={}
    for part, report_ledger in data['ledger'].items():
        mask=np.zeros(n,dtype=bool)
        for r in rows:
            if r['partition']==part and int(r['episode_length'])>=151:mask[int(r['episode_id'])]=True
        assert int(mask.sum())==report_ledger['length_eligible']
        for step in report_ledger['steps']:
            excluded=groups.get(step['reason'],np.zeros(n,dtype=bool))
            assert int((mask&excluded).sum())==step['newly_excluded']
            mask &= ~excluded
            assert int(mask.sum())==step['remaining']
        assert int(mask.sum())==data['remaining_by_partition'][part]['count']
        results[part]=mask
    combined=np.logical_or.reduce(list(results.values()))
    assert int(combined.sum())==data['combined_count']
    assert int((results['P3']|results['P4']).sum())==data['new_P3_P4_count']
    sp=root/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage/data/splits/pusht_episode_split_seed42.json'
    b=sp.read_bytes();assert hashlib.sha256(b).hexdigest()==data['sage_split_sha256'];split=json.loads(b)
    for role in ('train','val','test'):
        mask=np.zeros(n,dtype=bool);mask[split[role+'_episode_idx']]=True
        assert int((mask&combined).sum())==data['combined_sage_roles'][role]
        for part,selected in results.items():
            assert int((mask&selected).sum())==data['remaining_by_partition'][part]['sage_roles'][role]
    return {'all_checks_passed':True,'report_sha256':hashlib.sha256(raw).hexdigest(),
            'independently_reaggregated_projection_count':verified,
            'counts':{p:int(v.sum()) for p,v in results.items()},'combined_count':int(combined.sum()),
            'sage_test_count':data['maximum_sage_test_reserve'],
            'eligible_lists_emitted':False,'outcome_payloads_read':False,
            'method':'Boolean-mask reaggregation, separately implemented from set-ledger audit',
            'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    print(json.dumps(verify(a.root,a.report),indent=2,sort_keys=True))
