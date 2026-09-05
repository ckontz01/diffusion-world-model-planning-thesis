"""Prepare immutable final registry and bind it to verified collected records."""
import argparse,hashlib,json
from pathlib import Path
from independent_pusht_collect import sha
from independent_pusht_design import LOOKS,ALPHAS

ARMS=('vad_continuation','vad_greedy_300','diagonal_gaussian_continuation','vad_greedy_576','direct_gmm_continuation','sage')

def tasks_for(begin,end,chunk=64):
    rows=[]
    for arm in ARMS:
        for seed in (7201,7202,7203):
            for lo in range(begin,end,chunk):
                rows.append(dict(task=len(rows),arm=arm,seed=seed,begin=lo,end=min(lo+chunk,end)))
    return rows

def prepare(root,source):
    root=Path(root);source=Path(source);root.mkdir(parents=True,exist_ok=False)
    config={'study':'independent-pusht-reference-v1','collection_namespace':'final-20260906-primary-v1',
      'reference_count':6000,'max_attempts':30000,'looks':list(LOOKS),'alpha_by_look':list(ALPHAS),
      'arms':list(ARMS),'training_seed_blocks':[7201,7202,7203],'horizons':[75,150],
      'chunk_size':64,'source_directory':str(source),'source_manifest_sha256':sha(source/'SOURCE-MANIFEST.sha256'),
      'protocol_sha256':sha(source/'INDEPENDENT-PUSHT-PROTOCOL.md'),
      'same_dataset_for_all_arms':True,'minimum_final_sample':1600,'no_small_study_fallback':True}
    registry={'stages':[]};begin=0
    for n in LOOKS:registry['stages'].append(tasks_for(begin,n));begin=n
    for name,doc in [('CONFIG.json',config),('REGISTRY.json',registry)]:
        (root/name).write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'study':str(root),'stages':[len(x) for x in registry['stages']]}))

def lock(root):
    root=Path(root);cfg=json.loads((root/'CONFIG.json').read_text())
    result=json.loads((root/'COLLECTION-VALIDATION.json').read_text())
    assert result['all_passed'] and result['records']==6000
    assert result['collection_sha256']==sha(root/'collection/COLLECTION.json')
    source=Path(cfg['source_directory']);assert sha(source/'SOURCE-MANIFEST.sha256')==cfg['source_manifest_sha256']
    value={'config_sha256':sha(root/'CONFIG.json'),'registry_sha256':sha(root/'REGISTRY.json'),
       'collection_sha256':sha(root/'collection/COLLECTION.json'),'collection_validation_sha256':sha(root/'COLLECTION-VALIDATION.json'),
       'source_manifest_sha256':cfg['source_manifest_sha256'],'protocol_sha256':cfg['protocol_sha256']}
    path=root/'INPUT-LOCK.json'
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
    # Keep source records immutable against accidental writes after the lock.
    for p in (root/'collection').iterdir():
        if p.is_file():p.chmod(0o444)
    for name in ('CONFIG.json','REGISTRY.json','INPUT-LOCK.json','COLLECTION-VALIDATION.json'):(root/name).chmod(0o444)
    print(json.dumps({'locked':True,'collection_sha256':value['collection_sha256']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--source');p.add_argument('--lock',action='store_true');a=p.parse_args()
    if a.lock:lock(a.study)
    else:
        if not a.source:p.error('--source required when preparing')
        prepare(a.study,a.source)
