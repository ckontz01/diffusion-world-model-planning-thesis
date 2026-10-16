"""New tiny owned-process regression, no research objects or allocation."""
import inspect,json
from .common import *
from .transport import call
from .supervisor import stop_owned

def program():
    code='import os,pathlib,stat,subprocess,signal,time,json,hashlib,resource\nfrom pathlib import Path\n'
    code+="os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]));resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592));resource.setrlimit(resource.RLIMIT_CPU,(15,15));resource.setrlimit(resource.RLIMIT_FSIZE,(1000000,1000000))\n"
    code+=inspect.getsource(sampled_bytes)+'\n'+inspect.getsource(stop_owned)+'\n'
    code+='ROOT='+repr(RUN+'-artificial-ONE')+'\n'
    code+=r'''
root=Path(ROOT);root.mkdir(exist_ok=False);tmp=root/'tmp';tmp.mkdir()
source=Path(__file__) if '__file__' in globals() else None
with (root/'GUARD-SOURCE.txt').open('x') as f:f.write(SOURCE)
child="import os,sys,time; p=os.fork(); print(p,flush=True) if p else None; sys.exit(0) if p else time.sleep(10)"
proc=subprocess.Popen(['python3','-B','-c',child],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
pid=int(proc.stdout.readline().strip());proc.wait(timeout=3)
path=Path('/proc')/str(pid)/'stat';before=path.read_text().rsplit(')',1)[1].split()
if int(before[2])!=proc.pid or path.stat().st_uid!=os.getuid():raise ValueError('only owned synthetic descendant')
ticks=before[19];stop_owned(proc);time.sleep(.1)
after=path.read_text().rsplit(')',1)[1].split() if path.exists() else None
if after and after[19]==ticks and after[0]!='Z':raise RuntimeError('owned synthetic descendant remained running')
producer="import pathlib,sys; p=pathlib.Path(sys.argv[1]); [( (p/str(i)).write_bytes(b'x'*128),(p/str(i)).unlink()) for i in range(1000)]"
proc=subprocess.Popen(['python3','-B','-c',producer,str(tmp)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
samples=0
while proc.poll() is None:
 sampled_bytes(tmp);samples+=1
proc.wait(timeout=2)
if proc.returncode:raise RuntimeError('tiny transient producer')
stop_owned(proc)
z={'status':'NEW_LINUX_MUTABLE_TMP_AND_EARLY_LEADER_CLEANUP_PASSED','temporary_race_samples':samples,
 'owned_descendant_PID':pid,'owned_descendant_start_ticks':ticks,'after_state':'absent' if after is None else after[0],
 'research_allocations_scheduler_model_physics_calls':0,'scientific_payloads_read':False,'root':str(root)}
with (root/'RESULT.json').open('x') as f:json.dump(z,f,sort_keys=True)
print(json.dumps(z))
'''
    return 'SOURCE='+repr(code)+'\n'+code

def main():
    z=call('LINUXTEST001',program(),seconds=40)
    if z['status']!='NEW_LINUX_MUTABLE_TMP_AND_EARLY_LEADER_CLEANUP_PASSED':raise ValueError('actual Linux guard test')
    print(json.dumps(z))

if __name__=='__main__':main()
