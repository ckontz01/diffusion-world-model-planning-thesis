"""Retain failed Linux snapshot; derive explicit dependency-complete V2 files."""
import json
from .common import DOC,write_new
from .build import derive
def main():
    p='wm_diag0_rc1_close_v1/';made={}
    made['identity']=derive(p+'closed_identity.py',p+'closed_identity_v2.py',[
        ('from wm_diag0_rc1_final_v2.evidence_auth_v1 import ordinary','from wm_diag0_rc1_final_v2.evidence_auth_v1 import ordinary,bound_bytes')])
    made['closure']=derive(p+'analysis_closure.py',p+'analysis_closure_v2.py',[
        ('from .closed_identity import identity','from .closed_identity_v2 import identity')])
    made['entry']=derive(p+'entry.py',p+'entry_v2.py',[
        ("result=subprocess.check_output(['scontrol','show','job','-o',job],universal_newlines=True,timeout=8)",
         "result=subprocess.check_output(['scontrol','show','job','-o',job],universal_newlines=True,timeout=8,env=dict(os.environ,TZ='UTC'))"),
        ("    return {'job_id':job,'affinity':sorted(affinity),'kernel_memory_limits':limits,'scheduler_job_sha256':__import__('hashlib').sha256(result.encode()).hexdigest()}",
         "    import calendar\n    started=calendar.timegm(time.strptime(fields['StartTime'],'%Y-%m-%dT%H:%M:%S'))\n    return {'job_id':job,'allocation_started_epoch':started,'affinity':sorted(affinity),'kernel_memory_limits':limits,'scheduler_job_sha256':__import__('hashlib').sha256(result.encode()).hexdigest()}")])
    made['archive']=derive(p+'archive_operation.py',p+'archive_operation_v2.py',[
        ('from .analysis_closure import','from .analysis_closure_v2 import'),
        ('from .entry import','from .entry_v2 import'),
        ("'wm_diag0_rc1_close_v1.archive_operation'","'wm_diag0_rc1_close_v1.archive_operation_v2'")])
    made['workflow']=derive(p+'workflow.py',p+'workflow_v2.py',[
        ('from .analysis_closure import','from .analysis_closure_v2 import'),
        ('from .archive_operation import','from .archive_operation_v2 import'),
        ('from .closed_identity import','from .closed_identity_v2 import')])
    made['driver']=derive(p+'driver.py',p+'driver_v2.py',[
        ('from .entry import','from .entry_v2 import'),('from .workflow import','from .workflow_v2 import'),
        ('from .closed_identity import','from .closed_identity_v2 import'),
        ("dispatch=bound_json(dispatch_path,identity(dispatch_path,16000,deadline),16000,deadline)","dispatch=bound_json(dispatch_path,identity(dispatch_path,200000,deadline),200000,deadline)"),
        ("    start=os.environ.get('SLURM_JOB_START_TIME','')\n    if not start.isdigit():raise PermissionError('Slurm allocation start epoch required')\n    elapsed=time.time()-int(start)",
         "    elapsed=time.time()-gate['allocation_started_epoch']")])
    write_new(DOC/'KERNEL-REPAIR-002.json',{'status':'NEW_EXPLICIT_V2_CONTROLLER_FILES_PRESERVE_LINUX_FAILURE_PREIMAGES','derived':made,
        'diagnosis':'extracted identity helper omitted bound_bytes import','before_any_actual_analysis':True})
    print(json.dumps({'status':'NEW_V2_CONTROLLER_FILES_DERIVED'}))
if __name__=='__main__':main()
