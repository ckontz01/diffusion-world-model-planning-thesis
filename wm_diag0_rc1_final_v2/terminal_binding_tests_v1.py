"""New127-control/138-ledger synthetic regression, never real study reads."""
import ast,copy,hashlib,json,tempfile,time
from pathlib import Path
from . import terminal_binding_v1 as t
from .cpu_entry_guard_v1 import source_closure,check_frozen_extension
from .evidence_auth_v1 import bound_json
from .cpu_schedule_v2 import CPU_V2
from wm_diag0_rc1_final_v1.ledger import OLD_ALLOCATED,OLD_UNALLOCATED,reconcile
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except (ValueError,PermissionError,TimeoutError,FileNotFoundError):return
    raise AssertionError('required terminal/source/entry guard rejection absent')


def fixture():
    c={'run':t.RUN,'rc1_grid':{'technical_run':t.TECH,'technical_contract':t.TECH_CONTRACT}}
    raw={str(i):str(400000+i) for i in range(124)};lines=[]
    for logical,(actual,state,code,seconds) in sorted(OLD_ALLOCATED.items()):lines.append('|'.join((logical,actual,state,code,str(seconds),'4','gpu09')))
    for n,logical in enumerate(sorted(OLD_UNALLOCATED)):lines.append('|'.join((logical,str(500000+n),'CANCELLED','0:0','0','4','None assigned')))
    for i in (1,2,3):lines.append('|'.join(('317177_'+str(i),t.TECH_RAW[str(i)],'COMPLETED','0:0',str({1:778,2:118,3:2156}[i]),'4','gpu09.cluster')))
    for i in range(124):lines.append('|'.join(('317180_'+str(i),raw[str(i)],'COMPLETED','0:0','10','4','gpu09')))
    b={'grid_dispatch':'317180','scheduler':'\n'.join(lines),'technical_raw_ids':dict(t.TECH_RAW),'grid_raw_ids':raw,'started_controls':{}}
    b['reconciled']=reconcile(b['scheduler'],'317180',{int(k):v for k,v in t.TECH_RAW.items()},{int(k):v for k,v in raw.items()})
    originals={}
    for logical,want in t.expected_starts(c,b).items():
        z={k:v for k,v in want.items() if k!='path'};z.update(PID=100,start_ticks='1000',node='gpu09.cluster',time=1234567890.)
        originals[want['path']]=z;v=t.canonical(z);b['started_controls'][logical]={'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}
    return c,b,originals


def main():
    c,b,originals=fixture();calls=[]
    def load(path,want,end):
        z=originals[path];v=t.canonical(z)
        if {'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}!=want:raise ValueError('synthetic original identity changed')
        calls.append(path);return z
    proof=t.check_terminal(c,b,load,time.monotonic()+10)
    if len(calls)!=127 or proof['allocated_attempts']!=138 or proof['GPU_charged_seconds']!=4623:raise AssertionError('complete synthetic138/127/failure-inclusive accounting')
    for role in ('missing_start','changed_raw','changed_seconds','duplicate_row','running','coerced_index','changed_source','extra_field','false_flag'):
        bad=copy.deepcopy(b);rows=copy.deepcopy(originals)
        if role=='missing_start':bad['started_controls'].pop('317180_123')
        if role=='changed_raw':bad['grid_raw_ids']['123']='999999'
        if role=='changed_seconds':bad['reconciled']['GPU_charged_seconds']+=1
        if role=='duplicate_row':bad['scheduler']+='\n'+bad['scheduler'].splitlines()[-1]
        if role=='running':bad['scheduler']=bad['scheduler'].replace('317180_123|400123|COMPLETED','317180_123|400123|RUNNING')
        target=t.RUN+'/tasks/grid-0/controls/STARTED.json'
        if role=='coerced_index':rows[target]['index']=False
        if role=='changed_source':rows[target]['contract']='0'*64
        if role=='extra_field':rows[target]['ignored']=True
        if role=='false_flag':bad['independently_authenticated']=True
        reject(lambda:t.check_terminal(c,bad,lambda p,w,e:rows[p],time.monotonic()+5))
    reject(lambda:t.check_terminal(c,b,load,time.monotonic()-1))
    with tempfile.TemporaryDirectory(prefix='wm-rc1-terminal-source-') as tmp:
        root=Path(tmp);p=root/'ordinary.json';write_new(p,{'opaque':'synthetic technical control'})
        got=bound_json(p,identity(p),4000,time.monotonic()+5)
        if got!={'opaque':'synthetic technical control'}:raise AssertionError('ordinary source authentication')
        source_closure(root,{'ordinary.json':identity(p)},time.monotonic()+5)
        reject(lambda:source_closure(root,{'../outside':identity(p)},time.monotonic()+5))
        bad=identity(p);bad['sha256']='0'*64;reject(lambda:source_closure(root,{'ordinary.json':bad},time.monotonic()+5))
        bad=identity(p);bad['bytes']=True;reject(lambda:source_closure(root,{'ordinary.json':bad},time.monotonic()+5))
    layout=json.loads((ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/PRESERVATION-LAYOUT-001.json').read_text())['layout']
    grid=json.loads((ROOT/'docs/world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json').read_text());draft=copy.deepcopy(grid)
    draft['staged_members']['wm_diag0_rc1_final_v1/cpu_process_v2.py']=CPU_V2
    draft['rc1_final']={'run':layout['final_run'],'operational_root':layout['operational_root'],'archive_path':layout['archive_path'],
        'grid_run':grid['run'],'grid_contract':t.GRID,'analysis_authorized':True,'allocation_seconds':3600,'CPUs':4,
        'RAM_bytes':8589934592,'GPU_requested':0,'automatic_retry':False,
        'phase_seconds':{'analysis':1800,'independent_acceptance':600,'archive':1170,'finalize':30}}
    before=t.canonical(draft);check_frozen_extension(grid,draft,layout)
    if before!=t.canonical(draft):raise AssertionError('guard edited actual authority')
    bad=copy.deepcopy(draft);bad['rc1_final']['analysis_authorized']=False;reject(lambda:check_frozen_extension(grid,bad,layout))
    bad=copy.deepcopy(draft);bad['staged_members']['wm_diag0_rc1_final_v1/cpu_process_v2.py']={'bytes':10254,'sha256':CPU_V2['sha256']};reject(lambda:check_frozen_extension(grid,bad,layout))
    bad=copy.deepcopy(draft);bad['rc1_final']['GPU_requested']=False;reject(lambda:check_frozen_extension(grid,bad,layout))
    source={}
    for n in ('terminal_binding_v1.py','cpu_entry_guard_v1.py','terminal_binding_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-TERMINAL-ENTRY-001.json',{
        'status':'NEW_TERMINAL_START_AND_PREANALYSIS_SOURCE_GUARD_SYNTHETIC_PASSED','source':source,
        'synthetic_terminal_attempts':138,'synthetic_new_original_start_controls':127,'synthetic_GPU_charge':4623,
        'checks':['all138 incl historical failure and cancelled placeholders','all127 exact source/raw/index/PIDtick controls',
            'missing/raw/source/boolean/running/duplicate/forgedflag rejected','ordinary temp bounded source hashes',
            'strict tested V2 identity/noGPU/resources','actual frozen authority not mutated'],
        'actual_cluster_terminal_runtime_roots_or_historical_evidence_authenticated':False,
        'real_CPU_supervisor_stage_publication_SSD_authority_complete':False,'research_calls':0,'scheduler_queries':0,
        'actual_final_CPU_analysis_archive_or_SSD_run':False,'final_gate_ready':False},limit=16000)
    print(json.dumps({'status':'NEW_TERMINAL_START_AND_PREANALYSIS_SOURCE_GUARD_SYNTHETIC_PASSED','research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
