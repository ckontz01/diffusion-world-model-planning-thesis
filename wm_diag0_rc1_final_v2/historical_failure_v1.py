"""Supplement the56-file receipt with exact preserved failure-phase metadata."""
import ast,base64,json,shlex,subprocess,sys
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new

READ=r'''
import hashlib,json,pathlib,re,resource,os,stat
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592))
r=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/campaign-v4')
evidence={}
def read(p,cap):
 if p.is_symlink() or any(q.is_symlink() for q in p.parents):raise ValueError('no redirected historical evidence')
 s=p.lstat()
 if not stat.S_ISREG(s.st_mode) or s.st_size>cap:raise ValueError('bounded historical file')
 b=p.read_bytes();a=p.lstat()
 if (s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns):raise ValueError('historical evidence changed')
 evidence[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
cp=r/'source/CONTRACT.json';c=json.loads(read(cp,200000))
if evidence[str(cp)]['sha256']!='f08e53e73035171340fe2438e3061685a3be6d1f18a8b132540717bd447a60dc':raise ValueError('unchanged executed old contract')
source=r/'source/wm_diag0_campaign_v4/diagnostic.py';read(source,20000)
if evidence[str(source)]!=c['staged_members']['wm_diag0_campaign_v4/diagnostic.py']:raise ValueError('exact source defining failure order')
t=r/'tasks/technical-1';start=json.loads(read(t/'controls/STARTED.json',10000));result=json.loads(read(t/'controls/RESULT.json',10000))
if (start['job_id'],start['array_job_id'],start['phase'],start['index'],start['contract_sha256'])!=('317171','317164','technical',1,evidence[str(cp)]['sha256']):raise ValueError('exact failed allocation start')
if (result['job_id'],result['array_job_id'],result['status'],result['index'],result['phase'])!=('317171','317164','FAILED',1,'technical'):raise ValueError('exact retained failure result')
log=read(t/'logs/worker.log',1000000).decode('utf8',errors='strict')
if 'in parity' not in log or 'torch.testing.assert_close(first,second' not in log or 'Tensor-likes are not close' not in log:raise ValueError('expected uncached numerical-reference traceback, not an assumed failure point')
if 'wm_diag0_campaign_v4/diagnostic.py' not in log:raise ValueError('exact historical diagnostic source traceback')
print(json.dumps({'status':'EXACT_OLD_UNCACHED_REFERENCE_FAILURE_POINT_AUTHENTICATED',
 'job_id':'317171','array_job_id':'317164','failure_frame':'wm_diag0_campaign_v4.diagnostic.parity',
 'failed_expression':'torch.testing.assert_close(first,second,rtol=2**-6,atol=2**-8)',
 'error_kind':'AssertionError: Tensor-likes are not close',
 'native_reference_forward_preceded_this_assertion_in_authenticated_source':True,
 'evidence':evidence,'scheduler_calls':0,'filesystem_mutations':0,'research_calls':0,
 'array_values_or_readout_quality_or_outcomes_read':False,'final_gate_ready':False},sort_keys=True))
'''


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive supplemental metadata label')
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    dst=doc/('HISTORICAL-FAILURE-'+label+'.json');start=doc/('HISTORICAL-FAILURE-'+label+'.started.json')
    if dst.exists() or start.exists():raise FileExistsError('never repeat completed/ambiguous failure metadata read')
    ast.parse(READ,feature_version=(3,6))
    prior=doc/'HISTORICAL-USAGE-001.json'
    if identity(prior)!={'bytes':19046,'sha256':'c9397f411d2022963958470df0b4c53a8fdf43fbd34dcb4bdcb2ca6acfffef1d'}:raise ValueError('exact original historical receipt, never rewrite')
    write_new(start,{'source':identity(__file__),'prior_historical_receipt':identity(prior),'scope':'one missing exact old worker traceback phase; no bulk reader or scheduler repeat'})
    encoded=base64.b64encode(READ.encode()).decode()
    remote='timeout --kill-after=1s 15s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    cmd=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','20s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','ConnectionAttempts=1','prometheus',remote]
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=22)
    if p.returncode:raise RuntimeError('supplemental historical metadata unavailable, not research fault; '+p.stderr.decode(errors='replace')[-2000:])
    if len(p.stdout)>12000:raise ValueError('bounded failure metadata stdout')
    z=json.loads(p.stdout);z['prior_historical_receipt']=identity(prior)
    write_new(dst,z,limit=16000)
    print(json.dumps({'status':z['status'],'evidence_files':len(z['evidence']),'scheduler_calls':0,'research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
