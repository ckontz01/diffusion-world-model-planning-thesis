"""Scheduler/container argument check; no model or dataset imports."""
import argparse,json,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--index',type=int,required=True);a=p.parse_args()
assert a.index in (0,1)
q=Path(a.out)/('index-%d.json'%a.index)
with q.open('x') as f:json.dump({'index':a.index,'scheduler_env_removed':os.environ.get('SLURM_ARRAY_TASK_ID') is None,'model_called':False},f)
print('Explicit array index received:',a.index)
