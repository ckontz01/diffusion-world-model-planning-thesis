"""Prospective large-design calculations; no comparative outcomes read."""
import json
from pathlib import Path
import numpy as np
from scipy.stats import t,nct,norm
LOOKS=(1600,3200,6000)
ALPHAS=(.001,.004,.05/3-.005)

def boundaries(n,sd):
    return t.ppf(1-ALPHAS[LOOKS.index(n)],n-1)*sd/np.sqrt(n)

def simulate(mu,variance,reps=100000,seed=202609061):
    rng=np.random.default_rng(seed);v=min(variance,1-mu*mu)
    second=v+mu*mu
    prob=np.array([(second-mu)/2,1-second,(second+mu)/2])
    counts=np.zeros((reps,3),np.int64);passed=np.zeros(reps,bool);rows=[];prior=0
    for n,alpha in zip(LOOKS,ALPHAS):
        counts+=rng.multinomial(n-prior,prob,size=reps);prior=n
        mean=(counts[:,2]-counts[:,0])/n
        var=np.maximum((counts[:,2]+counts[:,0]-n*mean*mean)/(n-1),0)
        passed |= mean-t.ppf(1-alpha,n-1)*np.sqrt(var/n)>0
        p=float(passed.mean())
        rows.append({'n':n,'cumulative_marginal_probability':p,'mc_se':float(np.sqrt(p*(1-p)/reps))})
    return {'mean':mu,'variance':v,'rows':rows}

def design():
    rows=[]
    for v in (.25,.5,1.):
        power=simulate(.05,v);null=simulate(0.,v,seed=202609062)
        final=nct.sf(t.ppf(1-ALPHAS[-1],LOOKS[-1]-1),LOOKS[-1]-1,.05*np.sqrt(LOOKS[-1]/v))
        rows.append({'variance_scenario':v,'power':power,'null':null,
                     'joint_power_bonferroni_lower_from_final_normal_approx':max(0,float(1-3*(1-final))),
                     'approx_false_futility_union_upper_at_true5pp':float(3*sum(norm.cdf(-t.ppf(.999,n-1)-.05*np.sqrt(n/v)) for n in LOOKS)),
                     'family_error_upper_from_simulated_marginal':3*null['rows'][-1]['cumulative_marginal_probability']})
    return {'looks':LOOKS,'per_comparison_look_alpha':ALPHAS,'comparisons':3,'total_alpha':sum(ALPHAS)*3,
            'target_true_effect':.05,'observed_effect_threshold':None,'monte_carlo_replicates':100000,
            'scenarios':rows,'notes':'Paired episode means; t approximation, not a universal finite-sample guarantee. Bonferroni across looks and contrasts. No training or test outcomes used. Stop early only after all three registered superiority nulls have crossed their spending boundaries; otherwise continue up to N6000. A prespecified strong-adverse-signal futility rule may also stop; its false-futility probability under positive effects is bounded using the separate approximation reported.'}

if __name__=='__main__':
    import sys
    p=Path(sys.argv[1]);assert not p.exists();p.write_text(json.dumps(design(),indent=2)+'\n')
    print(p.read_text())
