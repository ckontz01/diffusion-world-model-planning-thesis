"""New source namespace; defer unrelated data-format initialization only."""
import hashlib,json,sys
from .common import DOC,ROOT,SOURCE_RUN,identity,write_new
from wm_diag0_native_v3.common import DOC as OLD_DOC,RUN as OLD_RUN
from wm_diag0_native_v3.transport import ssh

DEST=DOC/'source-import-r1'

def build():
    DEST.mkdir(exist_ok=False)
    c=json.loads((OLD_DOC/'CONTRACT.json').read_text());raw=(ROOT/'wm_diag0_campaign_v4/native_init.py').read_bytes()
    c['run']=SOURCE_RUN
    old=c['staged_members']['stable_worldmodel/__init__.py']
    c['staged_members']['stable_worldmodel/__init__.py']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    c['source_import_repair']={'reason':'remove eager optional lancedb/data/World initialization from package __init__ only',
            'old_initializer':old,'new_initializer':c['staged_members']['stable_worldmodel/__init__.py'],
            'all_other_reviewed_source_members_unchanged':True,'source_attempts_previously_started':0,
            'prior_source_contract':identity(OLD_DOC/'CONTRACT.json'),'prior_import_failure':identity(OLD_DOC/'NATIVE-IMPORT-CHECK-001.json'),
            'new_attempts_or_replacement_allocations':0,'preparation_charge':'covered by original full2000-second native-v3 charge'}
    write_new(DEST/'CONTRACT.json',c)
    print(json.dumps({'contract':identity(DEST/'CONTRACT.json'),'new_run':SOURCE_RUN,'only_changed_runtime_member':'stable_worldmodel/__init__.py','source_roots_started':0}))

def stage():
    from .small import published
    published('source-import-r1')
    contract=(DEST/'CONTRACT.json').read_bytes();init=(ROOT/'wm_diag0_campaign_v4/native_init.py').read_bytes()
    expected=hashlib.sha256(contract).hexdigest()
    write_new(DEST/'STAGE-001.started.json',{'contract':expected,'run':SOURCE_RUN})
    code='RUN='+repr(SOURCE_RUN)+'\nOLD='+repr(OLD_RUN)+'\nEXPECTED='+repr(expected)+'\nCBYTES='+str(len(contract))+'\n'+'''
import hashlib,json,os,pathlib,sys
r=pathlib.Path(RUN);old=pathlib.Path(OLD)
if (old/'controls/DISPATCH-source.json').exists() or (old/'controls/SUBMIT-source-STARTED.json').exists():raise RuntimeError('old source allocation requires reconciliation')
if any((old/'tasks').iterdir()):raise RuntimeError('existing native source root cannot be repeated')
r.mkdir(exist_ok=False)
for n in ('source','controls','tasks','logs','tmp'):(r/n).mkdir()
b=sys.stdin.buffer.read(CBYTES);init=sys.stdin.buffer.read(10000)
if hashlib.sha256(b).hexdigest()!=EXPECTED:raise ValueError('new contract identity')
c=json.loads(b);oldc=json.loads((old/'source/CONTRACT.json').read_text())
for name,x in c['staged_members'].items():
 p=r/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name=='stable_worldmodel/__init__.py':
  if len(init)!=x['bytes'] or hashlib.sha256(init).hexdigest()!=x['sha256']:raise ValueError('only initializer repair')
  with p.open('xb') as f:f.write(init)
  p.chmod(0o444)
 else:
  if x!=oldc['staged_members'][name]:raise ValueError('scientific source changed')
  src=old/'source'/name
  if src.stat().st_size!=x['bytes'] or hashlib.sha256(src.read_bytes()).hexdigest()!=x['sha256']:raise ValueError('authenticated supplier')
  os.link(str(src),str(p))
with (r/'source/CONTRACT.json').open('xb') as f:f.write(b)
(r/'source/CONTRACT.json').chmod(0o444)
os.link(str(old/'controls/RUNTIME-MANIFEST.json'),str(r/'controls/RUNTIME-MANIFEST.json'))
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
result={'status':'SOURCE_IMPORT_REPAIR_STAGE_AUTHENTICATED','contract_sha256':EXPECTED,'old_source_roots_repeated':0,'unchanged_members_reused':len(c['staged_members'])-1,'model_files_recopied':0}
with (r/'controls/STAGE-VERIFIED.json').open('x') as f:json.dump(result,f,sort_keys=True)
print(json.dumps(result))
'''
    result=ssh(code,payload=contract+init);write_new(DEST/'STAGE-001.json',result);print(json.dumps(result))

if __name__=='__main__':
    if sys.argv[1]=='build':build()
    elif sys.argv[1]=='stage':stage()
    else:raise ValueError('build/stage')
