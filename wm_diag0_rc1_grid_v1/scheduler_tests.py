"""Only new scheduler-history repair fixtures, not a repeated research suite."""
import ast,contextlib,io,json,subprocess,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from .common import ROOT,DOC,identity,write_new
from .scheduler import SOURCE,HISTORY


def reject(fn):
    try:fn()
    except (ValueError,RuntimeError):return
    raise AssertionError('required rejection missing')


def main():
    ns={'subprocess':subprocess};exec(SOURCE+HISTORY,ns)
    rows=[]
    for k,(raw,state,code,seconds) in ns['HISTORY_EXPECTED'].items():rows.append('|'.join([k,raw,state,code,str(100 if seconds is None else seconds),'4','gpu09']))
    for k in sorted(ns['HISTORY_UNALLOCATED']):rows.append('|'.join([k,k.split('_')[0],'CANCELLED by 1201','0:0','0','4','None assigned']))
    raw='\n'.join(rows);required=set(ns['HISTORY_EXPECTED'])|ns['HISTORY_UNALLOCATED']
    technical,charged=ns['all_before_grid'](raw)
    if len(technical)!=3 or charged!=631:raise AssertionError('exact331historical plus300fixture new technical')
    p=SimpleNamespace(returncode=1,stdout='',stderr='slurm_load_jobs error: Invalid job id specified\n')
    with patch('subprocess.check_output',return_value=raw),patch('subprocess.run',return_value=p):
        q,a,note=ns['exact_snapshot']('artificial-exact-ids',required)
        if q or a!=raw or not note['invalid_live_queue_id_authenticated_by_complete_terminal_history']:raise AssertionError('purged queue+complete terminal history accepted')
    for bad in (raw.replace('|COMPLETED|','|RUNNING|',1),'\n'.join(rows[1:]),raw+'\n'+rows[0]):
        with patch('subprocess.check_output',return_value=bad),patch('subprocess.run',return_value=p):reject(lambda:ns['exact_snapshot']('artificial',required))
        reject(lambda:ns['all_before_grid'](bad))
    other=SimpleNamespace(returncode=1,stdout='',stderr='permission denied')
    with patch('subprocess.check_output',return_value=raw),patch('subprocess.run',return_value=other):reject(lambda:ns['exact_snapshot']('artificial',required))
    partial=SimpleNamespace(returncode=1,stdout='live job',stderr=p.stderr)
    with patch('subprocess.check_output',return_value=raw),patch('subprocess.run',return_value=partial):reject(lambda:ns['exact_snapshot']('artificial',required))
    from .technical_observation import READ
    from .operations import STAGE,OBSERVE
    with tempfile.TemporaryDirectory(prefix='wm-rc1-queue-race-') as tmp:
        r=Path(tmp);(r/'controls').mkdir();(r/'source').mkdir();t=r/'tasks/grid-0';(t/'controls').mkdir(parents=True);(t/'output').mkdir()
        write_new(r/'controls/DISPATCH.json',{'array_job_id':'1'});write_new(r/'source/GRID-CONTRACT.json',{'rc1_grid':{'GPU_charged_before':0,'full_future_GPU_seconds':0}})
        write_new(t/'output/MEMBERS.json',{});write_new(t/'controls/ACCEPTED.json',{'output_seal':identity(t/'output/MEMBERS.json')})
        output=io.StringIO()
        with patch('subprocess.check_output',return_value=''),patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')),contextlib.redirect_stdout(output):exec(compile(OBSERVE,'artificial-observer-r2','exec'),{'RUN':str(r)})
        row=json.loads(output.getvalue())
        if row['accepted_grid_parents']!=0 or not row['tasks']['0']['acceptance_finalization_pending']:raise AssertionError('publication race remains nonfault')
    for code in (SOURCE+HISTORY,STAGE,OBSERVE,SOURCE+READ):ast.parse(code,feature_version=(3,6))
    source={}
    for path in (ROOT/'wm_diag0_rc1_grid_v1').glob('*.py'):compile(path.read_bytes(),str(path),'exec');source[path.name]=identity(path)
    write_new(DOC/'ARTIFICIAL-SCHEDULER-003.json',{'status':'PASSED','source':source,'checks':['purged live queue requires complete exact terminal accounting','unknown/missing/duplicate/live allocation rejected','permission and partial queue errors not swallowed','all14allocated historical/current charges including failed317171','ACCEPTED-before-RESULT publication race with revised scheduler','Python3.6 remote/observer/controller syntax'],
        'research_or_scheduler_calls':0,'original56suite_repeated':False,'previous_resource_race_receipt_retained':'ARTIFICIAL-LOCAL-002.json','old_frozen_research_closures_edited':False})
    print(json.dumps({'status':'SCHEDULER_TERMINAL_HISTORY_REPAIR_ARTIFICIAL_PASSED','research_calls':0}))


if __name__=='__main__':main()
