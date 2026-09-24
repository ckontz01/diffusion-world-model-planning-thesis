"""Strict technical-recovery authority, separate from the frozen science capability."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
SCIENCE='9f91156fd11a5d54172e8cec79d37ca50199c132780b5aee3636f34b0dd2e916'
APPROVAL='22cf11af0742c4a17987d783cf984c313dfc45beaff2a7ba32d1b2c6f36f3d27'
RESEARCH='/lustreFS/data/superworld/ckontzias/thesis'
NAME='active-counterfactual-mechanism-replication-control-r1'
OLD_SOURCE=RESEARCH+'/snapshots/active-counterfactual-mechanism-replication-v1-9f91156fd11a5d54'
OLD_CONTROL=RESEARCH+'/staging/active-counterfactual-mechanism-replication-v1-9f91156fd11a5d54'
RUN=RESEARCH+'/experiments/active-counterfactual-mechanism-replication-v1/run-9f91156fd11a5d54'
REL='docs/active-counterfactual-mechanism-replication-20260924/runtime-v2'
science_root=Path(OLD_SOURCE)/REL
if not science_root.exists():science_root=REPO/REL
sys.dont_write_bytecode=True
sys.path.insert(0,str(science_root))
import common as c
sys.path.insert(0,str(ROOT))
require=c.require
sha=c.sha
read=c.read
write=c.write

def binding():
    h=sha(ROOT/'SOURCE-MANIFEST.json')
    contract=read(ROOT/'CONTRACT.json')
    return dict(manifest=h,contract=sha(ROOT/'CONTRACT.json'),source=RESEARCH+'/snapshots/'+NAME+'-'+h[:16],control=RESEARCH+'/staging/'+NAME+'-'+h[:16],run=RUN,science_manifest=SCIENCE,worker_approval=APPROVAL,instruction=sha(ROOT/'INSTRUCTION.txt'),baseline=sha(ROOT/'BASELINE.json'),max_new_attempts=8197,max_total_attempts=8198)

class Context:
    def __init__(self,approval):
        a=read(approval)
        require(set(a)=={'schema','authorized','instruction','binding'} and a['schema']=='ACVM1-recovery-r1','R1 approval schema')
        if a['authorized'] is not True:raise PermissionError('R1 recovery DISABLED')
        require(a['binding']==binding() and a['instruction']==(ROOT/'INSTRUCTION.txt').read_text(encoding='utf8'),'Exact recovery authority')
        contract=read(ROOT/'CONTRACT.json')
        require(contract['instruction_sha256']==sha(ROOT/'INSTRUCTION.txt') and contract['baseline_sha256']==sha(ROOT/'BASELINE.json') and contract['caps']==c.caps() and contract['max_new_attempts']==8197 and contract['max_total_attempts']==8198,'Exact finite recovery contract')
        for n,h in read(ROOT/'SOURCE-MANIFEST.json')['files'].items():
            require(Path(n).name==n and sha(ROOT/n)==h,'Frozen recovery source: '+n)
        self.binding=a['binding'];self.approval=a;self.approval_sha=sha(approval)
        self.control=Path(self.binding['control']);self.run=Path(RUN)
        self.old_control=Path(OLD_CONTROL);self.worker_approval=self.old_control/'EXECUTION-APPROVAL.json'
        self.auth=c.Authorization(self.worker_approval,RUN)
        require(self.auth.approval_sha==APPROVAL and self.auth.approval['package_sha256']==SCIENCE,'Unchanged scientific capability')
        self.baseline=read(ROOT/'BASELINE.json')
        self.jobs=c.grid()
        require(len(self.jobs)==8197 and self.jobs[0]['key']=='fit-pair1-joint','Original fixed scientific grid')

def baseline(ctx,exact_run=False):
    for n,i in ctx.baseline['inventory'].items():
        label,rel=n.split('/',1);p=Path(ctx.baseline['roots'][label])/rel
        require(not p.is_symlink() and p.stat().st_size==i['bytes'] and sha(p)==i['sha256'],'Retained original evidence: '+n)
    for label,root in ctx.baseline['roots'].items():
        if label=='run' and not exact_run:continue
        require({label+'/'+p.relative_to(root).as_posix() for p in c.files(root)}=={n for n in ctx.baseline['inventory'] if n.startswith(label+'/')},'Original member set: '+label)
    require(sha(ctx.old_control/'STOP.json')==ctx.baseline['stop_sha256'],'Only diagnosed historical STOP resolved')
    c.verify_seal(ctx.run/'reused')

def guard(ctx):
    require(sha(ctx.old_control/'STOP.json')==ctx.baseline['stop_sha256'],'Historical STOP changed')
    require(not (ctx.control/'STOP.json').exists(),'New recovery STOP')
    resolution=ctx.control/'HISTORICAL-RESOLUTION.json'
    if resolution.exists():
        entry=read(resolution)
        require(entry['approval']==ctx.approval_sha and entry['prior_stop']==ctx.baseline['stop_sha256'] and entry['failed_job']=='304589' and entry['total_attempts_max']==8198,'Exact historical fault resolution')
    allowed={n[4:] for n in ctx.baseline['inventory'] if n.startswith('run/') and any(x in n.upper() for x in ('STOP','FAILURE'))}
    for p in c.files(ctx.run):
        if any(x in p.name.upper() for x in ('STOP','FAILURE')):require(p.relative_to(ctx.run).as_posix() in allowed,'Unresolved worker failure')

def storage_check(ctx,done):
    import storage
    answer=storage.check(c.REPO,ctx.control,ctx.run,ctx.jobs,done)
    extra=c.bytes_in(ROOT)+c.bytes_in(ctx.old_control)
    require(answer['group_bytes']+extra<=storage.GROUP,'All original/recovery nonworker bytes included')
    members=sum(1 for root in (c.REPO,ROOT,ctx.old_control,ctx.control,ctx.run) for _ in c.files(root))
    require(members<=storage.MAX_MEMBERS,'All original/recovery archive members')
    return dict(answer,retained_original_and_recovery_extra_bytes=extra,total_members=members)

def slurm_log(run,key,suffix):
    if key=='fit-pair1-joint' and suffix.startswith('.slurm'):suffix='.r1'+suffix
    return Path(run)/'logs'/(key+suffix)
