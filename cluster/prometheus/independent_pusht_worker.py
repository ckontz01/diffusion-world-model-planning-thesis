"""Execute a registered immutable shard; no online method selection."""
import argparse,json,os
from pathlib import Path
from independent_pusht_collect import sha
from independent_pusht_evaluate import run

def tasks_for(arms,seeds,begin,end,chunk=64):
    return [{'task':i,'arm':arm,'seed':seed,'begin':lo,'end':min(lo+chunk,end)}
            for i,(arm,seed,lo) in enumerate((a,s,l) for a in arms for s in seeds for l in range(begin,end,chunk))]

def main(study,stage,index):
    study=Path(study);config=json.loads((study/'CONFIG.json').read_text())
    registry=json.loads((study/'REGISTRY.json').read_text())
    lock=json.loads((study/'INPUT-LOCK.json').read_text())
    assert sha(study/'collection/COLLECTION.json')==lock['collection_sha256']
    assert sha(study/'CONFIG.json')==lock['config_sha256']
    assert sha(study/'REGISTRY.json')==lock['registry_sha256']
    task=registry['stages'][stage][index]
    assert task['task']==index
    parent=study/f'stage-{stage}'/f'task-{index:04d}'
    parent.mkdir(parents=True,exist_ok=False)
    (parent/'TASK.json').write_text(json.dumps(task,indent=2)+'\n')
    run(study/'collection',parent/'results',task['arm'],task['seed'],
        indices=list(range(task['begin'],task['end'])),pilot=False,cap=None,action_rule='native_finite')
    (parent/'DONE.json').write_text(json.dumps({'task':task,'result_sha256':sha(parent/'results/RESULT.json'),
      'source_manifest_sha256':sha(Path(__file__).with_name('SOURCE-MANIFEST.sha256')),
      'config_sha256':lock['config_sha256']},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--stage',type=int,required=True)
    p.add_argument('--index',type=int,default=None);a=p.parse_args()
    main(a.study,a.stage,a.index if a.index is not None else int(os.environ['SLURM_ARRAY_TASK_ID']))
