"""Artificial supplier/ledger/inventory rejection tests; no research artifact read."""
import ast,json,tempfile
from pathlib import Path
from unittest.mock import patch
from .suppliers import chain,parent_location,retained_heads
from .ledger import OLD_ALLOCATED,OLD_UNALLOCATED,reconcile
from .inventory import plan,safe_name
from wm_diag0_rc1_grid_v1.common import ROOT,write_new,identity


def reject(fn):
    try:fn()
    except (ValueError,FileNotFoundError,KeyError):return
    raise AssertionError('required rejection missing')


def main():
    c={'run':'artificial-grid','recovery':{'old_run':'artificial-old','accepted_suppliers':{}},
       'rc1_technical':{'heads_run':'artificial-new','head_suppliers':{}},'rc1_grid':{'technical_suppliers':{}}}
    for i in range(4):
        c['recovery']['accepted_suppliers']['readout-'+str(i)]={'control':{},'output_seal':{}}
        c['rc1_grid']['technical_suppliers'][str(i)]={'run':'artificial-old' if i==0 else 'artificial-technical'}
        if i%2:c['rc1_technical']['head_suppliers'][str(i)]={'acceptance_identity':{},'output_seal':{}}
    heads=retained_heads(c)
    if len(heads)!=6 or [(r[0],r[5]) for r in heads if r[4]]!=[(0,False),(2,False),(1,True),(3,True)]:raise AssertionError('mixed active head supplier, not obsolete DINO')
    locations=[parent_location(c,s,i)[0].as_posix() for s in range(4) for i in range(32)]
    if len(set(locations))!=128 or 'artificial-old/tasks/technical-0' not in locations or 'artificial-grid/tasks/grid-123' not in locations:raise AssertionError('actual128 parent mapping')
    reject(lambda:parent_location(c,True,0));reject(lambda:parent_location(c,0,32))
    with tempfile.TemporaryDirectory(prefix='wm-rc1-final-artificial-') as tmp:
        base=Path(tmp);t=base/'parent';(t/'controls').mkdir(parents=True);(t/'output').mkdir()
        write_new(t/'output/MEMBERS.json',{});seal=identity(t/'output/MEMBERS.json')
        write_new(t/'controls/ACCEPTED.json',{'accepted':True,'output_seal':seal});control=identity(t/'controls/ACCEPTED.json')
        write_new(t/'controls/RESULT.json',{'status':'ACCEPTED','acceptance_identity':control})
        chain(t,control,seal);reject(lambda:chain(t,dict(control,bytes=1),seal))
        # Only synthetic files are mutated; no executed evidence is involved.
        (t/'controls/RESULT.json').write_text(json.dumps({'status':'ACCEPTED','acceptance_sha256':control['sha256']}))
        chain(t,control,seal)
        (t/'output/MEMBERS.json').write_text('{"changed":1}')
        reject(lambda:chain(t,control,seal))
        study=base/'study';(study/'old').mkdir(parents=True);(study/'new').mkdir()
        (study/'old/success').write_bytes(b'accepted');(study/'old/STOP.json').write_bytes(b'preserved old stop')
        (study/'new/failed.partial').write_bytes(b'partial')
        planned=plan(study,['old','new'],{},{} )
        if len(planned['members'])!=3 or planned['logical_payload_bytes_no_discounts']!=33:raise AssertionError('success/STOP/failure whole-root retention')
        reject(lambda:plan(study,['new'],{},{}))
        (study/'extra').mkdir();reject(lambda:plan(study,['old','new'],{},{}))
        for name in ('../x','x/../z','/abs','x\\y','x//z','x/./z','a:b','x'*513):reject(lambda:safe_name(name))
        with patch('wm_diag0_rc1_final_v1.inventory.MAX_PAYLOAD',1):reject(lambda:plan(study,['old','new','extra'],{},{}))
    technical={1:'317178',2:'317179',3:'317177'};grid={i:str(500000+i) for i in range(124)}
    lines=['|'.join([k,raw,state,exitcode,str(seconds),'4','gpu09']) for k,(raw,state,exitcode,seconds) in OLD_ALLOCATED.items()]
    lines+=['|'.join([k,k.split('_')[0],'CANCELLED by 1201','0:0','0','4','None assigned']) for k in sorted(OLD_UNALLOCATED)]
    lines+=['|'.join(['317177_'+str(i),technical[i],'COMPLETED','0:0','100','4','gpu09']) for i in (1,2,3)]
    lines+=['|'.join(['400000_'+str(i),grid[i],'COMPLETED','0:0','100','4','gpu09']) for i in range(124)]
    raw='\n'.join(lines);result=reconcile(raw,'400000',technical,grid)
    if result['allocated_attempts']!=138 or result['GPU_charged_seconds']!=13031:raise AssertionError('all failures charged and unallocated placeholders excluded')
    reject(lambda:reconcile('\n'.join(lines[1:]),'400000',technical,grid))
    reject(lambda:reconcile(raw+'\n'+lines[0],'400000',technical,grid))
    reject(lambda:reconcile(raw.replace('317171|FAILED|125:0|77','317171|COMPLETED|0:0|77'),'400000',technical,grid))
    reject(lambda:reconcile(raw.replace('400000_0|500000|COMPLETED','400000_0|500000|RUNNING'),'400000',technical,grid))
    reject(lambda:reconcile(raw.replace('400000_0|500000','400000_0|317178'),'400000',technical,grid))
    folder=ROOT/'wm_diag0_rc1_final_v1';source={}
    for p in folder.glob('*.py'):
        compile(p.read_bytes(),str(p),'exec');source[p.name]=identity(p)
    ast.parse((folder/'ledger.py').read_text(),feature_version=(3,6))
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v1-20261016';doc.mkdir(exist_ok=True)
    write_new(doc/'ARTIFICIAL-LOCAL-001.json',{'status':'PASSED','source':source,'checks':['six retained/four mixed active heads','128unique actual parent locations','original/new acceptance chains','mutated seal rejection','all138attempts including historical failure','cancelled unallocated placeholders retained','duplicate/missing/live/unexpected raw allocation rejection','unknown lineage/unsafe names/oversize inventory rejection','whole-root STOP/failure retention'],
        'research_artifacts_read':False,'model_or_simulator_calls':0,'source_generation_or_fitting':False,'analysis_or_final_archive_executed':False,
        'gate_ready':False,'remaining':'full scientific analysis assembly, actual all-lineage/runtime alias binding, archive creator/independent verifier, CPU supervisor/submission and native Windows final transfer'} )
    print(json.dumps({'status':'FINAL_SUPPLIER_LEDGER_INVENTORY_ARTIFICIAL_GUARDS_PASSED','research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
