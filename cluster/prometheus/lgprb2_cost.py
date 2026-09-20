"""Preparation cost arithmetic using only published completed RB1 accounting."""
import argparse,json,hashlib
from pathlib import Path
import lgprb2_contract as c

def prepare(repo):
    repo=Path(repo);base=Path('D:/THESIS-BACKUPS/local-goal-search-budget-20260919/preparation-v1')
    c.require(c.sha(base/c.rb1.MANIFEST)==c.RB1_SOURCE_SHA,'Actual executed source')
    old=c.read(repo/c.rb1.DOC/'REUSE.json')
    names=('lgp1_runtime.py','lgp1_tensor.py','local_goal_models.py','local_goal_proposals.py','lgp1_endpoint.py',
           'e18_fresh_driver.py','pusht_fresh_initialization.py','lgp1_train.py')
    unchanged={f'cluster/prometheus/{n}':c.sha(base/'cluster/prometheus'/n) for n in names}
    c.require(all(hashlib.sha256((repo/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==d for n,d in unchanged.items()),'Checkout matches actual policy/model/endpoint contracts')
    c.write(repo/c.DOC/'REUSE.json',dict(rb1_source_sha256=c.RB1_SOURCE_SHA,original_model_freeze_sha256=c.FREEZE_SHA,
        models=old['models'],unchanged_files=unchanged,historical_episodes_reused=0,
        historical_scientific_record='8a79e267cb0cb7b6243900cb3bc194e0eb069a85'))
    a=c.read(repo/c.rb1.DOC/'FINAL-ACCOUNTING.json');configs=a['configurations']
    # Publish raw measured summary inputs; estimates do not inspect new sources.
    selected=[v for v in configs if v['populations'] in (5,30)] if isinstance(configs,list) else configs
    c.write(repo/c.DOC/'MEASURED-COST-INPUTS.json',dict(accounting_sha256=hashlib.sha256((repo/c.rb1.DOC/'FINAL-ACCOUNTING.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        configurations=selected,source_count=32,scenarios='Four separately loaded measured jobs summed is a no-batching-credit baseline; use full 30 stages per arm then conservative overhead multiplier.'))
    print(json.dumps(selected,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);prepare(p.parse_args().repo)
