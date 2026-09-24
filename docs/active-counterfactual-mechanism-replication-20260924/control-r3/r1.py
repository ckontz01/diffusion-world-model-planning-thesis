"""R3 control-only continuation; carry one sealed R2 success without recomputation."""
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
NAME='active-counterfactual-mechanism-replication-control-r3'
OLD_SOURCE=RESEARCH+'/snapshots/active-counterfactual-mechanism-replication-v1-9f91156fd11a5d54'
OLD_CONTROL=RESEARCH+'/staging/active-counterfactual-mechanism-replication-v1-9f91156fd11a5d54'
R1_SOURCE=RESEARCH+'/snapshots/active-counterfactual-mechanism-replication-control-r1-2af896606b8d7f9a'
R1_CONTROL=RESEARCH+'/staging/active-counterfactual-mechanism-replication-control-r1-2af896606b8d7f9a'
R2_SOURCE=RESEARCH+'/snapshots/active-counterfactual-mechanism-replication-control-r2-068dff5df9b541ba'
R2_CONTROL=RESEARCH+'/staging/active-counterfactual-mechanism-replication-control-r2-068dff5df9b541ba'
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
    return dict(manifest=h,contract=sha(ROOT/'CONTRACT.json'),source=RESEARCH+'/snapshots/'+NAME+'-'+h[:16],control=RESEARCH+'/staging/'+NAME+'-'+h[:16],run=RUN,science_manifest=SCIENCE,worker_approval=APPROVAL,instruction=sha(ROOT/'INSTRUCTION.txt'),baseline=sha(ROOT/'BASELINE-TRANSPORT.json'),max_new_attempts=8196,max_total_attempts=8199)

class Context:
    def __init__(self,approval):
        a=read(approval)
        require(set(a)=={'schema','authorized','instruction','binding'} and a['schema']=='ACVM1-recovery-r3','R3 approval schema')
        if a['authorized'] is not True:raise PermissionError('R3 recovery DISABLED')
        require(a['binding']==binding() and a['instruction']==(ROOT/'INSTRUCTION.txt').read_text(encoding='utf8'),'Exact recovery authority')
        contract=read(ROOT/'CONTRACT.json')
        proposed=dict(c.caps());proposed['cpu_stage_allocation_seconds']=36008;proposed['cpu_core_seconds_reservation']=144032
        require(contract['instruction_sha256']==sha(ROOT/'INSTRUCTION.txt') and contract['baseline_sha256']==sha(ROOT/'BASELINE-TRANSPORT.json') and contract['caps']==proposed and contract['max_new_attempts']==8196 and contract['max_total_attempts']==8199 and contract['prior_cpu_seconds']==19,'Exact finite recovery contract')
        for n,h in read(ROOT/'SOURCE-MANIFEST.json')['files'].items():
            require(Path(n).name==n and sha(ROOT/n)==h,'Frozen recovery source: '+n)
        self.binding=a['binding'];self.approval=a;self.approval_sha=sha(approval)
        self.control=Path(self.binding['control']);self.run=Path(RUN)
        self.old_control=Path(OLD_CONTROL);self.worker_approval=self.old_control/'EXECUTION-APPROVAL.json'
        self.r1_control=Path(R1_CONTROL)
        self.r2_control=Path(R2_CONTROL)
        self.auth=c.Authorization(self.worker_approval,RUN)
        require(self.auth.approval_sha==APPROVAL and self.auth.approval['package_sha256']==SCIENCE,'Unchanged scientific capability')
        transport=read(ROOT/'BASELINE-TRANSPORT.json')
        require(transport['returncode']==0 and not transport['stderr'],'Authenticated R2 read-only audit')
        self.baseline=json.loads(transport['stdout'])
        self.jobs=c.grid()
        require(len(self.jobs)==8197 and self.jobs[0]['key']=='fit-pair1-joint' and self.baseline['successful_tasks']==1,'Original fixed scientific grid and one retained fit')

def baseline(ctx,exact_run=False):
    for n,i in ctx.baseline['inventory'].items():
        label,rel=n.split('/',1);p=Path(ctx.baseline['roots'][label])/rel
        require(not p.is_symlink() and p.stat().st_size==i['bytes'] and sha(p)==i['sha256'],'Retained original evidence: '+n)
    for label,root in ctx.baseline['roots'].items():
        if label=='run' and not exact_run:continue
        actual={label+'/'+p.relative_to(root).as_posix() for p in c.files(root)}
        expected={n for n in ctx.baseline['inventory'] if n.startswith(label+'/')}
        require(actual==expected,'Historical member set: '+label)
    require(sha(ctx.old_control/'STOP.json')==ctx.baseline['original_stop_sha256'] and sha(ctx.r1_control/'STOP.json')==ctx.baseline['r1_stop_sha256'] and sha(ctx.r2_control/'STOP.json')==ctx.baseline['r2_stop_sha256'],'Only diagnosed historical STOPs resolved')
    c.verify_seal(ctx.run/'reused')

def guard(ctx):
    require(sha(ctx.old_control/'STOP.json')==ctx.baseline['original_stop_sha256'] and sha(ctx.r1_control/'STOP.json')==ctx.baseline['r1_stop_sha256'] and sha(ctx.r2_control/'STOP.json')==ctx.baseline['r2_stop_sha256'],'Historical STOP changed')
    require(not (ctx.control/'STOP.json').exists(),'New recovery STOP')
    resolution=ctx.control/'HISTORICAL-RESOLUTION.json'
    if resolution.exists():
        entry=read(resolution)
        require(entry['approval']==ctx.approval_sha and entry['prior_stops']==[ctx.baseline['original_stop_sha256'],ctx.baseline['r1_stop_sha256'],ctx.baseline['r2_stop_sha256']] and entry['prior_jobs']==['304589','304591','304593'] and entry['total_attempts_max']==8199,'Exact historical fault resolution')
    accepted=ctx.control/'ACCEPTED-EXISTING.json'
    if accepted.exists():
        entry=read(accepted)
        require(entry['job']=='304593' and entry['key']=='fit-pair1-joint' and entry['seal']==ctx.baseline['fit_seal_sha256'] and entry['approval']==ctx.approval_sha,'One authenticated retained fit')
    allowed={n[4:] for n in ctx.baseline['inventory'] if n.startswith('run/') and any(x in n.upper() for x in ('STOP','FAILURE'))}
    if 'fit-pair1-joint/FAILURE.json' in allowed:allowed.add('recovery-history/r1/fit-pair1-joint/FAILURE.json')
    for p in c.files(ctx.run):
        if any(x in p.name.upper() for x in ('STOP','FAILURE')):require(p.relative_to(ctx.run).as_posix() in allowed,'Unresolved worker failure')

def storage_check(ctx,done):
    import storage
    answer=storage.check(c.REPO,ctx.control,ctx.run,ctx.jobs,done)
    extra=c.bytes_in(ROOT)+c.bytes_in(ctx.old_control)+c.bytes_in(Path(R1_SOURCE))+c.bytes_in(ctx.r1_control)+c.bytes_in(Path(R2_SOURCE))+c.bytes_in(ctx.r2_control)
    require(answer['group_bytes']+extra<=storage.GROUP,'All original/recovery nonworker bytes included')
    members=sum(1 for root in (c.REPO,Path(R1_SOURCE),Path(R2_SOURCE),ROOT,ctx.old_control,ctx.r1_control,ctx.r2_control,ctx.control,ctx.run) for _ in c.files(root))
    require(members<=storage.MAX_MEMBERS,'All original/recovery archive members')
    return dict(answer,retained_original_and_recovery_extra_bytes=extra,total_members=members)

def slurm_log(run,key,suffix):
    return Path(run)/'logs'/(key+suffix)

def authenticated_imports():
    """Give sealed study modules precedence over unrelated installed packages."""
    import importlib.util
    base=c.REPO/'docs/active-counterfactual-verification-20260923'
    bindings=base/'bindings-r1'
    manifest=read(c.ROOT/'SOURCE-MANIFEST.json')['files']
    for name,path in (('tree',base/'tree.py'),('model',base/'model.py')):
        rel=path.relative_to(c.REPO).as_posix()
        require(path.is_file() and sha(path)==manifest[rel],'Authenticated study module: '+name)
        loaded=sys.modules.get(name)
        require(loaded is None or Path(loaded.__file__).resolve()==path.resolve(),'Unexpected preloaded '+name)
    for path in (base,bindings):
        value=str(path)
        if value in sys.path:sys.path.remove(value)
        sys.path.insert(0,value)
    for name,path in (('tree',base/'tree.py'),('model',base/'model.py')):
        spec=importlib.util.find_spec(name)
        require(spec is not None and Path(spec.origin).resolve()==path.resolve(),'Study module origin: '+name)
