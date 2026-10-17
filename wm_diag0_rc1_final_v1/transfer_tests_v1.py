"""Artificial control/transfer tests; no cluster, D: access, or real archive."""
import io,json,os,sys,tempfile,threading,time
from pathlib import Path
from . import postarchive_v1 as side
from . import native_transfer_v1 as transfer
from .inventory import plan
from .archive_v1 import create,canonical
from .archive_verify_v1 import verify,portable_plan
from wm_diag0_rc1_grid_v1.common import ROOT,identity,write_new


def reject(fn,kind=Exception):
    try:fn()
    except kind:return
    raise AssertionError('required rejection absent')


class OwnedArtificialProcess:
    def __init__(self,raw=b'',code=0,blocked=False):
        self.returncode=None;self.code=code;self.stopped=threading.Event();self.killed=False
        if blocked:
            owner=self
            class Silent:
                def read(self,n):owner.stopped.wait(1);return b''
            self.stdout=Silent()
        else:self.stdout=io.BytesIO(raw)
    def wait(self,timeout):self.returncode=self.code if not self.killed else -9;return self.returncode
    def poll(self):return self.returncode
    def kill(self):self.killed=True;self.returncode=-9;self.stopped.set()


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive artificial receipt label')
    deadline=lambda:time.monotonic()+10
    with tempfile.TemporaryDirectory(prefix='wm-rc1-control-transfer-artificial-') as tmp:
        root=Path(tmp);controls=root/'post-controls';controls.mkdir()
        rows={'CPU-SCHEDULER.txt':b'fake-cpu|COMPLETED|0:0|4',
              'RESULT.json':b'{"status":"ACCEPTED","scientific_values_emitted":false}'}
        for n,b in rows.items():(controls/n).write_bytes(b)
        expected={n:side.digest(b) for n,b in rows.items()}
        binding={'final_contract_sha256':'0'*64,'archive_whole':{'bytes':100,'sha256':'1'*64},
                 'archive_manifest':{'bytes':10,'sha256':'2'*64},'analysis_output_seal':{'bytes':20,'sha256':'3'*64}}
        raw=side.build(controls,expected,binding,'TERMINAL_CPU',None,deadline());mid=side.digest(raw)
        proof=side.verify(raw,expected,binding,'TERMINAL_CPU',None,mid,deadline())
        if proof['controls_verified']!=2 or proof['decoded_controls_executed']!=0:raise AssertionError('every inert original control byte')
        side_path=root/'cpu-sidecar.json';side.write_exclusive(side_path,raw,deadline(),controls)
        reject(lambda:side.write_exclusive(side_path,raw,deadline(),controls),FileExistsError)
        reject(lambda:side.write_exclusive(controls/'recursive.json',raw,deadline(),controls),ValueError)
        reject(lambda:side.build(controls,expected,binding,'TERMINAL_CPU',None,time.monotonic()-1),TimeoutError)
        reject(lambda:side.verify(raw,expected,binding,'SSD_TRANSFER',mid,mid,deadline()),ValueError)
        raw2=side.build(controls,expected,binding,'SSD_TRANSFER',mid,deadline());id2=side.digest(raw2)
        side.verify(raw2,expected,binding,'SSD_TRANSFER',mid,id2,deadline())
        reject(lambda:side.verify(raw2,expected,binding,'SSD_TRANSFER',dict(mid,sha256='f'*64),id2,deadline()),ValueError)
        reject(lambda:side.verify(raw,expected,binding,'TERMINAL_CPU',None,dict(mid,sha256='f'*64),deadline()),ValueError)
        changed=json.loads(raw);changed['controls']['RESULT.json']['base64']='ZXh0cmE='
        forged=canonical(changed)
        reject(lambda:side.verify(forged,expected,binding,'TERMINAL_CPU',None,side.digest(forged),deadline()),ValueError)
        changed=json.loads(raw);changed['extra']='not allowed';forged=canonical(changed)
        reject(lambda:side.verify(forged,expected,binding,'TERMINAL_CPU',None,side.digest(forged),deadline()),ValueError)
        reject(lambda:side.build(controls,dict(expected,**{'../escape':side.digest(b'')}),binding,'TERMINAL_CPU',None,deadline()),ValueError)
        reject(lambda:side.build(controls,{'RESULT.json':expected['RESULT.json']},binding,'TERMINAL_CPU',None,deadline()),ValueError)
        (controls/'unknown.partial').write_bytes(b'preserve unknown failed evidence; do not skip')
        reject(lambda:side.build(controls,expected,binding,'TERMINAL_CPU',None,deadline()),ValueError)
        (controls/'unknown.partial').unlink() # synthetic fixture owned by test
        (controls/'RESULT.json').write_bytes(b'changed synthetic control')
        reject(lambda:side.build(controls,expected,binding,'TERMINAL_CPU',None,deadline()),ValueError)
        (controls/'RESULT.json').write_bytes(rows['RESULT.json'])
        # No external command is launched. All factories return this explicit
        # small owned fake process; timeout fixture waits only on its own Event.
        payload=b'\x00\xffartificial transfer\x00';want=side.digest(payload);partial=root/'copy.partial'
        copied=transfer.stream_once(lambda:OwnedArtificialProcess(payload),partial,want,deadline())
        if partial.read_bytes()!=payload or copied['whole']!=want:raise AssertionError('exact byte transfer')
        calls=[]
        reject(lambda:transfer.stream_once(lambda:calls.append(1),partial,want,deadline()),FileExistsError)
        if calls:raise AssertionError('existing partial refused before transport launch')
        for n,data,code in (('short',payload[:-1],0),('extra',payload+b'x',0),('wrong',b'x'*len(payload),0),('exit',payload,1)):
            p=root/(n+'.partial');reject(lambda:transfer.stream_once(lambda:OwnedArtificialProcess(data,code),p,want,deadline()),ValueError)
            if not p.exists():raise AssertionError('failed partial removed')
        silent=OwnedArtificialProcess(blocked=True);p=root/'silent.partial';began=time.monotonic()
        reject(lambda:transfer.stream_once(lambda:silent,p,want,time.monotonic()+.07),TimeoutError)
        if not silent.killed or not p.exists() or time.monotonic()-began>1:raise AssertionError('silent-pipe deadline and owned-only cleanup')
        remote='/lustreFS/data/superworld/ckontzias/thesis/experiments/artificial/preservation/final-study.tar'
        cmd=transfer.transport_command(remote,remote,10)
        if cmd[:7]!=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout'] or cmd[-2]!='prometheus':raise AssertionError('existing configured transport only')
        reject(lambda:transfer.transport_command(remote,remote+'x',10),ValueError)
        reject(lambda:transfer.transport_command(remote,remote,7201),ValueError)
        # Exercise actual native temporary-file promotion only after the new
        # independent archive/member verifier, never the obsolete finalizer.
        study=root/'study';study.mkdir();(study/'fixture').write_bytes(payload)
        planned=plan(study,[],{'fixture-root':study},{}) if False else None
        base=root/'canonical';(base/'one').mkdir(parents=True);(base/'one/fixture').write_bytes(payload)
        planned=plan(base,['one'],{},{});archive_binding={'final_contract_sha256':'0'*64,'root_paths':{'study/one':str(base/'one')}}
        archive=root/'fake-source.tar';created=create(planned,archive,archive_binding,deadline())
        checked=verify(archive,planned,archive_binding,deadline());portable=portable_plan(planned,checked)
        temp=root/'final.tar.partial';target=root/'final.tar'
        transfer.stream_once(lambda:OwnedArtificialProcess(archive.read_bytes()),temp,created['whole'],deadline())
        if os.name=='nt':
            verified=transfer.verify_and_promote(temp,target,portable,archive_binding,created['whole'],created['manifest'],deadline())
            if temp.exists() or not target.is_file() or verified['whole']!=created['whole']:raise AssertionError('native rename only after whole/every-member gate')
            reject(lambda:transfer.verify_and_promote(archive,target,portable,archive_binding,created['whole'],created['manifest'],deadline()),FileExistsError)
    folder=ROOT/'wm_diag0_rc1_final_v1';sources={}
    for n in ('postarchive_v1.py','native_transfer_v1.py','transfer_tests_v1.py'):
        compile((folder/n).read_bytes(),n,'exec');sources[n]=identity(folder/n)
    import ast
    for n in sources:ast.parse((folder/n).read_text(),feature_version=(3,6))
    write_new(ROOT/('docs/world-model-diagnostic-rc1-final-v1-20261016/ARTIFICIAL-TRANSFER-'+label+'.json'),{
        'status':'PASSED','source':sources,'platform':os.name,'research_artifacts_or_results_read':False,
        'cluster_network_or_designated_SSD_accessed':False,'external_processes_launched':0,'research_calls':0,
        'checks':['exact every-control byte sidecar','external binding and predecessor chain','unknown/missing/changed/extra/forged/unsafe control rejection','sidecar recursion/existing target/deadline rejection','exact stream bytes and bounded queue','short/extra/corrupt/nonzero transfer rejection with retained partial','existing partial refused before transport factory','silent source deadline and owned transport cleanup','configured route/path/time command validation without launch','native temporary-file whole/every-member validation before nonoverwriting rename'],
        'actual_terminal_CPU_authentication_implemented':False,'actual_runtime_alias_root_binding_completed':False,
        'native_designated_SSD_transfer_executed':False,'actual_final_command_or_contract_ready':False,'final_gate_ready':False})
    print(json.dumps({'status':'ARTIFICIAL_POSTARCHIVE_AND_NATIVE_TRANSFER_PRIMITIVES_PASSED','research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
