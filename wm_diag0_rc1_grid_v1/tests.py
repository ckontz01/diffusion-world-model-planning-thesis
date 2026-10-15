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
    from .operations import STAGE,OBSERVE
    ast.parse('RUN="r"\nEXPECTED="e"\n'+STAGE,feature_version=(3,6));ast.parse('RUN="r"\n'+OBSERVE,feature_version=(3,6))
    ast.parse((ROOT/'wm_diag0_rc1_grid_v1/supervisor.py').read_text(),feature_version=(3,6))
    sources={}
    for p in (ROOT/'wm_diag0_rc1_grid_v1').glob('*.py'):compile(p.read_bytes(),str(p),'exec');sources[p.name]=identity(p)
    if 'from wm_diag0_campaign_v4.diagnostic import run' not in (ROOT/'wm_diag0_rc1_grid_v1/worker.py').read_text():raise AssertionError('same original science implementation')
    write_new(DOC/'ARTIFICIAL-LOCAL-001.json',{'status':'PASSED','source':sources,'model_calls':0,'source_or_labels_generated':False,'checks':['124unique mapping','module/frame/API overruns','all four gate chains','missing gate','changed accepted control','Python3.6 controller/transport syntax'],
        'original56tests_repeated':False,'actual_grid_execution_or_full_study_acceptance_claimed':False})
    print(json.dumps({'status':'RC1_FIXED_GRID_ARTIFICIAL_CONTRACT_GUARDS_PASSED','research_calls':0}))

if __name__=='__main__':main()
