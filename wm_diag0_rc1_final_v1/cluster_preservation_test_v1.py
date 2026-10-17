"""One exclusive Linux artificial codec/interface test, no scheduler/research IO."""
import base64,json,sys
from .archive_v1 import canonical
from wm_diag0_rc1_grid_v1.common import ROOT,BASE,identity,write_new
from wm_diag0_native_v3.transport import ssh

STUB='''import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def identity(p):
 b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write_new(p,x):
 with Path(p).open('x') as f:json.dump(x,f,sort_keys=True)
'''

PROGRAM=r'''
import base64,contextlib,hashlib,io,json,os,pathlib,resource,signal,sys,time
signal.alarm(20)
resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592))
resource.setrlimit(resource.RLIMIT_CPU,(15,15))
resource.setrlimit(resource.RLIMIT_FSIZE,(1000000,1000000))
resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
allowed=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,set(allowed[:4]))
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['CUDA_VISIBLE_DEVICES']=''
r=pathlib.Path(RUN);data=json.load(sys.stdin)
if len(data['source'])>10 or sum(x['identity']['bytes'] for x in data['source'].values())>100000:raise ValueError('small explicit artificial source closure')
r.mkdir(exist_ok=False);(r/'source').mkdir();(r/'controls').mkdir();(r/'fixtures').mkdir()
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(name,x):
 with (r/'controls'/name).open('x') as f:json.dump(x,f,sort_keys=True)
write('STARTED.json',{'phase':'ARTIFICIAL_PRESERVATION_CODEC','research_artifacts_allowed':False,'source':{n:x['identity'] for n,x in data['source'].items()}})
try:
 for name,x in data['source'].items():
  if name not in ALLOWED or '..' in name.split('/') or name.startswith('/'):raise ValueError('exact artificial code allowlist')
  raw=base64.b64decode(x['base64'])
  if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=x['identity']:raise ValueError('staged source identity')
  p=r/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(raw)
  p.chmod(0o444)
 for p in sorted((r/'source').rglob('*'),reverse=True):
  if p.is_dir():p.chmod(0o555)
 (r/'source').chmod(0o555);sys.path.insert(0,str(r/'source'))
 from wm_diag0_rc1_final_v1.inventory import plan
 from wm_diag0_rc1_final_v1.archive_v1 import create
 from wm_diag0_rc1_final_v1.archive_verify_v1 import verify,portable_plan
 from wm_diag0_rc1_final_v1.postarchive_v1 import build,verify as side_verify,digest
 fixture=r/'fixtures';base=fixture/'study';(base/'old').mkdir(parents=True)
 raw=b'\x00\xff\x80artificial Linux bytes\x00';(base/'old/tensor.bin').write_bytes(raw)
 (base/'old/STOP.json').write_bytes(b'{"artificial_failure":"retained"}')
 (base/'old/alias').symlink_to('tensor.bin')
 planned=plan(base,['old'],{},{'study/old/alias':'tensor.bin'})
 binding={'final_contract_sha256':'0'*64,'root_paths':{'study/old':str(base/'old')}}
 deadline=time.monotonic()+10;archive=fixture/'artificial.tar';made=create(planned,archive,binding,deadline)
 checked=verify(archive,planned,binding,deadline,expected_whole=made['whole'],expected_manifest=made['manifest'])
 portable=portable_plan(planned,checked);verify(archive,portable,binding,deadline,False,made['whole'],made['manifest'])
 if checked['regular_payload_members']!=2 or checked['logical_members']!=3:raise ValueError('real POSIX relative alias preserved inertly, not followed')
 post=fixture/'post';post.mkdir();(post/'RESULT.json').write_bytes(b'{"artificial_terminal":"ACCEPTED"}')
 expected={'RESULT.json':ident(post/'RESULT.json')}
 sb={'final_contract_sha256':'0'*64,'archive_whole':made['whole'],'archive_manifest':made['manifest'],'analysis_output_seal':ident(post/'RESULT.json')}
 rawside=build(post,expected,sb,'TERMINAL_CPU',None,deadline);side_verify(rawside,expected,sb,'TERMINAL_CPU',None,digest(rawside),deadline)
 # Harmless changed-original rejection. No real checkpoint or result is opened.
 (base/'old/tensor.bin').write_bytes(b'changed artificial bytes')
 try:verify(archive,planned,binding,deadline)
 except ValueError:changed_rejected=True
 else:raise ValueError('required independent original change rejection absent')
 logical=sum(p.lstat().st_size for p in r.rglob('*') if not p.is_dir())
 if logical>1000000:raise ValueError('one-MB additional artificial lineage reservation')
 result={'status':'LINUX_ARTIFICIAL_PRESERVATION_CODEC_AND_POSIX_ALIAS_PASSED','source':{n:x['identity'] for n,x in data['source'].items()},
 'python':sys.version,'affinity_cpus':len(os.sched_getaffinity(0)),'RAM_limit':8589934592,'wall_alarm_seconds':20,'CPU_seconds_limit':15,
 'logical_retained_bytes':logical,'additional_root_reserved_bytes':1000000,'archive_whole':made['whole'],'manifest':made['manifest'],
 'actual_POSIX_relative_alias_roundtrip':True,'originals_independently_reread':True,'changed_original_rejected':changed_rejected,
 'artificial_control_sidecar_verified':True,'source_common_stub_scope':'path/identity/exclusive-json helpers only; no scientific/runtime authentication',
 'scheduler_calls':0,'research_artifacts_or_models_or_results_read':False,'scientific_or_simulator_calls':0,'final_gate_ready':False}
 write('RESULT.json',result);print(json.dumps(result))
except BaseException as exc:
 write('ERROR.json',{'error':repr(exc),'research_compute_submitted':False,'all_source_fixtures_and_partials_retained':True});raise
'''


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive artificial label')
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v1-20261016';out=doc/('ARTIFICIAL-CLUSTER-'+label+'.json')
    if out.exists():raise FileExistsError('no repeated completed artificial operation')
    names=('__init__.py','inventory.py','archive_v1.py','archive_verify_v1.py','postarchive_v1.py')
    blobs={'wm_diag0_rc1_final_v1/'+n:(ROOT/'wm_diag0_rc1_final_v1'/n).read_bytes() for n in names}
    blobs['wm_diag0_rc1_grid_v1/__init__.py']=b'';blobs['wm_diag0_rc1_grid_v1/common.py']=STUB.encode()
    data={'source':{n:{'identity':{'bytes':len(b),'sha256':__import__('hashlib').sha256(b).hexdigest()},'base64':base64.b64encode(b).decode()} for n,b in blobs.items()}}
    run=BASE+'/campaign-v4-rc1-final-v1-artificial-'+label
    write_new(doc/('ARTIFICIAL-CLUSTER-'+label+'.started.json'),{'run':run,'source':{n:x['identity'] for n,x in data['source'].items()},'additional_root_reserved_bytes':1000000,'research_allowed':False})
    result=ssh('RUN='+repr(run)+'\nALLOWED='+repr(sorted(blobs))+'\n'+PROGRAM,canonical(data),timeout=25)
    write_new(out,dict(result,run=run,local_entry_source=identity(__file__)));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
