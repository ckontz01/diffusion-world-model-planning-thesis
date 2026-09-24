"""ACV0 R5 finalization-only recovery; no worker execution capability."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
REPO=BASE.parent.parent
SCIENCE_MANIFEST='c2c6fcbe8c41fed22d0fde17bcb5f8cd456a74c1cb0d77039f4df94d86e0d468'
WORKER_APPROVAL='e1e4b6f6d0e0d1fbb83e89d165be793128f02130647e21a1c12c5892d7d90460'
STOP_SHA='298615b25325a74d113cbda540528bc4b64508a0273b8dd1f1428b1c733f38fe'
DEVICE='NVIDIA RTX 6000 Ada Generation'
PAIRS=(('gpu09.cluster','gpu09'),('gpu09','gpu09'))
EXISTING_HASHES={'SEAL.json':'c280ffb2e71288e8ea40fc5db34ff42fb464a928f42ab388e8e9b14abb8b3b6a',
 'HARDWARE.json':'44729aa05006bead67008711e31c6448678f2181076b0040c8fde3bb25cdec07',
 'TECHNICAL.json':'6eb9997d681fa98953f6e0917ad89933b30cc9ef3c28934ba65db01be4ad6a7b'}
FIELDS='JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList,Partition,QOS,Account,TimelimitRaw'
sys.dont_write_bytecode=True

def require(ok,message):
    if not ok:raise ValueError(message)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,v):
    with Path(p).open('xb') as f:f.write(canonical(v)+b'\n');f.flush();os.fsync(f.fileno())
def append(p,v):
    with Path(p).open('ab') as f:f.write(canonical(v)+b'\n');f.flush();os.fsync(f.fileno())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]
def total(root):return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())

def binding(manifest):
    contract=read(ROOT/'CONTRACT.json')
    require(contract['instruction_sha256']==sha(ROOT/'INSTRUCTION.txt') and contract['baseline_sha256']==sha(ROOT/'BASELINE.json'),'R5 contract bytes')
    require(contract['authority_sha256']==sha(ROOT/'MONITORING-AUTHORIZATION.md'),'Direct authority identity')
    name='active-counterfactual-verification-finalization-r5-'+manifest[:16]
    return dict(contract,control_manifest=manifest,control_source=contract['research_root']+'/snapshots/'+name,
                control=contract['research_root']+'/staging/'+name,contract_sha256=sha(ROOT/'CONTRACT.json'))

def load_r4():
    contract=read(ROOT/'CONTRACT.json')
    path=ROOT.parent/'control-r4' if os.name=='nt' else Path(contract['r4_source'])/contract['r4_rel']
    require(sha(path/'SOURCE-MANIFEST.json')==contract['r4_manifest'],'Original R4 manifest')
    for n,h in read(path/'SOURCE-MANIFEST.json')['files'].items():require(sha(path/n)==h,'Original R4 closure: '+n)
    sys.path.insert(0,str(path));old=importlib.import_module('r4_core')
    require(old.ROOT.resolve()==path.resolve(),'Exact R4 import location');return old

class Context:
    def __init__(self,approval):
        a=read(approval)
        require(set(a)=={'schema','authorized','instruction','binding'} and a['schema']=='ACV0-finalization-only-r5','R5 approval schema')
        if a['authorized'] is not True:raise PermissionError('R5 finalization disabled')
        require(a['binding']==binding(sha(ROOT/'SOURCE-MANIFEST.json')),'Exact R5 binding')
        require(hashlib.sha256(a['instruction'].encode()).hexdigest()==a['binding']['instruction_sha256'],'Exact instruction')
        for n,h in read(ROOT/'SOURCE-MANIFEST.json')['files'].items():require(Path(n).name==n and sha(ROOT/n)==h,'R5 frozen source: '+n)
        self.approval=a;self.approval_sha=sha(approval);self.binding=a['binding'];self.baseline=read(ROOT/'BASELINE.json')
        self.control=Path(self.binding['control']);self.run=Path(self.binding['run'])
        old=load_r4();self.r4=old.Context(Path(self.binding['r4_control'])/'EXECUTION-APPROVAL.json')
        require(self.r4.approval_sha==self.binding['r4_approval_sha256'] and self.r4.run==self.run,'Unchanged R4 authority/run')
        self.r4.recovery_context=self;self.jobs=self.r4.jobs
        require(self.baseline['successful_tasks']==339 and self.baseline['attempts']==340
                and self.binding['new_allocations']==self.binding['replacements']==self.binding['reanalysis']==0,'Finalization only')

def guard(ctx):
    """Exact old STOP permitted only through new authority; unknown faults block."""
    require(sha(ctx.r4.control/'STOP-R4.json')==ctx.binding['r4_stop_sha256'],'Exact known R4 STOP only')
    expected=ctx.baseline['inventory']
    for name,info in expected.items():
        label,rel=name.split('/',1);root=Path(ctx.baseline['paths'][label]);p=root/rel
        require(p.resolve().is_relative_to(root.resolve()) and not p.is_symlink(),'Evidence path')
        require(p.stat().st_size==info['bytes'] and sha(p)==info['sha256'],'Original byte changed: '+name)
    for label,path in ctx.baseline['paths'].items():
        root=Path(path);actual=set()
        for p in root.rglob('*'):
            if not p.is_file():continue
            rel=p.relative_to(root).as_posix()
            if label=='run' and (rel=='COMPUTE-COMPLETE.json' or rel.startswith('final-preservation/')):continue
            actual.add(label+'/'+rel)
        require(actual=={n for n in expected if n.startswith(label+'/')},'Unknown historical member: '+label)
    old=ctx.baseline['r4_controller'];stat=Path('/proc',str(old['pid']),'stat')
    if stat.exists():
        f=stat.read_text().rsplit(')',1)[1].split();require(f[19]!=old['start_ticks'] or f[0]=='Z','Original R4 controller active')
    for p in ctx.control.rglob('*'):
        if p.is_file() and any(s in p.name.upper() for s in ('STOP','FAILURE')):
            require(p==ctx.control/'STOP-RESOLUTION.json','New R5 fault; do not retry')
            s=read(p);require(s['original_r4_stop_sha256']==ctx.binding['r4_stop_sha256'] and s['r5_approval_sha256']==ctx.approval_sha
                and s['baseline_sha256']==ctx.binding['baseline_sha256'] and s['scientific_jobs_resubmitted']==0,'Exact R5 resolution')

def result_from_ledger(ctx):
    ledger=lines(ctx.r4.control/'CAMPAIGN-R4.jsonl');terminal=[v for v in ledger if v['event']=='terminal']
    rows=ctx.r4.baseline['successful_rows']+terminal
    require(rows==ctx.baseline['successful_rows'] and [v['spec'] for v in rows]==ctx.jobs,'All339 original rows unchanged')
    gpu=23+sum(v['seconds']*v['gpus'] for v in rows if v['spec']['gpu'])
    cpu=sum(v['seconds'] for v in rows if not v['spec']['gpu'])
    require(gpu==ctx.binding['gpu_seconds'] and cpu==ctx.binding['cpu_stage_seconds'],'Frozen original cumulative charges')
    return dict(jobs=rows,campaign_gpu_seconds=gpu,campaign_cpu_stage_seconds=cpu,new_r4_allocations=302,
        campaign_allocations=340,successful_unique_tasks=339,historical_failed_allocations=1,
        previously_authorized_replacements=1,new_replacements_authorized=0,automatic_retry_count=0)

def accept_existing(ctx):
    old=load_r4();rows=result_from_ledger(ctx)['jobs']
    return rows,[old.verify_worker(ctx.r4,j,row) for j,row in zip(ctx.jobs,rows)]

def reconcile(ctx):
    guard(ctx)
    import validation5
    snapshot=validation5.scheduler_snapshot(ctx.r4,result_from_ledger(ctx))
    require({v['job']:v for v in snapshot['allocations']}=={v['job']:v for v in ctx.baseline['allocations']},'Exact340 original attempts and charges')
    return snapshot

def storage(ctx):
    base=load_r4().storage(ctx.r4);extra=total(ROOT)+total(ctx.control)
    require(base['source_control_models_analysis_including_r2_r4']+extra<=500000000,'R5-inclusive control cap')
    require(total(ctx.run)+extra<2000000000,'Current live bound')
    return dict(base,r5_source_control_bytes=extra,all_source_control_models_analysis=base['source_control_models_analysis_including_r2_r4']+extra)
