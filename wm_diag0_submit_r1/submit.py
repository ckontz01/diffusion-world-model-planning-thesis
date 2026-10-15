"""One precise scheduler repair, original frozen scientific sources unchanged."""
import ast,json
from .common import DOC,BASE,RUN,ROOT,SOURCE_COMMIT,identity,write_new
from .preserve import published
from wm_diag0_native_v3.transport import ssh
from wm_diag0_campaign_v4.submit import specification

def program(expected,publication):
    # Reuse the immutable reviewed dispatch algorithm, changing only journal
    # names, reconciliation guard, and the already-authorized GPU QOS flag.
    from wm_diag0_preflight_v1.preserve import git
    raw=(ROOT/'wm_diag0_campaign_v4/submit.py').read_bytes()
    if raw!=git('show',SOURCE_COMMIT+':wm_diag0_campaign_v4/submit.py'):raise ValueError('frozen dispatcher template bytes')
    tree=ast.parse(raw);literals=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith('import hashlib,json,os,pathlib,subprocess,time')]
    if len(literals)!=1:raise ValueError('exact reviewed dispatcher body')
    code=literals[0]
    old="if any((control/n).exists() for n in ('DAG-DISPATCH.json','SUBMIT-STARTED.json','STOP.json')):raise RuntimeError('existing/ambiguous campaign; never duplicate')"
    new="""if any((control/n).exists() for n in ('DAG-DISPATCH.json','SUBMIT-R1-STARTED.json','STOP.json')):raise RuntimeError('existing/ambiguous repaired campaign; never duplicate')
previous=json.loads((control/'SUBMISSION-ERROR.json').read_text())
if previous['known_job_ids'] or any((r/'tasks').iterdir()):raise RuntimeError('previous live/ambiguous/accepted work; no repeated compute')
if json.loads((control/'SBATCH-readout-RESPONSE.json').read_text())['stderr']!='sbatch: error: Batch job submission failed: Invalid qos specification'+chr(10):raise ValueError('exact rejected nonallocation fault')
write('SUBMISSION-R1-PUBLICATION.json',PUBLICATION)"""
    if code.count(old)!=1:raise ValueError('exact guard replacement')
    code=code.replace(old,new).replace("write('SUBMIT-STARTED.json'","write('SUBMIT-R1-STARTED.json'")
    code=code.replace("if gpu:args+=['--gres=gpu:1']","if gpu:args+=['--gres=gpu:1','--qos=normal-a6000']")
    for old,new in (("write('SBATCH-'+phase","write('SBATCH-R1-'+phase"),("write('RELEASE-'+phase","write('RELEASE-R1-'+phase"),("write('SUBMISSION-ERROR.json'","write('SUBMISSION-R1-ERROR.json'"),("write('SUBMISSION-CANCEL-'+phase","write('SUBMISSION-R1-CANCEL-'+phase")):
        code=code.replace(old,new)
    result='RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\nSPEC='+repr(specification())+'\nPUBLICATION='+repr(publication)+'\n'+code
    ast.parse(result,feature_version=(3,6));return result

def main():
    p=published();expected=identity(BASE/'campaign/CONTRACT.json')['sha256']
    write_new(DOC/'SUBMIT-001.started.json',{'scientific_contract':expected,'GPU_QOS':'normal-a6000','previous_GPU_allocations':0})
    r=ssh(program(expected,p));write_new(DOC/'DAG-DISPATCH-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
