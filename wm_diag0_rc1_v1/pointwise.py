"""Actual shared role loop; no implicit batching or cross-call cache."""
import numpy as np

def extract(rgb,one,concatenate):
    rgb=np.asarray(rgb)
    if rgb.dtype!=np.uint8 or rgb.ndim!=4 or rgb.shape[1:]!=(224,224,3) or not 1<=len(rgb)<=352:
        raise ValueError('bounded RGB image order')
    outputs=[]
    for i in range(len(rgb)):
        outputs.append(one(rgb[i:i+1]))
    return concatenate(outputs)
