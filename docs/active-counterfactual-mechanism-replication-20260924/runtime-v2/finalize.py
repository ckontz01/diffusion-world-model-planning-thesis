"""Independent final acceptance, exact terminal snapshot, optionally bound fault resolution."""
import common as c
import argparse
from pathlib import Path
import acceptance
import scheduler
def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--control',required=True);p.add_argument('--resolution');a=p.parse_args()
    auth=c.Authorization(a.approval,a.run);control=Path(a.control)
    state=acceptance.ledger(control,c.grid(),False)
    ids=[e['job'] for e in state['submitted'].values()]
    c.require(len(ids)==8197,'All tasks dispatched before finalization')
    raw=scheduler.observe(control,ids,'independent-final-acceptance')
    result=acceptance.full(auth,control,[scheduler.parse(r) for r in raw.splitlines() if r],a.resolution)
    c.write(control/'FINAL-ACCEPTANCE.json',result)
    print(c.json.dumps({k:v for k,v in result.items() if k!='receipts'}))
if __name__=='__main__':main()
