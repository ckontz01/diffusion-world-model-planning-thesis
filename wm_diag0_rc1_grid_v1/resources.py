"""Physical-work accounting only; never emit choices, outcomes or efficacy.

The old failed DINO helper is an additional reset/replay beyond the128 eventual
accepted parents. Do not omit it or enlarge old physical caps. Real accepted
technical resource usage, plus FULL remaining grid maxima, must fit before sbatch.
"""
import json
from pathlib import Path

CAPS={'world_resets':6402,'controller_actions':386924,'Reacher_dm_steps':386968,'PushT_controller_actions':193440,
      'PushT_integrator_steps':1940800,'native_CEM_decisions':4224}

def source_and_failed_helper():
    # Original analysis's source121/resets,5324actions include the preserved
    # same-seed Reacher persistence failure. Old failed DINO's ONE PushT helper
    # adds one reset/20replay actions; its two restoration checks never ran.
    return {'world_resets':122,'controller_actions':5344,'Reacher_dm_steps':5368,
            'PushT_controller_actions':2660,'PushT_world_resets':61,'native_CEM_decisions':0}

def parent(directory):
    root=Path(directory);selected=json.loads((root/'SELECTION.json').read_text());n=len(selected['candidate_ids']);task=selected['root']['task']
    if not 1<=n<=16 or task not in ('pusht','reacher'):raise ValueError('bounded fixed parent resource input')
    worlds=1+3*n+(2 if selected['technical'] else 0)
    u={'world_resets':worlds,'controller_actions':20*worlds,'Reacher_dm_steps':40*worlds if task=='reacher' else 0,
       'PushT_controller_actions':20*worlds if task=='pusht' else 0,'PushT_world_resets':worlds if task=='pusht' else 0,'native_CEM_decisions':1}
    # The one initial solve is charged to its original supplier for retained-bank
    # continuation, NOT claimed as a new CEM solve in that continuation job.
    for i in range(n):
        p=json.loads((root/'oracle'/str(i)/'PREFIX.json').read_text());steps=p['actions']
        if type(steps) is not int or not 0<=steps<=25:raise ValueError('bounded prefix work')
        u['controller_actions']+=steps
        if task=='pusht':u['PushT_controller_actions']+=steps
        else:u['Reacher_dm_steps']+=p['events'][-1]['native_clocks']['step_count']-p['events'][0]['native_clocks']['step_count']
        for j in (0,1):
            b=json.loads((root/'evaluation'/(str(i)+'-'+str(j))/'BRANCH.json').read_text());steps=b['elapsed'];tails=b['tail_replans']
            if type(steps) is not int or not 0<=steps<=50 or tails!=int(steps>25):raise ValueError('bounded branch work')
            u['controller_actions']+=steps;u['native_CEM_decisions']+=tails
            if task=='pusht':u['PushT_controller_actions']+=steps
            else:u['Reacher_dm_steps']+=b['events'][-1]['native_clocks']['step_count']-b['events'][0]['native_clocks']['step_count']
    return u

def add(a,b):return {k:a[k]+b[k] for k in a}

def finalize(u):return dict(u,PushT_integrator_steps=10*u['PushT_controller_actions']+2*u['PushT_world_resets'])

def require(u):
    u=finalize(u)
    if any(u[k]>v or type(u[k]) is not int or u[k]<0 for k,v in CAPS.items()):raise ValueError('unchanged all-attempt physical-work cap')
    return u

def future_124(current):
    #124ordinary jobs:62PushT/62Reacher, at most16candidates,49freshworlds,
    #25oracle and50evaluation controller steps,32tail solves each.
    remaining={'world_resets':124*49,'controller_actions':124*2980,'Reacher_dm_steps':62*5960,
               'PushT_controller_actions':62*2980,'PushT_world_resets':62*49,'native_CEM_decisions':124*33}
    return require(add(current,remaining))

def before_grid(c):
    u=source_and_failed_helper()
    if set(c['rc1_grid']['technical_suppliers'])!={'0','1','2','3'}:raise ValueError('all4actual accepted settings first')
    for k,x in c['rc1_grid']['technical_suppliers'].items():u=add(u,parent(Path(x['run'])/'tasks'/('technical-'+k)/'output'))
    return {'scope':'failure-inclusive physical-resource counters only, not scientific outcomes','actual_sources_failed_helper_and_four_settings':require(u),
        'full_remaining_124_grid_reservation':future_124(u),'unchanged_caps':CAPS,'old_failed_helper_retained_and_counted':True,
        'initial_retained_bank_solve_charged_once_to_original_supplier':True,'efficacy_choices_outcomes_or_readout_quality_emitted':False}
