"""Exclusive R5 staging/finalization/archive; no launch or submission entry point."""
import argparse,base64,os,shlex,subprocess,sys,time
from pathlib import Path
import r5_core as r
r.load_r4()
import transport4 as old
HERE=r.REPO/'docs/active-counterfactual-verification-publication-20260923/finalization-r5'
REL='docs/active-counterfactual-verification-20260923/finalization-r5'
SSH=old.SSH
BOOTSTRAP=old.BOOTSTRAP.replace('2000001','8000001').replace('2000000','8000000').replace('acv0-r4-operation','acv0-r5-operation')
verify_archive=old.verify_archive
def instruction():return (r.ROOT/'INSTRUCTION.txt').read_bytes().decode('utf8')
def configuration():
    return dict(binding=r.binding(r.sha(r.ROOT/'SOURCE-MANIFEST.json')),rel=REL,
        transport=r.read(r.ROOT/'SOURCE-TRANSPORT.json'),baseline=r.read(r.ROOT/'BASELINE.json'),
        approval_sha256=r.sha(HERE/'EXECUTION-APPROVAL.json'))
def envelope(code,payload=b'',config=None):
    compile(code,'<acv0-r5-operation>','exec')
    data=r.canonical({'config':configuration() if config is None else config,'code':code,'payload':base64.b64encode(payload).decode()})
    r.require(len(data)<=8000000,'Transport envelope bound');return data
def local():
    cfg=configuration();b=cfg['binding']
    for n,h in r.read(r.ROOT/'SOURCE-MANIFEST.json')['files'].items():r.require(r.sha(r.ROOT/n)==h,'Frozen R5 source: '+n)
    verify_archive(r.ROOT/'source-export.tar',cfg['transport'])
    r.require(r.read(HERE/'EXECUTION-APPROVAL.json')=={'schema':'ACV0-finalization-only-r5','authorized':True,'instruction':instruction(),'binding':b},'Exact direct recovery authority')
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
    print(r.json.dumps({k:v for k,v in result.items() if k!='stdout'},indent=2))
    r.require(result['returncode']==0,'Operation stopped; preserve and reconcile, no retry');return result

NAMESPACE=old.NAMESPACE
STAGE=old.STAGE.replace('Existing R4 namespace','Existing R5 namespace').replace('read(2000000)','read(8000000)').replace('import r4_core as r','import r5_core as r').replace("'acceptance_record_written':False","'acceptance_record_written':False,'new_jobs_authorized':0")
# This does not launch any process. It imports the separately frozen adapter.
OPERATE=NAMESPACE+r'''
source=Path(b['control_source']);control=Path(b['control']);root=source/CONFIG['rel']
sys.path.insert(0,str(root));import r5_core as r
ctx=r.Context(control/'EXECUTION-APPROVAL.json')
assert r.read(control/'TRANSPORT-VERIFIED.json')['approval_sha256']==ctx.approval_sha
from controller_runtime import verify
verify()
import finalize5
mode=json.loads(sys.stdin.buffer.read(100))['mode'];assert mode in ('finalize','archive')
print(json.dumps((finalize5.finalize if mode=='finalize' else finalize5.archive)(ctx)))
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['stage','finalize','archive']);a=p.parse_args()
    if a.mode=='stage':
        r.write(HERE/'LOCAL-PREFLIGHT.json',local())
        delivery=r.read(HERE/'DELIVERY.json');r.require(delivery['status']=='VERIFIED' and delivery['remote_head_verified'],'Small SSD package and remote verified')
        payload={'archive':base64.b64encode((r.ROOT/'source-export.tar').read_bytes()).decode(),
            'approval':base64.b64encode((HERE/'EXECUTION-APPROVAL.json').read_bytes()).decode(),
            'delivery':delivery,'provenance':r.read(HERE/'AUTHORIZATION-PROVENANCE.json')}
        once('SOURCE-TRANSPORT',STAGE,r.canonical(payload))
    else:
        r.require(r.read(HERE/'SOURCE-TRANSPORT.json')['returncode']==0,'Successful stage required')
        local();once(a.mode.upper(),OPERATE,r.canonical({'mode':a.mode}))
if __name__=='__main__':main()
