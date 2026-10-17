"""Exclusive actual POSIX early-leader-exit regression; no research execution."""
import base64,hashlib,json,sys
from .archive_v1 import canonical
from .cluster_cpu_test_v1 import PROGRAM as ORIGINAL_PROGRAM
from wm_diag0_rc1_grid_v1.common import ROOT,BASE,identity,write_new
from wm_diag0_native_v3.transport import ssh

BODY=r'''
 from wm_diag0_rc1_final_v1.cpu_process_v1 import run_child as old_run
 from wm_diag0_rc1_final_v1.cpu_process_v2 import run_child as new_run
 f=r/'fixtures';out=f/'out';out.mkdir();env=dict(os.environ)
 def state(meta):
  p=pathlib.Path('/proc')/str(meta['PID'])/'stat'
  if not p.exists():return 'PID absent'
  s=p.read_text().rsplit(')',1)[1].split()
  if s[19]!=meta['start_ticks']:return 'original start identity absent'
  return 'zombie, not live' if s[0]=='Z' else 'same PID/start_ticks still live'
 def fixture(name,run):
  meta=out/(name+'.json')
  code='import subprocess,sys,os,json,pathlib; g=subprocess.Popen([sys.executable,"-B","-c","import time;time.sleep(10)"]); s=pathlib.Path("/proc/"+str(g.pid)+"/stat").read_text().rsplit(")",1)[1].split(); own=pathlib.Path("/proc/self/stat").read_text().rsplit(")",1)[1].split(); pathlib.Path('+repr(str(meta))+').write_text(json.dumps({"PID":g.pid,"start_ticks":s[19],"leader_PID":os.getpid(),"leader_start_ticks":own[19],"child_PGID":os.getpgrp(),"grandchild_PGID":os.getpgid(g.pid)}))'
  end=time.monotonic()+.4
  try:run([sys.executable,'-B','-c',code],env,f/(name+'.log'),[out],40000000,100000,end,end+2.5)
  except TimeoutError:pass
  else:raise ValueError('expected inherited silent pipe timeout')
  if not meta.is_file():raise ValueError('artificial child did not reach owned fixture')
  z=json.loads(meta.read_text())
  if z['child_PGID']!=z['leader_PID'] or z['grandchild_PGID']!=z['child_PGID'] or z['child_PGID']==os.getpgrp():raise ValueError('only newly owned fixture process group')
  p=pathlib.Path('/proc')/str(z['leader_PID'])/'stat'
  if p.exists() and p.read_text().rsplit(')',1)[1].split()[19]==z['leader_start_ticks']:raise ValueError('fixture leader must already have exited and been reaped')
  return z
 old=fixture('legacy-early-leader',old_run)
 if state(old)!='same PID/start_ticks still live':raise ValueError('diagnosed V1 condition not reproduced')
 write('V1-EARLY-LEADER-FAULT.json',dict(old,disposition=state(old),research_fault=False))
 # Cleanup ONLY this synthetic group after independently checking its actual
 # PID/start identity, UID and group. No unrelated PID/group is signalled.
 p=pathlib.Path('/proc')/str(old['PID'])
 if state(old)!='same PID/start_ticks still live' or p.stat().st_uid!=os.getuid() or os.getpgid(old['PID'])!=old['child_PGID']:raise ValueError('owned fixture cleanup authentication')
 os.killpg(old['child_PGID'],signal.SIGKILL)
 new=fixture('v2-early-leader',new_run)
 if state(new)=='same PID/start_ticks still live':raise ValueError('V2 still leaked same owned descendant')
 if state(old)=='same PID/start_ticks still live':raise ValueError('old synthetic fault cleanup failed')
 write('OWNED-GROUP-READBACK.json',{'old':dict(old,disposition=state(old)),'new':dict(new,disposition=state(new)),'unrelated_processes_signalled':False})
 logical=sum(p.lstat().st_size for p in r.rglob('*') if not p.is_dir())
 if logical>1000000:raise ValueError('one-MB additional artificial root reservation')
 result={'status':'LINUX_ACTUAL_EARLY_EXIT_DESCENDANT_FAULT_REPRODUCED_AND_V2_FIXED','source':{n:x['identity'] for n,x in data['source'].items()},
  'python':sys.version,'affinity_cpus':len(os.sched_getaffinity(0)),'RAM_address_space_limit_bytes':8589934592,'CPU_seconds_limit':15,'wall_alarm_seconds':20,
  'logical_retained_bytes_before_final_receipt':logical,'additional_root_reserved_bytes':1000000,'V1_fault_reproduced':True,
  'old_synthetic_fault_cleanup_disposition':state(old),'V2_descendant_final_disposition':state(new),'old_and_new_PID_start_ticks_readback':{'old':old,'new':new},
  'unrelated_processes_signalled':False,'scheduler_calls':0,'model_simulator_fit_source_generation_calls':0,
  'research_artifacts_or_values_read':False,'actual_final_CPU_supervisor_or_contract_ready':False,'final_gate_ready':False}
 write('RESULT.json',result);print(json.dumps(result))
'''


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive artificial label')
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v1-20261016';out=doc/('ARTIFICIAL-CLUSTER-CPU-V2-'+label+'.json')
    if out.exists():raise FileExistsError('no repeated completed artificial operation')
    names=('__init__.py','inventory.py','archive_v1.py','cpu_process_v1.py','cpu_process_v2.py')
    blobs={'wm_diag0_rc1_final_v1/'+n:(ROOT/'wm_diag0_rc1_final_v1'/n).read_bytes() for n in names}
    data={'source':{n:{'identity':{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},'base64':base64.b64encode(b).decode()} for n,b in blobs.items()}}
    prefix=ORIGINAL_PROGRAM.split(' from wm_diag0_rc1_final_v1.cpu_process_v1 import run_child,artifact_bytes')[0]
    ending=ORIGINAL_PROGRAM[ORIGINAL_PROGRAM.rfind('except BaseException as exc:'):]
    program=prefix+BODY+ending;run=BASE+'/campaign-v4-rc1-final-v1-artificial-'+label
    write_new(doc/('ARTIFICIAL-CLUSTER-CPU-V2-'+label+'.started.json'),{'run':run,'source':{n:x['identity'] for n,x in data['source'].items()},
        'program_identity':{'bytes':len(program.encode()),'sha256':hashlib.sha256(program.encode()).hexdigest()},'additional_root_reserved_bytes':1000000,'research_allowed':False})
    result=ssh('RUN='+repr(run)+'\nALLOWED='+repr(sorted(blobs))+'\n'+program,canonical(data),timeout=25)
    write_new(out,dict(result,run=run,local_entry_source=identity(__file__),preamble_source=identity(ROOT/'wm_diag0_rc1_final_v1/cluster_cpu_test_v1.py')));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
