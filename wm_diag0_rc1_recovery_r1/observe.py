"""One compact current recovery-array observation; no research mutation."""
import json,time,sys
from .common import *
from .transport import call

READ=r'''
import hashlib,json,os,pathlib,re,shlex,subprocess,time
root=pathlib.Path(RUN);old=pathlib.Path(OLD)
def ident(p):
 h=hashlib.sha256();n=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
 return {'bytes':n,'sha256':h.hexdigest()}
def body(p):
 if p.stat().st_size>20000:raise ValueError('finite technical control')
 return json.loads(p.read_text())
if ident(root/'source/GRID-CONTRACT.json')['sha256']!=EXPECTED:raise ValueError('published recovery contract')
c=body(root/'controls/DISPATCH.json');jid=c['array_job_id']
if not jid.isdigit() or c['original_indices']!=list(range(66,124)) or c['contract_sha256']!=EXPECTED:raise ValueError('exact dispatched recovery')
p=subprocess.run(['sacct','-X','-n','-P','-j',jid,'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=5)
if p.returncode:raise RuntimeError('exact current recovery accounting unavailable '+p.stderr)
raw=[x.split('|') for x in p.stdout.splitlines() if x];rows=[];coverage=[];terminal={'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}
gpu=45902;done=0;live=0;rawids=[];faults=[]
for x in raw:
 if len(x)!=7 or not x[0].startswith(jid+'_') or x[5]!='4' or not x[4].isdigit() or not 0<=int(x[4])<=3600:raise ValueError('bound exact recovery scheduler columns')
 index=x[0][len(jid)+1:];state=x[2].split()[0];row=[index]+x[1:];rows.append(row)
 if index.isdigit():indices=[int(index)]
 elif re.fullmatch(r'\[[0-9,%-]+\]',index) and state in ('PENDING','CANCELLED') and x[4]=='0' and x[6]=='None assigned':
  indices=[]
  for part in index[1:-1].split('%')[0].split(','):
   ends=part.split('-')
   if not 1<=len(ends)<=2:raise ValueError('finite group range')
   indices.extend(range(int(ends[0]),int(ends[-1])+1))
 else:raise ValueError('unrecognized recovery logical task')
 coverage+=indices
 if x[6] in ('gpu09','gpu09.cluster'):
  if len(indices)!=1:raise ValueError('no grouped allocated attempts')
  rawids.append(x[1])
  if state in terminal:gpu+=int(x[4]);done+=1
  else:live+=1
 elif state not in ('PENDING','CANCELLED') or x[6]!='None assigned' or x[4]!='0':raise ValueError('no ambiguous allocated identity')
 if state in terminal and (state!='COMPLETED' or x[3]!='0:0'):faults.append({'indices':indices,'state':x[2],'exit':x[3]})
if sorted(coverage)!=list(range(66,124)) or len(set(rawids))!=len(rawids) or live>1 or gpu+(58-done)*3600>468000:raise ValueError('complete serial failure-inclusive recovery allocation bounds')
q=subprocess.run(['squeue','-h','-j',jid,'-o','%i|%T|%M|%N|%R'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=4)
all_terminal=all(x[2].split()[0] in terminal for x in raw)
if q.returncode and not (q.returncode==1 and not q.stdout.strip() and q.stderr.strip()=='slurm_load_jobs error: Invalid job id specified' and all_terminal):raise RuntimeError('queue ambiguous; terminal guard retained '+q.stderr)
accepted=[];active=[];controls={}
table={x[0]:x for x in rows if x[0].isdigit()}
for i in range(66):
 t=old/'tasks'/('grid-'+str(i));r=body(t/'controls/RESULT.json');a=body(t/'controls/ACCEPTED.json')
 if r['status']!='ACCEPTED' or a['accepted'] is not True or ident(t/'controls/ACCEPTED.json')!=r['acceptance_identity'] or ident(t/'output/MEMBERS.json')!=a['output_seal']:raise ValueError('preserved accepted original parent changed')
for i in range(66,124):
 t=root/'tasks'/('grid-'+str(i));s=body(t/'controls/STARTED.json') if (t/'controls/STARTED.json').exists() else None
 r=body(t/'controls/RESULT.json') if (t/'controls/RESULT.json').exists() else None
 a=body(t/'controls/ACCEPTED.json') if (t/'controls/ACCEPTED.json').exists() else None
 if s and (s['contract']!=EXPECTED or s['array_job_id']!=jid or s['index']!=i):raise ValueError('new start source/raw/index')
 if a and r:
  row=table.get(str(i))
  if r['status']!='ACCEPTED' or a['accepted'] is not True or a['contract_sha256']!=EXPECTED or not row or row[1]!=r['job_id'] or not s or s['job_id']!=r['job_id'] or row[2:4]!=['COMPLETED','0:0']:raise ValueError('new independent accepted scheduler chain')
  if ident(t/'controls/ACCEPTED.json')!=r['acceptance_identity'] or ident(t/'output/MEMBERS.json')!=a['output_seal'] or a['output_seal']!=r['output_seal']:raise ValueError('new accepted control/seal')
  accepted.append(i)
 if s and not r:active.append(s)
 if r and r['status']=='FAILED':faults.append({'index':i,'error':str(r.get('error',''))[:512]})
if len(active)>1:raise ValueError('one active controller')
for s in active:
 if s['node'] not in ('gpu09','gpu09.cluster'):raise ValueError('actual compute-node namespace required')
 code="import json,pathlib;p=pathlib.Path('/proc')/"+repr(str(s['PID']))+"/'stat';print(json.dumps({'PID_exists':p.exists(),'start_ticks_match':p.exists() and p.read_text().rsplit(')',1)[1].split()[19]=="+repr(str(s['start_ticks']))+"}))"
 v=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=2',s['node'],'python3 -B -c '+shlex.quote(code)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=3)
 s['node_verification']=json.loads(v.stdout) if v.returncode==0 else {'unavailable':True,'returncode':v.returncode}
stop=body(root/'controls/STOP.json') if (root/'controls/STOP.json').exists() else None
z={'status':'CURRENT_RECOVERY_TECHNICAL_SNAPSHOT','array_job_id':jid,'contract_sha256':EXPECTED,'original_preserved_accepted':66,'recovery_accepted':len(accepted),'accepted_grid_total':66+len(accepted),'accepted_recovery_bitmask_hex':hex(sum(1<<i for i in accepted)),
 'scheduler_rows':rows,'queue_returncode':q.returncode,'queue_stderr':q.stderr,'queue_stdout':q.stdout,'active_process_records':active,'STOP':stop,'faults':faults,
 'GPU_terminal_all_attempts':gpu,'GPU_full_remaining_maxima_plus_terminal':gpu+(58-done)*3600,'all_old_failures_retained':True,'scientific_values_or_quality_read':False,'research_mutations':False,'final_gate_ready':False,'captured_epoch':time.time()}
if len(json.dumps(z,separators=(',',':')).encode())>10000:raise ValueError('compact monitoring bound')
print(json.dumps(z,sort_keys=True,separators=(',',':')))
'''

def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('new exclusive observation label')
    pub=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    for n,x in pub['working_source_members'].items():
        if identity(ROOT/n)!=x:raise ValueError('published observer closure unchanged')
    if not Path('D:/WSL/Thesis-Ubuntu/ext4.vhdx').is_file():raise RuntimeError('existing WSL path unavailable, not research failure')
    code='RUN='+repr(RUN)+'\nOLD='+repr(OLD)+'\nEXPECTED='+repr(pub['contract']['sha256'])+'\n'+READ
    z=call('OBSERVE'+label,code,seconds=20)
    print(json.dumps({'status':z['status'],'accepted_grid_total':z['accepted_grid_total'],'active_process_records':z['active_process_records'],'STOP':z['STOP'],'faults':z['faults']}))

if __name__=='__main__':main()
