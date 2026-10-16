"""Separate read-only observer revision, outside executed technical closure."""
import json,sys
from .common import ROOT,TECHNICAL_RUN,identity,write_new
from .scheduler import SOURCE
from wm_diag0_native_v3.transport import ssh

READ=r'''
import hashlib,json,pathlib,shlex,subprocess
r=pathlib.Path(RUN);cp=r/'source/TECHNICAL-CONTRACT.json'
def ident(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
if ident(cp)['sha256']!='101cd417d9a823a559a29d3813887ad17f721b450ce4f21d267b597e4ef788fd':raise ValueError('actual executed source/contract')
c=json.loads(cp.read_text());d=json.loads((r/'controls/DISPATCH.json').read_text());jid=d['array_job_id']
if jid!='317177' or d['contract_sha256']!=ident(cp)['sha256']:raise ValueError('exact original native dispatch')
q,a,queue_diagnostic=exact_snapshot(jid,{'317177_1','317177_2','317177_3'})
tasks={};suppliers={}
for i in (1,2,3):
 t=r/'tasks'/('technical-'+str(i));z={}
 for n in ('STARTED','RESULT','WORKER-SUCCESS','ACCEPTED'):
  p=t/'controls'/(n+'.json')
  if p.exists():z[n]=json.loads(p.read_text())
 if 'STARTED' in z:
  s=z['STARTED'];z['process']={'node':s['node'],'PID':s['PID'],'start_ticks':s['start_ticks']}
  if 'RESULT' not in z:
   code="import json,pathlib;p=pathlib.Path('/proc')/"+repr(str(s['PID']))+"/'stat';print(json.dumps({'PID_exists':p.exists(),'start_ticks_match':p.exists() and p.read_text().rsplit(')',1)[1].split()[19]=="+repr(str(s['start_ticks']))+"}))"
   try:
    p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5',s['node'],'python3 -B -c '+shlex.quote(code)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=8)
    z['process']['node_verification']=json.loads(p.stdout) if p.returncode==0 else {'unavailable_not_cluster_failure':True,'returncode':p.returncode}
   except subprocess.TimeoutExpired:z['process']['node_verification']={'unavailable_not_cluster_failure':True}
  else:z['process']['terminal_control_no_live_process_expected']=True
 if 'ACCEPTED' in z:
  aa=z['ACCEPTED']
  if not aa['accepted'] or ident(t/'output/MEMBERS.json')!=aa['output_seal']:raise ValueError('actual independent output acceptance/seal')
  if 'RESULT' in z:
   rr=z['RESULT']
   if rr['status']!='ACCEPTED' or rr['acceptance_identity']!=ident(t/'controls/ACCEPTED.json') or rr['output_seal']!=aa['output_seal']:raise ValueError('independent result/control/seal chain')
   suppliers[str(i)]={'run':str(r),'acceptance_identity':ident(t/'controls/ACCEPTED.json'),'output_seal':aa['output_seal']}
  else:z['acceptance_finalization_pending']=True
 if 'RESULT' in z and z['RESULT']['status']=='FAILED':
  p=t/'logs/worker.log';z['stderr']=p.read_text(errors='replace')[-16000:] if p.exists() else ''
 tasks[str(i)]=z
stop=json.loads((r/'controls/STOP.json').read_text()) if (r/'controls/STOP.json').exists() else None
old=pathlib.Path(c['recovery']['old_run']);s=c['recovery']['accepted_suppliers']['technical-0'];t=old/'tasks/technical-0'
if ident(t/'controls/ACCEPTED.json')!=s['control'] or ident(t/'output/MEMBERS.json')!=s['output_seal']:raise ValueError('original accepted PushT LeWM supplier')
oldctl=json.loads((t/'controls/ACCEPTED.json').read_text());oldresult=json.loads((t/'controls/RESULT.json').read_text())
if not oldctl['accepted'] or oldresult['status']!='ACCEPTED' or oldresult['acceptance_sha256']!=s['control']['sha256']:raise ValueError('original accepted terminal supplier')
suppliers['0']={'run':str(old),'acceptance_identity':s['control'],'output_seal':s['output_seal']}
rows=[x.split('|') for x in a.splitlines() if x.strip()];physical=None
if not q.strip() and stop is None and set(suppliers)=={'0','1','2','3'} and len(rows)==3 and all(x[2:4]==['COMPLETED','0:0'] for x in rows):
 # This source is separately hash-bound in the new dated observation. It reads
 # only accepted physical clock/action-count metadata and emits no outcomes.
 exec(RESOURCE_SOURCE,globals())
 physical=before_grid(dict(c,rc1_grid={'technical_suppliers':suppliers}))
logical=sum(p.stat().st_size for p in r.parent.rglob('*') if p.is_file())
live=logical+2100000000+3139002368+144694193+620000000+3720000000+124000000+60000000+20000000+300000000
storage={'logical_current_study_bytes':logical,'full_future_live_bytes':live,'full_future_archive_bytes':live+500000000,'full_future_inclusive_bytes':live+28000000000+2874852312,
 'passes':live<=13500000000 and live+500000000<=14000000000 and live+28000000000+2874852312<=44000000000,'no_compression_or_hardlink_savings':True}
print(json.dumps({'dispatch':d,'queue':q,'scheduler':a,'queue_diagnostic':queue_diagnostic,'tasks':tasks,'STOP':stop,'original_technical0_acceptance':s,
 'all_four_physical_full_future':physical,'fresh_full_future_storage':storage,'research_outcomes_predictions_or_quality_read':False}))
'''


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive observation')
    doc=ROOT/'docs/world-model-diagnostic-rc1-technical-v1-20261016';target=doc/('OBSERVE-'+label+'.json')
    if target.exists():raise FileExistsError('never repeat a receipt')
    resource=ROOT/'wm_diag0_rc1_grid_v1/resources.py'
    z=ssh('RUN='+repr(TECHNICAL_RUN)+'\nRESOURCE_SOURCE='+repr(resource.read_text())+'\n'+SOURCE+'\n'+READ)
    z['observer_revision']='UNFROZEN_GRID_TECHNICAL_OBSERVER_R2_READ_ONLY'
    z['resource_metadata_reader_source']=identity(resource)
    write_new(target,z);print(json.dumps(z,indent=2))


if __name__=='__main__':main()
