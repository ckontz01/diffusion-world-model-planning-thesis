"""Complete-cohort native-success analysis; no outcome-dependent dispatch."""
import json
from pathlib import Path
import lgprb2_contract as c

def task(root,spec):
    c.old.verify(root);m=c.read(root/'TECHNICAL.json')
    c.require(m['task']==spec and m['complete'] and m['gpu_used']==spec['gpu'],'Exact sealed worker')
    if spec['gpu']:
        c.require(m['episodes']==8 and m['models_unchanged'] and m['technical_checks']==dict(
            common_initial_banks=True,fresh_episode_ownership=True,endpoint_checks_passed=8),'Eight authenticated fresh episodes')
    return m

def summarize(rows,refs):
    import numpy as np
    tasks=c.grid(refs)
    expected={(r,s,f,n,h) for r in refs for s in c.SEEDS for f,n in c.ARMS for h in (75,150)}
    keys=[(r['reference'],r['seed'],r['family'],r['populations'],r['horizon']) for r in rows]
    c.require(len(rows)==12288 and len(set(keys))==12288 and set(keys)==expected,'Complete RB2 grid; no historical rows')
    c.require(all(type(r['success']) is int and r['success'] in (0,1) for r in rows),'Binary native success')
    lookup=dict(zip(keys,[r['success'] for r in rows]));effects=[]
    for ref in refs:
        means={f'{f}-{n}':sum(lookup[ref,s,f,n,h] for s in c.SEEDS for h in (75,150))/6 for f,n in c.ARMS}
        delta5=means['diffusion-5']-means['gmm-5'];delta30=means['diffusion-30']-means['gmm-30']
        effects.append(dict(reference=ref,means=means,delta5=delta5,delta30=delta30,interaction=delta5-delta30,
            diffusion5_minus_diffusion30=means['diffusion-5']-means['diffusion-30'],
            diffusion5_minus_gmm30=means['diffusion-5']-means['gmm-30']))
    indices=np.random.default_rng(20260920).integers(0,512,size=(10000,512))
    def interval(values):
        v=np.asarray(values,float);return dict(mean=float(v.mean()),interval95=np.quantile(v[indices].mean(1),[.025,.975]).tolist())
    return dict(independent_sources=512,main_episodes=12288,reused_episodes=0,source_effects=effects,
        primary=dict(name='delta5',**interval([e['delta5'] for e in effects])),
        secondary={k:interval([e[k] for e in effects]) for k in ('delta30','interaction','diffusion5_minus_diffusion30','diffusion5_minus_gmm30')},
        absolute={f'{f}-{n}':interval([e['means'][f'{f}-{n}'] for e in effects]) for f,n in c.ARMS},
        strata=[dict(family=f,populations=n,horizon=h,seed=s,success=sum(lookup[r,s,f,n,h] for r in refs)/512) for f,n in c.ARMS for h in (75,150) for s in c.SEEDS],
        interpretation='Outcome-informed source-disjoint development; not untouched confirmation, no noninferiority or automatic promotion; secondary intervals descriptive.')

def aggregate(source,run,specs):
    from lgp1_endpoint import verify_file
    from lgprb2_contract import cell_name
    refs=c.read(source/c.DOC/'DATA-ROLES.json')['ordered_references'];lock=c.read(source/c.DOC/'INPUTS.json')
    c.verify_models(source);rows=[];resources=[]
    for spec in specs[:-1]:
        root=run/spec['name'];m=task(root,spec)
        c.require(m['source_sha256']==c.sha(source/c.MANIFEST) and m['approval_sha256']==c.sha(run/'APPROVAL.json'),'Worker provenance')
        report=c.read(root/'REPORT.json');resources.append(m)
        c.require(len(report['rows'])==8,'All eight rows')
        for cell,r in zip(spec['episodes'],report['rows']):
            c.require(all(r[k]==v for k,v in cell.items()) and r['reference']==spec['reference'] and r['seed']==spec['seed'],'Arm/order identity')
            verify_file(root/cell_name(cell),r,lock['references'][str(spec['reference'])])
            n=r['populations']
            c.require(all(len(s['rounds'])==s['cost_calls']==n and s['candidate_trajectories']==300*n and
                s['predicted_primitive_steps']==4500*n and all(q['candidates']==300 for q in s['rounds']) for s in r['stages']),'Exact scoring budget')
            compact={k:v for k,v in r.items() if k!='stages'}
            compact['planning']={k:sum(s[k] for s in r['stages']) for k in ('seconds','proposal_seconds','context_seconds','refinement_total_seconds','scoring_seconds','bank_hash_seconds','cost_calls','candidate_trajectories','predicted_primitive_steps')}
            compact['planning']['stages']=len(r['stages']);rows.append(compact)
    ledger=[json.loads(s) for s in (run/'DISPATCH.jsonl').read_text().splitlines()]
    gate=c.read(run/'TECHNICAL-TRANCHE-PASSED.json');submitted=[r for r in ledger if r['event']=='submitted']
    c.require(len(submitted)==1537 and all(r['unix']>gate['unix'] for r in submitted[4:]),'Complete grid and technical ordering')
    result=summarize(rows,refs);result.update(rows=rows,resources=resources,accounting=c.read(run/'PRE-ANALYSIS-ACCOUNTING.json'))
    return result
