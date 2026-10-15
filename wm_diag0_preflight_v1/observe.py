"""Read exact-dispatch scheduler/process/control/tensor-metadata only; no action."""
import hashlib
import json
import struct
import sys
from wm_diag0_preflight_v1.common import DOC,RUN,identity,write_new,reservation
from wm_diag0_preflight_v1.transport import ssh

def main():
    label=sys.argv[1]
    if not label.isalnum(): raise ValueError('exclusive observation label')
    doc=DOC/'stage-recovery-r1' if len(sys.argv)>2 and sys.argv[2]=='stage-r1' else DOC
    run=RUN+'-stage-r1' if doc!=DOC else RUN
    dest=doc/('OBSERVATION-'+label+'.json')
    if dest.exists(): raise FileExistsError('no overwrite')
    dispatch=json.loads((doc/'DISPATCH-001.json').read_text()); job=dispatch['job_id']
    if not job.isdigit(): raise ValueError('exact ID')
    code='RUN='+repr(run)+'\nJOB='+repr(job)+'\n'+'''
import hashlib,json,pathlib,subprocess,time
root=pathlib.Path(RUN)
def call(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
 return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
r={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'job_id':JOB,
   'squeue':call(['squeue','-j',JOB,'-h','-o','%i|%j|%T|%N|%M']),
   'sacct':call(['sacct','-j',JOB,'-X','-n','-P','--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,ReqMem,NodeList,Start,End']),
   'controls':{},'output':{},'logs':{}}
for group in ('controls','output','logs'):
 total=0
 for p in sorted((root/group).iterdir()):
  if not p.is_file() or p.is_symlink(): raise RuntimeError('unexpected member type')
  total+=p.stat().st_size
  if total>({'controls':150000,'output':1000000,'logs':100000}[group]): raise RuntimeError('metadata read bound')
  raw=p.read_bytes()
  r[group][p.name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'data':json.loads(raw) if p.suffix=='.json' else raw.decode('utf8',errors='replace')}
print(json.dumps(r))
'''
    r=ssh(code)
    r['parent_review']={'accepted':False,'full_campaign_ready':False}
    rows=[s.split('|') for s in r['sacct']['stdout'].strip().splitlines() if s]
    if len(rows)==1 and rows[0][0]==job and rows[0][1]=='COMPLETED' and rows[0][2]=='0:0':
        elapsed=int(rows[0][3]); reservation(elapsed)
        if elapsed>1200 or rows[0][4]!='4': raise ValueError('allocation bounds')
        expected={'runtime.json','dino-pusht.json','dino-reacher.json','encoder.json','lewm-pusht.json','lewm-reacher.json','SUCCESS.json'}
        if set(r['output'])!=expected: raise ValueError('complete output member set')
        if r['controls']['DISPATCH.json']['data']['job_id']!=job: raise ValueError('dispatch authentication')
        c=identity(doc/'CONTRACT.json')['sha256']
        if r['controls']['INPUTS-VERIFIED.json']['data']['contract_sha256']!=c: raise ValueError('contract authentication')
        if r['controls']['ALLOCATION-RESULT.json']['data']['status']!='CPU_PREFLIGHT_COMPLETED': raise ValueError('supervisor acceptance')
        success=r['output']['SUCCESS.json']['data']
        if success['forwards']!=0 or success['physics_steps']!=0 or success['job_id']!=job: raise ValueError('non-forward stage')
        # Independent expected mask bits from the fixed 3 x 196 architecture,
        # not from a converter/worker-emitted manifest.
        bits=b''.join(struct.pack('<f',float(i//196>=j//196)) for i in range(588) for j in range(588))
        mask_hash=hashlib.sha256(bits).hexdigest()
        for task in ('pusht','reacher'):
            d=r['output']['dino-'+task+'.json']['data']; tensors=d['objects']['predictor']['tensors']
            if len(d['required_masks'])!=6: raise ValueError('lost causal mask')
            for key in d['required_masks']:
                m=tensors[key]
                if m['kind']!='unregistered' or m['shape']!=[1,1,588,588] or m['dtype']!='torch.float32' or m['sha256']!=mask_hash: raise ValueError('independent causal mask identity')
        r['parent_review']={'accepted':True,'accepted_stage':'CPU_LOAD_AND_METADATA_ONLY','cpu_allocation_seconds':elapsed,
                            'other_cpu_full_future_seconds':12600,'cpu_total_charged_plus_full_future':elapsed+12600,
                            'gpu_allocation_seconds':0,'gpu_full_future_seconds':468000,'conversion_seconds':0,
                            'full_campaign_ready':False,'functional_equivalence_tested':False}
    write_new(dest,r)
    print(json.dumps({'job_id':job,'squeue':r['squeue'],'sacct':r['sacct'],'review':r['parent_review'],
                      'result':r['controls'].get('ALLOCATION-RESULT.json'),'logs':r['logs']},indent=2))

if __name__=='__main__': main()
