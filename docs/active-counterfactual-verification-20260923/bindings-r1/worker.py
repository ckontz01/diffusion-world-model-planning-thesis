"""Real worker entry point. False authorization rejected before all data loads."""
import common as c
import argparse
import os
from pathlib import Path
import signal
import time
import traceback


def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--task',required=True);a=p.parse_args()
    auth=c.Authorization(a.approval,a.run)
    spec=next(j for j in c.grid() if j['key']==a.task)
    c.require(os.environ.get('SLURM_JOB_ID','').isdigit() and os.environ.get('SLURM_CPUS_PER_TASK')=='4','Exact allocated worker required')
    run=auth.run;out=run/a.task;out.mkdir(exist_ok=False)
    started=time.monotonic();cpu=time.process_time()
    def timeout(*_):raise TimeoutError('Work deadline; frozen preservation margin, no retry')
    signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGTERM,timeout)
    signal.alarm(c.work_seconds(spec))
    try:
        auth.runtime()
        import resource
        import numpy as np
        from dispatch import storage
        storage(c.ROOT,run,c.grid())
        if spec['stage']=='collection' and spec['reference'] not in (490,545):
            gate=c.read(run/'TECHNICAL-TRANCHE-PASSED.json')
            for key,h in gate['seals'].items():c.require(c.sha(run/key/'SEAL.json')==h,'Tranche seal changed')
            c.require(set(gate['seals'])=={'collect-fit-490','collect-fit-545'} and gate['scientific_selection'] is False,'Included technical gate')
        if spec['gpu']:
            import torch
            from hardware import initialize_backend
            hardware,backend=initialize_backend(torch,lambda value:c.write(out/'HARDWARE.json',value),auth)
            from bridge import source_factory
            from episodes import collect,evaluate,save
            from verify import verify_arrays
            torch.set_num_threads(4)
            torch.cuda.reset_peak_memory_stats()
            role=spec.get('role','final_development')
            # Check sealed models BEFORE any final source open.
            if spec['stage']=='evaluation':
                from fitting import load_models
                from policy import Selector
                selector=Selector(*load_models(run))
            factory,ref,record=source_factory(auth,spec['reference'],role,backend)
            def preserve(arrays,meta):
                import io
                stream=io.BytesIO();np.savez(stream,**arrays)
                c.require(stream.tell()+len(c.canonical(meta))+100_000<=spec['byte_cap'],'Partial evidence reservation')
                with (out/'PARTIAL-EVIDENCE.npz').open('xb') as f:f.write(stream.getvalue())
                c.write(out/'PARTIAL-EVIDENCE.json',meta)
            if spec['stage']=='collection': arrays,metadata=collect(factory,backend.rollout,spec['reference'],role,preserve=preserve)
            else:arrays,metadata=evaluate(factory,backend.rollout,spec['reference'],spec['control'],selector,preserve=preserve)
            check=verify_arrays(arrays,metadata)
            np.testing.assert_array_equal(arrays['requested_initial'],record['state'])
            np.testing.assert_array_equal(arrays['goal_state'],record['goal_state'])
            c.require(backend.fingerprint()==backend.frozen_hash,'Le-WM tensors mutated during frozen inference')
            metadata['reference_identity']=ref
            metadata['initial_sha256']=__import__('bridge').array_hash(arrays['requested_initial'])
            metadata['goal_sha256']=__import__('bridge').array_hash(arrays['goal_state'])
            save(out,arrays,metadata)
            # A second read from the actual saved bytes, not just an in-memory assertion.
            from verify import load_verify
            _,_,saved_check=load_verify(out,authorization=auth);c.require(saved_check==check,'Saved evidence changed')
            resource_extra={'hardware':hardware,'image_encodings':backend.encodings,'peak_torch_allocated_bytes':torch.cuda.max_memory_allocated(),
                            'peak_torch_reserved_bytes':torch.cuda.max_memory_reserved(),
                            'checks':{k:v for k,v in check.items() if k!='successes'},
                            'lewm_tensors_sha256_before_after':backend.frozen_hash,'models_unchanged':True,
                            'fingerprinting_seconds':backend.fingerprint_seconds,
                            'search_and_decision_counts':[b['ledger'] for b in metadata['branches']]}
        else:
            c.require(not os.environ.get('CUDA_VISIBLE_DEVICES'),'CPU job must not see GPU')
            if spec['stage']=='fitting':
                from verify import load_verify,dataset_rows
                from mock import pack
                from fitting import fit_job
                datasets={}
                for role in ('fit','validation'):
                    rows=[]
                    for ref in c.roles()[role]:
                        key=f'collect-{role}-{ref}';c.verify_seal(run/key,next(j for j in c.grid() if j['key']==key))
                        arrays,meta,_=load_verify(run/key,authorization=auth);rows+=dataset_rows(arrays,meta)
                    datasets[role]=pack(rows)
                # Persist exact source-grouped inputs for independent role audit.
                for role,data in datasets.items():
                    with (out/(role+'-dataset.npz')).open('xb') as f:np.savez(f,**data)
                result=fit_job(spec['key'][4:],datasets['fit'],datasets['validation'],out,run/'fit-joint')
                resource_extra={'updates':result['updates'],'fit_count':64,'validation_count':16,'selection':False}
            else:
                from analysis import aggregate
                c.write(out/'REPORT.json',aggregate(run,auth));resource_extra={'verified_grid':339,'analysis':'all32 sources/all8 arms'}
        technical={'passed':True,'spec':spec,'package':auth.approval['package_sha256'],'approval':auth.approval_sha,
                   'attempt':2 if spec['key']=='collect-fit-490' else 1,
                   'hard_seconds':spec['seconds'],'work_seconds':c.work_seconds(spec),'supervisor_seconds':c.supervisor_seconds(spec),
                   'worker_wall_seconds_through_payload':time.monotonic()-started,'process_cpu_seconds':time.process_time()-cpu,
                   'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                   'rss_scope':'Linux worker process high-water RSS; not total node RAM',**resource_extra}
        c.write(out/'TECHNICAL.json',technical);c.seal(out,spec)
        c.require(sum(f.stat().st_size for f in out.rglob('*') if f.is_file())<=spec['byte_cap'],'Complete output plus seal cap')
        storage(c.ROOT,run,c.grid())
    except BaseException as e:
        signal.alarm(0)
        c.write(out/'FAILURE.json',{'error':repr(e),'traceback':traceback.format_exc(),'wall_seconds':time.monotonic()-started,
                                  'process_cpu_seconds':time.process_time()-cpu,'automatic_retry':False})
        raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
