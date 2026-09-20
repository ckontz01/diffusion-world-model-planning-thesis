"""Identifier-only preparation; never opens reference payloads or models."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import lgprb2_contract as c

ROLE_FILES={
 'cvl':'docs/candidate-value-learning-20260914/PROPOSED-ALLOCATION.json',
 'bp1':'docs/candidate-value-breadth-precision-20260915/DATA-ROLES.json',
 'si1':'docs/candidate-value-score-information-20260918/FOLDS.json',
 'lgp1':'docs/local-goal-proposals-20260918/DATA-ROLES.json'}

def role_inventory(repo):
    raw={k:c.read(repo/v) for k,v in ROLE_FILES.items()}
    cv=raw['cvl']['allocation'];bp=raw['bp1']['allocation'];lgp=raw['lgp1']
    roles={'CVL-'+k:v for k,v in cv.items() if isinstance(v,list)}
    roles.update({'BP1-'+k:bp[k] for k in ('original_train','extra_train','evaluation')})
    roles.update({'BP1-recorded-'+k:v for k,v in bp['exclusions'].items()})
    roles['LGP1/RB1-development']=lgp['development_reference_indices']
    roles['LGP1-technical']=lgp['technical_reference_indices']
    # SI1 folds expose identifiers only. Validate no extra SI1 role was omitted.
    def collect(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ('fit','heldout','fitting','held_out','train','validation','fitting_references','heldout_references') and isinstance(v,list):
                    for item in v:
                        if isinstance(item,list):yield from item
                        else:yield item
                else:yield from collect(v)
        elif isinstance(x,list):
            for v in x:yield from collect(v)
    si=set(collect(raw['si1']))
    require_si=set(bp['original_train']+bp['extra_train'])
    c.require(si==require_si,'SI1 exact 192 reused role union')
    roles['SI1-fitting-heldout']=sorted(si)
    c.require(set(bp['exclusions']['historical_32'])==set(lgp['development_reference_indices']),'Bottleneck/single-anchor/LGP1/RB1 role equivalence')
    return roles,{v:hashlib.sha256((repo/v).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for v in ROLE_FILES.values()}

REMOTE=r'''
import hashlib,json,sys
from pathlib import Path
root=Path('/lustreFS/data/superworld/ckontzias/thesis')
source=root/'snapshots/candidate-value-learning-20260914-521a0e6627c570ff'
sys.path.insert(0,str(source/'cluster/prometheus'))
from candidate_value_freeze import identity_projection
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=root/'experiments/independent-pusht/final-20260906-4a608e5'
lock=base/'INPUT-LOCK.json';assert sha(lock)=='90ac1fd4e8e5fbaa3941ab9a5b7ed127bc20cb96018bed5d143b7dec2cbf64cb'
registry=base/'collection/COLLECTION.json';assert sha(registry)==json.loads(lock.read_text())['collection_sha256']
records=identity_projection(registry,range(1600))
assert len({(v['namespace'],v['attempt']) for v in records.values()})==1600
assert all(v['index']==i and v['file']==f'reference-{i:05d}.npz' for i,v in records.items())
print(json.dumps(dict(records=records,registry_sha256=sha(registry),input_lock_sha256=sha(lock),
 reader_sha256=sha(source/'cluster/prometheus/candidate_value_freeze.py'),reference_payload_reads=0,
 outcome_fields_decoded=0,distinct_source_keys=1600)))
'''

def prepare(repo):
    repo=Path(repo);roles,pins=role_inventory(repo);allocation=c.allocate(roles)
    raw=subprocess.check_output(['wsl','-d','Thesis-Ubuntu','-u','chris','--','ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus','/usr/bin/python3.9','-B','-'],input=REMOTE,text=True)
    meta=json.loads(raw)
    reader=repo/'cluster/prometheus/candidate_value_freeze.py'
    c.require(meta['reader_sha256']==hashlib.sha256(reader.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),'Accepted lexical reader bytes')
    old=c.read(repo/c.old.DOC/'INPUTS.json');base=c.ROOT/'experiments/independent-pusht/final-20260906-4a608e5/collection'
    records={str(r):dict(file=(base/meta['records'][str(r)]['file']).as_posix(),sha256=meta['records'][str(r)]['sha256'],
        environment_seed=meta['records'][str(r)]['environment_seed'],
        source_key=meta['records'][str(r)]['namespace']+':'+str(meta['records'][str(r)]['attempt'])) for r in allocation['ordered_references']}
    old_reference_paths={v['file'] for v in old['references'].values()}
    inputs={**old,'references':records,'files':{p:d for p,d in old['files'].items() if p not in old_reference_paths},
            'payload_files':[p for p in old['payload_files'] if p not in old_reference_paths]}
    for v in records.values():inputs['files'][v['file']]=v['sha256'];inputs['payload_files'].append(v['file'])
    result={**allocation,'source_record_hashes':pins,'identity_certificate':{k:v for k,v in meta.items() if k!='records'},
            'selected_identity_digest':c.digest(records),'population':'historically exposed 0-1599; not untouched confirmation',
            'reference_payloads_opened':False}
    c.write(repo/c.DOC/'DATA-ROLES.json',result);c.write(repo/c.DOC/'INPUTS.json',inputs)
    c.write(repo/c.DOC/'GRID.json',c.grid(allocation['ordered_references']))
    print(json.dumps({k:v for k,v in result.items() if k not in ('ordered_references','exclusion_roles')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);prepare(p.parse_args().repo)
