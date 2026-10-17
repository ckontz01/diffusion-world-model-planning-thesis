"""One fresh terminal/whole-runtime/every-root opaque binding, never analysis."""
import ast,hashlib,inspect,json,sys
from .common import ROOT,DOC,identity,write_new
from wm_diag0_rc1_recovery_r1 import common as recovery
from wm_diag0_rc1_final_v2 import inventory_v3 as inv,archive_v2 as archive,archive_verify_v2 as readback,root_binding_v1 as roots
from wm_diag0_rc1_final_v2 import recovery_suppliers_v1 as terminal,terminal_binding_v1 as starts
from wm_diag0_rc1_final_v1 import postarchive_v1 as sidecar,ledger

def layout():
    old=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/PRESERVATION-LAYOUT-001.json'
    if identity(old)!={'bytes':10618,'sha256':'0f64eb876a3f0007ae0188f4902d4d8a114548d62e0c1cef610af02d5ffc3243'}:raise ValueError('original reviewed layout identity')
    value=json.loads(old.read_text())['layout'];base=value['study_base']
    additions=['campaign-v4-rc1-grid-recovery-r1','campaign-v4-rc1-grid-recovery-r1-artificial-ONE']
    value['approved_children_before_final']=sorted(value['approved_children_before_final']+additions)
    value['approved_children_with_final']=sorted(value['approved_children_with_final']+additions)
    for n in additions:value['root_paths']['study/'+n]=base+'/'+n
    if len(value['approved_children_before_final'])!=21 or len(value['approved_inert_alias_literals'])!=30:raise ValueError('exact all21 retained roots/30 independently approved inert literals')
    return {'status':'RECOVERY_INCLUSIVE_COMPLETE_LAYOUT_SOURCE_AUTHORITY','predecessor':identity(old),
        'recovery_authority':identity(ROOT/'docs/world-model-diagnostic-rc1-recovery-r1-20261016/AUTHORITY-001.json'),
        'layout':value}

BODY=r'''
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592))
deadline=time.monotonic()+140
data=json.load(sys.stdin);layout=data['layout'];base=Path(layout['study_base']);auth=data['layout_identity']['sha256']
cp=Path(RUN)/'source/GRID-CONTRACT.json'
def ident(p):
 p=Path(p);s=p.lstat()
 if not stat.S_ISREG(s.st_mode):raise ValueError('ordinary technical evidence')
 return {'bytes':s.st_size,'sha256':source_hash(p,s.st_size,deadline)}
def body(p,limit=200000):
 p=Path(p)
 if p.lstat().st_size>limit:raise ValueError('bounded technical metadata')
 return json.loads(p.read_text())
if ident(cp)!=data['recovery_contract']:raise ValueError('exact published recovery contract')
c=body(cp)
oldraw={str(i):body(Path(OLD)/'tasks'/('grid-'+str(i))/'controls/STARTED.json')['job_id'] for i in range(67)}
newraw={str(i):body(Path(RUN)/'tasks'/('grid-'+str(i))/'controls/STARTED.json')['job_id'] for i in range(66,124)}
query=subprocess.run(['sacct','-X','-n','-P','-j','317163,317164,317165,317166,317172,317173,317174,317175,317177,317180,317441','--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=15)
if query.returncode:raise RuntimeError('full terminal accounting unavailable: '+query.stderr)
reconciled=terminal_ledger(c,query.stdout,oldraw,newraw)
if reconciled['GPU_charged_seconds']!=97360:raise ValueError('latest complete observed all-attempt charge changed')
wants=expected_starts(c,oldraw,newraw);controls={}
for logical,want in wants.items():
 record=body(want['path'],4000);check_started(record,want);controls[logical]=ident(want['path'])
terminal={'scheduler':query.stdout,'old_grid_raw_ids':oldraw,'recovery_grid_raw_ids':newraw,'started_controls':controls,'reconciled':reconciled}
for root,count in ((OLD,66),(RUN,124)):
 for i in range(0 if root==OLD else 66,count):
  t=Path(root)/'tasks'/('grid-'+str(i));r=body(t/'controls/RESULT.json');a=body(t/'controls/ACCEPTED.json')
  if r['status']!='ACCEPTED' or a['accepted'] is not True or ident(t/'controls/ACCEPTED.json')!=r['acceptance_identity'] or ident(t/'output/MEMBERS.json')!=a['output_seal']:raise ValueError('all124 accepted technical chains')
external={k:v for k,v in layout['root_paths'].items() if not k.startswith('study/')}
planned=plan(str(base),layout['approved_children_before_final'],external,layout['approved_inert_alias_literals'])
paths={k:v for k,v in layout['root_paths'].items() if k in planned['root_labels']}
proof=authenticate(planned,paths,auth,deadline)
if canonical(plan(str(base),layout['approved_children_before_final'],external,layout['approved_inert_alias_literals']))!=canonical(planned):raise ValueError('full inventory changed during binding')
# Every pinned runtime member is checked against the opaque hash actually read
# by the full no-follow inventory; unmanifested members also enter root proof.
manifest=Path(c['recovery']['old_run'])/'controls/RUNTIME-MANIFEST.json'
if ident(manifest)!=c['runtime_manifest']:raise ValueError('pinned runtime manifest')
runtime=body(manifest,10000000)['members']
for name,want in runtime.items():
 p=str(Path(c['venv'])/name)
 if observed.get(p)!=want:raise ValueError('pinned runtime member changed: '+name)
if observed.get(c['sif'],{}).get('sha256')!=c['sif_sha256']:raise ValueError('pinned SIF bytes')
for entry in c['lewm'].values():
 if observed.get(entry['path'])!={k:entry[k] for k in ('bytes','sha256')}:raise ValueError('pinned LeWM object')
f=os.statvfs(str(base));free=f.f_bavail*f.f_frsize
# Reserve complete new final output/source/controls, auxiliary copies and all
# artificial roots, in addition to all measured original logical copies.
live=planned['logical_payload_bytes_no_discounts']+80000000+5000000+60000000+20000000
storage={'current_whole_payload':planned['logical_payload_bytes_no_discounts'],'live_full_future':live,'archive_full_future':live+500000000,
 'inclusive_full_future':live+28000000000+data['preparation_bytes'],'preparation_bytes':data['preparation_bytes'],'cluster_free_bytes':free,
 'auxiliary_all_copies':80000000,'future_final_source_output_controls':80000000,'artificial_roots_reserved':5000000,'no_copy_discounts':True}
if live>13500000000 or live+500000000>14000000000 or storage['inclusive_full_future']>44000000000 or free<15000000000:raise ValueError('complete actual full-future byte proof')
print(json.dumps({'status':'ALL139_TERMINAL_ALL128_STARTS_ALL21_ROOTS_FULL_RUNTIME_EVERY_MEMBER_BOUND','terminal':terminal,
 'precompute_roots':proof,'storage':storage,'registered_runtime_members_authenticated':len(runtime),
 'full_runtime_regular_members':proof['roots']['runtime/venv']['regular_files'],'scientific_payloads_deserialized':False,'captured_epoch':time.time()},separators=(',',':')))
'''

def program():
    functions=[inv.safe_name,inv.alias_literal,inv.plan,sidecar.valid_identity,archive.canonical,archive.check_time,
        archive.token,archive.open_regular,archive.checked_plan,archive.check_bindings,readback.source_hash,
        roots.accumulator,roots.add,roots.finish,roots.authenticate,recovery.closed_indices,
        starts.check_started,terminal.expected_starts,terminal.terminal_ledger]
    prefix='import os,stat,sys,json,time,hashlib,resource,subprocess\nfrom pathlib import Path,PurePosixPath\n'
    constants={'MAX_MEMBERS':100000,'MAX_PAYLOAD':13500000000,'OVERHEAD':500000000,'MAX_MANIFEST':20000000,
        'MAX_ARCHIVE':14000000000,'MAX_FILE':4000000000,'BLOCK':1048576,'SCHEMA':roots.SCHEMA,
        'OLD':recovery.OLD,'RUN':recovery.RUN,'GRID_HASH':recovery.GRID_HASH,'HUMAN':recovery.HUMAN,'INDICES':recovery.INDICES,
        'RECOVERY_HASH':terminal.RECOVERY_HASH,'TECH':starts.TECH,'TECH_RAW':starts.TECH_RAW,'TECH_CONTRACT':starts.TECH_CONTRACT,
        'OLD_ALLOCATED':ledger.OLD_ALLOCATED,'OLD_UNALLOCATED':ledger.OLD_UNALLOCATED}
    text=prefix+''.join(k+'='+repr(v)+'\n' for k,v in constants.items())+'\n'.join(inspect.getsource(f) for f in functions)
    text+='\noriginal_source_hash=source_hash\nobserved={}\ndef source_hash(path,size,deadline):\n value=original_source_hash(path,size,deadline)\n observed[str(path)]={"bytes":size,"sha256":value}\n return value\n'+BODY
    ast.parse(text,feature_version=(3,6));return text

def main():
    from .transport import call
    if not Path('D:/WSL/Thesis-Ubuntu/ext4.vhdx').is_file():raise RuntimeError('configured WSL path unavailable')
    value=layout();write_new(DOC/'LAYOUT-001.json',value)
    prep=json.loads((DOC/'PREPARATION-COPIES-001.json').read_text())
    args={'layout':value['layout'],'layout_identity':identity(DOC/'LAYOUT-001.json'),
        'recovery_contract':identity(ROOT/'docs/world-model-diagnostic-rc1-recovery-r1-20261016/GRID-CONTRACT.json'),
        'preparation_bytes':prep['full_future_preparation_bytes']}
    z=call('BINDING001',program(),args,seconds=165)
    for name,field in [('ALL-ALLOCATIONS-TERMINAL.json','terminal'),('PRECOMPUTE-ROOTS.json','precompute_roots')]:write_new(DOC/name,z[field])
    print(json.dumps({'status':z['status'],'storage':z['storage'],'full_runtime_regular_members':z['full_runtime_regular_members']}))

if __name__=='__main__':main()
