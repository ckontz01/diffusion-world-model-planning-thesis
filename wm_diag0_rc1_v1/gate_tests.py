"""Artificial complete saved-output acceptance and rejection, CPU arrays only."""
import ast,json,tempfile
from pathlib import Path
import numpy as np
from wm_diag0_native_v3.store import save_array,seal
from wm_diag0_numerical_v3.metrics import compare
from wm_diag0.core import array_id
from .common import DOC,identity,write_new,EXPECTED_GATE_USAGE,CONTEXT,REPRESENTATION
from .decision import timing,decision
from .validate import validate

def fixture(root):
    old=root/'v3';old.mkdir();source=root/'supplier/controls';source.mkdir(parents=True)
    a=np.zeros((16,5,196,384),np.float32);goal=np.zeros((196,384),np.float32)
    prior={'bank_id':'a'*64,'candidate_ids':[str(i).zfill(64) for i in range(16)],'source_RGB_id':'b'*64,'goal_RGB_id':'c'*64,
        'source_cache':{'left_id':array_id(goal[None,None])},'goal_id':array_id(goal),'terminal_cost':{'left_id':array_id(np.zeros((1,16),np.float32))}}
    save_array(old/'predicted.npy',a);save_array(old/'goal.npy',goal);write_new(old/'VALIDATION.json',{'conditional':prior})
    old_seal=seal(old,26_000_000)
    seals={t+'-000':{'bytes':1,'sha256':'d'*64} for t in ('pusht','reacher')};write_new(source/'ALL-SOURCES-ACCEPTED.json',{'source_seals':seals})
    run=root/'run';(run/'source').mkdir(parents=True);out=run/'tasks/rc1-gate/output';out.mkdir(parents=True);controls=out.parent/'controls';controls.mkdir()
    # Production path convention, entirely artificial and unrelated to real runs.
    supplied=root/'v3-run/tasks/numerical-validation';supplied.mkdir(parents=True);old.rename(supplied/'output');old=supplied/'output'
    c={'source_run':str(source.parent),'rc1':{'V3_run':str(root/'v3-run'),'V3_output_seal':old_seal,'V3_report':identity(old/'VALIDATION.json')}}
    write_new(run/'source/RC1-CONTRACT.json',c);expected=identity(run/'source/RC1-CONTRACT.json')['sha256']
    small=np.zeros((5,196,384),np.float32)
    r={'roles':{},'timing':{},'source_seals':{t:seals[t+'-000'] for t in ('pusht','reacher')},'contract_sha256':expected,'representation':REPRESENTATION,
       'rtol':2**-6,'atol':2**-8,'tolerances_changed':False,'efficacy_inspected':False,'old_uncached_PushT':'FAILED','old_uncached_Reacher':'UNTESTED','campaign_resumed':False,
       'actual_usage':EXPECTED_GATE_USAGE.copy()}
    for t in ('pusht','reacher'):
        r['roles'][t]={'comparisons':{str(i)+'-'+p:compare(small,small) for i in (0,1) for p in ('1v5','1v8','5v8')},
            'repeats':{k:compare(np.zeros((8 if k=='8' else 5,196,384),np.float32),np.zeros((8 if k=='8' else 5,196,384),np.float32)) for k in ('1','5','8')},
            'input_ids':{str(i):'e'*64 for i in CONTEXT}}
        r['timing'][t]=timing(1,[.01]*36)
    q={k:prior[k] for k in ('bank_id','candidate_ids','source_RGB_id','goal_RGB_id','goal_id')}
    q.update(forecast=compare(a,a),production_forecast_supplier_id=array_id(a),source_cache_id=prior['source_cache']['left_id'],
        pointwise_goal_id=prior['goal_id'],terminal_cost_id=prior['terminal_cost']['left_id'],source_binding_exact=True,goal_binding_exact=True,
        terminal_cost_identity_exact=True,reference_boundary_calls=1,reused_not_newly_computed=True,CEM_repeated=False)
    r['reference']=q;r.update(decision(r));r['status']='RC1_GATE_PASSED_PENDING_PRO'
    return run,out,controls,expected,r,a

def main():
    for defect in ('none','forecast_bytes','extra_file','missing_role','workload','goal_binding','timing'):
        with tempfile.TemporaryDirectory(prefix='wm-rc1-artificial-') as tmp:
            run,out,controls,expected,r,a=fixture(Path(tmp))
            if defect=='forecast_bytes':a[0,0,0,0]=1
            if defect=='extra_file':write_new(out/'unexpected.json',{})
            if defect=='missing_role':del r['roles']['pusht']['comparisons']['0-1v5']
            if defect=='workload':r['actual_usage']['predictor_calls']+=1
            if defect=='goal_binding':r['reference']['pointwise_goal_id']='f'*64
            if defect=='timing':r['timing']['pusht']['samples'][0]=float(100)
            save_array(out/'reference.npy',a);write_new(out/'RC1-GATE.json',r);write_new(controls/'OUTPUT-SEAL.json',seal(out,26_000_000))
            try:result=validate(run,expected)
            except (ValueError,KeyError):
                if defect=='none':raise
            else:
                if defect!='none' or not result['all_RC1_checks_passed']:raise AssertionError('rejection/pass fixture')
    for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_bytes())
    ast.parse(Path(__file__).with_name('supervisor.py').read_bytes(),feature_version=(3,6))
    row={'status':'NEW_ARTIFICIAL_COMPLETE_GATE_VALIDATOR_AND_REJECTION_TESTS_PASSED','fixtures':7,'research_model_calls':0,'research_inputs':0,
        'independent_saved_full_comparison_exercised':True,'old56tests_repeated':False}
    write_new(DOC/'ARTIFICIAL-GATE-001.json',row);print(json.dumps(row))

if __name__=='__main__':main()
