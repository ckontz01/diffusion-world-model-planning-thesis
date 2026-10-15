"""Finite transport recovery: preserve old partial, reuse verified suppliers.

No original source/contract is edited. No scientific or scheduler retry.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
from wm_diag0_preflight_v1.common import ROOT,DOC as OLD_DOC,DOCREL,RUN as OLD_RUN,identity,write_new,reservation
from wm_diag0_preflight_v1.build import blobs
from wm_diag0_preflight_v1.transport import ssh
from wm_diag0_preflight_v1.preserve import git,volume,verify_zip,digest

DOC=OLD_DOC/'stage-recovery-r1'
RUN=OLD_RUN+'-stage-r1'

def freeze():
    DOC.mkdir(exist_ok=False)
    r=json.loads((OLD_DOC/'STAGE-FAILURE-RECONCILIATION-001.json').read_text())
    if r['exact_upload_processes'] or r['dispatch_exists']: raise ValueError('live/ambiguous operation')
    c=json.loads((OLD_DOC/'CONTRACT.json').read_text())
    c.update(run=RUN,prior_contract=identity(OLD_DOC/'CONTRACT.json'),
             failed_stage_namespace=OLD_RUN,failed_stage_retained_bytes=r['total_retained_bytes'],
             live_bytes_reserved=c['live_bytes_reserved']+r['total_retained_bytes'],
             recovery='Transport-only: verify all old files; hard-link successful original inputs; copy preserved 16MiB partial prefix into a NEW file and transmit only its missing suffix. No old file changed.',
             allocation_attempts_before_recovery=0,preparation_charge='Covered by same 1680-second reservation; exact supplementary operation receipts retained.')
    if c['live_bytes_reserved']>c['live_cap']: raise ValueError('all-failure-inclusive live reservation')
    write_new(DOC/'CONTRACT.json',c)
    write_new(DOC/'RECOVERY.json',{'status':'FINITE_TRANSPORT_ONLY_RECOVERY','suppliers':r,'new_run':RUN,
                'old_run_untouched':True,'old_successful_suppliers_not_retransmitted':True,
                'maximum_suffix_bytes':88837855-16777216,'new_cpu_allocations_authorized':1,
                'max_cpu_seconds':1200,'full_future_other_cpu_seconds':12600,
                'live_full_future_bytes':c['live_bytes_reserved'],'live_cap':c['live_cap'],
                'inclusive_full_future_bytes':c['inclusive_reserved'],'inclusive_cap':c['inclusive_cap'],
                'immutable_worker_source':'04969e38ab070dd5e88f53d23fd60063956d208f',
                'diagnosis':'Original monolithic 266MB stdin upload exceeded its bounded transport deadline after 194MB; exact receiver process no longer exists. Complete suppliers match hashes; Reacher has a 16MiB prefix. No scheduler attempt occurred.'})
    print(json.dumps({'contract':identity(DOC/'CONTRACT.json'),'live_full_future':c['live_bytes_reserved']}))

def preserve(commit):
    v=volume()
    if len(commit)!=40 or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit: raise ValueError('remote full hash')
    prefixes=[DOCREL+'/stage-recovery-r1','wm_diag0_preflight_v1/stage_recovery_r1.py','wm_diag0_preflight_v1/observe.py']
    names=git('ls-tree','-r','--name-only',commit,'--',*prefixes).decode().splitlines()
    additional=['STAGE-001.started.json','LOCAL-STAGE001.json','LOCAL-STAGE001.started.json',
                'STAGE-FAILURE-RECONCILIATION-001.json','SSD-VERIFIED-001.json']
    names += [DOCREL+'/'+n for n in additional]
    data={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,data.values()))>1_000_000: raise ValueError('recovery metadata cap')
    data['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in data.items()},'prior_package_not_rearchived':True},sort_keys=True,indent=2).encode()
    d=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-preflight-v1-20261015/stage-recovery-r1'); d.mkdir(exist_ok=False)
    local=OLD_DOC/'delivery'; name='stage-r1-'+commit+'.zip'; a=local/name; b=d/name
    with a.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,raw in sorted(data.items()): z.writestr(n,raw)
        f.flush(); os.fsync(f.fileno())
    verify_zip(a,data)
    with b.open('xb') as f: f.write(a.read_bytes()); f.flush(); os.fsync(f.fileno())
    if identity(a)!=identity(b): raise ValueError('recovery whole hash')
    verify_zip(b,data)
    row={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,
         'whole':identity(b),'archive':str(b),'verified_members':len(data),'contract':identity(DOC/'CONTRACT.json'),'volume':v}
    write_new(DOC/'SSD-VERIFIED-001.json',row); write_new(d/'SSD-VERIFIED-001.json',row)
    if identity(DOC/'SSD-VERIFIED-001.json')!=identity(d/'SSD-VERIFIED-001.json'): raise ValueError('receipt hash')
    print(json.dumps(row,indent=2))

def gate():
    r=json.loads((DOC/'SSD-VERIFIED-001.json').read_text()); volume()
    if r['contract']!=identity(DOC/'CONTRACT.json') or identity(r['archive'])!=r['whole']: raise ValueError('preservation changed')
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=r['source_commit']: raise ValueError('published full hash')
    return r['contract']['sha256']

def stage():
    expected=gate(); items=blobs(); c=json.loads((DOC/'CONTRACT.json').read_text())
    if {n:digest(b) for n,b in items.items()}!=c['staged_members']: raise ValueError('original source changed')
    r=json.loads((OLD_DOC/'STAGE-FAILURE-RECONCILIATION-001.json').read_text())
    for n,row in r['partial'].items():
        if digest(items[n][:row['bytes']])!={k:row[k] for k in ('bytes','sha256')}: raise ValueError('partial prefix does not match original input')
    items['CONTRACT.json']=(DOC/'CONTRACT.json').read_bytes()
    rows=[]; payload=[]
    for n,b in sorted(items.items()):
        supplier=r['complete'].get(n); partial=r['partial'].get(n)
        offset=len(b) if supplier else partial['bytes'] if partial else 0
        rows.append(dict(name=n,**digest(b),offset=offset,supplier=bool(supplier),partial=partial))
        if not supplier: payload.append(b[offset:])
    raw=json.dumps(rows).encode()+b'\n'+b''.join(payload)
    if len(raw)>74_000_000: raise ValueError('finite missing-suffix transport bound')
    write_new(DOC/'STAGE-001.started.json',{'contract_sha256':expected,'transport_bytes':len(raw)})
    code='RUN='+repr(RUN)+'\nOLD='+repr(OLD_RUN)+'\nPREVIOUS='+repr(r['members'])+'\nEXPECTED='+repr(expected)+'\n'+'''
import hashlib,json,os,pathlib,sys,time
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
old=pathlib.Path(OLD)
for n,r in PREVIOUS.items():
 p=old/n
 if p.is_symlink() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']: raise ValueError('old evidence changed')
root=pathlib.Path(RUN); root.mkdir(parents=True,exist_ok=False)
for n in ('source','controls','logs','output','tmp'): (root/n).mkdir()
with (root/'controls/STAGING-STARTED.json').open('x') as f: json.dump({'time':time.time(),'pid':os.getpid(),'contract_sha256':EXPECTED},f)
rows=json.loads(sys.stdin.buffer.readline(200000))
if len(rows)>100 or len(rows)!=len(set(r['name'] for r in rows)): raise ValueError('member bound/set')
for r in rows:
 name=r['name']; p=pathlib.PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or chr(92) in name or ':' in name: raise ValueError('path')
 target=root/'source'/name; target.parent.mkdir(parents=True,exist_ok=True)
 if r['supplier']:
  os.link(str(old/'source'/name),str(target))
 else:
  remaining=r['bytes']-r['offset']
  with target.open('xb') as f:
   if r['offset']:
    with (old/'source'/name).open('rb') as prior:
     while True:
      b=prior.read(1048576)
      if not b: break
      f.write(b)
   while remaining:
    b=sys.stdin.buffer.read(min(1048576,remaining))
    if not b: raise EOFError('preserve recovery partial; never blind retry')
    f.write(b); remaining-=len(b)
   f.flush(); os.fsync(f.fileno())
 if target.stat().st_size!=r['bytes'] or sha(target)!=r['sha256']: raise ValueError('complete recovered member identity')
 target.chmod(0o444)
if sys.stdin.buffer.read(1): raise ValueError('extra bytes')
if sha(root/'source/CONTRACT.json')!=EXPECTED: raise ValueError('contract')
result={'status':'EXCLUSIVE_STAGE_AUTHENTICATED','contract_sha256':EXPECTED,'members':len(rows),'old_evidence_preserved':True,'old_supplier_links':sum(r['supplier'] for r in rows)}
with (root/'controls/STAGING-VERIFIED.json').open('x') as f: json.dump(result,f)
for p in sorted((root/'source').rglob('*'),reverse=True):
 if p.is_dir(): p.chmod(0o555)
(root/'source').chmod(0o555)
print(json.dumps(result))
'''
    result=ssh(code,payload=raw); write_new(DOC/'STAGE-001.json',result); print(json.dumps(result))

def submit():
    expected=gate(); reservation(1200)
    write_new(DOC/'SUBMIT-001.started.json',{'contract_sha256':expected,'attempts':1,'allocation_seconds':1200})
    # Reuse the exact published held-submission protocol without editing it.
    tree=ast.parse((ROOT/'wm_diag0_preflight_v1/deploy.py').read_text())
    raw=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('\nimport hashlib,json,os,pathlib,subprocess,time')][0]
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\n'+raw
    r=ssh(code); write_new(DOC/'DISPATCH-001.json',r); print(json.dumps(r))

if __name__=='__main__':
    if sys.argv[1]=='freeze': freeze()
    elif sys.argv[1]=='preserve': preserve(sys.argv[2])
    elif sys.argv[1]=='stage': stage()
    elif sys.argv[1]=='submit': submit()
    else: raise ValueError('explicit finite operation required')
