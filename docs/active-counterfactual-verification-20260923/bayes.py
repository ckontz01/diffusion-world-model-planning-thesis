"""Established references, never represented as an exact real-task oracle."""
import numpy as np
from tree import finite


class BayesianRegression:
    """Bayesian last-layer regression on frozen ordinary-network features.

    Gaussian unit observation noise, N(0,I) coefficient prior; clipped posterior
    mean is an approximate binary-success estimate, NOT calibrated probability.
    Source/prefix/suffix-balanced weighted likelihood. No new optimizer or labels.
    Deployment conditions features on the actual response; coefficient posterior
    is frozen. This is Bayesian regression, not full ALPaCA meta-learning or a
    claim of online identification of physical parameters.
    """
    def __init__(self,ordinary):self.ordinary=ordinary

    def features(self,x,a,r):
        _,cache=self.ordinary.forward(x,a,r)
        return np.concatenate((cache[-2],np.ones((len(cache[-2]),1))),-1)

    def fit(self,data):
        from model import row_weights
        if set(data['roles'])!={'fit'}:raise ValueError('Fitting only')
        phi=self.features(data['x'],data['a'],data['r'])
        w=(row_weights(data)[:,None]*data['mask']/np.maximum(data['mask'].sum(1,keepdims=True),1)).ravel()
        # Source effective count, not raw branches: finite declared likelihood scale.
        w*=len(set(data['source_ids']))
        self.precision=np.eye(phi.shape[1])+phi.T@(phi*w[:,None])
        self.covariance=np.linalg.solve(self.precision,np.eye(phi.shape[1]))
        self.mean=np.linalg.solve(self.precision,phi.T@(w*data['y'].ravel()))
        finite(self.mean);return self

    def predict(self,x,a,r):
        return np.clip(self.features(x,a,r)@self.mean,0,1).reshape(a.shape[:2])


def exact_artificial_policy(case):
    """Correct known artificial test law; identical inputs/control options.

    It knows reversal when that case's test law reverses. This privileged *law*
    knowledge is disclosed: no hidden source mode or unexecuted outcome supplied.
    No neural superiority over this contingent optimum is expected.
    """
    from prototype.experiment import tables,choose
    law,_,info=tables(case,test=True)
    return choose(law,info,'oracle_contingent')
