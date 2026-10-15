"""Model-independent full-coordinate checks. No scalar-cost equivalence claim."""
import numpy as np
from wm_diag0.core import array_id

def compare(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.dtype != np.float32 or b.dtype != np.float32 or a.shape != b.shape:
        raise ValueError('exact F32 layout')
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('finite full tensors')
    delta = np.abs(a-b)
    limit = np.float32(2**-8) + np.float32(2**-6)*np.abs(b)
    return dict(shape=list(a.shape), elements=a.size, left_id=array_id(a), right_id=array_id(b),
        exact_bits=array_id(a)==array_id(b), within_original_tolerance=bool(np.all(delta<=limit)),
        mismatched_elements=int(np.count_nonzero(delta>limit)), max_absolute_difference=float(delta.max()))

def check_metric(row, shape):
    if set(row) != {'shape','elements','left_id','right_id','exact_bits','within_original_tolerance','mismatched_elements','max_absolute_difference'}:
        raise ValueError('exact metric schema')
    if row['shape'] != list(shape) or row['elements'] != int(np.prod(shape)):
        raise ValueError('full coordinate comparison')
    for k in ('left_id','right_id'):
        if len(row[k])!=64 or any(x not in '0123456789abcdef' for x in row[k]):raise ValueError('tensor identity')
    n=row['mismatched_elements']; d=row['max_absolute_difference']
    if type(n) is not int or not 0<=n<=row['elements'] or not np.isfinite(d) or d<0:raise ValueError('metric bound')
    if type(row['exact_bits']) is not bool or type(row['within_original_tolerance']) is not bool:raise ValueError('boolean metric')
    if row['exact_bits'] != (row['left_id']==row['right_id']) or row['within_original_tolerance'] != (n==0):raise ValueError('metric consistency')
    if row['exact_bits'] and d!=0:raise ValueError('exact disagreement')

def decision(report):
    """Independent schema/decision check, not a second model forward."""
    role_ok=True
    if set(report['roles']) != {'pusht','reacher'}:raise ValueError('two fixed tasks')
    for task,r in report['roles'].items():
        if set(r['comparisons']) != {str(i)+'-'+p for i in (0,1) for p in ('1v5','1v8','5v8')}:
            raise ValueError('all fixed pair comparisons')
        if set(r['repeats']) != {'1','5','8'}:raise ValueError('all exact same-route repeats')
        for x in r['comparisons'].values():
            check_metric(x,(5,196,384));role_ok &= x['within_original_tolerance']
        for route,x in r['repeats'].items():
            check_metric(x,(8 if route=='8' else 5,196,384));role_ok &= x['exact_bits']
    q=report['conditional']
    for key,shape in [('source_cache',(1,1,196,384)),('goal',(196,384)),('forecast',(16,5,196,384)),
                      ('cached_cost',(16,)),('terminal_cost',(1,16))]:check_metric(q[key],shape)
    conditional_ok=(q['source_cache']['exact_bits'] and q['goal']['exact_bits'] and q['cached_cost']['exact_bits']
                    and q['forecast']['within_original_tolerance'] and q['terminal_cost']['within_original_tolerance'])
    return {'role_compatibility_passed':bool(role_ok),'conditional_recurrence_passed':bool(conditional_ok),
            'all_numerical_checks_passed':bool(role_ok and conditional_ok)}
