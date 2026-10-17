"""Metadata/header-only accepted-input join; no new numeric derived analysis."""
import base64,json
from .common import DOC,OLD,identity,write_new
from .transport import call

CODE=r'''
import ast,hashlib,json,os,resource,stat,struct,sys,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592));os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
d=json.load(sys.stdin);cp=Path(d['contract_path']);end=time.monotonic()+45
def ident(p):
 p=Path(p)
 for q in (p,)+tuple(p.parents):
  s=q.lstat()
  if stat.S_ISLNK(s.st_mode):raise ValueError('required input alias')
 if not p.is_file():raise ValueError('required ordinary file')
 b=p.read_bytes()
 return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def bound(p,w):
 if w['bytes']>2000000 or ident(p)!=w:raise ValueError('exact completed control/source identity '+str(p))
 return json.loads(Path(p).read_text())
c=bound(cp,d['anchors']['FINAL-CONTRACT-002.json'])
oldtask=Path(c['rc1_final']['run'])/'tasks/analysis-0'
accepted=bound(oldtask/'output/ACCEPTANCE.json',d['anchors']['ACCEPTANCE.json'])
if accepted['status']!='ALL120_SOURCES_6_RETAINED_FITS_4_ACTIVE_HEADS_128_PARENTS_INDEPENDENTLY_ACCEPTED':raise ValueError('complete accepted source cohort')
settings=[('pusht','lewm'),('pusht','dinowm_noprop'),('reacher','lewm'),('reacher','dinowm_noprop')]
parents=[];allbytes=0
for s,(task,backbone) in enumerate(settings):
 head=c['recovery']['accepted_suppliers']['readout-'+str(s)] if s%2==0 else c['rc1_technical']['head_suppliers'][str(s)]
 if s%2==0:headmeta={'active_run':c['recovery']['old_run'],'output_seal':head['output_seal'],'acceptance':head['control'],'role':'original_LeWM'}
 else:headmeta={'active_run':c['rc1_technical']['heads_run'],'output_seal':head['output_seal'],'acceptance':head['acceptance_identity'],'role':'RC1_pointwise_DINO'}
 for ri in range(32):
  if time.monotonic()>end:raise TimeoutError('input join metadata deadline')
  if ri==0:
   supplier=c['rc1_grid']['technical_suppliers'][str(s)];p=Path(supplier['run'])/'tasks'/('technical-'+str(s))
  else:
   index=s*31+ri-1;run=c['rc1_recovery']['original_grid_run'] if 'rc1_recovery' in c and index<66 else None
   # Exact original/recovery roots come from the authenticated executed contract.
   root=c['rc1_grid_recovery']['original_run'] if 'rc1_grid_recovery' in c else None
   if index<66:p=Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/campaign-v4-rc1-grid-v1')/'tasks'/('grid-'+str(index))
   else:p=Path(c['run'])/'tasks'/('grid-'+str(index))
  out=p/'output';ctl=json.loads((p/'controls/ACCEPTED.json').read_text());result=json.loads((p/'controls/RESULT.json').read_text())
  ctl_id=ident(p/'controls/ACCEPTED.json');selpath=out/'SELECTION.json'
  if ctl.get('accepted') is not True or result.get('status')!='ACCEPTED' or result.get('acceptance_identity',{}).get('sha256',result.get('acceptance_sha256'))!=ctl_id['sha256']:raise ValueError('actual accepted supplier chain')
  members=bound(out/'MEMBERS.json',ctl['output_seal']);sel=bound(selpath,members['SELECTION.json'])
  key=sel['root']['root_id']+'|'+backbone
  if accepted['parent_output_seals'].get(key)!=ctl['output_seal'] or sel['root']['task']!=task or sel['root']['root_index']!=ri or sel['backbone']!=backbone:raise ValueError('final accepted mapping, not old v4 assumption')
  ext=json.loads((p/'controls/SELECTION-EXTERNAL.json').read_text())
  if ext['seal']!=members['SELECTION.json']:raise ValueError('externally sealed original choices')
  n=len(sel['candidate_ids']);shape=[192] if backbone=='lewm' else [196,384]
  if not 1<=n<=16 or len(set(sel['candidate_ids']))!=n or sel['native_index']!=0 or sel['route']['feature_shape']!=shape or sel['route']['positions']!=[5,10,15,20,25]:raise ValueError('fixed native bank/representation')
  if backbone!='lewm' and sel['route']!=c['rc1_technical']['head_suppliers'][str(s)]['route']:raise ValueError('accepted RC1 pointwise DINO route')
  names=['SELECTION.json','actions.npy','predicted.npy','realized.npy','goal.npy','costs.npy']
  names+=['oracle/'+str(i)+'/PREFIX.json' for i in range(n)]
  names+=['evaluation/'+str(i)+'-'+str(draw)+'/BRANCH.json' for i in range(n) for draw in (0,1)]
  required={name:members[name] for name in names};headers={}
  for name in names:
   q=out/name
   if q.is_symlink() or not q.is_file() or q.stat().st_size!=required[name]['bytes']:raise ValueError('specific missing/changed required artifact '+str(q))
   if name.endswith('.npy'):
    with q.open('rb') as stream:
     if stream.read(6)!=b'\x93NUMPY':raise ValueError('required numeric NPY')
     version=tuple(stream.read(2));width=2 if version==(1,0) else 4 if version==(2,0) else 0
     if not width:raise ValueError('supported NPY header only')
     count=int.from_bytes(stream.read(width),'little')
     if count>4096:raise ValueError('bounded numeric header')
     header=ast.literal_eval(stream.read(count).decode('latin1'))
     if header['fortran_order'] or header['descr'] not in ('<f4','<f8'):raise ValueError('ordinary nonobject saved feature dtype')
     headers[name]={'shape':list(header['shape']),'dtype':header['descr']}
  expected={'actions.npy':([n,25,2],'<f4'),'predicted.npy':([n,5]+shape,'<f4'),'realized.npy':([n,5]+shape,'<f4'),'goal.npy':(shape,'<f4'),'costs.npy':([4,n],'<f8')}
  if any(headers[k]!={'shape':sh,'dtype':dt} for k,(sh,dt) in expected.items()):raise ValueError('scientific array schema cannot be reconciled')
  for name in names:
   if name!='SELECTION.json' and not name.startswith('evaluation/') and sel['members_before_evaluation'].get(name)!=required[name]:raise ValueError('pre-evaluation feature/prefix identity')
  allbytes+=sum(x['bytes'] for x in required.values())
  parents.append({'setting':s,'task':task,'backbone':backbone,'root_index':ri,'root_id':sel['root']['root_id'],'parent_path':str(p),'output':str(out),
   'output_seal':ctl['output_seal'],'accepted_control':ctl_id,'accepted_result':ident(p/'controls/RESULT.json'),'external_selection':ident(p/'controls/SELECTION-EXTERNAL.json'),
   'candidate_count':n,'candidate_ids':sel['candidate_ids'],'native_index':sel['native_index'],'source_id':sel['source_id'],'source_seal':sel['source_seal'],
   'route':sel['route'],'readout_id':sel['readout_id'],'active_head':headmeta,'required_members':required,'array_headers':headers})
if len(parents)!=128 or len({p['root_id']+'|'+p['backbone'] for p in parents})!=128:raise ValueError('all four complete settings')
core=cp.parent/'wm_diag0/core.py';core_id=ident(core)
if core_id!=c['staged_members']['wm_diag0/core.py']:raise ValueError('unchanged pure-array S0 source')
body={'status':'REQUIRED_ACCEPTED_INPUT_METADATA_AND_NUMERIC_HEADERS_FROZEN_NO_NEW_DERIVED_RESULTS','completed_publication':d['completed_publication'],
 'completed_contract':{'path':str(cp),'identity':d['anchors']['FINAL-CONTRACT-002.json']},'completed_acceptance':{'path':str(oldtask/'output/ACCEPTANCE.json'),'identity':d['anchors']['ACCEPTANCE.json']},
 'completed_results':{'path':str(oldtask/'output/RESULTS.json'),'identity':d['anchors']['RESULTS.json']},'pure_array_core':{'path':str(core),'identity':core_id},
 'venv':c['venv'],'sif':c['sif'],'study_base':str(Path(c['run']).parent),'parents':parents,'required_saved_bytes_streamed_in_one_parent_at_a_time':allbytes,
 'new_numeric_derived_analysis_executed':False,'model_checkpoint_or_physics_reads':False,'whole_study_audit_repeated':False}
raw=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
if len(raw)>3500000:raise ValueError('bounded input manifest')
print(raw.decode())
'''

def main():
    activation=json.loads((DOC/'ACTIVATION.json').read_text());c=json.loads((OLD/'FINAL-CONTRACT-002.json').read_text())
    value=call('INPUTMETA001',CODE,{'contract_path':c['rc1_final']['run']+'/source/FINAL-CONTRACT.json','anchors':activation['completed_anchors'],'completed_publication':activation['completed_publication']},seconds=65)
    write_new(DOC/'INPUT-MANIFEST.json',value)
    print(json.dumps({'status':value['status'],'parents':len(value['parents']),'input_manifest':identity(DOC/'INPUT-MANIFEST.json'),'required_bytes':value['required_saved_bytes_streamed_in_one_parent_at_a_time']}))

if __name__=='__main__':main()
