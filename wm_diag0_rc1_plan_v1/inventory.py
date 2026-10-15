"""No arrays are decoded, models imported, files changed, or jobs submitted."""
import json
from wm_diag0_native_v3.common import ROOT, identity, write_new
from wm_diag0_native_v3.transport import ssh

DOCREL = 'docs/world-model-diagnostic-rc1-final-plan-v1-20261016'
DOC = ROOT / DOCREL

PROGRAM = r'''
import hashlib,json,os,pathlib,shutil,stat,subprocess,time
base=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015')
def ident(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
 return {'bytes':size,'sha256':h.hexdigest()}
old=base/'campaign-v4'
cpath=old/'source/CONTRACT.json'
if ident(cpath)['sha256']!='f08e53e73035171340fe2438e3061685a3be6d1f18a8b132540717bd447a60dc':raise ValueError('exact executed contract')
c=json.loads(cpath.read_text())
ids=['317163','317164','317165','317166','317172','317173']
queue=subprocess.check_output(['squeue','-h','-j',','.join(ids),'-o','%i|%T|%N'],universal_newlines=True,timeout=10)
acct=subprocess.check_output(['sacct','-X','-n','-P','-j',','.join(ids),'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
if queue.strip():raise ValueError('study allocations live; no quiescent accounting')
rows={};seen=set();logical=0;unique=0;files=0;syms=[]
for p in sorted(base.rglob('*')):
 st=p.lstat()
 if stat.S_ISDIR(st.st_mode):continue
 rel=p.relative_to(base).as_posix();part=rel.split('/')[0]
 row=rows.setdefault(part,{'logical_bytes':0,'unique_inode_bytes':0,'files':0,'symlinks':0})
 if stat.S_ISLNK(st.st_mode):
  target=os.readlink(str(p))
  if '/renderer-r6/' not in '/'+rel or c['renderer']['aliases'].get(p.name)!=target:raise ValueError('unreviewed symlink')
  row['symlinks']+=1;syms.append([rel,target]);continue
 if not stat.S_ISREG(st.st_mode):raise ValueError('special file')
 logical+=st.st_size;files+=1;row['logical_bytes']+=st.st_size;row['files']+=1
 key=(st.st_dev,st.st_ino)
 if key not in seen:unique+=st.st_size;row['unique_inode_bytes']+=st.st_size;seen.add(key)
 if files>30000 or logical>8000000000:raise ValueError('bounded exact-study inventory')
accepted={}
for key in ('readout-0','readout-1','readout-2','readout-3','technical-0'):
 task=old/'tasks'/key;control=task/'controls/ACCEPTED.json';seal=task/'output/MEMBERS.json'
 a=json.loads(control.read_text());s=json.loads(seal.read_text())
 if ident(seal)!=a['output_seal']:raise ValueError('accepted seal changed')
 for n,x in s.items():
  p=task/'output'/n
  if p.is_symlink() or ident(p)!=x:raise ValueError('accepted member identity')
 accepted[key]={'control':ident(control),'seal':ident(seal),'member_bytes':sum(x['bytes'] for x in s.values()),'members':len(s)}
# Only authenticated runtime-manifest sizes; no framework imported or executed.
rp=old/'controls/RUNTIME-MANIFEST.json';rm=json.loads(rp.read_text())
runtime_bytes=0
for rel,x in rm['members'].items():
 p=pathlib.Path(c['venv'])/rel
 if p.is_symlink() or p.stat().st_size!=x['bytes']:raise ValueError('runtime member size changed')
 runtime_bytes+=x['bytes']
if runtime_bytes!=1658213811:raise ValueError('reviewed runtime closure size')
sif=pathlib.Path(c['sif'])
if sif.stat().st_size!=3139002368:raise ValueError('SIF size changed')
lewm={k:ident(pathlib.Path(v['path'])) for k,v in c['lewm'].items()}
if any(lewm[k]!={'bytes':v['bytes'],'sha256':v['sha256']} for k,v in c['lewm'].items()):raise ValueError('LeWM artifact identity')
v3=base/'campaign-v4-numerical-v3/tasks/numerical-validation/output'
vreport=v3/'VALIDATION.json'
if ident(vreport)!= {'bytes':15815,'sha256':'196bd63be202ac7cecbac1f21f7e4689e64c47748fb98be1222914c2dab8240f'}:raise ValueError('V3 report identity')
print(json.dumps({'status':'QUIESCENT_TECHNICAL_STORAGE_INVENTORY','UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
 'study_root':str(base),'components':rows,'logical_study_bytes':logical,'unique_inode_study_bytes':unique,'files':files,'symlinks':syms,
 'runtime_manifest':ident(rp),'runtime_manifest_member_bytes':runtime_bytes,'runtime_files':len(rm['members']),
 'runtime_size_only_readback_not_new_hash_authentication':True,'SIF_bytes':sif.stat().st_size,'LeWM':lewm,
 'accepted':accepted,'old_STOP':ident(old/'controls/STOP.json'),'V3_report':ident(vreport),
 'queue':queue,'exact_scheduler_snapshot':acct,'cluster_free_bytes':shutil.disk_usage(str(base)).free,
 'scientific_arrays_decoded':False,'efficacy_read':False,'remote_mutations':0,'new_allocations':0}))
'''

def main():
    DOC.mkdir(exist_ok=True)
    if (DOC/'INVENTORY-001.json').exists():
        raise FileExistsError('exclusive observation already exists')
    result = ssh(PROGRAM)
    write_new(DOC/'INVENTORY-001.json', result)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
