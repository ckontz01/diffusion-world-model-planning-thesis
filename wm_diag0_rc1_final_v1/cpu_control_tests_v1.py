"""Artificial draft/resource/owned-child tests; no model, network or Slurm."""
import ast,copy,json,os,sys,tempfile,time
from pathlib import Path
from .cpu_process_v1 import validate_design,run_child,artifact_bytes
from wm_diag0_rc1_grid_v1.common import ROOT,identity,write_new


def reject(fn,kind=Exception):
    try:fn()
    except kind:return
    raise AssertionError('required rejection absent')


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive artificial receipt')
    with tempfile.TemporaryDirectory(prefix='wm-rc1-final-cpu-artificial-') as tmp:
        base=Path(tmp);study=base/'study';grid={'run':str(study/'campaign-v4-rc1-grid-v1'),'science':{'ridge_alpha':1,'roots':120,'parents':128},
            'gpu_stages_authorized':False,'staged_members':{'fixed/original.py':{'bytes':1,'sha256':'0'*64}}}
        c=copy.deepcopy(grid);ops=base/'study-rc1-preservation-v1'
        c['rc1_final']={'analysis_authorized':False,'run':str(study/'campaign-v4-rc1-final-v1'),'operational_root':str(ops),
            'archive_path':str(ops/'archive/final-study.tar'),'allocation_seconds':3600,'CPUs':4,'RAM_bytes':8589934592,'GPU_requested':0,'automatic_retry':False,
            'phase_seconds':{'analysis':1800,'independent_acceptance':600,'archive':1195,'finalize':5}}
        c['staged_members']['wm_diag0_rc1_final_v1/new.py']={'bytes':1,'sha256':'1'*64}
        good=validate_design(grid,c)
        if good['CPU_full_future_seconds']!=6836 or good['final_gate_ready'] or good['input_publication_SSD_runtime_historical_supplier_gates_checked']:raise AssertionError('draft cannot claim actual readiness or consume conversion reserve')
        def mutation(field,value):
            z=copy.deepcopy(c);z['rc1_final'][field]=value;return validate_design(grid,z)
        for k,v in (('analysis_authorized',True),('GPU_requested',1),('CPUs',5),('RAM_bytes',8589934593),('allocation_seconds',3601),('automatic_retry',True),('archive_path',str(study/'recursive.tar'))):reject(lambda:mutation(k,v),ValueError)
        reject(lambda:mutation('phase_seconds',{'analysis':1800,'independent_acceptance':600,'archive':1200,'finalize':5}),ValueError)
        altered=copy.deepcopy(c);altered['science']['ridge_alpha']=2;reject(lambda:validate_design(grid,altered),ValueError)
        altered=copy.deepcopy(c);altered['staged_members']['fixed/original.py']['sha256']='2'*64;reject(lambda:validate_design(grid,altered),ValueError)
        altered=copy.deepcopy(c);altered['staged_members']['unexpected/new.py']={'bytes':1,'sha256':'1'*64};reject(lambda:validate_design(grid,altered),ValueError)
        out=base/'out';out.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
        def run(name,code,cap=100000,seconds=3,artifact_cap=40000000):
            end=time.monotonic()+seconds
            return run_child([sys.executable,'-B','-c',code],env,base/(name+'.log'),[out],artifact_cap,cap,end,end+2.5)
        result=run('ok','print("artificial CPU log")')
        if result['returncode'] or (base/'ok.log').read_text().strip()!='artificial CPU log':raise AssertionError('actual harmless child log roundtrip')
        reject(lambda:run('ok','raise Exception("must not launch")'),FileExistsError)
        reject(lambda:run('nonzero','raise SystemExit(3)'),RuntimeError)
        reject(lambda:run('loglimit','print("x"*64)',cap=8),ValueError)
        if (base/'loglimit.log').stat().st_size>8:raise AssertionError('hard log bound before write')
        began=time.monotonic();reject(lambda:run('timeout','import time;time.sleep(10)',seconds=.12),TimeoutError)
        if time.monotonic()-began>2.5:raise AssertionError('silent child killed promptly without indefinite wait')
        (out/'large.partial').write_bytes(b'0123456789')
        reject(lambda:run('artifactlimit','print("must not launch")',artifact_cap=5),ValueError)
        if (out/'large.partial').read_bytes()!=b'0123456789' or artifact_bytes([out])!=10:raise AssertionError('failed artifact retained')
        end=time.monotonic()+3
        reject(lambda:run_child([sys.executable,'-B','-c','print(1)'],env,base/'noreserve.log',[out],40,10,end,end+.1),ValueError)
    folder=ROOT/'wm_diag0_rc1_final_v1';sources={}
    for n in ('cpu_process_v1.py','cpu_control_tests_v1.py'):
        compile((folder/n).read_bytes(),n,'exec');ast.parse((folder/n).read_text(),feature_version=(3,6));sources[n]=identity(folder/n)
    write_new(ROOT/('docs/world-model-diagnostic-rc1-final-v1-20261016/ARTIFICIAL-CPU-CONTROL-'+label+'.json'),{
        'status':'PASSED','source':sources,'research_artifacts_or_values_read':False,'model_simulator_fit_source_generation_calls':0,
        'Slurm_or_network_calls':0,'checkpoint_loading':False,'harmless_local_child_processes':4,
        'checks':['fixed old grid science/source cannot mutate','new explicit final-only source roles','CPU3600/fourCPU/8GiB/noGPU/noRetry draft bounds','full phase plus cleanup reservation and CPU6836 with untouched1800conversion reserve','draft cannot grant analysis authority','disjoint archive/operational-root draft paths','actual harmless child exact log','existing log refused before launch','nonzero child no retry','hard log write bound','silent child deadline and owned-only cleanup','artifact overrun refusal with retained partial','cleanup cannot be unfunded'],
        'actual_runtime_or_historical_provenance_binding_done':False,'complete_final_CPU_supervisor_or_submission_implemented':False,
        'draft_phase_split_is_frozen_or_a_timing_guarantee':False,'real_final_analysis_or_archive_run':False,'final_gate_ready':False})
    print(json.dumps({'status':'ARTIFICIAL_CPU_DRAFT_AND_FINITE_PROCESS_PRIMITIVE_PASSED','research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
