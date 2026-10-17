"""One exclusive POSIX CPU-process interface fixture; no scheduler/research IO."""
import base64,hashlib,json,sys
from .archive_v1 import canonical
from wm_diag0_rc1_grid_v1.common import ROOT,BASE,identity,write_new
from wm_diag0_native_v3.transport import ssh

PROGRAM=r'''
import base64,hashlib,json,os,pathlib,resource,signal,sys,time
signal.alarm(20)
resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592));resource.setrlimit(resource.RLIMIT_CPU,(15,15))
resource.setrlimit(resource.RLIMIT_FSIZE,(1000000,1000000));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['CUDA_VISIBLE_DEVICES']=''
r=pathlib.Path(RUN);data=json.load(sys.stdin)
if set(data['source'])!=set(ALLOWED) or sum(x['identity']['bytes'] for x in data['source'].values())>100000:raise ValueError('exact small artificial source closure')
r.mkdir(exist_ok=False);(r/'source').mkdir();(r/'controls').mkdir();(r/'fixtures').mkdir()
def write(name,row):
 with (r/'controls'/name).open('x') as f:json.dump(row,f,sort_keys=True)
write('STARTED.json',{'phase':'ARTIFICIAL_POSIX_CPU_PROCESS','source':{n:x['identity'] for n,x in data['source'].items()},'research_artifacts_allowed':False})
try:
 for n,x in data['source'].items():
  if n not in ALLOWED:raise ValueError('exact reviewed code members')
  raw=base64.b64decode(x['base64'])
  if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=x['identity']:raise ValueError('source identity')
  p=r/'source'/n;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(raw)
  p.chmod(0o444)
 for p in sorted((r/'source').rglob('*'),reverse=True):
  if p.is_dir():p.chmod(0o555)
 (r/'source').chmod(0o555);sys.path.insert(0,str(r/'source'))
 from wm_diag0_rc1_final_v1.cpu_process_v1 import run_child,artifact_bytes
 f=r/'fixtures';out=f/'out';out.mkdir();env=dict(os.environ)
 def run(name,code,cap=100000,seconds=3,artifact_cap=40000000):
  end=time.monotonic()+seconds
  return run_child([sys.executable,'-B','-c',code],env,f/(name+'.log'),[out],artifact_cap,cap,end,end+2.5)
 result=run('ok','print("artificial Linux CPU child")')
 if result['returncode'] or (f/'ok.log').read_text().strip()!='artificial Linux CPU child':raise ValueError('POSIX child roundtrip')
 try:run('loglimit','print("x"*64)',cap=8)
 except ValueError:pass
 else:raise ValueError('log overflow not rejected')
 if (f/'loglimit.log').stat().st_size>8:raise ValueError('hard log byte bound')
 meta=out/'owned-grandchild.json'
 code='import subprocess,sys,os,json,pathlib,time; g=subprocess.Popen([sys.executable,"-B","-c","import time;time.sleep(10)"]); s=pathlib.Path("/proc/"+str(g.pid)+"/stat").read_text().rsplit(")",1)[1].split(); pathlib.Path('+repr(str(meta))+').write_text(json.dumps({"PID":g.pid,"start_ticks":s[19],"child_PGID":os.getpgrp(),"grandchild_PGID":os.getpgid(g.pid)})); time.sleep(10)'
 began=time.monotonic()
 try:run('timeout-owned-group',code,seconds=.4)
 except TimeoutError:pass
 else:raise ValueError('silent owned group not timed out')
 if time.monotonic()-began>2.5 or not meta.is_file():raise ValueError('bounded timeout fixture must reach its own synthetic child')
 record=json.loads(meta.read_text())
 if record['child_PGID']!=record['grandchild_PGID'] or record['child_PGID']==os.getpgrp():raise ValueError('fixture only targets its newly owned process group')
 p=pathlib.Path('/proc')/str(record['PID'])/'stat'
 if p.exists():
  s=p.read_text().rsplit(')',1)[1].split()
  if s[19]==record['start_ticks'] and s[0]!='Z':raise ValueError('same owned grandchild remains live')
  disposition='same-start-ticks zombie, not live' if s[19]==record['start_ticks'] else 'PID reused; original start identity absent'
 else:disposition='PID absent'
 write('OWNED-GROUP-READBACK.json',dict(record,disposition=disposition,unrelated_processes_signalled=False))
 logical=sum(p.lstat().st_size for p in r.rglob('*') if not p.is_dir())
 if logical>1000000:raise ValueError('one-MB additional artificial lineage reservation')
 result={'status':'LINUX_ARTIFICIAL_CPU_PROCESS_AND_OWNED_GROUP_TIMEOUT_PASSED','source':{n:x['identity'] for n,x in data['source'].items()},
  'python':sys.version,'affinity_cpus':len(os.sched_getaffinity(0)),'RAM_address_space_limit_bytes':8589934592,
  'CPU_seconds_limit':15,'wall_alarm_seconds':20,'logical_retained_bytes_before_final_receipt':logical,'additional_root_reserved_bytes':1000000,
  'roundtrip':True,'hard_log_cap_rejection':True,'silent_child_and_owned_grandchild_timeout':True,'grandchild_final_disposition':disposition,
  'owned_grandchild_PID_and_start_ticks_readback':record,'scheduler_calls':0,'model_simulator_fit_source_generation_calls':0,
  'research_artifacts_or_values_read':False,'actual_final_CPU_supervisor_or_contract_ready':False,'final_gate_ready':False}
 write('RESULT.json',result);print(json.dumps(result))
except BaseException as exc:
 write('ERROR.json',{'error':repr(exc),'research_compute_submitted':False,'all_source_fixtures_logs_and_partials_retained':True});raise
'''


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive new artificial label')
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v1-20261016';out=doc/('ARTIFICIAL-CLUSTER-CPU-'+label+'.json')
    if out.exists():raise FileExistsError('no repeated completed test')
    names=('__init__.py','inventory.py','archive_v1.py','cpu_process_v1.py')
    blobs={'wm_diag0_rc1_final_v1/'+n:(ROOT/'wm_diag0_rc1_final_v1'/n).read_bytes() for n in names}
    data={'source':{n:{'identity':{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},'base64':base64.b64encode(b).decode()} for n,b in blobs.items()}}
    run=BASE+'/campaign-v4-rc1-final-v1-artificial-'+label
    write_new(doc/('ARTIFICIAL-CLUSTER-CPU-'+label+'.started.json'),{'run':run,'source':{n:x['identity'] for n,x in data['source'].items()},'additional_root_reserved_bytes':1000000,'research_allowed':False})
    result=ssh('RUN='+repr(run)+'\nALLOWED='+repr(sorted(blobs))+'\n'+PROGRAM,canonical(data),timeout=25)
    write_new(out,dict(result,run=run,local_entry_source=identity(__file__)));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
