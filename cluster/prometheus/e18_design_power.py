"""Reproducible, bounded-outcome episode-cluster design simulations, no models.

Each simulated observation is a PAIR of contrasts after averaging six binary
outcomes per arm. A shared treatment constrains support: |d1-d2| <= 1.
Maximum-entropy distributions match the declared mean and covariance on this
support. The actual proposed paired Student test is applied to every replicate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize,brentq
from scipy.special import logsumexp
from scipy.stats import norm,t,nct

ARMS=('vad_continuation','vad_greedy_300','diagonal_gaussian_continuation',
      'vad_greedy_576','direct_gmm_continuation')
SUPPORT=np.array([(i/6,j/6) for i in range(-6,7) for j in range(-6,7) if abs(i-j)<=6])
FEATURES=np.column_stack((SUPPORT,SUPPORT**2,SUPPORT[:,0]*SUPPORT[:,1]))


def historical(d):
    rows=d['rows']; episodes=sorted({int(r['episode_id']) for r in rows}); points=[]
    for episode in episodes:
        er=[r for r in rows if int(r['episode_id'])==episode]
        starts=sorted({int(r['start_step']) for r in er});by_start=[]
        for start in starts:
            sr=[r for r in er if int(r['start_step'])==start]
            cells={}
            for r in sr:
                key=(r['arm'],int(r['horizon']),int(r['learned_seed']))
                assert key not in cells
                cells[key]=int(r['success']);assert cells[key] in (0,1)
            assert set(cells)=={(a,h,s) for a in ARMS for h in (75,150) for s in (7201,7202,7203)}
            by_start.append([np.mean([cells[a,h,s] for h in (75,150) for s in (7201,7202,7203)]) for a in ARMS])
        means=np.mean(by_start,axis=0)
        points.append(dict(episode_id=episode,starts=starts,arm_means=means.tolist(),
                           contrasts=(means[0]-means[1:3]).tolist()))
    x=np.array([p['contrasts'] for p in points]);cov=np.cov(x,rowvar=False,ddof=1)
    loo=[]
    for i,p in enumerate(points):
        rest=np.delete(x,i,axis=0)
        loo.append(dict(removed_episode=p['episode_id'],mean=rest.mean(0).tolist(),
                        covariance=np.cov(rest,rowvar=False,ddof=1).tolist()))
    # Exploratory episode bootstrap quantifies uncertainty in planning inputs,
    # not confirmation inference or confidence in the changed interface.
    rng=np.random.default_rng(2026090501)
    sample=x[rng.integers(len(x),size=(20000,len(x)))]
    centered=sample-sample.mean(1,keepdims=True)
    boot_cov=np.einsum('bni,bnj->bij',centered,centered)/(len(x)-1)
    return dict(n_episodes=len(x),n_base_starts=sum(len(p['starts']) for p in points),
        outcome_rows=len(rows),horizons=[75,150],training_seeds=[7201,7202,7203],
        arm_order=ARMS,episode_points=points,contrast_order=['continuation_minus_greedy300','continuation_minus_gaussian'],
        mean=x.mean(0).tolist(),covariance=cov.tolist(),correlation=np.corrcoef(x.T).tolist(),
        leave_one_episode_out=loo,
        exploratory_bootstrap_covariance_95_percentile=np.quantile(boot_cov,[.025,.975],axis=0).tolist(),
        warning='Twelve old-interface development episodes. Estimates and bootstrap limits are unstable planning inputs, not properties of the fresh driver.')


def fit_distribution(mean,cov):
    mean=np.asarray(mean);cov=np.asarray(cov)
    target=np.r_[mean,np.diag(cov)+mean**2,cov[0,1]+np.prod(mean)]
    def fun(theta):
        score=FEATURES@theta;p=np.exp(score-logsumexp(score))
        return logsumexp(score)-theta@target,FEATURES.T@p-target
    opt=minimize(fun,np.zeros(5),jac=True,method='BFGS',options={'gtol':1e-11,'maxiter':2000})
    p=np.exp(FEATURES@opt.x-logsumexp(FEATURES@opt.x))
    residual=np.max(np.abs(FEATURES.T@p-target))
    if residual>1e-7:raise ValueError(f'infeasible/unresolved requested moments: {residual}')
    return SUPPORT,p,float(residual)


def trial(n,support,prob,rng,reps):
    count=rng.multinomial(n,prob,size=reps)
    means=count@support/n
    variance=np.maximum((count@(support**2)-n*means**2)/(n-1),0)
    se=np.sqrt(variance/n);critical=t.ppf(.975,n-1)
    lower=means-critical*se
    reject=lower>0
    # Degenerate samples: positive constant difference rejects; zero does not.
    return reject,dict(mean_simultaneous_one_sided_halfwidth=(critical*se).mean(0).tolist(),
        mean_individual_two_sided_95_width=(2*critical*se).mean(0).tolist())


def rate_record(flags):
    p=float(np.mean(flags));return dict(rate=p,mc_standard_error=float(np.sqrt(p*(1-p)/len(flags))))


def simulate(n,scenario,cov,rng,reps):
    results={}
    for label,mean in [('both_true_5pp',[.05,.05]),('global_null',[0,0]),
                       ('greedy_null_gaussian_5pp',[0,.05]),('greedy_5pp_gaussian_null',[.05,0])]:
        if scenario=='bounded_extreme_rho1':
            # Coherent worst marginal contrast variance, perfectly correlated.
            # Mixed nulls have no common ±1 support; not claimed evaluated here.
            if mean[0]!=mean[1]:continue
            support=np.array([[-1.,-1.],[1.,1.]])
            prob=np.array([(1-mean[0])/2,(1+mean[0])/2]);residual=0.
        else:support,prob,residual=fit_distribution(mean,cov)
        reject,precision=trial(n,support,prob,rng,reps)
        nulls=np.array(mean)<=0
        results[label]=dict(marginal=[rate_record(reject[:,j]) for j in range(2)],
            joint=rate_record(reject.all(1)),any_rejection=rate_record(reject.any(1)),
            familywise_false_positive=rate_record(reject[:,nulls].any(1)) if nulls.any() else None,
            precision=precision,moment_residual=residual,
            actual_variance=((prob[:,None]*support**2).sum(0)-np.array(mean)**2).tolist())
    return results


def main(inputs,out,reps):
    out.mkdir(parents=True,exist_ok=False)
    availability=json.loads((inputs/'availability.json').read_text())
    hist=historical(json.loads((inputs/'historical.json').read_text()))
    cov=np.array(hist['covariance']);maximum=availability['metadata_eligible_maximum']
    scenarios={'historical_plugin':cov,'twice_historical_variance':2*cov,
               'four_times_historical_variance':4*cov,
               'variance_0.25_rho0':np.eye(2)*.25,
               'variance_0.25_rho0.5':np.array([[.25,.125],[.125,.25]]),
               'bounded_extreme_rho1':np.ones((2,2))}
    rng=np.random.default_rng(2026090502);results=[]
    for n in sorted({maximum,400,600,800}):
        for name,c in scenarios.items():
            print(f'simulating N={n} {name}',flush=True)
            result=simulate(n,name,c,rng,reps)
            mde=[]
            for v in np.diag(c):
                mde.append(brentq(lambda d:nct.sf(t.ppf(.975,n-1),n-1,d*np.sqrt(n/v))-.8,1e-8,2.))
            results.append(dict(n=n,feasible_from_current_authorized_metadata=n<=maximum,
                scenario=name,covariance_input=c.tolist(),simulation=result,
                approximate_marginal_80pct_MDE=mde))
    report=dict(kind='preparatory_design_simulation_not_confirmation',
        input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.glob('*.json')},
        monte_carlo_replicates=reps,seed=2026090502,alpha_family=.05,alpha_each=.025,
        primary_claims=['mean episode-averaged VAD continuation success exceeds VAD greedy300',
                        'mean episode-averaged VAD continuation success exceeds Gaussian continuation'],
        inference='Two one-sided paired Student tests on distinct-episode averages; Bonferroni .025 each; df=N-1; reject iff lower bound >0. No observed +.05 gate.',
        estimand='Equal H75/H150 and equal three fixed training seeds within each episode; one common start per episode. Across-episode equal weight. Fixed checkpoints, not a new-seed population.',
        scenarios=list(scenarios),
        support='six Bernoulli runs per arm averaged; contrast pair on 1/6 hexagonal grid with a shared treatment. Maximum entropy matches moments. Not a calibrated generative model of the new interface.',
        data_capacity=availability, historical=hist,results=results,
        generality_warning='Power and false-positive checks are conditional on simulated distributions, not a universal finite-sample guarantee. No finite-population correction or independent seed/start inflation.',
        distribution_free_alternative='Bonferroni Hoeffding lower bounds subtract sqrt(2 log(40)/N); at N=82 this is about .300, substantially less sensitive.',
        confirmation_frozen=False,confirmation_launched=False)
    (out/'planning.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    (out/'sha256.txt').write_text(hashlib.sha256((out/'planning.json').read_bytes()).hexdigest()+'  planning.json\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--replicates',type=int,default=20000)
    a=p.parse_args();main(a.inputs,a.out,a.replicates)
