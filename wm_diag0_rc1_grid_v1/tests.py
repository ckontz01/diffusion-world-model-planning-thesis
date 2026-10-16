import ast,json,tempfile
from pathlib import Path
from .common import ROOT,DOC,setting,bounds,check_usage,gates,identity,write_new

def reject(fn):
    try:fn()
    except (ValueError,FileNotFoundError):return
    raise AssertionError('rejection missing')

def main():
    if len({setting(i) for i in range(124)})!=124 or {setting(i)[1] for i in range(124)}!=set(range(1,32)):raise AssertionError('fixed grid mapping')
    for i in (-1,124,True):reject(lambda:setting(i))
    for i in (0,31,62,93,123):
        cap=bounds(i);check_usage(i,dict(cap))
        for k in cap:reject(lambda:check_usage(i,dict(cap,**{k:cap[k]+1})))
        reject(lambda:check_usage(i,dict(cap,extra=0)))
    with tempfile.TemporaryDirectory(prefix='wm-rc1-grid-gates-') as tmp:
        suppliers={}
        for i in range(4):
            r=Path(tmp)/str(i);t=r/'tasks'/('technical-'+str(i));(t/'controls').mkdir(parents=True);(t/'output').mkdir()
            write_new(t/'output/MEMBERS.json',{});seal=identity(t/'output/MEMBERS.json')
            write_new(t/'controls/ACCEPTED.json',{'accepted':True,'output_seal':seal});a=identity(t/'controls/ACCEPTED.json')
            write_new(t/'controls/RESULT.json',{'status':'ACCEPTED',**({'acceptance_sha256':a['sha256']} if i==0 else {'acceptance_identity':a})})
            suppliers[str(i)]={'run':str(r),'acceptance_identity':a,'output_seal':seal}
        c={'rc1_grid':{'technical_suppliers':suppliers}};gates(c)
        reject(lambda:gates({'rc1_grid':{'technical_suppliers':{k:v for k,v in suppliers.items() if k!='3'}}}))
        path=Path(suppliers['2']['run'])/'tasks/technical-2/controls/ACCEPTED.json'
        # Artificial fixture mutation only: no executed source/data are involved.
        path.write_text('{"accepted":false}')
        reject(lambda:gates(c))
    from .resources import source_and_failed_helper,future_124,parent
    maximum_four={'world_resets':326,'controller_actions':17424,'Reacher_dm_steps':17448,'PushT_controller_actions':8700,'PushT_world_resets':163,'native_CEM_decisions':132}
    reject(lambda:future_124(maximum_four))
    within=dict(maximum_four,controller_actions=17384,PushT_controller_actions=8660)
    if future_124(within)['world_resets']!=6402 or source_and_failed_helper()['controller_actions']!=5344:raise AssertionError('old failed helper included once, full remaining work reserved')
    with tempfile.TemporaryDirectory(prefix='wm-rc1-physical-fixture-') as tmp:
        r=Path(tmp);write_new(r/'SELECTION.json',{'candidate_ids':['artificial'],'root':{'task':'reacher'},'technical':True})
        (r/'oracle/0').mkdir(parents=True)
        write_new(r/'oracle/0/PREFIX.json',{'actions':10,'events':[{'native_clocks':{'step_count':40}},{'native_clocks':{'step_count':60}}]})
        for j,n in enumerate((30,50)):
            d=r/'evaluation'/('0-'+str(j));d.mkdir(parents=True)
            write_new(d/'BRANCH.json',{'elapsed':n,'tail_replans':1,'events':[{'native_clocks':{'step_count':40}},{'native_clocks':{'step_count':40+2*n}}]})
        got=parent(r)
        if got!={'world_resets':6,'controller_actions':210,'Reacher_dm_steps':420,'PushT_controller_actions':0,'PushT_world_resets':0,'native_CEM_decisions':3}:raise AssertionError('independent metadata-only physical arithmetic')
    from .operations import STAGE,OBSERVE
    import contextlib,io
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='wm-rc1-observer-fixture-') as tmp:
        r=Path(tmp);(r/'controls').mkdir();(r/'source').mkdir();t=r/'tasks/grid-0';(t/'controls').mkdir(parents=True);(t/'output').mkdir()
        write_new(r/'controls/DISPATCH.json',{'array_job_id':'1'});write_new(r/'source/GRID-CONTRACT.json',{'rc1_grid':{'GPU_charged_before':0,'full_future_GPU_seconds':0}})
        write_new(t/'output/MEMBERS.json',{});write_new(t/'controls/ACCEPTED.json',{'output_seal':identity(t/'output/MEMBERS.json')})
        output=io.StringIO()
        with patch('subprocess.check_output',return_value=''),contextlib.redirect_stdout(output):exec(compile(OBSERVE,'artificial-observer','exec'),{'RUN':str(r)})
        row=json.loads(output.getvalue())
        if row['accepted_grid_parents']!=0 or not row['tasks']['0']['acceptance_finalization_pending']:raise AssertionError('ACCEPTED-before-RESULT race must not appear a failure')
    ast.parse('RUN="r"\nEXPECTED="e"\n'+STAGE,feature_version=(3,6));ast.parse('RUN="r"\n'+OBSERVE,feature_version=(3,6))
    ast.parse((ROOT/'wm_diag0_rc1_grid_v1/supervisor.py').read_text(),feature_version=(3,6))
    sources={}
    for p in (ROOT/'wm_diag0_rc1_grid_v1').glob('*.py'):compile(p.read_bytes(),str(p),'exec');sources[p.name]=identity(p)
    if 'from wm_diag0_campaign_v4.diagnostic import run' not in (ROOT/'wm_diag0_rc1_grid_v1/worker.py').read_text():raise AssertionError('same original science implementation')
    write_new(DOC/'ARTIFICIAL-LOCAL-002.json',{'status':'PASSED','source':sources,'model_calls':0,'source_or_labels_generated':False,'checks':['124unique mapping','module/frame/API overruns','all four gate chains','missing gate','changed accepted control','failed-helper inclusive physical reserve overrun rejection','actual physical metadata arithmetic','ACCEPTED-before-RESULT observer race','Python3.6 controller/transport syntax'],
        'original56tests_repeated':False,'actual_grid_execution_or_full_study_acceptance_claimed':False})
    print(json.dumps({'status':'RC1_FIXED_GRID_ARTIFICIAL_CONTRACT_GUARDS_PASSED','research_calls':0}))

if __name__=='__main__':main()
