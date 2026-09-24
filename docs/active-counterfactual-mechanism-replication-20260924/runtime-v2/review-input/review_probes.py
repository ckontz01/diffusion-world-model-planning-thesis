"""Narrow source-excerpt probes for bb181cc6b6c60770898afacdcca3fb9e604c90c1.
No cluster connection, scheduler, research payload, model or physics is used.
These isolate the published command builder and evaluation/reader contract.
They are NOT a reproduction of the author's full integration suite.
"""
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
import hashlib, io, json, os, sys, tempfile
import numpy as np

# Exact function excerpt from runtime-v1/dispatch.py.
COMMAND_SOURCE = '''def command(spec,approval,run):
    cmd=['/usr/bin/sbatch','--parsable','--no-requeue','--account=superworld','--cpus-per-task=4',
         '--mem='+str(spec['ram_gib'])+'G','--time='+str(spec['seconds']//60),
         '--job-name=acvm1-'+spec['key'],'--output='+str(run/'logs'/(spec['key']+'.slurm.out')),
         '--error='+str(run/'logs'/(spec['key']+'.slurm.err'))]
    if spec['gpu']: cmd+=['--partition=a6000','--qos=normal-a6000','--gres=gpu:1','--nodelist=gpu09']
    else: cmd+=['--partition=defq','--qos=normal']
    return cmd+['/bin/bash',str(c.ROOT/'run_worker.sh'),str(c.ROOT),str(approval),str(run),spec['key'],str(spec['gpu'])]
'''
# Exact evaluation function excerpt from runtime-v1/worker.py.
EVALUATION_SOURCE = '''def evaluation(auth,spec,out):
    import numpy as np
    import torch
    from hardware import verify_device
    from models import check_freeze,load_pair
    from selector import CommittedFeedbackSelector
    from bridge import load_backend,source_factory
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
    _,_,again=load_verify(out,role_map=c.roles(),authorization=auth);c.require(again==check,'Independent saved endpoint verification')
    return dict(hardware=h,checks={k:v for k,v in check.items() if k!='successes'},models_unchanged=True,
                episode_identity=[spec['reference'],spec['pair'],spec['control']],
                tree_digest=arrays_digest(arrays,[k for k in arrays if k.startswith('tree/')]),
                initial_goal_digest=arrays_digest(arrays,['requested_initial','goal_state','initial_image','goal_image','goal_latent']),
                image_encodings=backend.encodings,fingerprinting_seconds=backend.fingerprint_seconds,
                lewm_tensor_hash=backend.frozen_hash,peak_torch_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_torch_reserved_bytes=torch.cuda.max_memory_reserved(),counts=meta['branches'][0]['ledger'])
'''
# Exact independent-reader excerpt from the pinned inherited bindings-r1/verify.py.
READER_SOURCE = '''def load_verify(directory, *, role_map=None, authorization=None):
    with np.load(directory/'evidence.npz', allow_pickle=False) as z: a = {k:z[k] for k in z.files}
    m = c.read(directory/'EVIDENCE.json')
    if authorization is not None:
        c.require(type(authorization) is c.Authorization,'Independent reference check requires execution capability')
        ref=authorization.reference(m['reference'],m['role'])
        c.require(m['reference_identity']==ref,'Saved exact input/source identity')
        # Independent reader, distinct from the world factory. Only this job's
        # explicitly allowlisted initial/H75 pair is decoded, not old endpoints.
        with np.load(ref['file'],allow_pickle=False) as z:
            np.testing.assert_array_equal(a['requested_initial'],z['initial_request'])
            np.testing.assert_array_equal(a['goal_state'],z['states'][75])
        c.require(ah(a['requested_initial']).hex()==m['initial_sha256'] and ah(a['goal_state']).hex()==m['goal_sha256'],'Saved initial/goal digests')
    return a, m, verify_arrays(a,m,role_map=role_map)
'''

def require(ok, message):
    if not ok: raise ValueError(message)
def write(path,value):
    with Path(path).open('xb') as f: f.write(json.dumps(value,sort_keys=True).encode()+b'\n')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ah(a):
    a=np.ascontiguousarray(a)
    return hashlib.sha256(str((a.shape,a.dtype.str)).encode()+a.tobytes()).digest()
def module(name,**attrs):
    m=ModuleType(name);m.__dict__.update(attrs);return m
class FakeAuthorization:
    def __init__(self,run,reference):
        self.run=run;self.ref=reference;self.approval={'package_sha256':'synthetic-only'}
    def reference(self,index,role): return self.ref

def main():
    result={'commit':'bb181cc6b6c60770898afacdcca3fb9e604c90c1','scope':'source-excerpt tests with artificial data/mocked runtime; no full-suite rerun', 'scheduler_submissions':0, 'research_model_loads':0,'physics_steps':0}
    with tempfile.TemporaryDirectory() as td:
        run=Path(td); package=run/'package';package.mkdir()
        (package/'run_worker.sh').write_bytes(b'#!/bin/bash\nexit 0\n')
        c=SimpleNamespace(ROOT=package,require=require,write=write,sha=sha,canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')).encode(),read=lambda p:json.loads(Path(p).read_text()),roles=lambda:{'mechanism_evaluation':[123]},Authorization=FakeAuthorization)
        command_ns={'c':c};exec(COMMAND_SOURCE,command_ns)
        checks=[]
        for gpu in (0,1):
            spec={'key':'synthetic-fit' if gpu==0 else 'synthetic-evaluation','ram_gib':8 if gpu==0 else 24,'seconds':7200 if gpu==0 else 300,'gpu':gpu}
            argv=command_ns['command'](spec,run/'approval.json',run)
            # Every option produced by this builder is a single --key=value or flag.
            operand=next(x for x in argv[1:] if not x.startswith('-'))
            checks.append({'gpu':gpu,'first_script_operand':operand,'intended_script':str(package/'run_worker.sh'),'operand_magic_hex':Path(operand).read_bytes()[:4].hex(),'intended_script_starts_hashbang':(package/'run_worker.sh').read_bytes().startswith(b'#!')})
            assert operand=='/bin/bash' and Path(operand).read_bytes()[:4]==b'\x7fELF'
        result['batch_script_operand_checks']=checks
        (run/'ALL-MODELS-FROZEN.json').write_text('{}')
        state=np.arange(7,dtype=np.float64);goal=state+1
        ref_path=run/'artificial-reference.npz';np.savez(ref_path,initial_request=state,states=np.tile(goal,(76,1)))
        ref={'file':str(ref_path)};auth=FakeAuthorization(run,ref)
        backend=SimpleNamespace(frozen_hash='synthetic-fingerprint',fingerprint=lambda:'synthetic-fingerprint',rollout=None,encodings=0,fingerprint_seconds=0)
        small=SimpleNamespace(params=[np.zeros(1)])
        def verify_arrays(a,m,role_map=None):return {'passed':True,'successes':[0]}
        reader_ns={'c':c,'np':np,'ah':ah,'verify_arrays':verify_arrays};exec(READER_SOURCE,reader_ns)
        def evaluate(factory,rollout,reference,control,selector,preserve=None):
            # Metadata keys supplied by the pinned episodes.evaluate return path.
            arrays={'requested_initial':state.copy(),'goal_state':goal.copy(),'initial_image':np.zeros((1,1,3),np.uint8),'goal_image':np.ones((1,1,3),np.uint8),'goal_latent':np.zeros(192)}
            meta={'reference':reference,'role':'final_development','kind':'evaluation','control':control,'branches':[{'success':False,'steps':150,'ledger':{}}],'wall_seconds':0.0}
            return arrays,meta
        def save(out,arrays,meta):
            np.savez(out/'evidence.npz',**arrays);write(out/'EVIDENCE.json',meta)
        def gate(torch,writer):
            h={'hostname':'gpu09.cluster'};writer(h);return h
        replacements={
            'torch':module('torch',set_num_threads=lambda x:None,cuda=SimpleNamespace(reset_peak_memory_stats=lambda:None,max_memory_allocated=lambda:0,max_memory_reserved=lambda:0)),
            'hardware':module('hardware',verify_device=gate),
            'models':module('models',check_freeze=lambda *a:{'synthetic':True},load_pair=lambda *a:(small,small)),
            'selector':module('selector',CommittedFeedbackSelector=lambda j,o:SimpleNamespace(joint=j,ordinary=o)),
            'bridge':module('bridge',load_backend=lambda *a:backend,source_factory=lambda *a:(None,ref,{'state':state,'goal_state':goal})),
            'episodes':module('episodes',evaluate=evaluate,save=save),
            'verify':module('verify',verify_arrays=verify_arrays,load_verify=reader_ns['load_verify']),
        }
        ev_ns={'c':c,'os':os,'io':io,'arrays_digest':lambda *a:'synthetic-array-digest'};exec(EVALUATION_SOURCE,ev_ns)
        metadata_tests=[]
        with patch.dict(sys.modules,replacements), patch.dict(os.environ,{'SLURM_JOB_NODELIST':'gpu09'}):
            for index,arm in enumerate(('static','committed_feedback','no_update','active','ordinary','early-replan')):
                out=run/arm;out.mkdir();spec={'reference':123,'control':arm,'pair':None if arm=='early-replan' else 0,'key':'synthetic-'+arm,'byte_cap':2_000_000}
                try: ev_ns['evaluation'](auth,spec,out)
                except KeyError as exc:
                    assert exc.args==('initial_sha256',)
                    metadata=json.loads((out/'EVIDENCE.json').read_text())
                    assert 'initial_sha256' not in metadata and 'goal_sha256' not in metadata
                    metadata_tests.append({'control':arm,'failure':repr(exc),'missing_keys':['initial_sha256','goal_sha256']})
                else:raise AssertionError('Expected absent-authentication-metadata failure')
            # Demonstrate the required two fields resolve THIS narrow reader-contract failure.
            original_eval=evaluate
            def complete_metadata(*a,**kw):
                arrays,meta=original_eval(*a,**kw)
                meta['initial_sha256']=ah(arrays['requested_initial']).hex();meta['goal_sha256']=ah(arrays['goal_state']).hex()
                return arrays,meta
            replacements['episodes'].evaluate=complete_metadata
            out=run/'metadata-repaired-control';out.mkdir()
            ev_ns['evaluation'](auth,{'reference':123,'control':'active','pair':0,'key':'synthetic-active','byte_cap':2_000_000},out)
        result['authenticated_reader_checks']=metadata_tests
        result['supplying_both_missing_fields_resolves_isolated_reader_failure']=True
        result['all_expected_probe_checks_passed']=True
    target=Path(__file__).with_name('PROBE-RESULTS.json');target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
