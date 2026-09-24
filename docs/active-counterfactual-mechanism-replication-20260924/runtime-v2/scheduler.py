"""Strict Slurm identities; finite, exact pending-placeholder grace in dispatcher."""
import common as c
import subprocess
import time
FIELDS='JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList,Partition,QOS,Account,TimelimitRaw'
ACTIVE={'PENDING','RUNNING','CONFIGURING','COMPLETING'}
TERMINAL={'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','BOOT_FAIL','DEADLINE','PREEMPTED','REVOKED'}
DEVICE='NVIDIA RTX 6000 Ada Generation'

def columns(raw):
    r=raw.split('|')
    if len(r)==13 and r[-1]=='': r.pop()
    c.require(len(r)==12,'Scheduler column count'); return r
def parse(raw):
    r=columns(raw)
    c.require(all(r) and all(r[i].isdigit() for i in (0,4,5,11)),'Incomplete terminal identity')
    t=dict(x.split('=',1) for x in r[6].split(',') if '=' in x)
    return dict(job=r[0],name=r[1],state=r[2].split()[0],exit=r[3],seconds=int(r[4]),cpus=int(r[5]),tres=t,
                node=r[7],partition=r[8],qos=r[9],account=r[10],minutes=int(r[11]),raw=raw)
def status(raw,job,spec):
    rows=[columns(s) for s in raw.splitlines() if s]
    if not rows: return 'INCOMPLETE'
    c.require(len(rows)==1 and rows[0][0]==str(job),'Exact submitted allocation ID')
    r=rows[0]
    if spec['gpu'] and r==[str(job),'allocation','PENDING','0:0','0','0','','gpu09','','Unknown','superworld','']:
        return 'INCOMPLETE'
    c.require(r[1]=='acvm1-'+spec['key'],'Exact task name (no requeue or generic placeholder acceptance)')
    state=r[2].split()[0]
    c.require(state in ACTIVE|TERMINAL,'Unknown scheduler state')
    return state
def allocation(spec,row,successful=True):
    t=row['tres']
    c.require(row['job'].isdigit() and row['name']=='acvm1-'+spec['key'],'Allocation identity')
    c.require(row['state'] in TERMINAL,'Terminal required')
    if successful: c.require(row['state']=='COMPLETED' and row['exit']=='0:0','Successful exit required')
    c.require(0<=row['seconds']<=spec['seconds'] and row['minutes']==spec['seconds']//60,'Hard wall envelope')
    c.require(row['cpus']==4 and t.get('cpu')=='4' and t.get('node')=='1','Four CPU/single node')
    c.require(int(t.get('gres/gpu',0))==spec['gpu'] and row['account']=='superworld','GPU/account')
    c.require(row['partition']==('a6000' if spec['gpu'] else 'defq') and row['qos']==('normal-a6000' if spec['gpu'] else 'normal'),'Site partition/QOS')
    c.require(t.get('mem') in (str(spec['ram_gib'])+'G',str(spec['ram_gib']*1024)+'M'),'Memory allocation')
    c.require(row['node']=='gpu09' if spec['gpu'] else bool(row['node']) and not any(x in row['node'] for x in ',[] '),'Exact GPU node')
def association(h,row):
    c.require((h['hostname'],row['node']) in (('gpu09','gpu09'),('gpu09.cluster','gpu09')),'Authenticated hostname pair')
    c.require(h['slurm_job_id']==row['job'] and h['accepted'] is True and h['query_status']=='complete' and h['cuda_available'] is True
              and h['visible_device_count']==1 and h['device_name']==DEVICE,'Exact hardware/job association')
def observe(control,ids,label):
    cmd=['/usr/bin/sacct','-X','-n','-P','-j',','.join(map(str,ids)),'--format='+FIELDS]
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        receipt=dict(unix=time.time(),ids=list(map(str,ids)),command=cmd,stdout=p.stdout,stderr=p.stderr,returncode=p.returncode)
    except subprocess.TimeoutExpired as e:
        receipt=dict(unix=time.time(),ids=list(map(str,ids)),error='timeout',stdout=str(e.stdout or ''),stderr=str(e.stderr or ''),returncode=124)
    # Always preserve raw evidence BEFORE parsing, including on a fault.
    c.append(control/'SCHEDULER.jsonl',dict(label=label,**receipt))
    c.require(receipt['returncode']==0,'Scheduler unavailable; no inference of research failure')
    return receipt['stdout']
