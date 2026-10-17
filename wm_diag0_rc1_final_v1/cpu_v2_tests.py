"""Targeted unfrozen V2 cleanup/type regression tests, no research artifacts."""
import ast,copy,json,os,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
from . import cpu_process_v1 as legacy
from . import cpu_process_v2 as repaired
from wm_diag0_rc1_grid_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('required strict rejection absent')


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive label')
    class AlreadyExited:
        pid=424242424
        def poll(self):return 0
        def wait(self,timeout):raise AssertionError('do not wait again for a reaped leader')
    with patch.object(repaired.os,'name','posix'),patch.object(repaired.os,'killpg',create=True) as kill,patch.object(repaired.signal,'SIGKILL',9,create=True):
        legacy.stop_owned(AlreadyExited())
        if kill.called:raise AssertionError('record exact original missing-group-cleanup condition')
        repaired.stop_owned(AlreadyExited());kill.assert_called_once_with(424242424,9)
    with tempfile.TemporaryDirectory(prefix='wm-rc1-cpu-v2-artificial-') as tmp:
        b=Path(tmp);grid={'run':str(b/'study/campaign-v4-rc1-grid-v1'),'science':{'unchanged':True},'staged_members':{}}
        c=copy.deepcopy(grid);ops=b/'study-rc1-preservation-v1'
        c['rc1_final']={'analysis_authorized':False,'run':str(b/'study/campaign-v4-rc1-final-v1'),'operational_root':str(ops),
            'archive_path':str(ops/'archive/final-study.tar'),'allocation_seconds':3600,'CPUs':4,'RAM_bytes':8589934592,'GPU_requested':0,'automatic_retry':False,
            'phase_seconds':{'analysis':1800,'independent_acceptance':600,'archive':1195,'finalize':5}}
        repaired.validate_design(grid,c)
        for k,v in (('CPUs',4.0),('GPU_requested',False),('automatic_retry',0)):
            bad=copy.deepcopy(c);bad['rc1_final'][k]=v;reject(lambda:repaired.validate_design(grid,bad))
        (b/'out').mkdir();end=time.monotonic()+3
        z=repaired.run_child([sys.executable,'-B','-c','print("artificial V2 child")'],dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''),b/'v2.log',[b/'out'],40000000,100000,end,end+2.5)
        if z['returncode'] or (b/'v2.log').read_text().strip()!='artificial V2 child':raise AssertionError('ordinary V2 child preserved')
    folder=ROOT/'wm_diag0_rc1_final_v1';sources={}
    for n in ('cpu_process_v1.py','cpu_process_v2.py','cpu_v2_tests.py'):
        compile((folder/n).read_bytes(),n,'exec');ast.parse((folder/n).read_text(),feature_version=(3,6));sources[n]=identity(folder/n)
    write_new(ROOT/('docs/world-model-diagnostic-rc1-final-v1-20261016/ARTIFICIAL-CPU-V2-'+label+'.json'),{
        'status':'PASSED','source':sources,'original_V1_source_preserved':True,
        'checks':['original early-exited leader cleanup omission demonstrated with inert POSIX syscall mock','V2 signals only the newly owned group even after leader exit','no second wait for reaped leader','strict integer resource fields/boolean retry fields reject float/bool coercion','ordinary native harmless V2 child roundtrip'],
        'POSIX_process_group_test_here_is_mocked':True,'harmless_native_local_children':1,'model_simulator_fit_source_generation_calls':0,
        'research_artifacts_or_values_read':False,'Slurm_network_calls':0,'complete_final_CPU_supervisor_or_contract_ready':False,'final_gate_ready':False})
    print(json.dumps({'status':'ARTIFICIAL_CPU_V2_TARGETED_REGRESSION_PASSED','final_gate_ready':False}))


if __name__=='__main__':main()
