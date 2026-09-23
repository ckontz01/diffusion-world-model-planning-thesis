"""One-shot configured SSH-stdin transport. No science or retry implementation."""
import r2_core as r
import argparse
import base64
import io
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile
import time

HERE=r.REPO/'docs/active-counterfactual-verification-publication-20260923/continuation-r2'
REL='docs/active-counterfactual-verification-20260923/control-r2'
SSH=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',
     '-o','ServerAliveInterval=15','-o','ServerAliveCountMax=4','prometheus']
BOOTSTRAP="""import base64,io,json,sys
raw=sys.stdin.buffer.read(2000001)
assert len(raw)<=2000000,'Transport envelope bound'
request=json.loads(raw)
assert set(request)=={'config','code','payload'},'Envelope schema'
sys.stdin=io.TextIOWrapper(io.BytesIO(base64.b64decode(request['payload'],validate=True)),encoding='utf8')
exec(compile(request['code'],'<acv0-r2-operation>','exec'),{'CONFIG':request['config'],'json':json,'__name__':'__main__'})
"""

def configuration():
    b=r.binding(r.sha(r.ROOT/'SOURCE-MANIFEST.json'))
    return dict(binding=b,rel=REL,transport=r.read(r.ROOT/'SOURCE-TRANSPORT.json'),baseline=r.read(r.ROOT/'BASELINE.json'),
                approval_sha256=r.sha(HERE/'EXECUTION-APPROVAL.json'))

def instruction():return (r.ROOT/'INSTRUCTION.txt').read_bytes().decode('utf8')

def envelope(code,payload=b'',config=None):
    compile(code,'<acv0-r2-operation>','exec')
    data=r.canonical({'config':configuration() if config is None else config,'code':code,'payload':base64.b64encode(payload).decode()})
    r.require(len(data)<=2000000,'Transport envelope bound');return data

def verify_archive(path,transport):
    r.require(r.sha(path)==transport['sha256'] and path.stat().st_size==transport['bytes'],'Control archive identity')
    seen=set()
    with tarfile.open(path,'r:') as tar:
        for m in tar:
            n=PurePosixPath(m.name)
            r.require(m.isfile() and len(n.parts)==1 and not n.is_absolute() and m.name not in seen and m.name in transport['members'],'Flat control member')
            data=tar.extractfile(m).read();r.require({'bytes':len(data),'sha256':r.hashlib.sha256(data).hexdigest()}==transport['members'][m.name],'Control member bytes');seen.add(m.name)
    r.require(seen==set(transport['members']),'Complete control member set')

def local():
    cfg=configuration();b=cfg['binding']
    for n,h in r.read(r.ROOT/'SOURCE-MANIFEST.json')['files'].items():r.require(r.sha(r.ROOT/n)==h,'Frozen R2 source: '+n)
    verify_archive(r.ROOT/'source-export.tar',cfg['transport'])
    a=r.read(HERE/'EXECUTION-APPROVAL.json')
    r.require(a=={'schema':'ACV0-control-only-r2','authorized':True,'instruction':instruction(),'binding':b},'Exact additional authority')
    cmd='Get-Volume -DriveLetter D | Select-Object UniqueId,FileSystemLabel,SizeRemaining | ConvertTo-Json -Compress'
    v=r.json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',cmd],text=True,timeout=30))
    r.require(v['FileSystemLabel']=='THESIS_SSD' and v['UniqueId']=='\\\\?\\Volume{0a2f1ba9-0000-0000-0000-100000000000}\\' and v['SizeRemaining']>=40000000000,'Designated SSD identity/capacity')
    return {'unix':time.time(),'control_manifest':b['control_manifest'],'approval_sha256':cfg['approval_sha256'],'volume':v}

def once(name,code,payload=b''):
    r.require(name and Path(name).name==name and '/' not in name and '\\' not in name,'Receipt basename')
    with (HERE/(name+'.json')).open('xb') as f:
        start=time.time()
        try:
            p=subprocess.run(SSH+['/usr/bin/python3.9 -B -S -c '+shlex.quote(BOOTSTRAP)],input=envelope(code,payload),capture_output=True,timeout=240)
            result={'start_unix':start,'end_unix':time.time(),'returncode':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')}
        except BaseException as e:result={'start_unix':start,'end_unix':time.time(),'returncode':125,'error':repr(e),'state':'unresolved; no retry'}
        f.write(r.canonical(result)+b'\n');f.flush();os.fsync(f.fileno())
    print(r.json.dumps(result,indent=2))
    r.require(result['returncode']==0,'Operation stopped; preserve and reconcile, no retry')
    return result

NAMESPACE=r'''
from pathlib import Path
import hashlib,os,sys,time
b=CONFIG['binding'];base=CONFIG['baseline']
for label,key in [('source','control_source'),('control','control')]:
 parent=Path(b[key]).parent
 actual={str(p) for p in parent.iterdir() if 'active-counterfactual' in p.name.lower() or 'acv0' in p.name.lower()}
 expected=set(base['namespaces'][label])
 if Path(b[key]).exists():expected.add(b[key])
 assert actual==expected,'Unknown ACV0 control/source namespace'
run=Path(b['run'])
assert {str(p) for p in run.parent.iterdir()}=={b['run'],str(run.parent/'run-5630b222e8a88d0e')},'Unknown research run namespace'
'''

STAGE=NAMESPACE+r'''
import base64,io,tarfile
from pathlib import PurePosixPath
assert not Path(b['control_source']).exists() and not Path(b['control']).exists(),'Existing R2 namespace; no repeat'
for name,info in base['inventory'].items():
 label,rel=name.split('/',1);p=Path(base['paths'][label])/rel
 assert p.stat().st_size==info['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256'],'Original bytes changed: '+name
package=json.loads(sys.stdin.buffer.read(2000000));data=base64.b64decode(package['archive'],validate=True)
approval=base64.b64decode(package['approval'],validate=True)
assert hashlib.sha256(approval).hexdigest()==CONFIG['approval_sha256']
transport=CONFIG['transport'];assert len(data)==transport['bytes'] and hashlib.sha256(data).hexdigest()==transport['sha256']
contents={}
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as tar:
 for m in tar:
  p=PurePosixPath(m.name);assert m.isfile() and len(p.parts)==1 and not p.is_absolute() and m.name not in contents
  raw=tar.extractfile(m).read();assert {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==transport['members'][m.name]
  contents[m.name]=raw
assert set(contents)==set(transport['members'])
assert hashlib.sha256(contents['SOURCE-MANIFEST.json']).hexdigest()==b['control_manifest']
manifest=json.loads(contents['SOURCE-MANIFEST.json']);assert set(contents)==set(manifest['files'])|{'SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json'}
for n,h in manifest['files'].items():assert hashlib.sha256(contents[n]).hexdigest()==h
assert json.loads(contents['APPROVAL-TEMPLATE.json'])['authorized'] is False
source=Path(b['control_source']);control=Path(b['control']);source.mkdir();control.mkdir()
root=source/CONFIG['rel'];root.mkdir(parents=True)
for n,raw in contents.items():
 with (root/n).open('xb') as f:f.write(raw)
 assert hashlib.sha256((root/n).read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
for n,raw in [('EXECUTION-APPROVAL.json',approval),('AUTHORIZATION-PROVENANCE.json',json.dumps(package['provenance'],sort_keys=True).encode()),
              ('EXECUTION-INSTRUCTION.txt',contents['INSTRUCTION.txt'])]:
 with (control/n).open('xb') as f:f.write(raw)
sys.path.insert(0,str(root))
import r2_core as r
ctx=r.Context(control/'EXECUTION-APPROVAL.json')
from controller_runtime import verify
pins=verify();reconciled=r.reconcile(ctx);existing,accepted=r.accept_existing(ctx);space=r.storage(ctx)
assert 'numpy' not in sys.modules and 'torch' not in sys.modules
result={'unix':time.time(),'control_manifest':b['control_manifest'],'approval_sha256':ctx.approval_sha,'transport_sha256':transport['sha256'],
 'source':str(source),'control':str(control),'original_run':str(run),'readback_verified':True,'members':len(contents),
 'original_scientific_source_unchanged':True,'host_runtime':pins,'reconciliation':reconciled,'existing_supplier_hash_checks':accepted,
 'acceptance_record_written':False,'storage':space,'research_calls':0,'scientific_payloads_decoded':0}
r.write(control/'TRANSPORT-VERIFIED.json',result);print(json.dumps(result))
'''

LAUNCH=NAMESPACE+r'''
import subprocess
source=Path(b['control_source']);control=Path(b['control']);root=source/CONFIG['rel']
assert not (control/'LAUNCH-INTENT.json').exists() and not (control/'CONTROLLER-PROCESS.json').exists(),'Prior launch or ambiguity; never restart'
sys.path.insert(0,str(root));import r2_core as r
ctx=r.Context(control/'EXECUTION-APPROVAL.json')
assert r.read(control/'TRANSPORT-VERIFIED.json')['approval_sha256']==ctx.approval_sha
from controller_runtime import verify
pins=verify();r.reconcile(ctx);r.accept_existing(ctx);r.storage(ctx)
command=[pins['python'],'-B','-S',str(root/'controller.py'),'--approval',str(control/'EXECUTION-APPROVAL.json')]
env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4',
 PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',CUDA_VISIBLE_DEVICES='')
r.write(control/'LAUNCH-INTENT.json',{'unix':time.time(),'command':command,'automatic_retry':False,'original_controller_restart':False})
with (control/'controller.out').open('xb') as out,(control/'controller.err').open('xb') as err:
 process=subprocess.Popen(command,env=env,cwd=source,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
stat=Path('/proc',str(process.pid),'stat');assert stat.exists(),'Controller exited; reconcile, never relaunch'
identity={'pid':process.pid,'start_ticks':stat.read_text().rsplit(')',1)[1].split()[19],'unix':time.time(),'command':command,
 'control_manifest':b['control_manifest'],'approval_sha256':ctx.approval_sha,'original_scientific_manifest':r.SCIENCE_MANIFEST}
r.write(control/'CONTROLLER-PROCESS.json',identity);print(json.dumps(identity))
'''

OBSERVE=r'''
from pathlib import Path
import sys,subprocess,time
b=CONFIG['binding'];root=Path(b['control_source'])/CONFIG['rel'];control=Path(b['control']);run=Path(b['run'])
sys.path.insert(0,str(root));import r2_core as r
identity=r.read(control/'CONTROLLER-PROCESS.json');stat=Path('/proc',str(identity['pid']),'stat')
process={'identity':identity,'exists':stat.exists()}
if stat.exists():
 f=stat.read_text().rsplit(')',1)[1].split();process.update(state=f[0],start_ticks=f[19],same_start=f[19]==identity['start_ticks'])
rows=r.lines(control/'CAMPAIGN-R2.jsonl') if (control/'CAMPAIGN-R2.jsonl').exists() else []
submitted=[v for v in rows if v['event']=='submitted'];terminal=[v for v in rows if v['event']=='terminal'];ids=[v['job'] for v in submitted]
accounting=[]
if ids:
 p=subprocess.run(['sacct','-X','-n','-P','-j',','.join(ids),'--format='+r.FIELDS],capture_output=True,text=True,timeout=60)
 assert p.returncode==0,p.stderr;accounting=[r.parse_row(s) for s in p.stdout.splitlines() if s.split('|')[0] in ids]
records={n:r.read(control/n) for n in ('ACCEPTED-EXISTING.json','STOP-RESOLUTION.json','TECHNICAL-TRANCHE-R2.json','MODEL-FREEZE-R2.json','STOP-R2.json') if (control/n).exists()}
technical={n:r.read(run/n/'TECHNICAL.json') for n in ('collect-fit-490','collect-fit-545') if (run/n/'TECHNICAL.json').exists()}
print(json.dumps({'unix':time.time(),'process':process,'submitted':submitted,'terminal':terminal,'accounting':accounting,
 'unresolved':[v for v in rows if 'unresolved' in v['event']],'records':records,'technical':technical,
 'original_stop_sha256':r.sha(run/'STOP.json'),'controller_stderr_bytes':(control/'controller.err').stat().st_size,
 'controller_stdout_bytes':(control/'controller.out').stat().st_size,'compute_complete':(control/'COMPUTE-COMPLETE.json').exists()}))
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['stage','launch','observe']);p.add_argument('--receipt');a=p.parse_args()
    if a.mode=='stage':
        r.write(HERE/'LOCAL-PREFLIGHT.json',local())
        delivery=r.read(HERE/'DELIVERY.json');r.require(delivery['status']=='VERIFIED' and delivery['remote_head_verified'],'Frozen small-package backup required')
        payload={'archive':base64.b64encode((r.ROOT/'source-export.tar').read_bytes()).decode(),
                 'approval':base64.b64encode((HERE/'EXECUTION-APPROVAL.json').read_bytes()).decode(),
                 'provenance':r.read(HERE/'AUTHORIZATION-PROVENANCE.json')}
        once('SOURCE-TRANSPORT',STAGE,r.canonical(payload))
    elif a.mode=='launch':
        r.require(r.read(HERE/'SOURCE-TRANSPORT.json')['returncode']==0,'Successful staged package')
        local();once('LAUNCH',LAUNCH)
    else:r.require(bool(a.receipt),'New observation receipt required');once(a.receipt,OBSERVE)

if __name__=='__main__':main()
