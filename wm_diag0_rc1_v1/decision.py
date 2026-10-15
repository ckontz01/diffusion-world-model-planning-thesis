"""Model-free full-coordinate and finite timing acceptance."""
import math
from wm_diag0_numerical_v3.metrics import check_metric

def timing(load,values):
    if len(values)!=36 or not all(math.isfinite(x) and x>=0 for x in [load]+values):raise ValueError('exact role timing samples')
    single=max(values)
    h=2*(load+352*single)+600;p=2*(load+166*single)+1800
    return {'load_seconds':load,'single_image_max_seconds':single,'samples':values,
            'head_work_estimate_seconds':h,'parent_work_estimate_seconds':p,
            'head_screen_passed':h<=1740,'parent_screen_passed':p<=3540}

def decision(report):
    if set(report['roles'])!={'pusht','reacher'}:raise ValueError('two tasks')
    role_ok=True;time_ok=True
    for task,r in report['roles'].items():
        if set(r['comparisons'])!={str(i)+'-'+p for i in (0,1) for p in ('1v5','1v8','5v8')} or set(r['repeats'])!={'1','5','8'}:
            raise ValueError('complete fixed role comparisons')
        for x in r['comparisons'].values():check_metric(x,(5,196,384));role_ok &= x['exact_bits']
        for key,x in r['repeats'].items():check_metric(x,(8 if key=='8' else 5,196,384));role_ok &= x['exact_bits']
        t=report['timing'][task];computed=timing(t['load_seconds'],t['samples'])
        if computed!=t:raise ValueError('frozen timing formula')
        time_ok &= t['head_screen_passed'] and t['parent_screen_passed']
    q=report['reference']
    check_metric(q['forecast'],(16,5,196,384))
    if type(q['source_binding_exact']) is not bool or type(q['goal_binding_exact']) is not bool or type(q['terminal_cost_identity_exact']) is not bool:
        raise ValueError('strict identity decisions')
    reference_ok=q['forecast']['within_original_tolerance'] and q['source_binding_exact'] and q['goal_binding_exact'] and q['terminal_cost_identity_exact']
    return {'role_exact_passed':bool(role_ok),'amended_reference_passed':bool(reference_ok),
            'timing_screen_passed':bool(time_ok),'all_RC1_checks_passed':bool(role_ok and reference_ok and time_ok)}
