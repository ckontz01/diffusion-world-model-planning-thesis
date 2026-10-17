"""One bounded read-only failed-parent forensic capture. No research payloads."""
import ast,base64,hashlib,json,shlex,subprocess
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,identity,write_new

CODE=r'''
import hashlib,json,os,pathlib,re,resource,time
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
lo,hi=resource.getrlimit(resource.RLIMIT_AS);cap=min([8589934592]+[x for x in (lo,hi) if x!=resource.RLIM_INFINITY]);resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
root=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/campaign-v4-rc1-grid-v1')
task=root/'tasks/grid-66';cp=root/'source/GRID-CONTRACT.json';expected='da2766c3f8c33266ee54cea9fb2e3bdf650046e9a61ac39c209816f1b1e7514b'
if hashlib.sha256(cp.read_bytes()).hexdigest()!=expected:raise ValueError('exact executed grid contract')
c=json.loads(cp.read_text())
def ident(p,limit):
 if p.is_symlink() or not p.is_file() or p.stat().st_size>limit:raise ValueError('bounded ordinary evidence file')
 h=hashlib.sha256();n=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):
   n+=len(b)
   if n>limit:raise ValueError('evidence grew')
   h.update(b)
 return {'bytes':n,'sha256':h.hexdigest()}
controls={}
for name,p in [('STOP',root/'controls/STOP.json')]+[(n,task/'controls'/(n+'.json')) for n in ('STARTED','RESULT','WORKER-SUCCESS','ACCEPTED','CANCEL-PENDING')]:
 if p.exists():controls[name]={'identity':ident(p,20000),'technical_body':json.loads(p.read_text())}
logs={}
for name,p in [('worker',task/'logs/worker.log'),('slurm',root/'logs/grid-317180_66.log')]:
 if not p.exists():logs[name]={'exists':False};continue
 want=ident(p,1000000);lines=p.read_text(errors='replace').splitlines();technical=[]
 for line in lines:
  if re.match(r'^\s*File ".*", line [0-9]+',line) or line.startswith(('Traceback (','FileNotFoundError:','RuntimeError:','ValueError:','PermissionError:','OSError:','ImportError:','ModuleNotFoundError:')):technical.append(line)
 raw='\n'.join(technical)
 if len(raw.encode())>12000:raise ValueError('finite exception-only text, never arbitrary output')
 logs[name]={'exists':True,'identity':want,'total_lines':len(lines),'exception_only_lines':technical}
entries=[];counts={};total=0
for folder in ('output','tmp'):
 base=task/folder
 if not base.exists():counts[folder]={'exists':False};continue
 stack=[base];n=0;size=0;top={}
 while stack:
  directory=stack.pop()
  with os.scandir(str(directory)) as scan:
   for e in scan:
    s=e.stat(follow_symlinks=False);p=pathlib.Path(e.path);rel=p.relative_to(base).as_posix()
    if e.is_symlink():raise ValueError('failed own output/tmp alias; no target following')
    if e.is_dir(follow_symlinks=False):stack.append(p)
    elif e.is_file(follow_symlinks=False):
     n+=1;size+=s.st_size;total+=s.st_size;top[rel.split('/')[0]]=top.get(rel.split('/')[0],0)+1
     entries.append([folder+'/'+rel,s.st_size,s.st_mtime_ns])
     if n>20000 or total>10000000:raise ValueError('failed LeWM parent existing output/tmp bound')
    else:raise ValueError('failed output/tmp special file')
 counts[folder]={'exists':True,'files':n,'logical_bytes':size,'top_level_file_counts':top}
source_missing=[];source_changed=[]
for name,want in c['staged_members'].items():
 p=root/'source'/name
 if not p.exists():source_missing.append(name)
 elif ident(p,2000000)!=want:source_changed.append(name)
required=[c['sif'],c['venv']+'/bin/python',c['renderer_path'],c['prior_source'],c['source_run'],*c['source_runs'].values()]+[x['path'] for x in c['lewm'].values()]
path_status={p:pathlib.Path(p).exists() for p in sorted(set(required))}
selection=task/'controls/SELECTION-EXTERNAL.json'
result={'status':'FAILED_PARENT66_TECHNICAL_FORENSICS_ONLY_NOT_RESUMPTION','contract_sha256':expected,
 'controls':controls,'logs':logs,'failed_output_tmp_metadata':counts,
 'failed_metadata_commitment':{'members':len(entries),'sha256':hashlib.sha256(json.dumps(sorted(entries),separators=(',',':')).encode()).hexdigest()},
 'selection_external_exists':selection.exists(),'selection_external_identity':ident(selection,1000000) if selection.exists() else None,
 'current_staged_source_missing':source_missing,'current_staged_source_changed':source_changed,'current_required_path_existence':path_status,
 'scientific_payloads_or_outcomes_deserialized':False,'jobs_or_controllers_changed':False,'scheduler_queries':0,'final_gate_ready':False}
print(json.dumps(result,sort_keys=True,separators=(',',':')))
'''


def main():
    target=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/FAILED-PARENT66-FORENSICS-001.json'
    started=target.with_name('FAILED-PARENT66-FORENSICS-001.started.json')
    if target.exists() or started.exists():raise FileExistsError('exclusive failed-parent diagnostic, no blind retry')
    ast.parse(CODE,feature_version=(3,6));write_new(started,{'source':identity(__file__),'program_sha256':hashlib.sha256(CODE.encode()).hexdigest(),'direct_human_request':'fully investigate why this happened and fix it','research_mutation_authorized_by_this_diagnostic':False})
    remote='timeout --kill-after=1s 30s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(CODE.encode()).decode())+'))')
    argv=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','40s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','ConnectionAttempts=1','prometheus',remote]
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=42)
    if p.returncode:
        write_new(target.with_name('FAILED-PARENT66-FORENSICS-001.failure.json'),{'returncode':p.returncode,'stdout':p.stdout.decode(errors='replace')[:16000],'stderr':p.stderr.decode(errors='replace')[:16000],'research_failure_not_inferred_from_diagnostic':True},limit=40000)
        raise RuntimeError('bounded technical forensic query unavailable; preserve failure, no retry')
    if len(p.stdout)>64000:raise ValueError('technical metadata capture bound')
    z=json.loads(p.stdout)
    if z['scientific_payloads_or_outcomes_deserialized'] is not False or z['jobs_or_controllers_changed'] is not False:raise ValueError('read-only technical evidence only')
    write_new(target,z,limit=64000);print(json.dumps(z,sort_keys=True))


if __name__=='__main__':main()
