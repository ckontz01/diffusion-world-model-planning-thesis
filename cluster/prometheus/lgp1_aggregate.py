"""Final source-paired native-success summary; no validation-selected gate."""
from pathlib import Path
import numpy as np
import json
import lgp1_contract as c
import lgp1_verify as verify

def summarize(rows):
    refs=sorted({r['reference'] for r in rows})
    c.require(len(refs)==32 and len(rows)==384,'Complete main population')
    keys={(r['reference'],r['horizon'],r['family'],r['seed']) for r in rows}
    c.require(len(keys)==384 and keys=={(r,h,f,s) for r in refs for h in (75,150) for f in c.FAMILIES for s in c.SEEDS},'Full paired grid')
    effects=[]
    for ref in refs:
        means={f:float(np.mean([r['success'] for r in rows if r['reference']==ref and r['family']==f])) for f in c.FAMILIES}
        effects.append(dict(reference=ref,**means,diffusion_minus_gmm=means['diffusion']-means['gmm']))
    x=np.array([r['diffusion_minus_gmm'] for r in effects]);rng=np.random.default_rng(20260918)
    boot=x[rng.integers(0,32,size=(10000,32))].mean(1)
    return dict(source_effects=effects,primary=float(x.mean()),descriptive_interval=np.quantile(boot,[.025,.975]).tolist(),
        family_success={f:float(np.mean([r['success'] for r in rows if r['family']==f])) for f in c.FAMILIES},
        strata=[dict(family=f,horizon=h,seed=s,success=float(np.mean([r['success'] for r in rows if (r['family'],r['horizon'],r['seed'])==(f,h,s)])))
                for f in c.FAMILIES for h in (75,150) for s in c.SEEDS],
        independent_units=32,interpretation='descriptive exposed development; proposer effect within modified planner; no promotion')

def aggregate(run,specs,source):
    run=Path(run);rows=[];resources=[];fits=[]
    approval=c.read(run/'APPROVAL.json');frozen=c.read(run/'PRE-EVALUATION-FREEZE.json')
    dispatch=[json.loads(line) for line in (run/'DISPATCH.jsonl').read_text().splitlines()]
    submitted=[r for r in dispatch if r['event']=='submitted' and r['task']['kind'] in ('technical','evaluation')]
    c.require(len(submitted)==196 and all(r['unix']>=frozen['unix'] for r in submitted),'Model-freeze ordering')
    c.require(len(frozen['models'])==6,'All-six model freeze')
    for name,digest in frozen['models'].items():
        c.require(c.sha(run/name/'model.pt')==digest and c.sha(run/name/'sha256.txt')==frozen['seals'][name],'Frozen model identity')
    for spec in specs:
        if spec['kind']=='analysis': continue
        root=c.task_root(run,spec);meta=verify.task(root,spec);resources.append(meta)
        origin=(root.parent if root.parent!=run else run)
        origin_approval=c.read(origin/'APPROVAL.json')
        c.require(meta['source_sha256']==origin_approval['source_sha256'] and
                  meta['approval_sha256']==c.sha(origin/'APPROVAL.json'),'Worker source/approval binding')
        if origin!=run:
            c.require(spec['kind']=='cache' and approval.get('validation_recovery'),'Only explicit cache reuse')
            c.require(origin_approval['input_sha256']==approval['input_sha256'],'Reused input identities')
        if spec['kind'] in ('technical','evaluation'):
            reference=c.read(Path(source)/c.DOC/'INPUTS.json')['references'][str(spec['reference'])]
            episodes=verify.episodes(run/spec['name'],spec,reference)
            if spec['kind']=='evaluation': rows.extend(episodes)
        if spec['kind']=='fit': fits.append(c.read(run/spec['name']/'REPORT.json'))
    c.require(sum(f['updates'] for f in fits)==72000 and sum(f['row_presentations'] for f in fits)==9216000,'Total fitting grid')
    if approval.get('validation_recovery'):
        from lgp1_validation_recovery import MODEL
        c.require(c.sha(run/'fit-gmm-8301/model.pt')==MODEL,'Original final GMM preserved')
        c.require(sum(f['optimizer_updates_this_allocation'] for f in fits)==60000,'No repeated saved-model updates')
        c.require(sum(f['row_presentations_this_allocation'] for f in fits)==7680000,'No repeated saved-model rows')
    result=summarize(rows)
    result.update(rows=rows,fits=fits,resources=resources,main_episodes=384,technical_episodes=8,
                  model_freeze=c.read(run/'PRE-EVALUATION-FREEZE.json'),ledger=c.read(run/'PRE-ANALYSIS-ACCOUNTING.json'))
    return result
