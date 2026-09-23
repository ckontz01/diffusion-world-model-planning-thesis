"""One-shot ACV0 transport/launch receipts outside the approved source closure.

Uses native Windows files and configured SSH stdin. No retry, scientific edit,
credential access, dependency installation or alternate namespace is provided.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PACKAGE=REPO/'docs/active-counterfactual-verification-20260923/bindings-v1'
ATTACHMENT=Path('C:/Users/Chris/.codex/attachments/576a07c9-bdce-4b41-84b9-c6fe1f1829e5/Pasted text.txt')
ROOT='/lustreFS/data/superworld/ckontzias/thesis'
SOURCE=ROOT+'/snapshots/active-counterfactual-verification-bindings-v1-bf3f4558f2cdfbca'
CONTROL=ROOT+'/staging/active-counterfactual-verification-bindings-v1-bf3f4558f2cdfbca'
RUN=ROOT+'/experiments/active-counterfactual-verification-pilot-v1/run-bf3f4558f2cdfbca'
REL='docs/active-counterfactual-verification-20260923/bindings-v1'
MANIFEST_SHA='bf3f4558f2cdfbca98715ad684c596d23626d5650e32a72a0e26f46dc3f83554'
ARCHIVE_SHA='558681e9bccb8773b434ea928d67e55c4c40a65896033ba54021a12f86b099e9'
SSH=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',
     '-o','ServerAliveInterval=15','-o','ServerAliveCountMax=4','prometheus']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,v):
    with Path(p).open('xb') as f:f.write(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n');f.flush();os.fsync(f.fileno())

def local():
    expected={'SOURCE-MANIFEST.json':MANIFEST_SHA,'source-export.tar':ARCHIVE_SHA,
              'INPUT-BINDINGS.json':'45a50874435617c7f5cc31eff865cd923b2970d6eaa808697c05c418154aa1df',
              'GRID.json':'d415ca967041e3ed79bcb4bd355331106db332a42c9896790d83dd1ddb3772e7'}
    for n,h in expected.items():assert sha(PACKAGE/n)==h,(n,'hash mismatch')
    assert (PACKAGE/'source-export.tar').stat().st_size==706560
    assert sha(PACKAGE.parent/'DATA-ROLES-PROPOSED.json')=='2c56493ab51011c4c37f30f45fc3f207f44dfb63bfc83a88e99ba70c98ef8c64'
    grid=read(PACKAGE/'GRID.json')
    assert hashlib.sha256(json.dumps(grid,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()=='f9b4986c9f674122c253cff9aaf802e8d4b181180553d0e5643c0c92bb175a2a'
    for name,h in read(PACKAGE/'SOURCE-MANIFEST.json')['files'].items():assert sha(REPO/name)==h,name
    with tarfile.open(PACKAGE/'source-export.tar','r:') as tar:
        members=read(PACKAGE/'SOURCE-TRANSPORT.json')['members'];seen=set()
        for m in tar:
            assert m.isfile() and m.name in members and m.name not in seen
            assert not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts
            b=tar.extractfile(m).read();assert {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}==members[m.name];seen.add(m.name)
        assert seen==set(members) and len(seen)==40
    volume=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',
       'Get-Volume -DriveLetter D | Select-Object UniqueId,FileSystemLabel,SizeRemaining | ConvertTo-Json -Compress'],text=True,timeout=30))
    assert volume['FileSystemLabel']=='THESIS_SSD' and volume['UniqueId']=='\\\\?\\Volume{0a2f1ba9-0000-0000-0000-100000000000}\\'
    assert volume['SizeRemaining']>=40_000_000_000
    return {'source_manifest':MANIFEST_SHA,'archive_sha256':ARCHIVE_SHA,'archive_bytes':706560,'transport_members':40,'volume':volume}

BOOTSTRAP="""import base64,io,json,sys
raw=sys.stdin.buffer.read(2000001)
assert len(raw)<=2000000,'Transport envelope bound'
request=json.loads(raw)
assert set(request)=={'config','code','payload'},'Envelope schema'
sys.stdin=io.TextIOWrapper(io.BytesIO(base64.b64decode(request['payload'],validate=True)),encoding='utf8')
exec(compile(request['code'],'<acv0-operation>','exec'),{'CONFIG':request['config'],'json':json,'__name__':'__main__'})
"""

def envelope(code,payload=b''):
    compile(code,'<acv0-operation>','exec')
    config={'source':SOURCE,'control':CONTROL,'run':RUN,'rel':REL,
            'manifest_sha':MANIFEST_SHA,'archive_sha':ARCHIVE_SHA,'inputs':read(PACKAGE/'INPUT-BINDINGS.json')}
    data=json.dumps({'config':config,'code':code,'payload':base64.b64encode(payload).decode()},ensure_ascii=True).encode()
    assert len(data)<=2_000_000,'Transport envelope bound'
    return data

def remote(code, payload=b'', timeout=180):
    # R1: only the fixed short bootstrap is an argument; all variable bytes use stdin.
    return subprocess.run(SSH+['python3.9 -B -S -c '+shlex.quote(BOOTSTRAP)],input=envelope(code,payload),capture_output=True,timeout=timeout)

def once(name,code,payload=b''):
    claim=HERE/(name+'.json')
    with claim.open('xb') as f:
        start=time.time()
        try:
            p=remote(code,payload)
            result={'start_unix':start,'end_unix':time.time(),'returncode':p.returncode,
                    'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')}
        except BaseException as e:
            result={'start_unix':start,'end_unix':time.time(),'returncode':125,'error':repr(e),'state':'unresolved; no retry'}
        f.write(json.dumps(result,indent=2).encode()+b'\n');f.flush();os.fsync(f.fileno())
    print(json.dumps(result,indent=2))
    if result['returncode']:raise SystemExit('Operation stopped. Preserve evidence and reconcile; no retry.')
    return result

PREFLIGHT=r'''
from pathlib import Path
import hashlib,os,subprocess,sys,time
start=time.time()
for n in ('source','control','run'):
    assert not Path(CONFIG[n]).exists(), 'Exclusive path exists: '+CONFIG[n]
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
a=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--format=JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw'],capture_output=True,text=True,timeout=30)
assert q.returncode==a.returncode==0,(q.stderr,a.stderr)
prior=[line for line in (q.stdout+'\n'+a.stdout).splitlines() if 'acv0b1-' in line]
assert not prior,prior
verified=[]
for name,h in CONFIG['inputs']['runtime_files'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
    verified.append(name)
image=CONFIG['inputs']['container'];digest=hashlib.sha256()
with Path(image['path']).open('rb') as f:
    for b in iter(lambda:f.read(1048576),b''):digest.update(b)
assert digest.hexdigest()==image['sha256'],'Container mismatch'
python=CONFIG['inputs']['runtime']+'/bin/python'
env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
p=subprocess.run([python,'-B','-c','import sys,numpy,json;print(json.dumps(dict(python=sys.version,executable=sys.executable,numpy=numpy.__version__)))'],env=env,capture_output=True,text=True,timeout=30)
assert p.returncode==0, p.stderr
print(json.dumps({'status':'READY_FOR_EXACT_TRANSPORT','exclusive_paths_absent':True,'prior_acv0b1_allocations':prior,
 'runtime_files_authenticated':len(verified),'container_sha256':digest.hexdigest(),'controller_runtime':json.loads(p.stdout),
 'unix':time.time(),'wall_seconds':time.time()-start,'research_checkpoint_loads':0,'reference_payload_reads':0,'gpu_allocations':0}))
'''

STAGE=r'''
from pathlib import Path,PurePosixPath
import hashlib,io,os,sys,tarfile,time
for n in ('source','control','run'):assert not Path(CONFIG[n]).exists(),'Exclusive path exists: '+CONFIG[n]
raw=sys.stdin.buffer.read(2_000_000);package=json.loads(raw)
import base64
data=base64.b64decode(package['archive']);approval=base64.b64decode(package['approval']);instruction=base64.b64decode(package['instruction'])
assert len(data)==706560 and hashlib.sha256(data).hexdigest()==CONFIG['archive_sha']
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as tar:
    contents={}
    for m in tar:
        p=PurePosixPath(m.name)
        assert m.isfile() and not p.is_absolute() and '..' not in p.parts and m.name not in contents
        contents[m.name]=tar.extractfile(m).read()
manifest_name=CONFIG['rel']+'/SOURCE-MANIFEST.json';template_name=CONFIG['rel']+'/APPROVAL-TEMPLATE.json'
assert len(contents)==40 and hashlib.sha256(contents[manifest_name]).hexdigest()==CONFIG['manifest_sha']
manifest=json.loads(contents[manifest_name])
assert set(contents)==set(manifest['files'])|{manifest_name,template_name}
for name,h in manifest['files'].items():assert hashlib.sha256(contents[name]).hexdigest()==h,name
assert json.loads(contents[template_name])['authorized'] is False
source=Path(CONFIG['source']);control=Path(CONFIG['control']);source.mkdir();control.mkdir()
for name,data in contents.items():
    p=source/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(data)
    assert hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(data).hexdigest()
for name,data in [('EXECUTION-APPROVAL.json',approval),('EXECUTION-INSTRUCTION.txt',instruction),('AUTHORIZATION-PROVENANCE.json',json.dumps(package['provenance'],sort_keys=True).encode())]:
    with (control/name).open('xb') as f:f.write(data)
sys.path.insert(0,str(source/CONFIG['rel']))
import common as c
auth=c.Authorization(control/'EXECUTION-APPROVAL.json',CONFIG['run'])
assert auth.approval['instruction']==instruction.decode('utf8')
result={'source':str(source),'control':str(control),'run':CONFIG['run'],'source_manifest':CONFIG['manifest_sha'],
 'archive_sha256':CONFIG['archive_sha'],'source_members':len(contents),'source_bytes':sum(map(len,contents.values())),
 'approval_sha256':hashlib.sha256(approval).hexdigest(),'instruction_sha256':hashlib.sha256(instruction).hexdigest(),
 'all_members_readback_verified':True,'run_absent':not Path(CONFIG['run']).exists(),'unix':time.time()}
c.write(control/'TRANSPORT-VERIFIED.json',result);print(json.dumps(result))
'''

LAUNCH=r'''
from pathlib import Path
import os,subprocess,sys,time
source=Path(CONFIG['source']);control=Path(CONFIG['control']);run=Path(CONFIG['run'])
assert not run.exists() and not (control/'LAUNCH-INTENT.json').exists(),'Prior launch or ambiguity; do not restart'
sys.path.insert(0,str(source/CONFIG['rel']))
import common as c
approval=control/'EXECUTION-APPROVAL.json';auth=c.Authorization(approval,run)
c.require(c.read(control/'TRANSPORT-VERIFIED.json')['approval_sha256']==auth.approval_sha,'Approval transport identity')
python=auth.inputs['runtime']+'/bin/python'
command=[python,'-B',str(source/CONFIG['rel']/'dispatch.py'),'--approval',str(approval),'--run',str(run)]
env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',CUDA_VISIBLE_DEVICES='')
c.write(control/'LAUNCH-INTENT.json',{'command':command,'unix':time.time(),'exclusive':True,'automatic_retry':False})
with (control/'controller.out').open('xb') as out,(control/'controller.err').open('xb') as err:
    proc=subprocess.Popen(command,env=env,cwd=source,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
stat=Path('/proc',str(proc.pid),'stat');c.require(stat.exists(),'Controller exited at launch; reconcile, never relaunch')
identity={'pid':proc.pid,'start_ticks':stat.read_text().rsplit(')',1)[1].split()[19],
          'unix':time.time(),'command':command,'source_manifest':CONFIG['manifest_sha'],'approval_sha256':auth.approval_sha}
c.write(control/'CONTROLLER-PROCESS.json',identity);print(json.dumps(identity))
'''

OBSERVE=r'''
from pathlib import Path
import subprocess,time
control=Path(CONFIG['control']);run=Path(CONFIG['run'])
identity=json.loads((control/'CONTROLLER-PROCESS.json').read_text())
stat=Path('/proc',str(identity['pid']),'stat')
process={'identity':identity,'exists':stat.exists()}
if stat.exists():
    parts=stat.read_text().rsplit(')',1)[1].split();process.update(state=parts[0],start_ticks=parts[19],same_start=parts[19]==identity['start_ticks'])
rows=[json.loads(line) for line in (run/'DISPATCH.jsonl').read_text().splitlines()] if (run/'DISPATCH.jsonl').exists() else []
submitted=[r for r in rows if r['event']=='submitted'];terminal=[r for r in rows if r['event']=='terminal']
ids=[r['job'] for r in submitted]
accounting=[]
if ids:
    p=subprocess.run(['sacct','-X','-n','-P','-j',','.join(ids),'--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES'],capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    accounting=[line for line in p.stdout.splitlines() if line.split('|')[0] in ids]
technical={}
for name in ('collect-fit-490','collect-fit-545'):
    t=run/name/'TECHNICAL.json'
    if t.exists():technical[name]=json.loads(t.read_text())
result={'unix':time.time(),'process':process,'run_exists':run.exists(),'submitted':submitted,'terminal':terminal,
 'unresolved':[r for r in rows if 'unresolved' in r['event']],'accounting':accounting,'technical':technical,
 'controller_stdout_bytes':(control/'controller.out').stat().st_size,'controller_stderr_bytes':(control/'controller.err').stat().st_size,
 'stop':json.loads((run/'STOP.json').read_text()) if (run/'STOP.json').exists() else None,
 'technical_gate':json.loads((run/'TECHNICAL-TRANCHE-PASSED.json').read_text()) if (run/'TECHNICAL-TRANCHE-PASSED.json').exists() else None,
 'compute_complete_exists':(run/'COMPUTE-COMPLETE.json').exists()}
print(json.dumps(result))
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','prepare','stage','launch','observe']);p.add_argument('--receipt');a=p.parse_args()
    if a.mode=='preflight':write(HERE/'LOCAL-PREFLIGHT-R1.json',local());once('REMOTE-PREFLIGHT-R1',PREFLIGHT)
    elif a.mode=='prepare':
        assert read(HERE/'REMOTE-PREFLIGHT-R1.json')['returncode']==0
        raw=ATTACHMENT.read_bytes();instruction=raw.decode('utf8');assert instruction.startswith('EXECUTE ACV0 ')
        approval=read(PACKAGE/'APPROVAL-TEMPLATE.json');assert approval['authorized'] is False
        approval.update(authorized=True,instruction=instruction)
        write(HERE/'EXECUTION-APPROVAL.json',approval)
        with (HERE/'EXECUTION-INSTRUCTION.txt').open('xb') as f:f.write(raw)
        write(HERE/'AUTHORIZATION-PROVENANCE.json',{'basis':'Explicit EXECUTE ACV0 instruction supplied here under standing user delegation; not a newly obtained direct user signature',
          'attachment':str(ATTACHMENT),'instruction_sha256':hashlib.sha256(raw).hexdigest(),
          'approved_implementation':'3b2db69e563af89b1ced2149b11c11a1999ba4df','approved_receipt':'b27605ccf7e9097beb02e3d0d638d3e31a175121',
          'transport_recovery_user_instruction':'fix it',
          'transport_recovery_scope':'Correct only prelaunch transport; continue same approved launch and paths; no scientific change or research retry',
          'source_manifest':MANIFEST_SHA,'false_template_preserved':True,'source':SOURCE,'control':CONTROL,'run':RUN,
          'approval_sha256':sha(HERE/'EXECUTION-APPROVAL.json'),'no_additional_general_approval_required':True})
        print('Separate enabled approval recorded; original false template unchanged. No launch yet.')
    elif a.mode=='stage':
        import base64
        local()
        payload={n:base64.b64encode(p.read_bytes()).decode() for n,p in [('archive',PACKAGE/'source-export.tar'),('approval',HERE/'EXECUTION-APPROVAL.json'),('instruction',HERE/'EXECUTION-INSTRUCTION.txt')]}
        payload['provenance']=read(HERE/'AUTHORIZATION-PROVENANCE.json')
        once('SOURCE-TRANSPORT',STAGE,json.dumps(payload).encode())
    elif a.mode=='launch':
        assert read(HERE/'SOURCE-TRANSPORT.json')['returncode']==0
        once('LAUNCH',LAUNCH)
    else:
        assert a.receipt and '/' not in a.receipt and '\\' not in a.receipt
        once(a.receipt,OBSERVE)


if __name__=='__main__':main()
