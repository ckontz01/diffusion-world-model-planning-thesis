"""One-shot, metadata/hash-only launch reconciliation outside the frozen source."""
import sys
from pathlib import Path
import subprocess
import time
import tarfile
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO / 'docs/active-counterfactual-mechanism-replication-20260924/runtime-v2'
sys.path.insert(0, str(ROOT))
import common as c
from preserve import ssd, verify_tar
from transport import remote
sys.path.append(str(c.PROPOSAL))
from prepare_proposal import reconcile, query

def main():
    out = HERE / 'PRELAUNCH.json'
    c.require(not out.exists() and not (HERE/'PRELAUNCH-FAILURE.json').exists(), 'Exclusive reconciliation receipt')
    start = time.monotonic()
    try:
        c.require(c.sha(ROOT/'SOURCE-MANIFEST.json') == '9f91156fd11a5d54172e8cec79d37ca50199c132780b5aee3636f34b0dd2e916', 'Source identity')
        c.require(c.sha(ROOT/'EXECUTION-APPROVAL.json') == '2e9afd7dee838c4b14ada69215dc151844908fd10f0e3c8bc6fbbe389d9f4c70', 'False template preserved')
        c.source_check()
        saved = c.reconciliation()
        names = subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','docs'],cwd=REPO,capture_output=True,text=True,check=True).stdout.splitlines()
        roles = {n for n in names if any(k in Path(n).name for k in ('DATA-ROLES','FOLDS','ALLOCATION','ELIGIBILITY'))}
        c.require(roles == set(saved['role_ledger_inventory']), 'Intervening role ledger inventory')
        for n,h in saved['role_ledger_inventory'].items(): c.require(c.sha(REPO/n)==h, 'Role ledger conflict: '+n)
        audit, ac = reconcile()
        records, reader = query(ac)
        old = c.read(c.PROPOSAL/'ELIGIBILITY.json')
        for k in ('metadata_pins','eligible_before_selection','acv0','rb2','prior_union','exclusion_roles'):
            c.require(audit[k]==old[k], 'Role reconciliation: '+k)
        c.require(reader==saved['reader_sha256'], 'Identity reader')
        selected = old['selected_references']
        c.require(len(selected)==512 and selected==c.roles()['mechanism_evaluation'], 'Exact ordered role')
        c.require({str(i):records[str(i)] for i in selected}==old['records'], 'Registry identities')
        c.require(c.digest(selected)==saved['selected_order'] and c.digest(old['records'])==saved['records'], 'Ordered identity digests')
        volume = ssd()
        receipt = c.read(ROOT/'PACKAGE-VERIFIED.json')
        bundle = ROOT/'SOURCE-PACKAGE.tar'
        c.require(c.sha(bundle)==receipt['bundle_sha256']=='ba58cff72d12322eb98cd40cd1707df437ca769e824da2d0a5599ccb6b8e44e2', 'Export identity')
        c.require(bundle.stat().st_size==4894720, 'Export bytes')
        expected = {}
        with tarfile.open(bundle, 'r:') as t:
            for m in t:
                c.require(m.isfile() and m.name not in expected and not m.name.startswith('/') and '..' not in Path(m.name).parts, 'Export member')
                p=REPO/m.name
                expected[m.name]=dict(bytes=p.stat().st_size,sha256=c.sha(p))
        verified = verify_tar(Path(receipt['ssd_bundle']), expected, start+300)
        c.require(verified==receipt['verified'] and verified['members']==76, 'SSD package whole/member receipt')
        inputs=c.read(ROOT/'INPUT-BINDINGS.json'); control_runtime=c.read(ROOT/'CONTROLLER-RUNTIME.json')
        reuse=c.read(ROOT/'MODEL-REUSE.json')
        hashes=dict(inputs['runtime_files']); hashes.update(control_runtime['files'])
        hashes[inputs['container']['path']]=inputs['container']['sha256']
        for item in reuse['files'].values(): hashes[item['path']]=item['sha256']
        code='''import os,sys,json,hashlib,subprocess,time
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
'''
        code += 'expected='+repr(hashes)+'\n'
        code += 'base=Path('+repr(c.RESEARCH)+')\nnamespace='+repr(c.NAMESPACE)+'\n'
        code += '''conflicts=[]
for sub in ('snapshots','staging','experiments'):
 conflicts.extend(str(p) for p in (base/sub).glob(namespace+'*'))
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=os.getuid():continue
  cmd=(p/'cmdline').read_bytes().replace(b'\\0',b' ').decode(errors='replace')
  if namespace in cmd:processes.append(dict(pid=int(p.name),cmdline=cmd))
 except (FileNotFoundError,ProcessLookupError,PermissionError):continue
queries={}
for name,cmd in [('sacct',['/usr/bin/sacct','-X','-n','-P','-u',os.environ['USER'],'-S','2026-09-24T00:00:00','-o','JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList']),('squeue',['/usr/bin/squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T|%N'])]:
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
 assert r.returncode==0,(name,r.stderr)
 queries[name]=[line for line in r.stdout.splitlines() if 'acvm1-' in line.lower()]
checks={p:sha(p)==h for p,h in expected.items()}
r=dict(unix=time.time(),python_version=list(sys.version_info[:3]),namespace_conflicts=conflicts,controller_conflicts=processes,scheduler_matches=queries,hash_checks=checks,reused_inputs_deserialized=False,reference_payload_reads=0)
print(json.dumps(r))
'''
        response=remote(code)
        raw=dict(unix=time.time(),returncode=response.returncode,stdout=response.stdout.decode(errors='replace'),stderr=response.stderr.decode(errors='replace'),automatic_retry=False)
        c.write(HERE/'PRELAUNCH-REMOTE.json',raw)
        c.require(response.returncode==0, 'Remote reconciliation transport failed')
        host=json.loads(raw['stdout'])
        c.require(host['python_version']==control_runtime['python_version'], 'Host Python version')
        c.require(not host['namespace_conflicts'] and not host['controller_conflicts'] and not any(host['scheduler_matches'].values()), 'Existing or ambiguous ACVM1 execution')
        c.require(all(host['hash_checks'].values()), 'Pinned control/worker/reused-input identity')
        result=dict(status='PRELAUNCH_PASSED',unix=time.time(),wall_seconds=time.monotonic()-start,source_manifest=c.sha(ROOT/'SOURCE-MANIFEST.json'),false_approval=c.sha(ROOT/'EXECUTION-APPROVAL.json'),role_ledger_inventory=saved['role_ledger_inventory'],selected_order=c.digest(selected),records=c.digest(old['records']),selected_count=512,excluded_count=944,registry=old['registry_sha256'],reader=reader,payload_reads=0,outcome_fields_decoded=0,source_backup=verified,backup_receipt=c.sha(ROOT/'PACKAGE-VERIFIED.json'),volume=volume,remote_receipt=c.sha(HERE/'PRELAUNCH-REMOTE.json'),new_allocations=0,automatic_retry=False)
        c.write(out,result)
        print(json.dumps(result))
    except BaseException as e:
        c.write(HERE/'PRELAUNCH-FAILURE.json',dict(unix=time.time(),error=repr(e),automatic_retry=False,wall_seconds=time.monotonic()-start))
        raise

if __name__=='__main__':main()
