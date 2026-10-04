"""Artificial-only pre-evaluation selection bundle and authenticated outcome gate.

Not a production launcher: native origin/model/phase rights remain unbound.
The outcome loader is called ONLY after the externally retained seal verifies.
"""
import json
from pathlib import Path
import numpy as np
from .core import array_id, digest, select_four, Bank, Candidate, FeatureContract, Features, native_terminal_score
from .readout import Ridge
from .saved import sha

def seal_artificial(path, bank, predicted, realized, goal, s0, readout, *,
                    oracle_prefix_id, oracle_draw, evaluation_draws, domain):
    if domain!='artificial':raise PermissionError('Research phase collection disabled')
    if not oracle_prefix_id or oracle_draw in evaluation_draws or len(set(evaluation_draws))!=2:
        raise ValueError('Separate oracle prefix and two independent evaluation draws')
    selection=select_four(bank,predicted,realized,goal,s0,readout)
    costs=np.stack([f(x,goal) for x,f in ((predicted,s0),(predicted,readout),(realized,s0),(realized,readout))])
    if tuple(array_id(c) for c in costs)!=selection.cost_ids:raise ValueError('Unstable score callable')
    arrays={'predicted':predicted.values,'realized':realized.values,'goal':goal,'costs':costs,
            'readout_mean':readout.mean,'readout_scale':readout.scale,
            'readout_weights':readout.weights,'readout_intercept':readout.intercept}
    arrays.update({f'action-{i}':c.actions for i,c in enumerate(bank.candidates)})
    path=Path(path);path.mkdir(exist_ok=False);members={}
    for name,value in arrays.items():
        with (path/(name+'.npy')).open('xb') as f:np.save(f,value,allow_pickle=False)
        members[name+'.npy']=sha(path/(name+'.npy'))
    body={'domain':domain,'phase':'SELECTION_BEFORE_EVALUATION','selection':selection.__dict__,
          'selection_id':selection.identity,'bank_id':bank.identity,'source_id':predicted.source_id,
          'contract':predicted.contract.__dict__,'candidate_ids':[c.identity for c in bank.candidates],
          'candidate_count':len(bank.candidates),'native_index':bank.native_index,'trace_digest':bank.trace_digest,
          'readout_id':readout.identity,'readout_task':readout.task,'fit_parents':readout.fit_parent_ids,
          'oracle_prefix_id':oracle_prefix_id,'oracle_draw':oracle_draw,
          'evaluation_draws':list(evaluation_draws),'members':members}
    with (path/'selection.json').open('x',encoding='utf8') as f:json.dump(body,f,sort_keys=True,allow_nan=False)
    return sha(path/'selection.json')

def authenticate_selection(path, expected_seal):
    path=Path(path)
    if sha(path/'selection.json')!=expected_seal:raise ValueError('Selection seal changed')
    body=json.loads((path/'selection.json').read_text())
    if body['domain']!='artificial':raise PermissionError('Research phase reading disabled')
    if body['phase']!='SELECTION_BEFORE_EVALUATION':raise ValueError('Wrong phase')
    members=body['members'];n=body['candidate_count']
    expected={'predicted.npy','realized.npy','goal.npy','costs.npy','readout_mean.npy',
              'readout_scale.npy','readout_weights.npy','readout_intercept.npy'}|{f'action-{i}.npy' for i in range(n)}
    if not 1<=n<=16 or set(members)!=expected:raise ValueError('Candidate membership')
    for name,identity in members.items():
        if sha(path/name)!=identity:raise ValueError('Phase member changed before outcome join')
    arrays={name:np.load(path/name,allow_pickle=False) for name in members}
    for i in range(n):
        if array_id(arrays[f'action-{i}.npy'])!=body['candidate_ids'][i]:raise ValueError('Action identity')
    if len(set(body['candidate_ids']))!=n:raise ValueError('Exact duplicate bank slots')
    s=body['selection'];costs=arrays['costs.npy']
    if costs.shape!=(4,n) or not np.isfinite(costs).all():raise ValueError('Four score arrays')
    if list(np.argmin(costs,axis=1))!=s['choices'] or [array_id(c) for c in costs]!=s['cost_ids']:
        raise ValueError('Lowest-valid-slot selection')
    if digest(s)!=body['selection_id'] or s['bank_id']!=body['bank_id'] or s['source_id']!=body['source_id']:
        raise ValueError('Source/bank selection binding')
    if s['s1_id']!=body['readout_id'] or array_id(arrays['goal.npy'])!=s['goal_id']:
        raise ValueError('Goal/readout binding')
    fields=dict(body['contract']);fields['feature_shape']=tuple(fields['feature_shape']);fields['positions']=tuple(fields['positions'])
    contract=FeatureContract(**fields)
    bank=Bank(tuple(Candidate(arrays[f'action-{i}.npy'],'saved',None) for i in range(n)),
              body['native_index'],body['trace_digest'])
    if bank.identity!=body['bank_id'] or contract.identity!=s['contract_id']:raise ValueError('Native bank/contract seal')
    readout=Ridge(contract,body['readout_task'],arrays['readout_mean.npy'],arrays['readout_scale.npy'],
                  arrays['readout_weights.npy'],arrays['readout_intercept.npy'],tuple(body['fit_parents']))
    predicted=Features(arrays['predicted.npy'],contract,bank.identity,body['source_id'],'predicted')
    realized=Features(arrays['realized.npy'],contract,bank.identity,body['source_id'],'realized')
    rebuilt=select_four(bank,predicted,realized,arrays['goal.npy'],native_terminal_score,readout)
    if rebuilt.identity!=body['selection_id']:raise ValueError('Independent four-score/readout reconstruction')
    if body['oracle_draw'] in body['evaluation_draws'] or len(set(body['evaluation_draws']))!=2:
        raise ValueError('Independent phase draws')
    return body

def join_artificial_outcomes(path, expected_seal, outcome_loader):
    body=authenticate_selection(path,expected_seal)
    # No outcome path is opened, or loader invoked, until authentication passes.
    outcomes=outcome_loader()
    if outcomes['source_id']!=body['source_id'] or outcomes['bank_id']!=body['bank_id']:
        raise ValueError('Evaluation source/bank mismatch')
    if list(outcomes['draws'])!=body['evaluation_draws']:raise ValueError('Evaluation draw ownership')
    values=np.asarray(outcomes['success'])
    if values.shape!=(body['candidate_count'],2) or not np.isin(values,[0,1]).all():
        raise ValueError('Valid candidate outcomes only')
    return body,values
