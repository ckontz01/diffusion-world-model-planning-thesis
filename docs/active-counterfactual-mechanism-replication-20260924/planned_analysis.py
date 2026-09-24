"""Executable estimator for a future complete sealed 512-source table.

Preparation tests supply artificial binary arrays only. Source axes, not seed
or branch rows, are resampled. No data loading, runtime, fitting or selection.
"""
import base
import math
from statistics import NormalDist
import numpy as np

ARMS=('static','committed_feedback','no_update','active','ordinary')
NAMES=('active-minus-no_update','active-minus-committed_feedback',
       'committed_feedback-minus-static','no_update-minus-static',
       'feedback-by-prefix-interaction','active-minus-ordinary','active-minus-early-replan')

def contrasts(y, early):
    y=np.asarray(y); early=np.asarray(early)
    if y.shape!=(512,3,5) or early.shape!=(512,): raise ValueError('Exact source/seed/arm axes')
    if not np.isin(y,[0,1]).all() or not np.isin(early,[0,1]).all(): raise ValueError('Complete binary outcomes required')
    y=y.astype(float); s,cf,nu,a,o=[y[:,:,i] for i in range(5)]
    return np.stack((a-nu,a-cf,cf-s,nu-s,(a-nu)-(cf-s),a-o,a-early[:,None]),axis=-1)

def sensitivity():
    # Approximate paired-normal planning formula, NOT achieved/exact power.
    z=NormalDist().inv_cdf(1-.05/(2*7))+NormalDist().inv_cdf(.8)
    return {'normal_80pct_two_sided_bonferroni7':[
        dict(discordance=d,conservative_difference_scale=z*math.sqrt(d/512)) for d in (.05,.1,.25,.5,1.)],
        'assumption':'single-pair Bernoulli difference variance <= discordance; no extra independence or gain from three model seeds assumed',
        'fixed_effect_size_of_interest':.05,'guaranteed_power':False,
        'hoeffding_family7_halfwidth':2*math.sqrt(math.log(2*7/.05)/(2*512)),
        'interaction_halfwidth':4*math.sqrt(math.log(2*7/.05)/(2*512))}

def analyze(y, early):
    d=contrasts(y,early); source=d.mean(axis=1)
    rng=np.random.default_rng(94431); draws=[]
    # Chunked <=100x512x7, well inside CPU analysis RAM cap.
    for _ in range(100):
        indices=rng.integers(0,512,(100,512)); draws.append(source[indices].mean(axis=1))
    boot=np.concatenate(draws); answer={}
    for k,name in enumerate(NAMES):
        r=4 if k==4 else 2; limit=r/2
        margin=r*math.sqrt(math.log(2*7/.05)/(2*512)); effect=float(source[:,k].mean())
        per_seed=d[:,:,k].mean(axis=0)
        answer[name]=dict(source_effects=source[:,k].tolist(),source_by_seed_effects=d[:,:,k].tolist(),
                         effect=effect,per_seed_means=per_seed.tolist(),
                         seed_mean_range=[float(per_seed.min()),float(per_seed.max())],
                         seed_mean_sample_sd=float(per_seed.std(ddof=1)),
                         descriptive95=np.quantile(boot[:,k],[.025,.975]).tolist(),
                         nominal_bonferroni99_285714=np.quantile(boot[:,k],[.05/14,1-.05/14]).tolist(),
                         simultaneous_hoeffding95=[max(-limit,effect-margin),min(limit,effect+margin)])
    return dict(source_count=512,model_seed_pairs=3,source_is_unit=True,family_size=7,
                fixed_seed_average_not_population_training_seed_inference=True,contrasts=answer,
                bootstrap_seed=94431,bootstrap_resamples=10000,
                interval_scope='Hoeffding requires independent bounded source observations; finite-cohort mean is descriptive/exact. Bootstrap is nominal, not a finite-sample guarantee.')
