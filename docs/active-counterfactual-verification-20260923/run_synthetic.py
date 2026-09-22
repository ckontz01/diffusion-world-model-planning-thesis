"""Fixed neural wiring experiment; no research data, optimization sweep or physics."""
import hashlib
import json
from pathlib import Path
import numpy as np
from bayes import BayesianRegression,exact_artificial_policy
from model import JointModel,OrdinaryModel,Preprocessing,train
from mock import prototype_dataset
from policy import Selector,features
from tree import Ledger
from prototype.experiment import CASES,tables,evaluate

ROOT=Path(__file__).resolve().parent


def main():
    out=ROOT/'neural-run-v1';out.mkdir(exist_ok=False)
    contract=json.loads((ROOT/'CONTRACT.json').read_text())
    config=contract['synthetic'];results=[]
    (out/'CONFIG.json').write_text(json.dumps(contract,indent=2)+'\n')
    original=json.loads((ROOT/'prototype/run-v1/RESULTS.json').read_text())
    for case in CASES:
        data,tree,h,digest=prototype_dataset(case,1024,24000,'fit')
        expected=next(r['training_digest'] for r in original['rows'] if r['case']==case.name and r['seed']==24000)
        if digest!=expected:raise AssertionError('Original artificial fitting source digest mismatch')
        pre=Preprocessing.fit(data)
        joint=JointModel(56,24,4,preprocessing=pre);ordinary=OrdinaryModel(56,24,4,preprocessing=pre)
        assert joint.parameter_count==5067 and ordinary.parameter_count==9921
        # Metadata is on disk BEFORE the first optimizer update for each model.
        casepath=out/case.name;casepath.mkdir()
        recipe=dict(case=case.name,fit_digest=digest,joint_parameters=joint.parameter_count,
                    ordinary_parameters=ordinary.parameter_count,config=config,loss=contract['neural'])
        (casepath/'FIT-RECIPE.json').write_text(json.dumps(recipe,indent=2)+'\n')
        jt=train(joint,data);ot=train(ordinary,data)
        joint.save(casepath/'joint.npz')
        # Ordinary model uses exactly the same saved preprocessing as joint.
        with (casepath/'ordinary.npz').open('xb') as f:
            np.savez(f,**{f'p{i}':p for i,p in enumerate(ordinary.params)},
                     metadata=np.array(json.dumps(dict(kind='ACV0-ordinary',dims=ordinary.net.dims,
                                                       preprocessing='joint.npz',seed=94012))))
        bayes=BayesianRegression(ordinary).fit(data)
        with (casepath/'bayesian-last-layer.npz').open('xb') as f:
            np.savez(f,mean=bayes.mean,precision=bayes.precision,covariance=bayes.covariance)
        selector=Selector(joint,ordinary,bayes)
        law,_,_=tables(case,test=True);rows=[]
        for mode in Selector.MODES:
            ledger=Ledger();decision=selector.select(tree,h,ledger,mode)
            aa=[]
            for bit in (0,1):
                node=tree.nodes[decision.prefix];observed=node.predicted_prefix+np.array([2*bit-1,0,0,0.])
                aa.append(selector.after(decision,tree,h,observed,ledger))
            rows.append(dict(control=mode,prefix=decision.prefix,suffix_by_observed_bit=aa,
                             direct_baseline=decision.direct_baseline,predicted_values=decision.values,
                             expected_success=evaluate((decision.prefix,np.array(aa)),law),cost=ledger.__dict__))
        oracle=exact_artificial_policy(case)
        rows.append(dict(control='correctly_specified_exact_Bayes',prefix=int(oracle[0]),
                         suffix_by_observed_bit=oracle[1].tolist(),expected_success=evaluate(oracle,law)))
        supporting={}
        for role,n,seed in [('validation',128,94101),('test',256,94102)]:
            dd,_,_,dg=prototype_dataset(case,n,seed,role)
            q=joint.forward(dd['x'],dd['a'],dd['r'])[0]['q'];qo=ordinary.forward(dd['x'],dd['a'],dd['r'])[0]
            supporting[role]=dict(sources=n,data_sha256=dg,joint_brier=float(np.mean((q-dd['y'])**2)),
                                  ordinary_brier=float(np.mean((qo-dd['y'])**2)),
                                  joint_bce=float(np.mean(-dd['y']*np.log(np.clip(q,1e-12,1-1e-12))-(1-dd['y'])*np.log1p(-np.clip(q,1e-12,1-1e-12)))))
        row=dict(case=case.name,training_digest=digest,original_fit_digest_matches=True,
                 fit_joint=jt,fit_ordinary=ot,controls=rows,held_out_support=supporting)
        results.append(row);(casepath/'RESULTS.json').write_text(json.dumps(row,indent=2)+'\n')
        print(json.dumps(dict(case=case.name,controls={r['control']:r['expected_success'] for r in rows})),flush=True)
    output=dict(status='ARTIFICIAL_WIRING_ONLY',research_runtime_executed=False,
                config_sha256=hashlib.sha256((out/'CONFIG.json').read_bytes()).hexdigest(),
                statement='All seven unchanged laws; no seed/parameter/scenario selection. Expected law values are not observed robot success.',
                results=results)
    (out/'RESULTS.json').write_text(json.dumps(output,indent=2)+'\n')


if __name__=='__main__':main()
