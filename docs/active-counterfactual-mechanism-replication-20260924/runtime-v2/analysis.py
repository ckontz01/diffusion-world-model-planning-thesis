"""Saved evidence only; exact reviewed seven-contrast estimator, no fitting/physics."""
import common as c
import sys
from prefix_coupling import check_actual

def analyze(auth,out):
    import numpy as np
    from verify import load_verify
    from models import check_freeze
    from acceptance import check_gate
    check_freeze(auth.run,auth.approval['package_sha256']);check_gate(auth.run)
    sys.path.append(str(c.PROPOSAL))
    from planned_analysis import analyze as estimate
    refs=c.roles()['mechanism_evaluation'];arms=list(c.CONTROLS[:-1]);y=np.zeros((512,3,5),dtype=np.int8);early=np.zeros(512,dtype=np.int8)
    evidence=[];trees={};initials={};counts={};prefixes={};prefix_source=None;prefix_records=0
    for j in c.grid():
        if j['stage']!='evaluation':continue
        root=auth.run/j['key'];c.verify_seal(root,j)
        a,m,check=load_verify(root,role_map=c.roles(),authorization=auth)
        c.require(m['pair']==j['pair'] and m['control']==j['control'] and m['reference']==j['reference'],'Evidence estimator axes')
        # Actual saved arrays, not controller digests. Retain only one source block.
        if prefix_source!=j['reference']:prefixes={};prefix_source=j['reference']
        check_actual(prefixes,a,m);prefix_records+=1
        success=int(m['branches'][0]['success']);idx=refs.index(j['reference'])
        if j['pair'] is None:early[idx]=success
        else:y[idx,j['pair'],arms.index(j['control'])]=success
        from worker import arrays_digest
        tree=arrays_digest(a,[k for k in a if k.startswith('tree/')]);initial=arrays_digest(a,['requested_initial','goal_state','initial_image','goal_image','goal_latent'])
        if j['pair'] is not None:
            if idx in trees:c.require(trees[idx]==tree,'Exact cross-arm/model tree actions/features')
            trees[idx]=tree
        if idx in initials:c.require(initials[idx]==initial,'Same fresh initial source across16 actual executions')
        initials[idx]=initial
        t=c.read(root/'TECHNICAL.json');counts[j['key']]=t
        evidence.append(dict(identity=[j['reference'],j['pair'],j['control']],success=success,seal=c.sha(root/'SEAL.json'),
                             prefix=m['branches'][0].get('prefix'),suffix=m['branches'][0].get('suffix'),steps=m['branches'][0]['steps']))
    result=estimate(y,early)
    primary=('active-minus-no_update','active-minus-committed_feedback')
    certificate=all(result['contrasts'][k]['simultaneous_hoeffding95'][0]>0 and min(result['contrasts'][k]['per_seed_means'])>0 for k in primary)
    c.write(out/'REPORT.json',dict(estimator=result,ordered_sources=refs,arms=arms,seed_pairs=[[94011,94012],[94411,94412],[94421,94422]],
            evidence=evidence,resources=counts,successes=y.tolist(),early_successes=early.tolist(),
            hoeffding_positive_additional_certificate=certificate,no_automatic_action=True,
            interpretation=c.read(c.ROOT/'REPORTING-CONTRACT.json')))
    return dict(verified_episodes=len(evidence),source_count=512,source_cluster_bootstrap=True,old32_included=False,prefix_coupling_checked_episodes=prefix_records)
