"""R6 archive-only recovery: explicit full source roots; no science execution."""
import hashlib,importlib,json,os,sys,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
REPO=ROOT.parents[2]
sys.dont_write_bytecode=True
def require(ok,why):
    if not ok:raise ValueError(why)
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def write(p,v):
    with Path(p).open('xb') as f:f.write(canonical(v)+b'\n');f.flush();os.fsync(f.fileno())
def total(root):return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())
def binding():
    c=read(ROOT/'CONTRACT.json');manifest=sha(ROOT/'SOURCE-MANIFEST.json')
    name='active-counterfactual-verification-preservation-r6-'+manifest[:16]
    return dict(c,manifest=manifest,source=c['research_root']+'/snapshots/'+name,control=c['research_root']+'/staging/'+name)
def load5():
    c=read(ROOT/'CONTRACT.json')
    root=ROOT.parent/'finalization-r5' if os.name=='nt' else Path(c['r5_source'])/c['r5_rel']
    require(sha(root/'SOURCE-MANIFEST.json')==c['r5_manifest'],'Exact R5 manifest')
    for n,h in read(root/'SOURCE-MANIFEST.json')['files'].items():require(sha(root/n)==h,'Unchanged R5 closure')
    sys.path.insert(0,str(root));r=importlib.import_module('r5_core');require(r.ROOT.resolve()==root.resolve(),'Exact R5 import')
    return r
class Context:
    def __init__(self,approval):
        a=read(approval);require(a.get('authorized') is True,'R6 disabled')
        require(a=={'schema':'ACV0-archive-only-r6','authorized':True,'binding':binding()},'Exact R6 authority')
        self.binding=a['binding'];self.approval_sha=sha(approval);self.control=Path(self.binding['control'])
        for n,h in read(ROOT/'SOURCE-MANIFEST.json')['files'].items():require(Path(n).name==n and sha(ROOT/n)==h,'R6 source identity')
        require(sha(ROOT/'BASELINE.json')==self.binding['baseline_sha256'],'R6 baseline identity')
        self.baseline=read(ROOT/'BASELINE.json');r=load5()
        self.old=r.Context(Path(self.binding['r5_control'])/'EXECUTION-APPROVAL.json');self.run=self.old.run
        require(self.old.approval_sha==self.binding['r5_approval_sha256'],'R5 unchanged approval')
def guard(ctx):
    import finalize5
    combined=finalize5.authenticate_complete(ctx.old)
    require(sha(ctx.run/'COMPUTE-COMPLETE.json')==ctx.binding['completion_sha256'],'Existing completion unchanged')
    entries=ctx.baseline['r5_control_members']
    actual={p.relative_to(ctx.old.control).as_posix() for p in ctx.old.control.rglob('*') if p.is_file()}
    require(actual==set(entries),'Unknown R5 control member')
    for n,info in entries.items():
        p=ctx.old.control/n;require(p.stat().st_size==info['bytes'] and sha(p)==info['sha256'],'Changed R5 evidence')
    require(not any('FAILURE' in p.name.upper() or 'STOP' in p.name.upper() for p in ctx.control.rglob('*') if p.is_file()),'New R6 fault; no retry')
    return combined
def roots(ctx):
    # Use the captured root itself, never strip a guessed repository prefix.
    return list(ctx.old.baseline['paths'].items())+[
        ('r5_source',ctx.binding['r5_source']),('r5_control',str(ctx.old.control)),
        ('r6_source',ctx.binding['source']),('r6_control',str(ctx.control))]
def inventory_from_roots(root_list,output,expected):
    items=[]
    require(len({label for label,path in root_list})==len(root_list),'Duplicate root labels')
    for label,path in root_list:
        root=Path(path);require(root.is_dir() and not root.is_symlink(),'Exact source/control root')
        for p in sorted(root.rglob('*')):
            require(not p.is_symlink(),'No archive symlink')
            if p.is_file() and output not in p.parents:
                items.append((label+'/'+p.relative_to(root).as_posix(),p))
    names={n for n,p in items};require(len(names)==len(items),'Unique names')
    for n,info in expected.items():
        require(n in names,'Original root-relative member missing: '+n)
        p=dict(items)[n];require(p.stat().st_size==info['bytes'] and sha(p)==info['sha256'],'Original member changed: '+n)
    return items
def archive(ctx):
    combined=guard(ctx);r=load5();space=r.storage(ctx.old)
    require(space['all_source_control_models_analysis']+total(ROOT)+total(ctx.control)<=500000000,'R6 inclusive500MBcap')
    output=ctx.run/'final-preservation'
    require(not output.exists() and not (ctx.control/'ARCHIVE-INTENT.json').exists(),'One new archive attempt only; never retry/overwrite')
    write(ctx.control/'ARCHIVE-INTENT.json',{'unix':time.time(),'approval_sha256':ctx.approval_sha,'new_jobs':0,'automatic_retry':False})
    start=time.monotonic();cpu=time.process_time()
    try:
        items=inventory_from_roots(roots(ctx),output,ctx.old.baseline['inventory'])
        members={n:{'bytes':p.stat().st_size,'sha256':sha(p)} for n,p in items}
        require(sum(v['bytes'] for v in members.values())<2000000000,'Archive input bound')
        output.mkdir(exist_ok=False);dest=output/'final.tar'
        with dest.open('xb') as stream:
            with tarfile.open(fileobj=stream,mode='w') as tar:
                for n,p in items:tar.add(p,arcname=n,recursive=False)
        from preserve import verify_tar,VOLUME
        verify_tar(dest,members);require(dest.stat().st_size<2000000000,'Archive byte bound')
        write(output/'BACKUP-REQUEST.json',{'archive':dest.as_posix(),'bytes':dest.stat().st_size,'sha256':sha(dest),'members':members,
            'package_sha256':r.SCIENCE_MANIFEST,'approval_sha256':r.WORKER_APPROVAL,'run_name':ctx.run.name,
            'r5_manifest':ctx.binding['r5_manifest'],'r6_manifest':ctx.binding['manifest'],'r6_approval_sha256':ctx.approval_sha,
            'archive_wall_seconds':time.monotonic()-start,'archive_cpu_seconds':time.process_time()-cpu,
            'ssd_volume':VOLUME,'ssd_free_required':40000000000,'automatic_retry':False,'campaign_accounting':combined,
            'r5_archive_invocation_failed_before_creation':True,'root_labels':[label for label,path in roots(ctx)]})
        return {'bytes':dest.stat().st_size,'sha256':sha(dest),'members':len(members),'request':str(output/'BACKUP-REQUEST.json')}
    except BaseException as e:
        write(ctx.control/'FAILURE-R6.json',{'error':repr(e)[:4096],'automatic_retry':False});raise
