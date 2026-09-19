"""Complete source-clustered descriptive contrasts; no model selection/gates."""
import json
from pathlib import Path
import lgprb1_contract as c

def task(root,spec):
    c.old.verify(root);m=c.read(root/'TECHNICAL.json')
    c.require(m['task']==spec and m['complete'] and m['gpu_used']==spec['gpu'],'Exact completed task')
    if spec['kind']=='evaluation':c.require(m['episodes']==2 and m['models_unchanged'],'Two frozen-model episodes')
    if spec['kind']=='compatibility':c.require(m['passed'] and m['first_decisions']==8 and m['physical_actions']==0,'Technical compatibility only')
    return m

def summarize(rows):
    import numpy as np
    refs=sorted({r['reference'] for r in rows});budgets=(1,5,30)
    expected={(r,b,f,h,s) for r in refs for b in budgets for f in c.old.FAMILIES for h in (75,150) for s in c.old.SEEDS}
    c.require(len(refs)==32 and len(rows)==1152 and {(r['reference'],r['populations'],r['family'],r['horizon'],r['seed']) for r in rows}==expected,'Complete 3-budget grid')
    effects=[]
    for ref in refs:
        means={str(b):{f:float(np.mean([r['success'] for r in rows if (r['reference'],r['populations'],r['family'])==(ref,b,f)])) for f in c.old.FAMILIES} for b in budgets}
        diffs={b:v['diffusion']-v['gmm'] for b,v in means.items()}
        effects.append(dict(reference=ref,means=means,family_differences=diffs,
            changes_relative_to_30={str(b):diffs[str(b)]-diffs['30'] for b in (1,5)}))
    rng=np.random.default_rng(20260919);indices=rng.integers(0,32,size=(10000,32))
    def interval(values):
        v=np.array(values);return dict(mean=float(v.mean()),descriptive_interval=np.quantile(v[indices].mean(1),[.025,.975]).tolist())
    result=dict(independent_sources=32,main_episodes=1152,new_episodes=768,reused_episodes=384,source_effects=effects,
        family_success={str(b):{f:interval([e['means'][str(b)][f] for e in effects]) for f in c.old.FAMILIES} for b in budgets},
        family_differences={str(b):interval([e['family_differences'][str(b)] for e in effects]) for b in budgets},
        changes_relative_to_30={str(b):interval([e['changes_relative_to_30'][str(b)] for e in effects]) for b in (1,5)},
        strata=[dict(populations=b,family=f,horizon=h,seed=s,success=float(np.mean([r['success'] for r in rows if (r['populations'],r['family'],r['horizon'],r['seed'])==(b,f,h,s)]))) for b in budgets for f in c.old.FAMILIES for h in (75,150) for s in c.old.SEEDS],
        interpretation='Outcome-informed exposed development; shared source resamples, no multiplicity-adjusted confirmatory claims, no favorable-budget/model promotion.')
    return result

def aggregate(source,run,specs):
    from lgp1_endpoint import verify_file
    reuse=c.verify_reuse(source);rows=[];resources=[];lock=c.read(source/c.old.DOC/'INPUTS.json')
    def consume(root,spec,reused=False):
        rr=c.read(root/'REPORT.json')['rows'];c.require(len(rr)==2 and {r['horizon'] for r in rr}=={75,150},'Both horizons')
        for r in rr:
            c.require((r['reference'],r['family'],r['seed'])==(spec['reference'],spec['family'],spec['seed']),'Row identity')
            verify_file(root,r,lock['references'][str(spec['reference'])])
            n=30 if reused else spec['populations']
            c.require(all(len(s['rounds'])==n and s['cost_calls']==n and s['candidate_trajectories']==300*n and
                s['predicted_primitive_steps']==4500*n and all(v['candidates']==300 for v in s['rounds']) for s in r['stages']),'Exact scored populations')
            if not reused:c.require(all('initial_unprojected_bank_sha256' in s and 'initial_projected_bank_sha256' in s for s in r['stages']),'New read-only fingerprints')
            row={k:v for k,v in r.items() if k!='stages'}
            row.update(populations=n,reused=reused,provenance=dict(root=str(root),seal=c.sha(root/'sha256.txt'),
                source_sha256=c.OLD_SOURCE_SHA if reused else c.sha(source/c.MANIFEST)))
            row['planning']=dict(stages=len(r['stages']),**{key:sum(s[key] for s in r['stages']) for key in
                ('seconds','proposal_seconds','refinement_total_seconds','context_seconds','scoring_seconds','cost_calls','candidate_trajectories','predicted_primitive_steps')},
                bank_hash_seconds=sum(s.get('bank_hash_seconds',0) for s in r['stages']))
            rows.append(row)
    for old in reuse['main_workers']:consume(c.OLD_RUN/old['name'],old['task'],True)
    for spec in specs:
        if spec['kind']=='analysis':continue
        root=run/spec['name'];m=task(root,spec)
        c.require(m['source_sha256']==c.sha(source/c.MANIFEST) and m['approval_sha256']==c.sha(run/'APPROVAL.json'),'New worker lineage')
        resources.append(m)
        if spec['kind']=='evaluation':consume(root,spec)
    dispatch=[json.loads(v) for v in (run/'DISPATCH.jsonl').read_text().splitlines()]
    gate=c.read(run/'COMPATIBILITY-PASSED.json')
    new=[r for r in dispatch if r['event']=='submitted' and r['task']['kind']=='evaluation']
    c.require(len(new)==384 and all(r['unix']>gate['unix'] for r in new),'Complete post-compatibility grid')
    result=summarize(rows);result.update(rows=rows,resources=resources,freeze_sha256=c.FREEZE_SHA,
        original_record='f42c189b2e18968303dee5a733cf670d2301a657',accounting=c.read(run/'PRE-ANALYSIS-ACCOUNTING.json'))
    return result
