"""Declared sample-size sensitivity and exhaustive known-law parameter grid.
Not a sweep used to choose an experiment setting; every cell is retained.
"""
from pathlib import Path
import dataclasses,json,time
import numpy as np
from experiment import CASES,METHODS,tables,draw_training,fit_joint,choose,evaluate,canonical,Case
root=Path(__file__).parent/'sensitivity-v1';root.mkdir(exist_ok=False)
config=dict(sample_sizes=[32,128,512,2048],seeds=list(range(26000,26100)),
            accuracy_grid=np.linspace(.50,.99,50).tolist(),survival_grid=np.linspace(.5,1,51).tolist(),
            fitting_law='same seven cases as v1, no changes',selection_from_grid=False)
(root/'CONFIG.json').write_bytes(canonical(config));start=time.perf_counter();result=[]
for n in config['sample_sizes']:
  for ci,c in enumerate(CASES):
    truth,_,info=tables(c,True);vals={m:[] for m in METHODS}
    for s in config['seeds']:
      obs,ys=draw_training(c,n,np.random.default_rng(np.random.SeedSequence([s,ci])))
      j=fit_joint(obs,ys)
      for m in METHODS:
        vals[m].append(evaluate(choose(truth if m=='oracle_contingent' else j,info,m),truth))
    result.append(dict(ntrain=n,case=c.name,methods={m:dict(mean=float(np.mean(v)),min=float(min(v)),max=float(max(v)),
                sd=float(np.std(v,ddof=1))) for m,v in vals.items()}))
count=0;error=0.;benefit=0
for acc in config['accuracy_grid']:
  for surv in config['survival_grid']:
    c=dataclasses.replace(CASES[0],signal_accuracy=acc,probe_survival=surv)
    j,_,info=tables(c);v=evaluate(choose(j,info,'oracle_contingent'),j)
    formula=max(.58,surv*max(.58,.15+.7*acc));error=max(error,abs(v-formula));count+=1
    benefit+=v>.58+1e-12
payload=dict(results=result,analytic_grid_cells=count,max_formula_error=error,
             cells_with_strict_information_benefit=benefit,
             fit_count=len(config['sample_sizes'])*len(CASES)*len(config['seeds']),
             training_sources=sum(config['sample_sizes'])*len(CASES)*len(config['seeds']),
             binary_branch_labels=sum(config['sample_sizes'])*len(CASES)*len(config['seeds'])*9,
             seconds=time.perf_counter()-start)
(root/'RESULTS.json').write_bytes(canonical(payload))
print(json.dumps({k:v for k,v in payload.items() if k!='results'},indent=2))
for row in result:
 if row['ntrain'] in (32,2048):
  print(row['ntrain'],row['case'], 'active',round(row['methods']['active_counterfactual_feedback']['mean']*100,3),
        'static',round(row['methods']['commit']['mean']*100,3))
