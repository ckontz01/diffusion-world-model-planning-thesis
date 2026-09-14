"""Single registered worker, requiring explicit exact future launch approval."""
import argparse
import os
from pathlib import Path
import resource
import time
import candidate_value_contract as ct


def work(source,run,approval,capsule,source_sha,kind,index):
    spec=ct.task(kind,index)
    cap=ct.authorize(source,run,approval,capsule,source_sha)
    ct.require(os.environ.get('SLURM_JOB_ID'),'Slurm allocation required')
    capsule_sha=ct.sha(capsule);out=Path(run)/('%s-%d'%(kind,index))
    out.mkdir(exist_ok=False);start=time.monotonic()
    # No data/model import before authorization and immutable source/runtime checks.
    import torch
    import candidate_value_learning as c
    torch.set_num_threads(4)
    from candidate_value_data import collect,load_record
    from candidate_value_models import train,Predictor
    from candidate_value_analyze import validation,closed,final_report
    try:
        if kind in ('train','validation','closed','preflight'):
            if kind!='preflight':
                for i in range(2):ct.check_report(Path(run)/('preflight-%d'%i),'preflight',i,source_sha,capsule_sha)
            if kind=='validation':
                ct.require(ct.check_report(Path(run)/'fit-0','fit',0,source_sha,capsule_sha)['advance'], 'Training gate')
            if kind=='closed':
                ct.require(ct.check_report(Path(run)/'validate-0','validate',0,source_sha,capsule_sha)['advance'],'Ranking gate')
            from candidate_value_runtime import RealBackend
            build_started=time.monotonic();backend=RealBackend();construction=time.monotonic()-build_started
            if kind=='preflight':
                # Constructor/tensor/decoder checks + all synthetic lifecycle tests;
                # no environment or selected reference is opened in preflight.
                import unittest
                suite=unittest.defaultTestLoader.discover(str(Path(source)/'cluster/prometheus'),pattern='test_candidate_value*.py')
                result=unittest.TextTestRunner().run(suite)
                ct.require(result.wasSuccessful(),'Synthetic pinned-runtime preflight')
                report=dict(test_count=result.testsRun,no_episode=True)
            elif kind in ('train','validation'):
                record,environment_seed=load_record(cap,spec['reference'],spec['h'],kind)
                report=collect(backend,record,environment_seed,spec['reference'],spec['h'],out)
            else:
                predict=Predictor(run,source_sha,capsule_sha)
                report=closed(backend,lambda h:load_record(cap,spec['reference'],h,'closed_loop'),
                              spec['reference'],out,predict)
            backend.assert_frozen()
            report.update(model_construction_seconds=construction,
                          gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                          gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved())
        elif kind=='fit':report=train(run,out,source_sha,capsule_sha,cap)
        elif kind=='validate':report=validation(run,out,source_sha,capsule_sha,cap)
        elif kind=='report':report=final_report(run,out,source_sha,capsule_sha,cap)
        else:raise RuntimeError('Unknown stage')
        seconds=time.monotonic()-start
        size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
        ct.require(seconds<=spec['seconds'] and size<ct.CAPS['job_bytes'],'Worker resource cap')
        report.update(kind=kind,index=index,technical_valid=True,source_sha256=source_sha,
                      capsule_sha256=capsule_sha,wall_seconds=seconds,
                      maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      bytes_before_report=size,protected_payload_reads=0,historical_decisions_changed=False)
        ct.json_write(out/'REPORT.json',report);ct.seal(out)
    except Exception as exc:
        # No catch-and-continue, guessed failure labels or overwritten partial output.
        ct.json_write(out/'TECHNICAL-FAILURE.json',dict(kind=kind,index=index,error_type=type(exc).__name__,
                      message=str(exc),wall_seconds=time.monotonic()-start,scientific_outputs_not_validated=True))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('source','run','approval','capsule','source-sha','kind'):p.add_argument('--'+n,required=True)
    p.add_argument('--index',type=int,required=True)
    a=p.parse_args();work(a.source,a.run,a.approval,a.capsule,a.source_sha,a.kind,a.index)
