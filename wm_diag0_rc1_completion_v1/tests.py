"""Small new artificial budget/observer tests; no scheduler or research calls."""
import copy,json,subprocess,sys,tempfile,time
from pathlib import Path
from .common import CAPS,DOC,authority,identity,check_reservation,write_new
from .compact import GRID_HASH,compact_payload,program
from .job import child_job

def main():
    a,v=authority();assert sum(CAPS.values())==21600 and a['new_charge_seconds']==21300
    check_reservation('implementation',10,time.time(),a,v,[],0)
    for component,seconds in [('monitoring',31),('native_SSD',7201),('unknown',10)]:
        try:check_reservation(component,seconds,time.time(),a,v,[],0)
        except (ValueError,RuntimeError):pass
        else:raise AssertionError('invalid reservation accepted')
    old={};rows=[]
    for i in range(35):
        raw=str(317181+i);seal={'bytes':1,'sha256':'a'*64}
        rows.append('317180_'+str(i)+'|'+raw+'|COMPLETED|0:0|210|4|gpu09')
        old[str(i)]={'STARTED':{'array_job_id':'317180','index':i,'contract':GRID_HASH,'job_id':raw},
                     'ACCEPTED':{'accepted':True,'contract_sha256':GRID_HASH,'output_seal':seal},
                     'RESULT':{'status':'ACCEPTED','job_id':raw,'output_seal':seal}}
    rows.append('317180_[35-123%1]|317180|PENDING|0:0|0|4|None assigned')
    o={'dispatch':{'array_job_id':'317180','indices':124,'contract_sha256':GRID_HASH,'automatic_retries':0},
       'scheduler':'\n'.join(rows),'queue':'pending','queue_diagnostic':{},'tasks':old,'accepted_grid_parents':35,
       'active_process_records':[],'STOP':None,'full_future_GPU_reservation':449783,'CPU_before_analysis':1436,
       'quality_choices_outcomes_or_predictions_read':False}
    good=compact_payload(o);assert good['GPU_terminal_all_attempts_seconds']==10733 and good['accepted_grid_parents']==35
    assert len(json.dumps(good).encode())<15000 and 'tasks' not in good
    b=copy.deepcopy(o);b['STOP']={'technical':'fixture'};assert compact_payload(b)['STOP_present']
    b=copy.deepcopy(o);b['tasks']['0']['RESULT']['job_id']='999'
    try:compact_payload(b)
    except ValueError:pass
    else:raise AssertionError('raw identity mutation accepted')
    b=copy.deepcopy(o);b['tasks']['0']['ACCEPTED']['accepted']=False
    try:compact_payload(b)
    except ValueError:pass
    else:raise AssertionError('false acceptance accepted')
    assert program().count('q,a,queue_diagnostic=exact_snapshot(')==1
    # Actual native owned job: worker cannot launch command until assignment.
    with tempfile.TemporaryDirectory(prefix='wmrc1-completion-test-') as tmp:
        pth=Path(tmp)/'ordinary.txt';cmd=[sys.executable,'-B','-m','wm_diag0_rc1_completion_v1.worker',sys.executable,'-B','-c','from pathlib import Path;Path('+repr(str(pth))+').write_text("fixture")']
        k,h,usage=child_job();p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        try:
            time.sleep(.05);assert not pth.exists()
            assert k.AssignProcessToJobObject(h,int(p._handle))
            out,_=p.communicate(b'GO\n',timeout=3);assert p.returncode==0 and pth.read_text()=='fixture',out
        finally:
            k.TerminateJobObject(h,125);k.CloseHandle(h)
            if p.poll() is None:p.kill();p.wait(timeout=1)
    receipt={'status':'ARTIFICIAL_COMPLETION_BUDGET_AND_COMPACT_OBSERVER_PASSED','scheduler_calls':0,'research_calls':0,'D_access':False,
             'tests':'approved sums; component/check limits; synthetic scheduler/acceptance/raw-ID/STOP; Linux3.6 syntax; actual owned Windows job/handshake',
             'source':{p.name:identity(p) for p in Path(__file__).parent.glob('*.py')}}
    write_new(DOC/'ARTIFICIAL-001.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':main()
