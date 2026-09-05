"""Read only existing training checkpoints; never open a dataset/holdout."""
import hashlib
import json
from pathlib import Path
import sys
import torch

ROOT=Path('/lustreFS/data/superworld/ckontzias/thesis')
TRAIN=ROOT/'experiments/gdp-cem-e15/development-run-20260825-ebd6109b/training/pusht'
EXPECTED={
 'vad': ['8a862f1773a3200391b37b954bcce09b682d8093bd56b69bd19d8ce3a0b4370e',
         '6b7033075ae9f08c25a455f2d54d1c5233c3cb15443826f186a96125a4bce500',
         '2a5b35176328468ed9360eb6cf34de239aba884266725b069be3643de8ff9cf3'],
 'diagonal_gaussian': ['fcbd0768920434c46451726a87e47baafcb380bf91ff0e95c20e6670933da81e',
         'e91bacbdad5128bbd9698da8c85bbbf49a92d7b2e937f0ee60f15c6c1e2d1dfc',
         '027cfa8d460bb64cfe03c3b6e0b9be93d064ea51ae054cf4cc66886a609c4ecd'],
 'direct_gmm': ['f42978fbccff10dd59d12ea62740f2df7569d13911cfe4823ffcd78dad024417',
         'e740cdb26f9440ac8b69c14094061f657fc29bf06f21783d4634e8f59c123342',
         '64c396a82ef7ee9515303f627c3cf254e5b4915ca10bf44e216260563e7d7151']}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def run(out):
    assert ROOT/'experiments/e18-fresh-integration' in out.resolve().parents
    out.mkdir(parents=True,exist_ok=False)
    rows=[];first=None
    for family in EXPECTED:
        for seed,digest in zip((7201,7202,7203),EXPECTED[family]):
            path=TRAIN/family/f'seed-{seed}'/'final.pt'
            assert sha(path)==digest
            p=torch.load(path,map_location='cpu',weights_only=False)
            assert p['kind']=='gdp_cem_e15_p1_final_proposer_checkpoint'
            assert p['task']=='pusht' and p['condition']==family and p['seed']==seed
            assert p['validation_payload_rows_read']==0
            stats={k:v.float().tolist() if torch.is_tensor(v) else v for k,v in p['statistics'].items()}
            if first is None:first=stats
            assert stats==first,'normalization differs across frozen checkpoint blocks'
            rows.append(dict(family=family,training_seed=seed,path=str(path),sha256=digest))
    result=dict(task='pusht',checkpoints=rows,statistics=first,
        normalization_identical_all_nine_checkpoints=True,
        lewm_sha256='c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659',
        adapter_sha256='c58726a3502bf52bbbaad6263c1f636ef393ecbd34835b021750f7451bed88b8',
        action_decoder=dict(mean=[-0.007812564379916172,0.006860687229453032],
                           scale=[0.20846744284501714,0.20674862637362224]),
        dataset_read=False,holdout_read=False,protected_read=False,fit_performed=False,
        purpose='pin_existing_training_inputs_not_confirmation_authorization')
    path=out/'PINNED-INPUTS.json'
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (out/'sha256.txt').write_text(sha(path)+'  PINNED-INPUTS.json\n')
    path.chmod(0o444);(out/'sha256.txt').chmod(0o444)
    print(json.dumps(dict(all_nine_checkpoint_hashes_pass=True,all_statistics_identical=True,
                         sha256=sha(path),dataset_read=False)))

if __name__=='__main__':run(Path(sys.argv[1]))
