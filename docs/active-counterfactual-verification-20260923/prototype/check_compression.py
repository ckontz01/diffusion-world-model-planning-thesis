"""Numerical consistency checks, not a coverage/novelty proof."""
import json,time
from pathlib import Path
import numpy as np
from contrast_filter import ContrastFilter,expected_max_affines
root=Path(__file__).parent/'compression-v1';root.mkdir(exist_ok=False)
config=dict(seed=20260923,cases=64,utility_dim=8,observation_dim=192,latent_rank=12,obs_noise=.3,observations_per_case=16)
(root/'CONFIG.json').write_text(json.dumps(config,sort_keys=True,indent=2)+'\n')
rng=np.random.default_rng(config['seed']);start=time.perf_counter();maxmean=0.;maxcov=0.;ranks=[]
for case in range(config['cases']):
 m,d,k=config['utility_dim'],config['observation_dim'],config['latent_rank']
 B=rng.normal(size=(m,k));H=rng.normal(size=(d,k));mu=rng.normal(size=m);mr=rng.normal(size=d)
 pu=B@B.T+.1*np.eye(m);pr=H@H.T+config['obs_noise']**2*np.eye(d);C=B@H.T
 f=ContrastFilter.build(mu,mr,pu,pr,C);D=f.contrast_matrix
 densecov=D@(pu-C@np.linalg.solve(pr,C.T))@D.T
 maxcov=max(maxcov,float(np.max(abs(densecov-f.posterior_covariance))))
 for _ in range(config['observations_per_case']):
  obs=mr+H@rng.normal(size=k)+config['obs_noise']*rng.normal(size=d)
  exact=D@(mu+C@np.linalg.solve(pr,obs-mr))
  maxmean=max(maxmean,float(np.max(abs(exact-f.posterior_mean(obs)))))
 ranks.append(f.dimension)
assert maxmean<1e-10 and maxcov<1e-10 and max(ranks)<=7
# A common utility error is decision-irrelevant even if perfectly measured.
H=np.eye(4);B=np.ones((8,4));pu=B@B.T+.1*np.eye(8);pr=2*np.eye(4);C=B
f=ContrastFilter.build(np.arange(8),np.zeros(4),pu,pr,C)
assert f.dimension==0
# Formula and high-accuracy independent Gauss-Hermite check of scalar acquisition.
# Upper envelopes have nonsmooth corners, so quadrature is a consistency check
# with disclosed tolerance, not evidence against exact integration if convergence slow.
analytic=expected_max_affines([0,0],[0,1]);assert abs(analytic-1/np.sqrt(2*np.pi))<1e-14
assert abs(expected_max_affines([0,1],[2,2])-1)<1e-14
assert abs(expected_max_affines([3,-1,2],[0,0,0])-3)<1e-14
for _ in range(100):
 a=rng.normal(size=8);b=rng.normal(size=8)
 v=expected_max_affines(a,b)
 assert v>=max(a)-1e-12
 assert abs(expected_max_affines(a+3,b+2)-v-3)<1e-12
out=dict(max_dense_compressed_mean_error=maxmean,max_dense_compressed_covariance_error=maxcov,
         cases=64,conditional_means_checked=1024,max_compressed_dimensions=max(ranks),raw_observation_dimensions=192,
         common_mode_dimensions=f.dimension,scalar_envelope_invariance_cases=100,
         seconds=time.perf_counter()-start,scope='Supplied valid Gaussian laws. No neural model was trained; no robotics result.')
(root/'RESULTS.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
