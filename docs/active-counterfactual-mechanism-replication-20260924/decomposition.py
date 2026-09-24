"""Saved-feature CPU predictions; no learned-world forward or outcome inference."""
import base
import numpy as np
from policy import features
from tree import Node, Tree, identity, tie_argmax

def restore_tree(a):
    nodes = []
    for p, count in enumerate(a['tree/count']):
        n = int(count)
        nodes.append(Node(a['tree/prefix'][p], tuple(a['tree/suffix'][p,:n]),
                          a['tree/predicted_prefix'][p], tuple(a['tree/predicted_terminal'][p,:n]),
                          tuple('saved' for _ in range(n))))
    return Tree(tuple(nodes), a['tree/baseline'], 0).validate()

def prefix_values(joint, tree, h, seed=94021):
    rng = np.random.default_rng(seed)
    half = rng.normal(size=(16, joint.rdim)); eps = np.concatenate((half,-half))
    result = []
    for p, node in enumerate(tree.nodes):
        x, a = features(h,node); o = joint.forward(x,a)[0]
        samples = (o['mu'][0,:,None,:]+np.sqrt(o['var'][0,:,None,:])*eps[None]).reshape(128,joint.rdim)
        r = samples*joint.pre.rstd+joint.pre.rmean if joint.pre else samples
        q = joint.forward(np.repeat(x,128,0),np.repeat(a,128,0),r)[0]['q']
        weights = np.repeat(o['pi'][0]/32,32)
        ps,pf,pa = map(float,o['terminal'][0])
        j = tie_argmax(o['q'][0], [(0 if (p,k)==(0,0) else 1,identity(s)) for k,s in enumerate(node.suffixes)])
        prior = float(o['q'][0,j]); sampled_fixed = float(weights@q[:,j])
        integrated_best = float(weights@np.max(q,axis=1))
        # Signed integration error is distinct from within-sample feedback gain.
        # This exactly reconstructs the ORIGINAL finite-integration score.
        row = dict(prefix=p, prefix_sha256=identity(node.prefix), committed_suffix=j,
                   terminal_success=ps, terminal_failure=pf, active_probability=pa,
                   committed_active_value=pa*prior,
                   committed_total=ps+pa*prior,
                   anticipated_feedback_increment=pa*(integrated_best-prior),
                   same_draw_feedback_increment=pa*float(weights@(np.max(q,axis=1)-q[:,j])),
                   quadrature_correction=pa*(sampled_fixed-prior),
                   active_value=ps+pa*integrated_best,
                   prior_suffix_probabilities=o['q'][0].tolist())
        assert abs(row['active_value']-(row['terminal_success']+row['committed_active_value']+row['anticipated_feedback_increment'])) < 1e-12
        assert abs(row['anticipated_feedback_increment']-row['same_draw_feedback_increment']-row['quadrature_correction']) < 1e-12
        result.append(row)
    return result
