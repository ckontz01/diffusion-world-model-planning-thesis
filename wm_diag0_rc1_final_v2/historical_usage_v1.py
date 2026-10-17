"""Historical counter provenance, not retrospective measurement or research.

Read only frozen source/contract hashes, controls, numeric-parity reports and
opaque hashes/NPY headers of the already-bound failed bank. No array values,
readout quality, outcome/selection/branch records, models or scientific imports.
"""
import ast,base64,hashlib,json,shlex,subprocess,sys
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new
from wm_diag0_rc1_grid_v1.common import RUN

KEYS=('visual_encoder_calls','encoded_frames','proprio_encoder_calls','action_encoder_calls','predictor_calls','cost_api_calls')
EXPECTED_DINO=dict(zip(KEYS,(923,1613,1018,115,485,37)))
EXPECTED_LEWM=dict(zip(KEYS,(88,704,0,0,0,0)))


def arithmetic(r1,v3,gate,heads):
    def report(u,api):
        out={k:u.get(k,0) for k in KEYS}
        out['cost_api_calls']=u[api]
        if any(type(v) is not int or v<0 for v in out.values()):raise ValueError('exact integer historical usage')
        return out
    r1=report(r1,'cost_calls');v3=report(v3,'cost_reforecast_API_operations');gate=report(gate,'cost_reforecast_API_operations')
    if r1!=dict(zip(KEYS,(2,17,2,6,0,0))) or v3!=dict(zip(KEYS,(34,78,37,7,15,3))) or gate!=dict(zip(KEYS,(88,88,88,5,5,1))):
        raise ValueError('unchanged original parity/R1/V3/RC1 resource metadata')
    if len(heads)!=2 or any(h!={'visual_encoder_calls':352,'encoded_frames':352,'proprio_encoder_calls':352,'action_encoder_calls':0,'predictor_calls':0} for h in heads):
        raise ValueError('exact two retained new DINO fit-only hook records')
    # Each old fit encodes16*16+12*8=352frames in44batches of8; two fits per
    # backbone. This is reviewed frozen-source arithmetic, NOT old hooks.
    old_fits=dict(zip(KEYS,(2*(16*2+12),2*(16*16+12*8),2*(16*2+12),0,0,0)))
    # Failed DINO reached parity after ONE completed30-step CEM solve. Its
    # six retained partial hashes and trace9000/bank16 headers authenticate
    # this point. Native reference ran before the preserved parity exception.
    cem_chunks=30*3
    failed={
        'visual_encoder_calls':2+1+1+2+1,
        'encoded_frames':2+1+1+2+16,
        'proprio_encoder_calls':2+cem_chunks+2+1+3+1,
        'action_encoder_calls':cem_chunks+1+1+5,
        'predictor_calls':5*(cem_chunks+1+1+1),
        'cost_api_calls':30+1+1+1}
    head_rows=[dict(h,cost_api_calls=0) for h in heads]
    rows=[old_fits,failed,r1,v3,gate]+head_rows
    dino={k:sum(row[k] for row in rows) for k in KEYS}
    lewm=dict(old_fits,proprio_encoder_calls=0)
    if dino!=EXPECTED_DINO or lewm!=EXPECTED_LEWM:raise ValueError('historical all-attempt baseline mismatch; no cap adjustment')
    return {'DINO_baseline':dino,'LeWM_baseline':lewm,
            'DINO_components':dict(zip(('two_old_fits_source_arithmetic','failed_DINO_source_arithmetic','R1_saved_declared_usage','V3_saved_hook_usage','RC1_saved_hook_usage','new_fit_1_saved_hook_usage','new_fit_3_saved_hook_usage'),rows)),
            'LeWM_basis':'two accepted old fit source paths,44batches/352frames each; no retrospective hook measurement',
            'baseline_encoded_frames_all_six_fits_and_failed_diagnostics':dino['encoded_frames']+lewm['encoded_frames'],
            'new_retroactive_hooks_or_model_calls':0}


READ=r'''
import ast,hashlib,json,os,pathlib,resource,stat,struct,time
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592))
began=time.monotonic();evidence={};limit=began+35
def ident(p,maximum=2000000):
 p=pathlib.Path(p)
 if time.monotonic()>limit:raise TimeoutError('historical metadata deadline')
 if p.is_symlink() or any(x.is_symlink() for x in p.parents):raise ValueError('no redirected evidence')
 s=p.lstat()
 if not stat.S_ISREG(s.st_mode) or s.st_size>maximum:raise ValueError('bounded exact ordinary technical evidence')
 h=hashlib.sha256();count=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);count+=len(b)
 after=p.lstat()
 if (s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('historical evidence changed')
 x={'bytes':count,'sha256':h.hexdigest()};evidence[str(p)]=x;return x
def read(p,expected=None):
 x=ident(p)
 if expected is not None and x!=expected:raise ValueError('independently bound historical identity: '+str(p))
 z=json.loads(pathlib.Path(p).read_text())
 if ident(p)!=x:raise ValueError('technical metadata read race')
 return z
def source(root,contract,names):
 for name in names:
  p=pathlib.Path(root)/'source'/name
  if ident(p)!=contract['staged_members'][name]:raise ValueError('executed source preimage: '+name)
def chain(task,acceptance,seal):
 a=read(task/'controls/ACCEPTED.json',acceptance);r=read(task/'controls/RESULT.json')
 if not a['accepted'] or r['status']!='ACCEPTED' or (r.get('acceptance_identity')!=acceptance and r.get('acceptance_sha256')!=acceptance['sha256']):raise ValueError('exact accepted retained-fit control chain')
 if a['output_seal']!=seal or ident(task/'output/MEMBERS.json')!=seal:raise ValueError('bound fit output seal, no quality read')
 return read(task/'controls/WORKER-SUCCESS.json')
r=pathlib.Path(RUN);c=read(r/'source/GRID-CONTRACT.json',EXPECTED['grid'])
old=pathlib.Path(c['recovery']['old_run']);oc=read(old/'source/CONTRACT.json',EXPECTED['old'])
source(old,oc,['wm_diag0_campaign_v4/models.py','wm_diag0_campaign_v4/readout.py','wm_diag0_campaign_v4/planning.py','wm_diag0_campaign_v4/diagnostic.py','wm_diag0_campaign_v4/worker.py','dino/models/visual_world_model.py'])
old_heads=[]
for i in range(4):
 x=c['recovery']['accepted_suppliers']['readout-'+str(i)];w=chain(old/'tasks'/('readout-'+str(i)),x['control'],x['output_seal'])
 if w['encoded_frames']!=352 or w['predictor_calls']!=0 or w['phase']!='readout' or w['setting']!=i:raise ValueError('old actual accepted fit-only worker metadata')
 old_heads.append({'setting':i,'encoded_frames':352,'predictor_calls':0})
stop=read(old/'controls/STOP.json')
if (stop['job_id'],stop['failed_task'])!=('317171','technical-1'):raise ValueError('preserved old DINO failure identity')
failed=old/'tasks/technical-1/output'
if set(p.name for p in failed.iterdir())!=set(c['recovery']['partial']):raise ValueError('exact failed-before-outcome partial set')
for n,x in c['recovery']['partial'].items():
 if ident(failed/n)!=x:raise ValueError('unchanged retained failed partial bytes')
def header(path,shape):
 with path.open('rb') as f:
  if f.read(8)!=bytes([147,78,85,77,80,89,1,0]):raise ValueError('fixed NPY header only')
  n=struct.unpack('<H',f.read(2))[0]
  if n>4096:raise ValueError('bounded failed trace header')
  h=ast.literal_eval(f.read(n).decode('latin1'))
 if h!={'descr':'<f4','fortran_order':False,'shape':shape}:raise ValueError('fixed retained failed solve shape/type')
header(failed/'trace.npy',(9000,25,2));header(failed/'actions.npy',(16,25,2))
r1=old.parent/'campaign-v4-parity-r1';pc=read(r1/'source/PROBE-CONTRACT.json',EXPECTED['probe'])
source(r1,pc,['wm_diag0_parity_r1/probe.py'])
p=read(r1/'tasks/encoding-only/output/DIAGNOSIS.json',EXPECTED['probe_report'])
if p['contract_sha256']!=EXPECTED['probe']['sha256']:raise ValueError('saved R1 report contract binding')
v3=pathlib.Path(c['rc1']['V3_run']);vc=read(v3/'source/VALIDATION-CONTRACT.json',EXPECTED['v3'])
source(v3,vc,['wm_diag0_numerical_v3/worker.py','wm_diag0_numerical_v3/reference.py','wm_diag0_numerical_v3/common.py'])
v=read(v3/'tasks/numerical-validation/output/VALIDATION.json',c['rc1']['V3_report'])
if v['actual_usage']!=c['recovery']['actual_usage']:raise ValueError('saved V3 hook metadata')
gate=pathlib.Path(c['rc1_technical']['gate_run']);gc=read(gate/'source/RC1-CONTRACT.json',EXPECTED['gate'])
source(gate,gc,['wm_diag0_rc1_v1/worker.py','wm_diag0_rc1_v1/models.py','wm_diag0_rc1_v1/reference.py'])
g=read(gate/'tasks/rc1-gate/output/RC1-GATE.json',c['rc1_technical']['gate_report'])
if g['actual_usage']!=c['rc1']['actual_usage']:raise ValueError('saved RC1 hook metadata')
heads=pathlib.Path(c['rc1_technical']['heads_run']);hc=read(heads/'source/HEADS-CONTRACT.json',c['rc1_technical']['heads_contract'])
source(heads,hc,['wm_diag0_rc1_heads_v1/worker.py','wm_diag0_rc1_v1/models.py','wm_diag0_campaign_v4/readout.py'])
new=[]
for i in (1,3):
 x=c['rc1_technical']['head_suppliers'][str(i)];w=chain(heads/'tasks'/('readout-'+str(i)),x['acceptance_identity'],x['output_seal'])
 if w['CEM_calls'] or w['physics_resets'] or w['controller_actions'] or (w['fit_frames'],w['validation_frames'])!=(256,96):raise ValueError('new heads fit-only resource metadata')
 new.append(w['actual_usage'])
out={'status':'ACTUAL_HISTORICAL_TECHNICAL_PROVENANCE_AUTHENTICATED_NOT_FINAL_GATE','evidence':evidence,
 'old_fit_metadata':old_heads,'R1_saved_usage':p['actual_usage'],'V3_saved_usage':v['actual_usage'],
 'RC1_saved_usage':g['actual_usage'],'new_fit_saved_usage':new,
 'failed_bank_shape':[16,25,2],'failed_trace_shape':[9000,25,2],
 'failed_DINO_usage_scope':'reviewed executed-source arithmetic, NOT hooks or a saved USAGE record',
 'old_fit_usage_scope':'saved manual352frames and frozen44batches source arithmetic, NOT hooks',
 'scheduler_calls':0,'filesystem_mutations':0,'scientific_runtime_imported':False,
 'array_values_read_or_decoded':False,'readout_quality_or_outcomes_read':False,
 'research_calls':0,'elapsed_seconds':time.monotonic()-began,'final_gate_ready':False}
if len(json.dumps(out).encode())>48000:raise ValueError('bounded historical metadata output')
print(json.dumps(out,sort_keys=True))
'''


def expected():
    docs=ROOT/'docs'
    def file(rel):return identity(docs/rel)
    return {'grid':file('world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json'),
            'old':file('world-model-diagnostic-a2-campaign-v4-20261015/campaign/CONTRACT.json'),
            'probe':file('world-model-diagnostic-a2-parity-r1-20261015/PROBE-CONTRACT.json'),
            'probe_report':{'bytes':1366,'sha256':'20c23bab7335b06d9eff7b38ad622a1158cf92717698150e03994729ee7c1747'},
            'v3':file('world-model-diagnostic-a2-numerical-validation-v3-20261016/VALIDATION-CONTRACT.json'),
            'gate':file('world-model-diagnostic-rc1-v1-20261016/RC1-CONTRACT.json')}


def program():
    values=expected()
    if values['grid']['sha256']!='da2766c3f8c33266ee54cea9fb2e3bdf650046e9a61ac39c209816f1b1e7514b' or values['old']['sha256']!='f08e53e73035171340fe2438e3061685a3be6d1f18a8b132540717bd447a60dc' or values['probe']['sha256']!='b76324759bce8560525f1788f32b8c9c911c3de4ed467772a1d8eda8ab5e1a2e':raise ValueError('original published authority identities')
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(values)+'\n'+READ
    ast.parse(code,feature_version=(3,6));return code


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive provenance operation label')
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    dst=doc/('HISTORICAL-USAGE-'+label+'.json');start=doc/('HISTORICAL-USAGE-'+label+'.started.json')
    if dst.exists() or start.exists():raise FileExistsError('no repeated or ambiguous metadata operation')
    code=program();write_new(start,{'source':identity(__file__),'expected_contracts':expected(),'scope':'control/source/numerical-parity metadata only; no scheduler or scientific values'})
    encoded=base64.b64encode(code.encode()).decode()
    remote='timeout --kill-after=1s 40s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    cmd=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','45s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','prometheus',remote]
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=50)
    if p.returncode:raise RuntimeError('historical authentication unavailable, not research failure; '+p.stderr.decode(errors='replace')[-4000:])
    if len(p.stdout)>48000:raise ValueError('bounded historical metadata stdout')
    z=json.loads(p.stdout);counts=arithmetic(z['R1_saved_usage'],z['V3_saved_usage'],z['RC1_saved_usage'],z['new_fit_saved_usage'])
    z.update(counts);z['independently_authenticated']=True
    z['authentication_basis']='exact executed published contracts, staged source hashes, accepted control/seal chains, bound numerical reports/failed-partial hashes and explicit disclosed source arithmetic; not a bare readiness flag'
    write_new(dst,z,limit=64000)
    print(json.dumps({'status':z['status'],'evidence_files':len(z['evidence']),'DINO_baseline':z['DINO_baseline'],'LeWM_baseline':z['LeWM_baseline'],'scheduler_calls':0,'research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
