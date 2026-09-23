"""ACV0 R3 status-only continuation; original workers and approvals unchanged."""
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
    require(contract['instruction_sha256']==sha(ROOT/'INSTRUCTION.txt') and contract['baseline_sha256']==sha(ROOT/'BASELINE.json'),'R3 contract bytes')
    name='active-counterfactual-verification-control-r3-'+manifest[:16]
    return dict(contract,control_manifest=manifest,control_source=contract['research_root']+'/snapshots/'+name,
                control=contract['research_root']+'/staging/'+name,contract_sha256=sha(ROOT/'CONTRACT.json'))

class Context:
    def __init__(self,approval):
        a=read(approval)
        require(set(a)=={'schema','authorized','instruction','binding'} and a['schema']=='ACV0-control-only-r3','R3 approval schema')
        if a['authorized'] is not True:raise PermissionError('R3 continuation disabled')
        require(a['binding']==binding(sha(ROOT/'SOURCE-MANIFEST.json')),'Exact R3 continuation binding')
        require(hashlib.sha256(a['instruction'].encode()).hexdigest()==a['binding']['instruction_sha256'],'Exact R3 instruction')
        for name,h in read(ROOT/'SOURCE-MANIFEST.json')['files'].items():
            p=ROOT/name;require(p.parent==ROOT and not p.is_symlink() and sha(p)==h,'R3 control source: '+name)
        self.approval=a;self.approval_sha=sha(approval);self.binding=a['binding']
        self.control=Path(self.binding['control']);self.run=Path(self.binding['run'])
        self.baseline=read(ROOT/'BASELINE.json')
        self.science_root=Path(self.binding['scientific_source'])/self.binding['scientific_rel']
        sys.path.insert(0,str(self.science_root))
        self.c=importlib.import_module('common')
        require(self.c.ROOT.resolve()==self.science_root.resolve(),'Original scientific import identity')
        self.worker_approval=Path(self.binding['worker_approval_path'])
        self.auth=self.c.Authorization(self.worker_approval,str(self.run))
        require(self.auth.approval_sha==WORKER_APPROVAL and self.auth.approval['package_sha256']==SCIENCE_MANIFEST,'Original worker authority unchanged')
        self.jobs=self.c.grid()
        require(digest(self.jobs)==self.binding['grid_sha256'] and len(self.jobs)==339,'Original logical339 grid')
        require(self.jobs[0]['key']=='collect-fit-490' and self.jobs[24]['key']=='collect-fit-505','Fixed continuation order')
        require([v['spec'] for v in self.baseline['successful_rows']]==self.jobs[:24],'All24 unchanged suppliers')

def verify_baseline(ctx,exact_run=False):
    expected=ctx.baseline['inventory']
    for name,info in expected.items():
        label,rel=name.split('/',1);root=Path(ctx.baseline['paths'][label]);p=root/rel
        require(p.resolve().is_relative_to(root.resolve()) and not p.is_symlink(),'Original evidence path')
        require(p.stat().st_size==info['bytes'] and sha(p)==info['sha256'],'Original immutable bytes: '+name)
    for label in ctx.baseline['paths']:
        if label=='run' and not exact_run:continue
        root=Path(ctx.baseline['paths'][label])
        actual={label+'/'+p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        require(actual=={n for n in expected if n.startswith(label+'/')},'Original member set: '+label)

def stop_guard(ctx):
    require(sha(ctx.run/'STOP.json')==STOP_SHA,'Only exact resolved R1 STOP permitted')
    require(sha(Path(ctx.baseline['paths']['r2_control'])/'STOP-R2.json')==ctx.binding['resolved_r2_stop_sha256'],'Only exact resolved R2 STOP permitted')
    allowed={n[4:]:v['sha256'] for n,v in ctx.baseline['inventory'].items() if n.startswith('run/') and any(k in Path(n).name.upper() for k in ('STOP','FAILURE'))}
    for p in ctx.run.rglob('*'):
        if p.is_file() and any(k in p.name.upper() for k in ('STOP','FAILURE')):
            name=p.relative_to(ctx.run).as_posix()
            require(name in allowed and sha(p)==allowed[name],'New/unrecognized run STOP')
    for p in ctx.control.rglob('*'):
        if not p.is_file() or not any(k in p.name.upper() for k in ('STOP','FAILURE')):continue
        require(p==ctx.control/'STOP-RESOLUTION.json','Unresolved R3 fault')
        resolved=read(p)
        require(resolved['resolved_stop_path']==str(ctx.run/'STOP.json') and resolved['resolved_stop_sha256']==STOP_SHA
                and resolved['resolved_r2_stop_sha256']==ctx.binding['resolved_r2_stop_sha256']
                and resolved['instruction_sha256']==ctx.binding['instruction_sha256'] and resolved['r3_approval_sha256']==ctx.approval_sha
                and resolved['accepted_existing_sha256']==sha(ctx.control/'ACCEPTED-EXISTING.json'),'Exact authorized stop resolution')

def columns(row):
    # sacct -P has no extra delimiter: an empty last field is still a field.
    r=row.split('|') if isinstance(row,str) else list(row)
    if len(r)==13 and r[-1]=='':r.pop()  # accept explicit -p extra delimiter only
    require(len(r)==12,'Unambiguous scheduler columns')
    return r

def parse_row(row):
    r=columns(row)
    require(all(r[i] for i in (0,1,2,3,4,5,6,7,8,9,10,11)),'Incomplete terminal accounting')
    require(all(r[i].isdigit() for i in (0,4,5,11)),'Invalid numeric accounting')
    tres=dict(v.split('=',1) for v in r[6].split(',') if '=' in v)
    return {'job':r[0],'job_name':r[1],'state':r[2].split()[0],'exit_code':r[3],'seconds':int(r[4]),
            'allocated_cpus':int(r[5]),'allocated_tres':r[6],'gpus':int(tres.get('gres/gpu',0)),
            'node':r[7],'partition':r[8],'qos':r[9],'account':r[10],'time_limit_minutes':int(r[11]),'raw_scheduler':r}

def allocation_contract(spec,row):
    t=dict(v.split('=',1) for v in row['allocated_tres'].split(',') if '=' in v)
    require(row['job'].isdigit() and row['state']=='COMPLETED' and row['exit_code']=='0:0','Successful exact allocation')
    historic=read(ROOT/'CONTRACT.json')['historical_job_names']
    require(row['job_name']==historic.get(row['job'],'acv0r3-'+spec['key']),'Exact allocation task name')
    require(0<=row['seconds']<=spec['seconds'] and row['time_limit_minutes']==spec['seconds']//60,'Original hard envelope')
    require(row['allocated_cpus']==4 and int(t.get('cpu',0))==4 and int(t.get('node',0))==1,'Single-node four-CPU allocation')
    require(row['gpus']==spec['gpu'] and row['account']=='superworld','GPU/account contract')
    require(row['partition']==('a6000' if spec['gpu'] else 'defq') and row['qos']==('normal-a6000' if spec['gpu'] else 'normal'),'Site contract')
    mem=t.get('mem','');wanted='24G' if spec['gpu'] else '8G'
    require(mem in (wanted,str((24 if spec['gpu'] else 8)*1024)+'M'),'Original allocation memory')
    require(bool(row['node']) and not any(x in row['node'] for x in ',[] '),'Unambiguous node')

def association(h,spec,row):
    allocation_contract(spec,row)
    require(spec['gpu']==1 and (h['hostname'],row['node']) in PAIRS,'Exact hostname association pair')
    require(h['slurm_job_id']==row['job'],'Exact hardware/allocation job ID')
    require(h['accepted'] is True and h['query_status']=='complete' and h['cuda_available'] is True
            and h['visible_device_count']==1 and h['device_name']==DEVICE,'Exact CUDA device contract')
    return {'worker_hostname':h['hostname'],'scheduler_node':row['node'],'slurm_job_id':row['job'],
            'rule':'explicit R2 allowlist pairs only; no DNS or prefix matching','device_name':h['device_name'],
            'gpu_uuid_scope':'per-allocation evidence, not a fixed future UUID'}

def verify_worker(ctx,spec,row):
    allocation_contract(spec,row);p=ctx.run/spec['key']
    seal=ctx.c.verify_seal(p,spec);tech=read(p/'TECHNICAL.json')
    require(tech['passed'] is True and tech['spec']==spec and tech['package']==SCIENCE_MANIFEST
            and tech['approval']==WORKER_APPROVAL,'Original worker source/approval/spec')
    require(tech['attempt']==(2 if spec['key']=='collect-fit-490' else 1),'Scientific task attempt')
    require(tech['hard_seconds']==spec['seconds'] and tech['work_seconds']==ctx.c.work_seconds(spec)
            and tech['supervisor_seconds']==ctx.c.supervisor_seconds(spec),'Worker preservation envelope')
    require(sum((p/n).stat().st_size for n in seal['files'])+(p/'SEAL.json').stat().st_size<=spec['byte_cap'],'Worker byte cap')
    receipt={'key':spec['key'],'job':row['job'],'attempt':tech['attempt'],'seal_sha256':sha(p/'SEAL.json')}
    if spec['gpu']:
        h=read(p/'HARDWARE.json');receipt['association']=association(h,spec,row)
        require(tech['hardware']==h and tech['models_unchanged'] is True and tech['checks']['passed'] is True,'Original technical/model checks')
        require(tech['checks']['reference']==spec['reference'],'Technical source identity')
        if spec['stage']=='collection':require(tech['checks']['role']==spec['role'] and tech['checks']['physical_replay_checked'],'Role/replay check')
    return receipt

def accept_existing(ctx):
    rows=ctx.baseline['successful_rows'];require(len(rows)==24 and [v['spec'] for v in rows]==ctx.jobs[:24],'Exact24 reused rows')
    require(rows[0]['job']=='304193' and rows[-1]['job']=='304220' and rows[-1]['seconds']==160,'Pinned boundary suppliers')
    accepted=[]
    for spec,row in zip(ctx.jobs[:24],rows):
        for name in ('SEAL.json','TECHNICAL.json','HARDWARE.json'):
            info=ctx.baseline['inventory']['run/'+spec['key']+'/'+name]
            require(sha(ctx.run/spec['key']/name)==info['sha256'],'Existing immutable worker: '+spec['key']+'/'+name)
        receipt=verify_worker(ctx,spec,row)
        receipt.update(event='accepted_existing',accepted_unix=time.time(),new_submission=False,
            originally_accepted_by_r2_controller=row['job']!='304220',
            message='Reused existing completion; no scientific work repeated. Missing R2 acceptance of304220 resolved now, not backdated.')
        accepted.append(receipt)
    require(23+sum(v['seconds']*v['gpus'] for v in rows)==3015,'All25 prior allocation charges')
    return rows,accepted

def validate_prior_scheduler(ctx,accounting,queue):
    expected={v['job']:v for v in ctx.baseline['allocations']}
    found=[parse_row(s) for s in accounting.splitlines() if 'acv0' in s.lower() or s.split('|')[0] in expected]
    require(len(found)==25 and {v['job']:v for v in found}==expected,'Unknown or changed prior ACV0 attempt')
    require(not any('acv0' in s.lower() or s.split('|')[0] in expected for s in queue.splitlines()),'Live prior campaign job')

def ensure_unstarted(ctx):
    require(not any((ctx.control/n).exists() for n in ('CONTROLLER-STARTED.json','CAMPAIGN-R3.jsonl','ACCEPTED-EXISTING.json','COMPUTE-COMPLETE.json','STOP-R3.json')),'Already-started R3; no restart')
    require(not any((ctx.run/j['key']).exists() for j in ctx.jobs[24:]),'Never-submitted task directory already exists')
    require(not any((ctx.run/n).exists() for n in ('MODEL-FREEZE.json','PRE-ANALYSIS-ACCOUNTING.json','COMPUTE-COMPLETE.json','final-preservation')),'Unexpected continuation outputs')
    require(read(ctx.run/'TECHNICAL-TRANCHE-PASSED.json')==ctx.baseline['gate'],'Preserved tranche changed')

def reconcile(ctx):
    verify_baseline(ctx,exact_run=True);stop_guard(ctx);ensure_unstarted(ctx)
    for old in ({'pid':684587,'start_ticks':'893012584'},ctx.baseline['r2_controller']):
        stat=Path('/proc',str(old['pid']),'stat')
        if stat.exists():
            f=stat.read_text().rsplit(')',1)[1].split();require(f[19]!=str(old['start_ticks']) or f[0]=='Z','Prior controller active')
    a=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],'--format='+FIELDS],capture_output=True,text=True,timeout=30)
    q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
    require(a.returncode==q.returncode==0,'Prior scheduler observation failed')
    validate_prior_scheduler(ctx,a.stdout,q.stdout)
    import recovery
    recovery.authenticate_prior_files();recovery.verify_prior_copy(ctx.run)
    return {'unix':time.time(),'failed_job':'304189','completed_suppliers':[v['job'] for v in ctx.baseline['successful_rows']],'gpu_seconds':3015,
            'cpu_stage_seconds':0,'live_or_unresolved':0,'old_controller_inactive':True,'baseline_sha256':sha(ROOT/'BASELINE.json')}

def storage(ctx):
    import dispatch
    base=dispatch.storage(ctx.c.ROOT,ctx.run,ctx.jobs)
    extra=total(ROOT)+total(ctx.control)+total(ctx.baseline['paths']['r2_source'])+total(ctx.baseline['paths']['r2_control'])
    require(base['source_control_models_analysis']+extra<=500000000,'R2/R3-inclusive source/model/control/analysis cap')
    require(base['full_live_reservation']<=2000000000 and base['inclusive_reservation']<=8000000000,'Full future storage reservation')
    return dict(base,r2_r3_source_and_control_bytes=extra,source_control_models_analysis_including_r2_r3=base['source_control_models_analysis']+extra)
