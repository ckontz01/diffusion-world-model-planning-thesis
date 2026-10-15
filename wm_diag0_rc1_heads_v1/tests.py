"""New route/dispatch regression fixtures only; no models, old suite or fitting."""
import ast,json
from dataclasses import replace
from wm_diag0.core import FeatureContract,digest
from .route import amend,require
from .common import ROOT,DOC,REPRESENTATION,USAGE,write_new,identity

def main():
    x=FeatureContract('dinowm_noprop','a'*64,'b'*64,(196,384),(5,10,15,20,25),1,'terminal_mse')
    y=amend(x);require(y,y)
    if x==y or y.preprocessing_sha256!=digest({'original_preprocessing_sha256':x.preprocessing_sha256,'representation':REPRESENTATION,'image_batch':1,'T':1,'concatenate_after_extraction':True}):raise AssertionError('exact shared pointwise mapping')
    rejected=[]
    for name,bad in [('old_head',x),('wrong_weights',replace(y,checkpoint_sha256='c'*64)),('wrong_layout',replace(y,feature_shape=(384,196))),('wrong_time',replace(y,history_length=3)),('wrong_preprocess',replace(y,preprocessing_sha256='d'*64))]:
        try:require(bad,y)
        except ValueError:rejected.append(name)
        else:raise AssertionError('route rejection '+name)
    members={}
    for p in sorted((ROOT/'wm_diag0_rc1_heads_v1').glob('*.py')):
        compile(p.read_bytes(),str(p),'exec');members[p.name]=identity(p)
    ast.parse((ROOT/'wm_diag0_rc1_heads_v1/supervisor.py').read_text(),feature_version=(3,6))
    text=(ROOT/'wm_diag0_rc1_heads_v1/worker.py').read_text()
    if 'from wm_diag0_campaign_v4.readout import fit' not in text or USAGE['encoded_frames']!=256+96:raise AssertionError('unchanged fit implementation/counters')
    write_new(DOC/'ARTIFICIAL-ROUTE-001.json',{'status':'PASSED','rejected':rejected,'source':members,'original_recipe_imported_unchanged':True,'model_calls':0,'fit_tasks':0,'old_56_suite_repeated':False,
        'limitations':['route/dispatch source-interface fixtures do not validate new real fitted parameters; allocated independent equation validation remains required']})
    print(json.dumps({'status':'RC1_HEAD_ARTIFICIAL_ROUTE_PASSED','rejected':rejected,'research_calls':0}))

if __name__=='__main__':main()
