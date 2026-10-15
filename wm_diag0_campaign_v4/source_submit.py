"""Exact fixed source array under repaired/import-tested contract; no retry."""
import json
from .common import DOC,SOURCE_RUN,identity,write_new
from .small import published
from wm_diag0_native_v3.transport import ssh

def main():
    published('source-import-r1');path=DOC/'source-import-r1';expected=identity(path/'CONTRACT.json')['sha256']
    write_new(path/'SUBMIT-001.started.json',{'contract_sha256':expected,'source_attempts':120,'replacements':0})
    code='RUN='+repr(SOURCE_RUN)+'\nEXPECTED='+repr(expected)+'\n'+'''
import json,os,pathlib,subprocess,time
r=pathlib.Path(RUN);control=r/'controls'
def write(n,x):
 with (control/n).open('x') as f:json.dump(x,f,sort_keys=True)
if any((control/n).exists() for n in ('DISPATCH-source.json','SUBMIT-source-STARTED.json','STOP.json')):raise RuntimeError('existing or ambiguous source execution; reconcile before action')
if json.loads((control/'STAGE-VERIFIED.json').read_text())['contract_sha256']!=EXPECTED:raise ValueError('stage identity')
checked=json.loads((control/'NATIVE-IMPORT-CHECK.json').read_text())
if checked['returncode']!=0:raise ValueError('new native import check failed')
queue=subprocess.check_output(['squeue','-u',str(os.getuid()),'-h','-o','%i|%j|%T'],universal_newlines=True)
if any('wm-a2-' in line for line in queue.splitlines()):raise RuntimeError('existing study job; no duplication')
write('SUBMIT-source-STARTED.json',{'time':time.time(),'contract_sha256':EXPECTED,'array_elements':120,'replacements':0})
script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),'exec python3 -B -m wm_diag0_native_v3.supervisor '+RUN+' '+EXPECTED+' source',''])
p=subprocess.run(['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-source-import-r1','--partition=defq','--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--time=00:01:00','--array=0-119%1','--chdir='+str(r/'source'),'--output='+str(r/'logs/source-%A_%a.log'),'--error='+str(r/'logs/source-%A_%a.log')],input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-source-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('sbatch failed; preserve no retry')
job=p.stdout.strip().split(';')[0]
if not job.isdigit():raise RuntimeError('ambiguous submission, never retry')
d={'job_id':job,'contract_sha256':EXPECTED,'array_elements':120,'allocation_seconds_each':60,'full_future_source_seconds':7200,'CPU_charged_before':17,'CPU_other_full_future_seconds':5400,'GPU_full_future_seconds':468000,'maximum_concurrency':1,'replacements':0}
write('DISPATCH-source.json',d)
p=subprocess.run(['scontrol','release',job],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE-source-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});d['release_returncode']=p.returncode
print(json.dumps(d))
'''
    r=ssh(code);write_new(path/'DISPATCH-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
