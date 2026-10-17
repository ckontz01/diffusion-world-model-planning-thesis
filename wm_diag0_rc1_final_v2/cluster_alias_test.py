"""One exclusive bounded POSIX alias fixture; no scheduler/research access."""
import ast,base64,hashlib,json,shlex,subprocess
from wm_diag0_rc1_completion_v1.common import ROOT,write_new,identity
DOC=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
REMOTE='/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/campaign-v4-rc1-final-v2-artificial-ONE'
NAMES=('wm_diag0_rc1_final_v1/__init__.py','wm_diag0_rc1_final_v1/inventory.py',
       'wm_diag0_rc1_final_v2/__init__.py','wm_diag0_rc1_final_v2/inventory.py','wm_diag0_rc1_final_v2/inventory_v3.py',
       'wm_diag0_rc1_final_v2/archive_v2.py','wm_diag0_rc1_final_v2/archive_verify_v2.py')

CODE=r'''
import base64,hashlib,json,os,pathlib,resource,signal,sys,time
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592));resource.setrlimit(resource.RLIMIT_CPU,(15,15));signal.alarm(20)
r=pathlib.Path(REMOTE)
if r.exists():raise FileExistsError('exclusive artificial lineage, no retry or overwrite')
data=json.load(sys.stdin)
if set(data)!=set(NAMES):raise ValueError('exact reviewed fixture sources')
decoded={n:base64.b64decode(b) for n,b in data.items()}
if sum(map(len,decoded.values()))>100000 or any(len(b)>1000000 for b in decoded.values()):raise ValueError('small fixed artificial source bounds')
r.mkdir();(r/'source').mkdir();(r/'fixtures').mkdir();(r/'controls').mkdir()
def write(p,x):
 raw=json.dumps(x,sort_keys=True).encode()
 if len(raw)>1000000:raise ValueError('individual compact control bound')
 with p.open('xb') as f:f.write(raw)
write(r/'controls/STARTED.json',{'scope':'synthetic POSIX aliases only','source':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in decoded.items()},'research_calls':0,'scheduler_calls':0})
for n,b in decoded.items():
 p=r/'source'/n;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
 p.chmod(0o444)
sys.path.insert(0,str(r/'source'))
from wm_diag0_rc1_final_v2.inventory_v3 import plan
from wm_diag0_rc1_final_v2.archive_v2 import create
from wm_diag0_rc1_final_v2.archive_verify_v2 import verify,portable_plan
f=r/'fixtures';study=f/'study';(study/'old').mkdir(parents=True);(study/'new').mkdir()
(study/'old/STOP.json').write_bytes(b'old STOP preserved');(study/'new/failure.partial').write_bytes(b'partial preserved')
runtime=f/'runtime';(runtime/'bin').mkdir(parents=True);(runtime/'lib').mkdir();(runtime/'lib/payload').write_bytes(b'artificial payload')
(runtime/'bin/python').symlink_to('/opt/conda/bin/python');(runtime/'bin/python3').symlink_to('python')
(runtime/'lib64').symlink_to('lib',target_is_directory=True);(runtime/'up').symlink_to('../not-read')
(f/'not-read').write_bytes(b'OUTSIDE-TARGET-MUST-NOT-BE-ARCHIVED')
aliases={'runtime/bin/python':'/opt/conda/bin/python','runtime/bin/python3':'python','runtime/lib64':'lib','runtime/up':'../not-read'}
inventory=plan(study,['old','new'],{'runtime':runtime},aliases)
if set(n for n,x in inventory['members'].items() if x['type']=='symlink')!=set(aliases):raise ValueError('exact approved inert alias set')
if any(n.startswith('runtime/lib64/') for n in inventory['members']):raise ValueError('directory alias followed')
if inventory['logical_payload_bytes_no_discounts']!=len(b'old STOP preserved')+len(b'partial preserved')+len(b'artificial payload'):raise ValueError('logical regular copy count')
binding={'root_paths':{'study/old':str(study/'old'),'study/new':str(study/'new'),'runtime':str(runtime)},'final_contract_sha256':'c'*64}
archive=f/'artificial-inert.tar';made=create(inventory,archive,binding,time.monotonic()+5)
proof=verify(archive,inventory,binding,time.monotonic()+5,expected_whole=made['whole'],expected_manifest=made['manifest'])
portable=portable_plan(inventory,proof);verify(archive,portable,binding,time.monotonic()+5,check_sources=False,expected_whole=made['whole'],expected_manifest=made['manifest'])
if b'OUTSIDE-TARGET-MUST-NOT-BE-ARCHIVED' in archive.read_bytes():raise ValueError('outside alias target contents accessed')
try:plan(study,['old','new'],{'runtime':runtime},dict(aliases,**{'runtime/up':'changed'}))
except ValueError:pass
else:raise ValueError('changed approved alias accepted')
write(r/'controls/ROUNDTRIP.json',{'whole':made['whole'],'manifest':made['manifest'],'approved_alias_literals':aliases,'directory_alias_followed':False,'files_extracted_or_executed':0})
logical=0;count=0
pending=[r]
while pending:
 d=pending.pop()
 with os.scandir(str(d)) as scan:
  for entry in scan:
   s=entry.stat(follow_symlinks=False)
   if __import__('stat').S_ISDIR(s.st_mode):pending.append(pathlib.Path(entry.path))
   elif __import__('stat').S_ISREG(s.st_mode):logical+=s.st_size;count+=1
if logical>1000000:raise ValueError('whole synthetic lineage reserve')
result={'status':'ACTUAL_POSIX_INERT_ABSOLUTE_PARENT_CHAIN_DIRECTORY_ALIAS_ROUNDTRIP_PASSED','root':str(r),'logical_regular_bytes_before_final_receipt':logical,'regular_members_before_final_receipt':count,
 'aliases':4,'originals_independently_reread':True,'portable_readback':True,'directory_alias_followed':False,'outside_alias_target_payload_read_or_archived':False,
 'research_calls':0,'scheduler_calls':0,'model_simulator_fit_source_generation_calls':0,'unrelated_processes_signalled':False,'whole_root_future_reservation_bytes':1000000,'final_gate_ready':False}
write(r/'controls/RESULT.json',result);print(json.dumps(result))
'''

def main():
    DOC.mkdir(exist_ok=True);started=DOC/'ARTIFICIAL-POSIX-001.started.json'
    if started.exists() or (DOC/'ARTIFICIAL-POSIX-001.json').exists():raise FileExistsError('no repeated/ambiguous artificial lineage')
    source='REMOTE='+repr(REMOTE)+'\nNAMES='+repr(NAMES)+'\n'+CODE;ast.parse(source,feature_version=(3,6))
    data={n:base64.b64encode((ROOT/n).read_bytes()).decode() for n in NAMES}
    write_new(started,{'remote':REMOTE,'source':identity(__file__),'staged_sources':{n:identity(ROOT/n) for n in NAMES},'whole_root_future_reservation_bytes':1000000})
    encoded=base64.b64encode(source.encode()).decode();remote='timeout --kill-after=1s 25s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    cmd=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','35s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','prometheus',remote]
    p=subprocess.run(cmd,input=json.dumps(data).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=38)
    if p.returncode:raise RuntimeError('exclusive artificial fixture failed; preserve all partials, no retry: '+p.stderr.decode(errors='replace')[-4000:])
    if len(p.stdout)>16000:raise ValueError('artificial result byte bound')
    result=json.loads(p.stdout);write_new(DOC/'ARTIFICIAL-POSIX-001.json',result);print(json.dumps(result))

if __name__=='__main__':main()
