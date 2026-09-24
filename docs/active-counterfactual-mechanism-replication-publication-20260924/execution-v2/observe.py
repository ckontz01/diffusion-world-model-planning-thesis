"""Read-only control, allocation and technical evidence; never scientific results."""
import sys
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-mechanism-replication-20260924/runtime-v2'
sys.path.insert(0,str(ROOT))
import common as c
from transport import remote

def main():
    label=sys.argv[1]
    c.require(label.replace('-','').isalnum(), 'Receipt label')
    dest=HERE/(label+'.json')
    c.require(not dest.exists(), 'Exclusive observation receipt')
    auth=c.Authorization(HERE/'EXECUTION-APPROVAL.json',c.read(HERE/'EXECUTION-APPROVAL.json')['run'])
    source=c.RESEARCH+'/snapshots/'+c.NAMESPACE+'-'+auth.approval['package_sha256'][:16]
    control=c.RESEARCH+'/staging/'+c.NAMESPACE+'-'+auth.approval['package_sha256'][:16]
    code='import sys,json,time,subprocess\nfrom pathlib import Path\n'
    code+='root=Path('+repr(source)+')/'+repr(ROOT.relative_to(c.REPO).as_posix())+'\n'
    code+='control=Path('+repr(control)+')\nrun=Path('+repr(str(auth.run))+')\n'
    code+='sys.path.insert(0,str(root));import common as c\n'
    code+='expected_approval='+repr(auth.approval_sha)+'\n'
    code+='''a=c.Authorization(control/'EXECUTION-APPROVAL.json',str(run))
assert a.approval_sha==expected_approval
r=dict(unix=time.time(),approval=a.approval_sha,source_manifest=c.sha(root/'SOURCE-MANIFEST.json'),false_template=c.sha(root/'EXECUTION-APPROVAL.json'),staged=c.read(control/'STAGED.json'),source_files=len(list(c.files(c.REPO))),source_bytes=c.bytes_in(c.REPO))
for name in ('CONTROLLER-PROCESS.json','CONTROLLER-STARTED.json','LAUNCH-INTENT.json','STOP.json','COMPUTE-COMPLETE.json'):
 p=control/name
 r[name]=dict(sha256=c.sha(p),record=c.read(p)) if p.exists() else None
identity=r['CONTROLLER-PROCESS.json']
if identity:
 pid=identity['record']['pid'];p=Path('/proc')/str(pid)
 if p.exists():
  stat=(p/'stat').read_text().rsplit(')',1)[1].split()
  r['process']=dict(pid=pid,start_ticks=stat[19],state=stat[0],cmdline=(p/'cmdline').read_bytes().replace(b'\\0',b' ').decode(),exact_start=stat[19]==str(identity['record']['start_ticks']))
 else:r['process']=dict(pid=pid,exists=False)
r['controller_logs']={n:(control/n).stat().st_size if (control/n).exists() else None for n in ('controller.out','controller.err')}
events=c.lines(control/'CAMPAIGN.jsonl')
submitted=[e for e in events if e['event']=='submitted'];terminal=[e for e in events if e['event']=='terminal'];accepted=[e for e in events if e['event']=='accepted'];claims=[e for e in events if e['event']=='claim']
specs={s['key']:s for s in c.grid()}
r['ledger']=dict(events=len(events),claims=len(claims),submitted=len(submitted),terminal=len(terminal),accepted=len(accepted),accepted_fits=sum(specs[e['key']]['stage']=='fitting' for e in accepted),accepted_evaluations=sum(specs[e['key']]['stage']=='evaluation' for e in accepted),last_events=events[-4:],unresolved_claims=sorted(set(e['key'] for e in claims)-set(e['key'] for e in submitted)),unaccepted_submissions=[e for e in submitted if e['key'] not in {a['key'] for a in accepted}],gpu_seconds=sum(e['row']['seconds'] for e in terminal if specs[e['key']]['gpu']),cpu_seconds=sum(e['row']['seconds'] for e in terminal if not specs[e['key']]['gpu']),failed_terminal=[e for e in terminal if e['row']['state']!='COMPLETED' or e['row']['exit']!='0:0'])
for name in ('ALL-MODELS-FROZEN.json','TECHNICAL-TRANCHE-PASSED.json'):
 p=run/name;r[name]=dict(sha256=c.sha(p),record=c.read(p)) if p.exists() else None
'''
    if '--scheduler' in sys.argv:
        code+='''if submitted:
 import scheduler
 cmd=['/usr/bin/sacct','-X','-n','-P','-j',','.join(e['job'] for e in submitted),'--format='+scheduler.FIELDS]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
 r['scheduler']=dict(command=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
'''
    code+="print(json.dumps(r))\n"
    p=remote(code)
    receipt=dict(unix=time.time(),returncode=p.returncode,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace'),read_only=True,scientific_aggregates_read=False)
    c.write(dest,receipt)
    c.require(p.returncode==0,'Observation unavailable; never infer failure or retry launch')
    print(receipt['stdout'])

if __name__=='__main__':main()
