"""Read-only remote source/identifier inspection; emit local preparation evidence.

Never loads HDF5/NPZ/checkpoints, imports research modules, or calls Slurm.
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

REMOTE = r'''
import csv,json,hashlib,subprocess
from pathlib import Path
r=Path('/lustreFS/data/superworld/ckontzias/thesis')
s=r/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage'
p=r/'manifests/partitions/pusht-v1/p1-train-val-seed-20260728.tsv'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(p)=='34dcff8a457fb636fbee836e836f752de66013154c36739613b9d5c81dcba5e6'
git=lambda *a:subprocess.check_output(['git','-C',str(s),*a],universal_newlines=True).strip()
assert git('rev-parse','HEAD')=='8219029fd52e89157e05aebb998ab26f0ef46966'
assert git('rev-parse','HEAD^{tree}')=='0c64066eeac97c27fee382c1879bb26968b3fd56'
assert not git('status','--porcelain')
rows=list(csv.DictReader(p.open(),delimiter='\t'))
paper=set(); manifests={}
for seed in (32,42,52):
 for h in (25,50,75,100,125,150):
  path=s/f'data/manifests/pusht/seed{seed}/h{h}.json'
  manifests[str(path.relative_to(s))]=sha(path)
  paper.update(int(x['episode_id']) for x in json.loads(path.read_text())['records'])
split_path=s/'data/splits/pusht_episode_split_seed42.json'
split=json.loads(split_path.read_text())
role_ids={k:set(map(int,split.get(k+'_episode_idx',split.get(k,[])))) for k in ('train','val','test')}
assert len(role_ids['train'])==14948 and len(role_ids['val'])==1868 and len(role_ids['test'])==1869
excluded=paper|role_ids['val']|role_ids['test']
out={'registry_sha256':sha(p),'paper_episode_count':len(paper),'roles':{},'manifest_hashes':manifests,
     'sage_split_sha256':sha(split_path),'excluded_membership_union_count':len(excluded),
     'exclusion_rule':'entire released val/test roles plus all paper memberships',
     'sage_commit':git('rev-parse','HEAD'),'sage_tree':git('rev-parse','HEAD^{tree}'),
     'payload_read':False,'model_or_simulator_called':False}
for role in ('P1_train','P1_val'):
 rr=[x for x in rows if x['p1_role']==role]
 elig=[x for x in rr if int(x['episode_id']) not in excluded]
 assert all(int(x['episode_id']) in role_ids['train'] for x in elig)
 out['roles'][role]={'original':len(rr),'excluded_memberships':len(rr)-len(elig),'eligible':len(elig),
  'eligible_id_sha256':hashlib.sha256(''.join(str(x)+'\n' for x in sorted(int(v['episode_id']) for v in elig)).encode()).hexdigest(),
  'window_counts_by_delta':{d:sum(max(0,int(x['episode_length'])-10-d) for x in elig) for d in range(15,151,15)}}
out['source_hashes']={n:sha(s/n) for n in ('sage/eval/pusht.py','sage/models/action_prior.py',
 'sage/models/subgoal.py','sage/train/pusht_action_prior.py','sage/runtime/lewm.py',
 'configs/training.json','configs/paper.json','stable_worldmodel/envs/pusht/env.py')}
print(json.dumps(out,indent=2,sort_keys=True))
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise RuntimeError('Exclusive preparation output')
    # Python is supplied via stdin, avoiding nested shell interpolation.
    prefix=['wsl','-d','Thesis-Ubuntu','-u','chris','--'] if os.name=='nt' else []
    result=subprocess.run(prefix+['ssh','prometheus','python3','-'],
                          input=REMOTE,text=True,capture_output=True)
    if result.returncode:
        raise RuntimeError('Read-only metadata probe failed: '+result.stderr)
    value=json.loads(result.stdout)
    with args.output.open('x',encoding='utf8',newline='\n') as f:
        json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'metadata_only':True,'roles':value['roles']}))


if __name__=='__main__': main()
