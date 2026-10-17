"""Phase-labelled lstat-only metadata, not the timed-out recursive hash reader."""
import ast,base64,json,shlex,subprocess,sys
from wm_diag0_rc1_completion_v1.common import ROOT,write_new
from wm_diag0_rc1_grid_v1.common import RUN

DOC=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
READ=r'''
import hashlib,json,os,pathlib,resource,stat,sys,time
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
lo,hi=resource.getrlimit(resource.RLIMIT_AS);cap=min([8589934592]+[x for x in (lo,hi) if x!=resource.RLIM_INFINITY]);resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
began=time.monotonic();r=pathlib.Path(RUN);p=r/'source/GRID-CONTRACT.json'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def phase(name):sys.stderr.write('METADATA_PHASE '+name+'\n');sys.stderr.flush()
phase('executed_contract')
if ident(p)['sha256']!='da2766c3f8c33266ee54cea9fb2e3bdf650046e9a61ac39c209816f1b1e7514b':raise ValueError('exact frozen grid contract')
c=json.loads(p.read_text());base=r.parent
phase('registered_runtime_manifest')
manifest=pathlib.Path(c['recovery']['old_run'])/'controls/RUNTIME-MANIFEST.json'
if ident(manifest)!=c['runtime_manifest']:raise ValueError('original runtime manifest identity')
rm=json.loads(manifest.read_text())
def scan(root,label):
 root=pathlib.Path(root)
 if root.is_symlink() or not root.is_dir():raise ValueError('explicit physical whole root')
 count=0;size=0;largest=0;aliases={};h=hashlib.sha256();directories=0
 for directory,dirs,names in os.walk(str(root),followlinks=False):
  directories+=1
  for n in sorted(list(dirs)+names):
   q=pathlib.Path(directory)/n;s=q.lstat();rel=q.relative_to(root).as_posix()
   if stat.S_ISLNK(s.st_mode):
    target=os.readlink(str(q));aliases[rel]=target
    if n in dirs:dirs.remove(n)
    if len(aliases)>256:raise ValueError('bounded alias review output')
    row=[rel,'inert-alias',target,s.st_mode,s.st_mtime_ns,s.st_ctime_ns]
   elif stat.S_ISREG(s.st_mode):
    count+=1;size+=s.st_size;largest=max(largest,s.st_size)
    if count>100000 or size>13500000000 or s.st_size>4000000000:raise ValueError('whole-root member/byte limit')
    row=[rel,'ordinary',s.st_size,s.st_mode,s.st_mtime_ns,s.st_ctime_ns]
   elif stat.S_ISDIR(s.st_mode):continue
   else:raise ValueError('special file requires explicit stop/review')
   h.update(json.dumps(row,sort_keys=True,separators=(',',':')).encode());h.update(b'\n')
 return {'root':str(root),'regular_files':count,'logical_regular_bytes':size,'largest_regular_member':largest,'directories':directories,
         'metadata_inventory_sha256_NOT_file_content_hash':h.hexdigest(),'aliases_metadata_only_candidates':aliases}
phase('full_venv_lstat_only')
venv=scan(c['venv'],'runtime')
if venv['logical_regular_bytes']>2100000000:raise ValueError('full venv reservation exceeded')
phase('whole_canonical_lineages_lstat_only')
children={}
for child in sorted(base.iterdir()):
 phase('lineage_'+child.name);children[child.name]=scan(child,'study')
phase('explicit_external_file_sizes')
sif=pathlib.Path(c['sif']).lstat()
if not stat.S_ISREG(sif.st_mode) or sif.st_size!=3139002368:raise ValueError('SIF size/type binding')
models={}
for name,x in c['lewm'].items():
 q=pathlib.Path(x['path']);s=q.lstat()
 if not stat.S_ISREG(s.st_mode) or s.st_size!=x['bytes']:raise ValueError('retained original object size/type')
 models[name]={'path':str(q),'bytes':s.st_size,'expected_sha256_NOT_reread':x['sha256']}
f=os.statvfs(str(base))
result={'status':'LSTAT_ONLY_ACTUAL_ROOT_RUNTIME_ALIAS_METADATA_NOT_FINAL_GATE','grid_contract':ident(p),'runtime_manifest':ident(manifest),
 'registered_runtime_members':len(rm['members']),'registered_runtime_member_bytes_NOT_full_venv':sum(x['bytes'] for x in rm['members'].values()),
 'full_venv':venv,'contract_runtime_aliases':c['runtime_symlinks'],'runtime_aliases_exactly_match_executed_contract':venv['aliases_metadata_only_candidates']==c['runtime_symlinks'],
 'canonical_children':children,'logical_current_canonical_regular_bytes':sum(x['logical_regular_bytes'] for x in children.values()),
 'SIF':{'path':c['sif'],'bytes':sif.st_size,'expected_sha256_NOT_reread':c['sif_sha256']},'LeWM_objects':models,
 'cluster_free_bytes':f.f_bavail*f.f_frsize,'elapsed_seconds':time.monotonic()-began,
 'research_values_outcomes_predictions_quality_read':False,'scientific_runtime_imported':False,'scheduler_calls':0,'filesystem_mutations':0,
 'full_file_content_runtime_authentication':False,'fresh_full_future_storage_proof':False,'final_gate_ready':False}
if len(json.dumps(result).encode())>64000:raise ValueError('bounded metadata result')
print(json.dumps(result,sort_keys=True))
'''

def program():
    text='RUN='+repr(RUN)+'\n'+READ;ast.parse(text,feature_version=(3,6));return text

def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive metadata label')
    DOC.mkdir(exist_ok=True);dst=DOC/('METADATA-'+label+'.json');started=DOC/('METADATA-'+label+'.started.json')
    if dst.exists() or started.exists():raise FileExistsError('no repeated/ambiguous metadata traversal')
    from wm_diag0_rc1_completion_v1.common import identity
    write_new(started,{'source':identity(__file__),'scope':'lstat-only, phase-labelled, no original metadata.py rerun','scheduler_calls':0})
    encoded=base64.b64encode(program().encode()).decode();remote='timeout --kill-after=1s 90s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    cmd=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','100s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','prometheus',remote]
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=105)
    if p.returncode:raise RuntimeError('metadata read unavailable, not inferred research failure; phases: '+p.stderr.decode(errors='replace')[-6000:])
    if len(p.stdout)>64000:raise ValueError('bounded metadata stdout')
    result=json.loads(p.stdout);write_new(dst,result,limit=64000)
    print(json.dumps({'status':result['status'],'canonical_children':len(result['canonical_children']),'full_venv_bytes':result['full_venv']['logical_regular_bytes'],
                      'full_venv_aliases':result['full_venv']['aliases_metadata_only_candidates'],'aliases_match_contract':result['runtime_aliases_exactly_match_executed_contract'],
                      'scheduler_calls':0,'research_values_outcomes_predictions_quality_read':False,'final_gate_ready':False}))

if __name__=='__main__':main()
