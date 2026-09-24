"""Create a separate enabled capability from the exact delivered instruction."""
import sys
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-mechanism-replication-20260924/runtime-v2'
sys.path.insert(0,str(ROOT))
import common as c

def main():
    instruction=Path(sys.argv[1])
    c.require(c.sha(instruction)=='b97743d0b3599dc1099377b515f5c8a301333a2df8a6c1aff695fa31a40780da','Exact delivered instruction')
    c.require(c.read(HERE/'PRELAUNCH.json')['status']=='PRELAUNCH_PASSED','Fresh checks required')
    c.require(time.time()-c.read(HERE/'PRELAUNCH.json')['unix']<1800,'Prelaunch receipt age')
    c.require(not (HERE/'EXECUTION-APPROVAL.json').exists(),'Never overwrite approval')
    template=ROOT/'EXECUTION-APPROVAL.json'
    c.require(c.sha(template)=='2e9afd7dee838c4b14ada69215dc151844908fd10f0e3c8bc6fbbe389d9f4c70','False template')
    with (HERE/'AUTHORIZATION-INSTRUCTION.md').open('xb') as f:f.write(instruction.read_bytes())
    approval=c.read(template)
    c.require(approval['authorized'] is False and approval['instruction']=='','Original disabled schema')
    approval['authorized']=True
    approval['instruction']=instruction.read_bytes().decode('utf8')
    c.write(HERE/'EXECUTION-APPROVAL.json',approval)
    authenticated=c.Authorization(HERE/'EXECUTION-APPROVAL.json',approval['run'])
    receipt=dict(unix=time.time(),authorization_basis='Explicit supplied execution direction under the user standing delegation; not a newly obtained direct user signature',instruction_sha256=c.sha(HERE/'AUTHORIZATION-INSTRUCTION.md'),enabled_approval_sha256=authenticated.approval_sha,false_template_sha256=c.sha(template),prelaunch_sha256=c.sha(HERE/'PRELAUNCH.json'),source_commit='d1710a059b047a37b4cd6419b087543c7ae0f6fa',reviewed_delivery_commit='7fa8ab412d0c24f9b0afc7854980733fb8dcc24e',manifest=approval['package_sha256'],bindings=approval['bindings'],caps=approval['caps'],run=approval['run'],no_retry=True,scientific_changes=False,old_monitors_restarted=False)
    c.write(HERE/'AUTHORIZATION.json',receipt)
    print(c.json.dumps(receipt))

if __name__=='__main__':main()
