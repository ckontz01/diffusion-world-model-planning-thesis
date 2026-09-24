"""Production CPU fit/analysis and GPU evaluation entry point. Disabled by default."""
import r1 as recovery
import common as c
import argparse
import io
import os
import signal
import socket
import time
import traceback

def arrays_digest(a,names):
    import hashlib
    h=hashlib.sha256()
    for k in sorted(names):
        x=a[k];h.update(c.canonical([k,x.dtype.str,list(x.shape)]));h.update(x.tobytes(order='C'))
    return h.hexdigest()

def evaluation(auth,spec,out):
    import numpy as np
    import torch
    from hardware import verify_device
    from models import check_freeze,load_pair
    from selector import CommittedFeedbackSelector
    from bridge import load_backend,source_factory,array_hash
    from episodes import evaluate,save
    from verify import verify_arrays,load_verify
    # All physical checks precede LeWM/checkpoint/reference access.
    h=verify_device(torch,lambda h:c.write(out/'HARDWARE.json',h))
    c.require(h['hostname'] in ('gpu09','gpu09.cluster') and os.environ.get('SLURM_JOB_NODELIST')=='gpu09','Explicit gpu09 hostname association')
    torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
    frozen=check_freeze(auth.run,auth.approval['package_sha256'])
    selector=CommittedFeedbackSelector(*load_pair(auth,spec['pair'])) if spec['pair'] is not None else None
    backend=load_backend(auth)
    factory,ref,record=source_factory(auth,spec['reference'],'mechanism_evaluation',backend)
    def preserve(arrays,meta):
        b=io.BytesIO();np.savez(b,**arrays)
        c.require(b.tell()+len(c.canonical(meta))+100000<=spec['byte_cap'],'Partial evidence cap')
        with (out/'PARTIAL-EVIDENCE.npz').open('xb') as f:f.write(b.getvalue())
        c.write(out/'PARTIAL-EVIDENCE.json',meta)
    arrays,meta=evaluate(factory,backend.rollout,spec['reference'],spec['control'],selector,preserve=preserve)
    meta.update(role='mechanism_evaluation',pair=spec['pair'],task=spec['key'],reference_identity=ref,model_freeze=c.sha(auth.run/'ALL-MODELS-FROZEN.json'))
    meta['initial_sha256']=array_hash(arrays['requested_initial'])
    meta['goal_sha256']=array_hash(arrays['goal_state'])
    meta['branches'][0]['prefix_steps']=min(5,meta['branches'][0]['steps'])
    check=verify_arrays(arrays,meta,role_map=c.roles())
    np.testing.assert_array_equal(arrays['requested_initial'],record['state']);np.testing.assert_array_equal(arrays['goal_state'],record['goal_state'])
    c.require(backend.fingerprint()==backend.frozen_hash,'LeWM mutated')
    c.require(check_freeze(auth.run,auth.approval['package_sha256'])==frozen,'Six model bytes changed')
    # In-memory model tensors cannot be changed by inference unnoticed.
    if selector is not None:
        j,o=load_pair(auth,spec['pair'])
        for left,right in ((selector.joint,j),(selector.ordinary,o)):
            for x,y in zip(left.params,right.params):np.testing.assert_array_equal(x,y)
    save(out,arrays,meta)
    saved,saved_meta,again=load_verify(out,role_map=c.roles(),authorization=auth);c.require(again==check,'Independent saved endpoint verification')
    from prefix_coupling import technical
    return dict(hardware=h,checks={k:v for k,v in check.items() if k!='successes'},models_unchanged=True,
                episode_identity=[spec['reference'],spec['pair'],spec['control']],
                tree_digest=arrays_digest(arrays,[k for k in arrays if k.startswith('tree/')]),
                initial_goal_digest=arrays_digest(arrays,['requested_initial','goal_state','initial_image','goal_image','goal_latent']),
                prefix_coupling=technical(saved,saved_meta),
                image_encodings=backend.encodings,fingerprinting_seconds=backend.fingerprint_seconds,
                lewm_tensor_hash=backend.frozen_hash,peak_torch_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_torch_reserved_bytes=torch.cuda.max_memory_reserved(),counts=meta['branches'][0]['ledger'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--task',required=True);a=p.parse_args()
    ctx=recovery.Context(os.environ['ACVM_R3_APPROVAL']);c.require(a.approval==str(ctx.worker_approval) and a.run==str(ctx.run),'Recovery worker invocation');auth=ctx.auth;spec=next(j for j in c.grid() if j['key']==a.task)
    c.require(os.environ.get('SLURM_JOB_ID','').isdigit() and os.environ.get('SLURM_CPUS_PER_TASK')=='4','Allocated worker only')
    started=time.monotonic();cpu=time.process_time();out=auth.run/spec['key'];out.mkdir(exist_ok=False)
    def timeout(*_):raise TimeoutError('Work timeout: retain partial evidence, no retry')
    signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGTERM,timeout);signal.alarm(spec['work_seconds'])
    try:
        claim=auth.run/'submissions-r3'/(spec['key']+'.json')
        while not claim.exists() and time.monotonic()-started<40:time.sleep(.2)
        r=c.read(claim);c.require(r==dict(job=os.environ['SLURM_JOB_ID'],spec=spec,package=auth.approval['package_sha256']),'Exact submitted allocation association')
        auth.runtime()
        recovery.authenticated_imports()
        if spec['gpu']: extra=evaluation(auth,spec,out)
        else:
            c.require(not os.environ.get('CUDA_VISIBLE_DEVICES'),'CPU stage cannot see GPU')
            if spec['stage']=='fitting':
                from models import fitting
                f=fitting(auth,spec,out);extra=dict(updates=f['updates'],seed=f['seed'],selection=False)
            else:
                from analysis import analyze
                extra=analyze(auth,out)
        import resource
        c.write(out/'TECHNICAL.json',dict(passed=True,spec=spec,package=auth.approval['package_sha256'],approval=auth.approval_sha,
                recovery_approval=ctx.approval_sha,job=os.environ['SLURM_JOB_ID'],hard_seconds=spec['seconds'],work_seconds=spec['work_seconds'],
                worker_wall_seconds=time.monotonic()-started,process_cpu_seconds=time.process_time()-cpu,
                peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                rss_scope='worker-process high-water RSS, not total node memory',**extra))
        c.seal(out,spec);c.require(c.bytes_in(out)<=spec['byte_cap'],'Complete worker including seal')
    except BaseException as e:
        signal.alarm(0);c.write(out/'FAILURE.json',dict(error=repr(e),traceback=traceback.format_exc(),wall_seconds=time.monotonic()-started,automatic_retry=False));raise
    finally:signal.alarm(0)
if __name__=='__main__':main()
