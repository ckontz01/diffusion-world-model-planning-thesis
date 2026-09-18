"""Metadata/source-only input lock. Never decodes a reference or data payload."""
import argparse,json,subprocess,os
from pathlib import Path

REMOTE=r'''
import csv,json,hashlib,sys
from pathlib import Path
root=Path('/lustreFS/data/superworld/ckontzias/thesis')
sage=root/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage'
prep=root/'experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988/preparation'
source=root/'snapshots/candidate-value-learning-20260914-521a0e6627c570ff'
sys.path.insert(0,str(source/'cluster/prometheus'))
from candidate_value_freeze import identity_projection
from candidate_value_contract import HISTORICAL
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=root/'experiments/independent-pusht/final-20260906-4a608e5'
lock=json.loads((base/'INPUT-LOCK.json').read_text())
assert sha(base/'INPUT-LOCK.json')=='90ac1fd4e8e5fbaa3941ab9a5b7ed127bc20cb96018bed5d143b7dec2cbf64cb'
assert sha(base/'collection/COLLECTION.json')==lock['collection_sha256']
refs=identity_projection(base/'collection/COLLECTION.json',HISTORICAL)
result=dict(sage=str(sage),registry=str(root/'manifests/partitions/pusht-v1/p1-train-val-seed-20260728.tsv'),
 lewm=str(root/'data/stablewm/pusht/lewm_hf_22b330c_object.ckpt'),
 generator=str(prep.parent/'checkpoints/pusht_generator.pt'),lance=str(prep/'pusht_expert_train.lance'),
 files={},payload_files=[],lance_files=[],references={})
files=result['files']
for name in ('INPUT-LOCK.json',): files[str(base/name)]=sha(base/name)
files[result['registry']]=sha(Path(result['registry']))
files[str(base/'collection/COLLECTION.json')]=lock['collection_sha256']
for ref,x in refs.items():
 p=str(base/'collection'/x['file'])
 result['references'][str(ref)]=dict(file=p,sha256=x['sha256'],environment_seed=x['environment_seed'],source_key=x['namespace']+':'+str(x['attempt']))
 result['payload_files'].append(p);files[p]=x['sha256']
for line in (prep/'lance-sha256.txt').read_text().splitlines():
 digest,name=line.split(None,1);p=str(prep/name.strip().lstrip('*'))
 files[p]=digest;result['lance_files'].append(p);result['payload_files'].append(p)
files[str(prep/'lance-sha256.txt')]=sha(prep/'lance-sha256.txt')
assert files[str(prep/'lance-sha256.txt')]=='a42875cc7c7109011956aa93069f1495531d59fda07efecf4e8672134ad80cdb'
files[result['lewm']]='c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659'
files[result['generator']]='0b3647a3a41435969d750ec58176ef5f92a419c4eacae2b5cda74b35e63f90da'
result['payload_files'] += [result['lewm'],result['generator']]
split_path=sage/'data/splits/pusht_episode_split_seed42.json';split=json.loads(split_path.read_text())
excluded=set(split['val_episode_idx'])|set(split['test_episode_idx']);files[str(split_path)]=sha(split_path)
for seed in (32,42,52):
 for h in (25,50,75,100,125,150):
  p=sage/f'data/manifests/pusht/seed{seed}/h{h}.json';files[str(p)]=sha(p)
  excluded.update(int(x['episode_id']) for x in json.loads(p.read_text())['records'])
result['excluded_episode_ids']=sorted(excluded)
# Source/config files only; no checkpoint loads. Bind all official Python code
# that its imported packages could reach, and installed simulator sources.
for folder in ('sage','stable_worldmodel'):
 for p in (sage/folder).rglob('*.py'):files[str(p)]=sha(p)
env=root/'envs/hi-lewm-artifact-py311-cu121-swm006'
site=env/'lib/python3.11/site-packages'
for p in (site/'stable_worldmodel').rglob('*.py'):files[str(p)]=sha(p)
for pattern in ('torch-*.dist-info/RECORD','numpy-*.dist-info/RECORD','pylance-*.dist-info/RECORD','torchvision-*.dist-info/RECORD','scikit_learn-*.dist-info/RECORD'):
 for p in site.glob(pattern):files[str(p)]=sha(p)
result['runtime']=str(env)
result['container']=dict(path=str(root/'containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'),sha256='589af9b428527ae2d315fbd5eaf7ef991efb1aa7249e30a6d28e6731df40afb2')
result['decoder']=dict(mean=[-0.007812564379916172,0.006860687229453032],scale=[0.20846744284501714,0.20674862637362224])
result['collection_identity_sha256']=lock['collection_sha256']
result['research_payloads_decoded']=False
result['checkpoint_digests_source']='accepted existing seals; verified again inside charged workers before load'
print(json.dumps(result,sort_keys=True,indent=2))
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise RuntimeError('Exclusive input lock')
    prefix=['wsl','-d','Thesis-Ubuntu','-u','chris','--'] if os.name=='nt' else []
    r=subprocess.run(prefix+['ssh','prometheus','python3','-'],input=REMOTE,text=True,capture_output=True)
    if r.returncode:raise RuntimeError(r.stderr)
    value=json.loads(r.stdout)
    with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(files=len(value['files']),references=len(value['references']),payloads_decoded=False)))

if __name__=='__main__':main()
