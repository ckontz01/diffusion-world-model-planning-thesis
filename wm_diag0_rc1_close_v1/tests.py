"""New recovery-finalization fixtures only; never open a scientific study file."""
import ast,copy,json,tempfile,time
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .binding import program,layout
from .usage import total
from . import analysis_validate as validator,analysis_closure as closure
from wm_diag0_rc1_grid_v1.common import SETTINGS,bounds
from wm_diag0_rc1_technical_v1.common import bounds as technical
from wm_diag0_rc1_final_v2 import inventory_v3,root_binding_v1
from wm_diag0_rc1_final_v2.archive_v2 import canonical

def reject(fn):
    try:fn()
    except (ValueError,PermissionError,FileNotFoundError):return
    raise AssertionError('required refusal absent')

def main():
    parents=[]
    for s,(task,backbone) in enumerate(SETTINGS):
        for i in range(32):
            proof={'accepted':True,'setting':s,'root_index':i,'root_id':'new-artificial:'+task+':'+str(i),
                'task':task,'backbone':backbone,'candidate_count':16,'technical':i==0}
            actual=technical(s) if i==0 and s else dict(visual_encoder_calls=2002,encoded_frames=2066,proprio_encoder_calls=0,action_encoder_calls=5958,predictor_calls=4965,cost_api_calls=993) if i==0 else bounds(s*31+i-1)
            usage={k:actual[k] for k in ('encoded_frames','predictor_calls','cost_api_calls')}
            worlds=51 if i==0 else 49;steps=3020 if i==0 else 2980
            if s==0 and i==0:steps-=40
            physical={'world_resets':worlds,'controller_actions':steps,'Reacher_dm_steps':2*steps if task=='reacher' else 0,
                'PushT_controller_actions':steps if task=='pusht' else 0,'PushT_world_resets':worlds if task=='pusht' else 0,'native_CEM_decisions':33}
            parents.append((proof,Path('never-opened-artificial'),usage,physical,None if s==0 and i==0 else actual))
    heads=[{'accepted':True,'active':i in (0,2,4,5),'fit_frames':256,'validation_frames':96} for i in range(6)]
    result=total(parents,heads,10);values=result['all_attempt_counts']
    expected={'DINO_predictor_calls':950760,'LeWM_predictor_calls':322095,'forecast_cost_API_operations':127851,
        'encoded_frames':145841,'native_CEM_decisions':4257,'CEM_sequences':38313000,'bank_reforecast_sequences':2080,
        'predicted_macro_sequence_transitions':191576280}
    for key,n in expected.items():
        if values[key]!=n:raise AssertionError('explicit failed-parent plus accepted usage '+key)
    reject(lambda:total(parents[:-1],heads,10));reject(lambda:total(parents,heads[:-1],10))
    bad=copy.deepcopy(parents);bad[32][4]['predictor_calls']+=1;bad[32][2]['predictor_calls']+=1
    reject(lambda:total(bad,heads,10))
    if closure.COUNTS['allocation_attempts']!=139 or closure.VALIDATOR!='wm_diag0_rc1_close_v1/analysis_validate.py':raise AssertionError('139-source proof closure')
    validator.compare_payloads({'all_attempt_usage':result},{'attempts':139},{'all_attempt_usage':copy.deepcopy(result)},{'attempts':139})
    reject(lambda:validator.compare_payloads({'attempts':138},{},{'attempts':139},{}))
    reject(lambda:validator.compare_payloads({'attempts':True},{},{'attempts':139},{}))
    value=layout()['layout']
    if len(value['approved_children_before_final'])!=21 or len(value['approved_children_with_final'])!=22:raise AssertionError('retain recovery and its artificial root')
    # Exercise the exact inventory_v3/root_binding implementation with NEW tiny
    # ordinary fixtures. The deliberately non-JSON payload is opaque throughout.
    with tempfile.TemporaryDirectory(prefix='wm-new-final-binding-') as tmp:
        base=Path(tmp);(base/'study').mkdir();(base/'study/old').mkdir()
        p=base/'study/old/old-STOP-and-failure.bin';p.write_bytes(b'NOT JSON\x00retained-failure')
        planned=inventory_v3.plan(base/'study',['old'],{},{});paths={'study/old':str(base/'study/old')}
        proof=root_binding_v1.authenticate(planned,paths,'a'*64,time.monotonic()+5)
        if proof['logical_regular_bytes_no_discounts']!=len(p.read_bytes()):raise AssertionError('opaque every-byte binding')
        p.write_bytes(b'mutated')
        reject(lambda:root_binding_v1.compare(root_binding_v1.authenticate(inventory_v3.plan(base/'study',['old'],{},{}),paths,'a'*64,time.monotonic()+5),proof))
    text=program();ast.parse(text,feature_version=(3,6))
    source={}
    for p in (ROOT/'wm_diag0_rc1_close_v1').glob('*.py'):
        ast.parse(p.read_text(),feature_version=(3,6));source[p.name]=identity(p)
    receipt={'status':'NEW_RECOVERY_AWARE_FINAL_SOURCES_AND_OPAQUE_BINDING_FIXTURES_PASSED','source':source,
        'synthetic_complete_parents':128,'synthetic_all_attempt_maxima':expected,'checks':['failed parent charged full maxima','original fixed counters preserved',
        'missing-parent/head/counter-overrun/bool/138-proof rejected','all21 retained roots plus futurefinal','real nofollow opaque root binding and mutation rejection','actual remote program AST3.6'],
        'scientific_study_payload_reads':False,'WSL_SSH_scheduler_calls':0,'actual_final_analysis_run':False,'final_gate_ready':False}
    write_new(DOC/'ARTIFICIAL-CLOSE-001.json',receipt)
    print(json.dumps({'status':receipt['status'],'real_study_reads':False,'final_gate_ready':False}))

if __name__=='__main__':main()
