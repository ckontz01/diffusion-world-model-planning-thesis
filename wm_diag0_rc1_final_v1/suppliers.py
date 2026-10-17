"""Resolve the actual six retained heads/four active heads/128 fixed parents.

These helpers run only inside the future allocated final analysis. Returned
parent proofs contain scientific values and MUST NOT be printed by a monitor.
No checkpoint, simulator, new fit, source generation, or model forward is used.
"""
import json
from pathlib import Path
from wm_diag0_rc1_grid_v1.common import SETTINGS,identity,gates,canonical


def chain(task,acceptance=None,seal=None):
    task=Path(task);p=task/'controls/ACCEPTED.json'
    a=json.loads(p.read_text());r=json.loads((task/'controls/RESULT.json').read_text())
    actual=identity(p)
    if acceptance is not None and actual!=acceptance:raise ValueError('bound accepted supplier identity')
    expected=r.get('acceptance_identity')
    if expected is not None:
        if expected!=actual:raise ValueError('new result/acceptance identity chain')
    elif r.get('acceptance_sha256')!=actual['sha256']:raise ValueError('original result/acceptance chain')
    if not a['accepted'] or r['status']!='ACCEPTED':raise ValueError('terminal independent acceptance required')
    if seal is not None and a['output_seal']!=seal:raise ValueError('bound output seal')
    if identity(task/'output/MEMBERS.json')!=a['output_seal']:raise ValueError('actual output seal')
    return a


def parent_location(c,setting,root_index):
    if type(setting) is not int or not 0<=setting<4 or type(root_index) is not int or not 0<=root_index<32:
        raise ValueError('fixed four settings and32 diagnostic roots')
    if root_index==0:
        s=c['rc1_grid']['technical_suppliers'][str(setting)]
        return Path(s['run'])/'tasks'/('technical-'+str(setting)),s
    return Path(c['run'])/'tasks'/('grid-'+str(setting*31+root_index-1)),None


def retained_heads(c):
    old=Path(c['recovery']['old_run']);new=Path(c['rc1_technical']['heads_run']);rows=[]
    for setting in range(4):
        s=c['recovery']['accepted_suppliers']['readout-'+str(setting)]
        rows.append((setting,old/'tasks'/('readout-'+str(setting)),s['control'],s['output_seal'],setting in (0,2),False))
    for setting in (1,3):
        s=c['rc1_technical']['head_suppliers'][str(setting)]
        rows.append((setting,new/'tasks'/('readout-'+str(setting)),s['acceptance_identity'],s['output_seal'],True,True))
    if len(rows)!=6 or sum(r[4] for r in rows)!=4:raise ValueError('six retained/four active heads')
    return rows


def independently_accept_heads(c):
    from wm_diag0_campaign_v4.accept_readout import accept as original
    from wm_diag0_rc1_heads_v1.validate import accept as pointwise
    active={};proofs=[]
    for setting,task,control,seal,is_active,is_rc1 in retained_heads(c):
        chain(task,control,seal)
        proof=(pointwise if is_rc1 else original)(task/'output',seal,c,setting)
        proof.update(active=is_active,RC1_pointwise=is_rc1,setting=setting,acceptance_identity=control)
        proofs.append(proof)
        if is_active:
            if setting in active:raise ValueError('ambiguous active head')
            active[setting]=(task/'output',seal)
    if set(active)!=set(range(4)):raise ValueError('complete active head map')
    return active,proofs


def independently_accept_sources(c):
    from wm_diag0_native_v3.store import authenticate
    control=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(control)!=c['source_acceptance']:raise ValueError('fixed source acceptance identity')
    sources=json.loads(control.read_text())
    plan=json.loads((Path(c['run'])/'source/ROOT-PLAN.json').read_text())['roots']
    if len(plan)!=120 or len({r['root_id'] for r in plan})!=120:raise ValueError('all120 original root identities')
    expected={task+'-'+str(i).zfill(3) for task in ('pusht','reacher') for i in range(60)}
    if set(sources['source_seals'])!=expected:raise ValueError('exact120 source seal keys')
    for row in plan:
        key=row['task']+'-'+str(row['root_index']).zfill(3)
        p=Path(c['source_runs'][row['task']])/'tasks'/key/'output'
        authenticate(p,sources['source_seals'][key],12000000)
        record=json.loads((p/'record.json').read_text())
        if record['root']!=row or not record['available']:raise ValueError('exact accepted source/role/seed')
    return sources


def independently_accept_parents(c,sources,heads):
    from wm_diag0_campaign_v4.accept import accept as original
    from wm_diag0_rc1_technical_v1.accept import accept as continued
    from wm_diag0_rc1_grid_v1.common import check_usage as grid_usage
    from wm_diag0_rc1_technical_v1.common import check_usage as technical_usage
    from wm_diag0_rc1_grid_v1.resources import parent
    gates(c);rows=[]
    plan=json.loads((Path(c['run'])/'source/ROOT-PLAN.json').read_text())['roots']
    for setting,(task,backbone) in enumerate(SETTINGS):
        for i in range(32):
            t,supplier=parent_location(c,setting,i)
            ctl=chain(t,*( (supplier['acceptance_identity'],supplier['output_seal']) if supplier else () ))
            w=json.loads((t/'controls/WORKER-SUCCESS.json').read_text())
            if w['output_seal']!=ctl['output_seal']:raise ValueError('worker accepted seal chain')
            selected=json.loads((t/'output/SELECTION.json').read_text())
            row=next(r for r in plan if r['task']==task and r['root_index']==i)
            if selected['root']!=row or selected['backbone']!=backbone or selected['technical']!=(i==0):raise ValueError('fixed root/task/backbone parent')
            if selected.get('RC1_retained_bank_continuation',False)!=(setting==1 and i==0):raise ValueError('only the approved retained-bank continuation')
            if backbone=='dinowm_noprop' and canonical(selected['route'])!=canonical(c['rc1_technical']['head_suppliers'][str(setting)]['route']):raise ValueError('own fixed pointwise route')
            if i:grid_usage(setting*31+i-1,ctl['actual_usage'])
            elif setting:technical_usage(setting,ctl['actual_usage'])
            key=task+'-'+str(i).zfill(3)
            proof=(continued if setting==1 and i==0 else original)(t/'output',ctl['output_seal'],t/'controls/SELECTION-EXTERNAL.json',
                Path(c['source_runs'][task])/'tasks'/key/'output',sources['source_seals'][key],*heads[setting],c,gpu=False)
            physical=parent(t/'output')
            if i and physical!=ctl['physical_resource_usage']:raise ValueError('independent physical resource chain')
            proof.update(setting=setting,root_index=i)
            rows.append((proof,t/'output',json.loads((t/'output/USAGE.json').read_text()),physical,ctl.get('actual_usage')))
    if len(rows)!=128 or len({(r[0]['setting'],r[0]['root_index']) for r in rows})!=128:raise ValueError('exact128 accepted logical parents')
    return rows
