"""Frozen stage reductions: discrimination first, calibration supplementary."""
from pathlib import Path
import numpy as np
import candidate_value_learning as c
import candidate_value_contract as ct
from candidate_value_data import validated_banks,write_npz,read_npz
from candidate_value_models import Predictor


def hierarchical(rows,key):
    refs=sorted({r['reference'] for r in rows});out=[]
    for ref in refs:
        hs=[]
        for h in (75,150):
            values=[r[key] for r in rows if r['reference']==ref and r['horizon']==h and r[key] is not None]
            if values:hs.append(float(np.mean(values)))
        if hs:out.append(dict(reference=ref,value=float(np.mean(hs))))
    return out


def validation(run,out,source_sha,capsule_sha):
    predictor=Predictor(run,source_sha,capsule_sha);rows=[];bins=[]
    constant=predictor.report['constant_probability']
    for ref,h,t,bank,ids,y in validated_banks(run,'validation',source_sha,capsule_sha):
        row=dict(reference=ref,horizon=h,anchor=t)
        for arm in ('value','linear','context'):
            p=predictor(arm,bank['x'][ids])
            if arm=='context':ct.require(np.all(p==p[0]),'Context-only predicts candidate variation')
            m=c.bank_metrics(p,y,continuation_index=ids.index(int(bank['continuation_index'])),
                           immediate_index=ids.index(int(bank['immediate_index'])),original_indices=ids)
            row[arm]=m
            if arm=='value':
                row['effect']=m['selected_empirical_success']-m['continuation_success']
                row['concordance']=m['pairwise_concordance'];row['informative_pairs']=m['informative_pairs']
                row['brier_difference']=m['brier']-float(((constant-y)**2).mean())
                for k,(pp,yy) in enumerate(zip(p,y)):
                    bins.append(dict(reference=ref,horizon=h,anchor=t,candidate=ids[k],
                                     bin=min(int(pp*5),4),probability=float(pp),success=float(yy.mean())))
        row['observed_success_values']=np.unique(y.mean(1)).tolist()
        row['candidate_success_variance']=float(np.var(y.mean(1)))
        row['context_selection_effect']=row['value']['selected_empirical_success']-row['context']['selected_empirical_success']
        row['linear_selection_effect']=row['value']['selected_empirical_success']-row['linear']['selected_empirical_success']
        rows.append(row)
    effects=hierarchical(rows,'effect');disc=hierarchical(rows,'concordance')
    info_refs={r['reference'] for r in rows if r['informative_pairs']>0}
    mean_effect=float(np.mean([r['value'] for r in effects]))
    concordance=float(np.mean([r['value'] for r in disc])) if disc else None
    # Promise != a technical pass, and a pooled calibration improvement cannot pass.
    promise=len(info_refs)>=10 and mean_effect>0 and concordance is not None and concordance>.5
    ct.json_write(Path(out)/'BANK-ROWS.json',rows);ct.json_write(Path(out)/'CALIBRATION-ROWS.json',bins)
    return dict(advance=bool(promise),decision='advance_closed_loop' if promise else 'stop_no_ranking_promise',
                technical_validity=True,scientific_promise=bool(promise),
                references=32,available_banks=len(rows),informative_references=len(info_refs),
                mean_informative_concordance=concordance,primary=c.reference_interval([r['value'] for r in effects]),
                reference_effects=effects,calibration_supplementary=True,
                no_unlabelled_candidate_outcomes_inferred=True,
                context_mean_selection_effect=float(np.mean([r['value'] for r in hierarchical(rows,'context_selection_effect')])),
                brier_difference=float(np.mean([r['value'] for r in hierarchical(rows,'brier_difference')])))


def closed(backend,record_for,reference,out,predictor):
    rows=[];steps=0
    for h in (75,150):
        record,environment_seed=record_for(h)
        for draw in (0,1):
            planner_seed=c.seed('closed-loop',reference,h,draw)
            for arm in ct.ARMS:
                result=backend.episode(record,h,planner_seed,environment_seed,arm=arm,predict=predictor)
                trace=result['trace'];file='h%d-d%d-%s.npz'%(h,draw,arm)
                write_npz(Path(out)/file,**trace)
                ct.json_write(Path(out)/(file+'.calls.json'),result['calls'])
                success=c.success_target(trace['flags'][:,0],trace['flags'][:,1],remaining=2*h)
                rows.append(dict(reference=reference,horizon=h,draw=draw,arm=arm,planner_seed=planner_seed,
                                 target=success,trace_file=file,score_seconds=result['score_seconds']))
                steps+=len(trace['actions'])
    backend.assert_frozen()
    return dict(reference=reference,rows=rows,primitive_steps=steps,provenance=backend.provenance)


def final_report(run,out,source_sha,capsule_sha):
    gate=ct.check_report(Path(run)/'validate-0','validate',0,source_sha,capsule_sha)
    ct.require(gate['advance'] is True,'Closed-loop advancement gate')
    reports=[ct.check_report(Path(run)/('closed-%d'%i),'closed',i,source_sha,capsule_sha) for i in range(32)]
    rows=[]
    for i,r in enumerate(reports):
        ref=ct.allocation()['closed_loop'][i]
        expected={(h,d,a) for h in (75,150) for d in (0,1) for a in ct.ARMS}
        ct.require(r['reference']==ref and len(r['rows'])==16 and
                   {(x['horizon'],x['draw'],x['arm']) for x in r['rows']}==expected,'Closed execution grid')
        for row in r['rows']:
            tr=read_npz(ct.child(Path(run)/('closed-%d'%i),row['trace_file']))
            ct.require(row['target']==c.success_target(tr['flags'][:,0],tr['flags'][:,1],remaining=2*row['horizon']),
                       'Closed label identity')
        values={a:float(np.mean([x['target']['success'] for x in r['rows'] if x['arm']==a])) for a in ct.ARMS}
        rows.append(dict(reference=ref,success=values,effect=values['value']-values['continuation']))
    ct.json_write(Path(out)/'REFERENCE-EFFECTS.json',rows)
    return dict(decision='completed_development_only',episodes=512,references=32,
                primary=c.reference_interval([r['effect'] for r in rows]),
                means={a:float(np.mean([r['success'][a] for r in rows])) for a in ct.ARMS},
                no_confirmation_or_gmm_authorization=True)
