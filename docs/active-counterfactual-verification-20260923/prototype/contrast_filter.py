"""Decision-contrast sufficient observation compression for a joint Gaussian.

Established Gaussian conditioning/SVD, offered as an implementation component,
NOT a new probability theorem. Utility need not be binary; this routine is NOT
used to attach a coverage or success-probability claim to the categorical demo.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

def _finite(x,name):
    a=np.asarray(x,dtype=np.float64)
    if not np.isfinite(a).all(): raise ValueError(f'{name}: nonfinite')
    return a

@dataclass
class ContrastFilter:
    mean: np.ndarray
    observation_mean: np.ndarray
    chol: np.ndarray
    right_basis: np.ndarray
    response: np.ndarray
    posterior_covariance: np.ndarray
    contrast_matrix: np.ndarray

    @classmethod
    def build(cls,utility_mean,observation_mean,utility_cov,observation_cov,cross_cov,baseline=0,tol=1e-10):
        mu=_finite(utility_mean,'mean');mr=_finite(observation_mean,'observation mean')
        pu=_finite(utility_cov,'utility covariance');pr=_finite(observation_cov,'observation covariance')
        cr=_finite(cross_cov,'cross covariance')
        m,d=len(mu),len(mr)
        if mu.ndim!=1 or mr.ndim!=1 or m<2 or not 0<=baseline<m: raise ValueError('Dimensions/baseline')
        if pu.shape!=(m,m) or pr.shape!=(d,d) or cr.shape!=(m,d): raise ValueError('Covariance shapes')
        joint=np.block([[pu,cr],[cr.T,pr]])
        if not np.allclose(joint,joint.T,atol=tol,rtol=tol) or np.linalg.eigvalsh(joint).min()<-tol: raise ValueError('Invalid joint covariance')
        chol=np.linalg.cholesky(pr)
        # Ordered alternatives relative to baseline. These suffice for argmax.
        D=np.delete(np.eye(m),baseline,axis=0);D[:,baseline]-=1
        C=D@cr
        W=np.linalg.solve(chol,C.T).T  # C @ L^{-T}
        u,s,vt=np.linalg.svd(W,full_matrices=False)
        keep=s>tol*max(1.,s.max(initial=0.))
        posterior=D@pu@D.T-W@W.T
        return cls(D@mu,mr,chol,vt[keep],u[:,keep]*s[keep],posterior,D)

    @property
    def dimension(self):return len(self.right_basis)

    def encode_observation(self,observed):
        observed=_finite(observed,'observed')
        if observed.shape!=self.observation_mean.shape: raise ValueError('Observation shape')
        return self.right_basis@np.linalg.solve(self.chol,observed-self.observation_mean)

    def posterior_mean(self,observed):
        return self.mean+self.response@self.encode_observation(observed)


def expected_max_affines(intercepts,slopes):
    """Exact E max_i(a_i+b_i Z), Z~Normal(0,1), via line upper envelope.
    This is the standard scalar correlated knowledge-gradient calculation.
    """
    a=_finite(intercepts,'intercepts');b=_finite(slopes,'slopes')
    if a.ndim!=1 or a.shape!=b.shape or len(a)==0:raise ValueError('Line shapes')
    unique={}
    for aa,bb in zip(a,b):unique[float(bb)]=max(float(aa),unique.get(float(bb),-math.inf))
    lines=[];starts=[]
    for bb,aa in sorted(unique.items()):
        start=-math.inf
        while lines:
            oldb,olda=lines[-1]
            start=(olda-aa)/(bb-oldb)
            if start>starts[-1]:break
            lines.pop();starts.pop()
        if not lines:start=-math.inf
        lines.append((bb,aa));starts.append(start)
    def cdf(z):return .5*(1+math.erf(z/math.sqrt(2)))
    def phi(z):return math.exp(-.5*z*z)/math.sqrt(2*math.pi) if math.isfinite(z) else 0.
    total=0.
    for i,(bb,aa) in enumerate(lines):
        lo=starts[i];hi=starts[i+1] if i+1<len(starts) else math.inf
        total+=aa*(cdf(hi)-cdf(lo))+bb*(phi(lo)-phi(hi))
    return total
