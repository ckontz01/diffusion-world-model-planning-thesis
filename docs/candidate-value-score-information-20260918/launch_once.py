"""Operational single-submission record; does not modify the approved worker."""
import hashlib,json,subprocess,time,os
from pathlib import Path
ROOT=Path('/lustreFS/data/superworld/ckontzias/thesis')
VERSION='candidate-value-score-information-20260918'
SOURCE=ROOT/'snapshots'/ (VERSION+'-68145e6458da0b90')
PARENT=ROOT/'experiments'/VERSION
SHA='68145e6458da0b90255dd98e4fa2b9469dea12907797d7830c9bd233314be35c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
assert sha(SOURCE/'SI1-SOURCE-MANIFEST.sha256')==SHA
for line in (SOURCE/'SI1-SOURCE-MANIFEST.sha256').read_text().splitlines():
    digest,name=line.split('  ',1);assert sha(SOURCE/name)==digest
old=subprocess.check_output(['sacct','-S','2026-09-18','--name=si1-score-info','--format=JobID','--noheader']).decode().strip()
assert not old, 'Prior SI1 allocation exists'
assert not PARENT.exists(), 'Prior SI1 namespace exists'
template=json.loads((SOURCE/'APPROVAL-TEMPLATE.json').read_text());assert template['execution_authorized'] is False
assert template['source_sha256']==SHA and template['fits']==24
env=ROOT/'envs/hi-lewm-artifact-py311-cu121-swm006'
image=ROOT/'containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'
assert (env/'bin/python').is_symlink() and os.readlink(str(env/'bin/python'))=='/opt/conda/bin/python' and image.is_file()
PARENT.mkdir()
control=PARENT/'control';control.mkdir()
approval=dict(template,execution_authorized=True,
    approved_commit='b1cfcdd8e062ca995feb439e4d8cefe2dac40f08',
    folds_sha256=sha(SOURCE/'docs'/VERSION/'FOLDS.json'),
    runtime_environment=str(env),runtime_image=str(image),
    authorization='Researcher SI1 execution approval; one allocation; no retry',
    backup_destination='D:/THESIS-BACKUPS/'+VERSION+'/execution-68145e6458da0b90',
    backup_volume='0a2f1ba9-0000-0000-0000-100000000000')
write(control/'EXECUTION-APPROVAL.json',approval)
out=PARENT/'run-68145e6458da0b90'
cmd=['sbatch','--parsable','--job-name=si1-score-info','--account=superworld','--partition=defq',
     '--qos=normal','--cpus-per-task=4','--mem=8G','--time=02:00:00','--no-requeue',
     '--chdir='+str(SOURCE),'--output='+str(control/'slurm-%j.out'),
     '--error='+str(control/'slurm-%j.err'),str(SOURCE/'cluster/prometheus/run_score_information.sh'),
     str(SOURCE),str(control/'EXECUTION-APPROVAL.json'),str(out)]
write(control/'SUBMISSION-CLAIM.json',dict(command=cmd,utc=time.time(),no_retry=True))
result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
record=dict(returncode=result.returncode,stdout=result.stdout.decode(),stderr=result.stderr.decode(),
            utc=time.time(),approval_sha256=sha(control/'EXECUTION-APPROVAL.json'),source_sha256=SHA)
write(control/'SUBMISSION-RESULT.json',record)
print(json.dumps(record));assert result.returncode==0
