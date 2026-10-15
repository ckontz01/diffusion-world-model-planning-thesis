"""Artificial arithmetic fixtures only; not a timing measurement."""
import json, math
from .inventory import DOC
from wm_diag0_native_v3.common import identity,write_new

def screen(load, single):
    if not all(math.isfinite(x) and x>=0 for x in (load,single)):
        raise ValueError('finite nonnegative measurement')
    return {'head':2*(load+352*single)+600<=1740,
            'parent':2*(load+166*single)+1800<=3540}

def main():
    assert screen(5,1)=={'head':True,'parent':True}
    assert screen(5,10)=={'head':False,'parent':False}
    assert screen(570,0)['head'] and not screen(570.001,0)['head']
    assert screen(870,0)['parent'] and not screen(870.001,0)['parent']
    for load,single in ((float('nan'),1),(1,float('inf')),(-1,1)):
        try: screen(load,single)
        except ValueError: pass
        else: raise AssertionError('invalid timing accepted')
    row={'status':'ARTIFICIAL_TIMING_FORMULA_FIXTURES_PASSED_NOT_REAL_TIMING',
      'clarification':identity(DOC/'TIMING-CLARIFICATION-20261016.md'),
      'head_nonencoding_work_reserve_seconds':600,'parent_nonencoding_work_reserve_seconds':1800,
      'independent_validation_seconds':55,'finalization_seconds':5,
      'real_model_calls':0,'RC1_timing_passed':False,'campaign_resumed':False}
    write_new(DOC/'TIMING-FORMULA-CHECK-001.json',row);print(json.dumps(row))

if __name__=='__main__':main()
