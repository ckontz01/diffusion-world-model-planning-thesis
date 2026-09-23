"""Final bounded namespace reconciliation before the sole R1 launch."""
import operate as o
CODE=r'''
from pathlib import Path
import sys,time
source=Path(CONFIG['source']);control=Path(CONFIG['control']);run=Path(CONFIG['run'])
assert not run.exists() and not (control/'LAUNCH-INTENT.json').exists(),'Existing or ambiguous R1 launch'
sys.path.insert(0,str(source/CONFIG['rel']))
import common as c,recovery
auth=c.Authorization(control/'EXECUTION-APPROVAL.json',run)
reconciled=recovery.reconcile();inventory={}
for label in ('source','control'):
 parent=Path(CONFIG[label]).parent
 matches={str(p) for p in parent.iterdir() if 'active-counterfactual' in p.name.lower() or 'acv0' in p.name.lower()}
 expected={CONFIG[label],CONFIG['prior']['paths'][label]}
 assert matches==expected,(label,sorted(matches),sorted(expected))
 inventory[label]=sorted(matches)
matches={str(p) for p in run.parent.iterdir()}
assert matches=={CONFIG['prior']['paths']['run']},('Run namespaces',sorted(matches))
inventory['runs']=sorted(matches)
result={'unix':time.time(),'namespace_inventory':inventory,'unknown_namespaces':0,
 'r1_run_absent':True,'r1_launch_intent_absent':True,'reconciliation':reconciled}
c.write(control/'NAMESPACE-AUDIT.json',result);print(json.dumps(result))
'''
if __name__=='__main__':o.once('NAMESPACE-AUDIT',CODE)
