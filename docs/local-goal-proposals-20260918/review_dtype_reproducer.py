"""Preserved review reproducer against immutable old preparation. Synthetic."""
import subprocess
import numpy as np

def run(repo):
    old=subprocess.check_output(['git','show','63e1d9229492aa193c625fdf19c78200f4614f22:cluster/prometheus/local_goal_proposals.py'],cwd=repo)
    import types,sys
    m=types.ModuleType('old_lgp1');sys.modules[m.__name__]=m;exec(compile(old,'old-preparation','exec'),m.__dict__)
    ctx=m.Context(np.zeros((1,3,192)),np.zeros((1,1,192)),np.zeros((1,1,192)),np.zeros((1,11)),np.array([75]),np.array([15]))
    observed=[]
    def cost(c,x): observed.append(str(x.dtype));return (x*x).sum((2,3))
    m.common_cem(ctx,lambda c,k,r:np.ones((1,k,3,10),np.float32),cost,
        proposal_rng=None,refinement_rng=np.random.default_rng(0),rounds=3,candidates=4,elites=2)
    affine=m.convert_actions(np.ones((1,3,10),np.float32),np.zeros(2),np.ones(2),np.zeros(2),np.ones(2))
    assert observed==['float32','float64','float64'] and affine.dtype==np.float64
    return dict(old_round_dtypes=observed,old_affine_dtype=str(affine.dtype))

if __name__=='__main__':
    import json,sys
    print(json.dumps(run(sys.argv[1])))
