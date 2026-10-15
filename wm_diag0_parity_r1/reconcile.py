"""Read exact terminal allocations, seals and resource counters, not efficacy."""
import json
from .common import DOC, OLD_RUN, OLD_CONTRACT, write_new
from wm_diag0_native_v3.transport import ssh

PROGRAM = '''
import hashlib,json,pathlib,subprocess,os,time
r=pathlib.Path(RUN)
def identity(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}
if identity(r/'source/CONTRACT.json')['sha256']!=EXPECTED:raise ValueError('frozen executed contract')
d=json.loads((r/'controls/DAG-DISPATCH.json').read_text())
if d['jobs']!={'readout':'317163','technical':'317164','grid':'317165','analysis':'317166'}:raise ValueError('exact dispatched lineage')
ids=list(d['jobs'].values())
q=subprocess.check_output(['squeue','-h','-j',','.join(ids),'-o','%i|%T|%N'],universal_newlines=True,timeout=10)
raw=subprocess.check_output(['sacct','-X','-n','-P','-j',','.join(ids),'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
rows=[x.split('|') for x in raw.splitlines() if x.strip()]
if q.strip() or any(not x[2].startswith(('COMPLETED','FAILED','CANCELLED')) for x in rows):raise ValueError('live or ambiguous allocation; no recovery submission')
charge=sum(int(x[4]) for x in rows)
if charge!=236:raise ValueError('unexpected cumulative GPU charge')
stop=json.loads((r/'controls/STOP.json').read_text())
if stop['job_id']!='317171' or stop['failed_task']!='technical-1':raise ValueError('exact retained STOP')
accepted={};results={}
for p in sorted((r/'tasks').glob('*/controls/RESULT.json')):
 z=json.loads(p.read_text());key=p.parents[1].name;results[key]=z
 if z['status']=='ACCEPTED':
  a=p.parent/'ACCEPTED.json';ctl=json.loads(a.read_text())
  if identity(a)['sha256']!=z['acceptance_sha256']:raise ValueError('accepted control hash')
  directory=p.parents[1]/'output';manifest=directory/'MEMBERS.json'
  if identity(manifest)!=ctl['output_seal']:raise ValueError('accepted output seal')
  members=json.loads(manifest.read_text())
  for n,x in members.items():
   if identity(directory/n)!=x:raise ValueError('accepted member changed')
  accepted[key]={'control':identity(a),'output_seal':ctl['output_seal'],'members':len(members)}
if set(accepted)!={'readout-0','readout-1','readout-2','readout-3','technical-0'}:raise ValueError('exact successful suppliers')
failed=r/'tasks/technical-1';out=failed/'output'
names={p.name for p in out.iterdir()}
if names!={'native-elites.npy','native-mean.npy','native-indices.npy','trace.npy','trace-costs.npy','actions.npy'}:raise ValueError('failed stage not exactly before oracle/evaluation')
partial={p.name:identity(p) for p in sorted(out.iterdir())}
# Header parsing only. No array values or scientific outputs are decoded.
import struct,ast
with (out/'actions.npy').open('rb') as f:
 if f.read(8)!=bytes([147,78,85,77,80,89,1,0]):raise ValueError('bounded NPY header')
 length=struct.unpack('<H',f.read(2))[0]
 if length>4096:raise ValueError('header size')
 header=ast.literal_eval(f.read(length).decode('latin1'))
if header['shape']!=(16,25,2) or header['descr']!='<f4':raise ValueError('fixed failed bank layout')
# Accepted diagnostic usage is resource metadata only. Do not return labels,
# endpoints, choices, predicted/realized values, or termination reasons.
t=r/'tasks/technical-0/output';u=json.loads((t/'USAGE.json').read_text())
physical={'world_resets':u['physics_worlds'],'controller_actions':20*u['physics_worlds'],'native_CEM_decisions':1,'PushT_world_resets':u['physics_worlds']}
for p in (t/'oracle').glob('*/PREFIX.json'):physical['controller_actions']+=json.loads(p.read_text())['actions']
for p in (t/'evaluation').glob('*/BRANCH.json'):
 x=json.loads(p.read_text());physical['controller_actions']+=x['elapsed'];physical['native_CEM_decisions']+=x['tail_replans']
physical['PushT_integrator_steps']=10*physical['controller_actions']+2*physical['world_resets']
unique={}
for p in r.rglob('*'):
 if p.is_file() and not p.is_symlink():
  st=p.stat();unique[(st.st_dev,st.st_ino)]=st.st_size
v=os.statvfs(str(r))
print(json.dumps({'status':'STOPPED_DAG_FULLY_TERMINAL_RECONCILED','UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scheduler':raw,'queue':q,
 'GPU_charged_seconds':charge,'CPU_charged_before':1436,'accepted':accepted,'results':results,'STOP':stop,
 'failed_partial_members':partial,'failed_bank_shape':header['shape'],'failed_before_oracle_evaluation':True,
 'failed_physics':{'world_resets':1,'controller_actions':20,'PushT_integrator_steps':202,'native_CEM_decisions':1},
 'accepted_technical0_usage':u,'accepted_technical0_physical':physical,'old_campaign_bytes':sum(unique.values()),
 'cluster_free_bytes':v.f_bavail*v.f_frsize,'scientific_values_read_or_released':False}))
'''

def main():
    DOC.mkdir(exist_ok=True)
    result = ssh('RUN='+repr(OLD_RUN)+'\nEXPECTED='+repr(OLD_CONTRACT)+'\n'+PROGRAM)
    write_new(DOC/'RECONCILIATION-001.json', result)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
