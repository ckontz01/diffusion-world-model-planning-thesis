"""Native sklearn in-place float32 scaler rounding and physical grouping."""
import numpy as np

def decode(z,mean,std):
    z=np.asarray(z)
    if z.shape[-2:]!=(5,10) or z.dtype!=np.float32: raise ValueError('native float32 grouped plan')
    out=z.reshape(*z.shape[:-2],25,2).copy()
    out*=std; out+=mean
    return out

def normalize(a,mean,std):
    a=np.asarray(a)
    if a.shape[-2:]!=(25,2) or a.dtype!=np.float32: raise ValueError('retained physical float32 plan')
    out=a.copy(); out-=mean; out/=std
    return out.reshape(-1,5,10)
