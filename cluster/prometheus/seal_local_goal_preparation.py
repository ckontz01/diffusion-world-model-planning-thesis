"""Generate preparation-only pins and synthetic test evidence. No real data."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
import torch
from local_goal_models import LocalProposer
from candidate_value_contract import HISTORICAL, allocation

REPO=Path(__file__).resolve().parents[2]
DOC=REPO/'docs/local-goal-proposals-20260918'
BASE='a99d6d144300a3067c86ee295c94f4775f06267c'

def write(name,value):
    with (DOC/name).open('x',encoding='utf8',newline='\n') as f:
        json.dump(value,f,indent=2,sort_keys=True);f.write('\n')

def main():
    torch.set_num_threads(1)
    suite=unittest.defaultTestLoader.discover(str(REPO/'cluster/prometheus'),pattern='test_local_goal_proposals.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful(): raise RuntimeError('Synthetic test failure')
    counts={}
    for family in ('gmm','diffusion'):
        model=LocalProposer(family)
        counts[family]=sum(p.numel() for p in model.parameters())
        del model
    write('TEST-RESULTS.json',dict(tests=result.testsRun,failures=0,errors=0,
        synthetic_only=True,optimizer_steps=0,checkpoint_loads=0,simulator_calls=0,
        torch_version=torch.__version__,full_width_parameter_counts=counts))
    selected=tuple(HISTORICAL)
    assert len(selected)==32 and not set(selected)&set(allocation()['closed_loop'])
    write('DATA-ROLES.json',dict(expert_roles='Existing P1_train/P1_val minus entire released SAGE val/test roles and paper memberships; INVENTORY-ELIGIBLE.json',
        episode_registry_sha256='34dcff8a457fb636fbee836e836f752de66013154c36739613b9d5c81dcba5e6',
        development_reference_indices=list(selected),training_seeds=[8301,8302,8303],
        technical_reference_indices=list(selected[:2]),horizons=[75,150],
        reference_namespace='independent-pusht/final-20260906-4a608e5/collection',
        whole_source_roles=True,reference_payloads_opened=False,
        reserved_closed_loop_excluded=True,indices_1600_5999_excluded=True))
    paths=['cluster/prometheus/e18_fresh_driver.py','cluster/prometheus/pusht_fresh_initialization.py',
        'cluster/prometheus/INDEPENDENT-PINNED-INPUTS.json','cluster/prometheus/gdp_cem_e14_models.py',
        'cluster/prometheus/gdp_cem_e18.py','cluster/prometheus/independent_pusht_runtime.py',
        'cluster/prometheus/candidate_value_contract.py']
    pins={}
    for name in paths:
        p=REPO/name
        if not p.exists():
            if name.endswith('/gdp_cem_e18.py'): continue
            raise RuntimeError(name)
        original=subprocess.check_output(['git','show',BASE+':'+name],cwd=REPO)
        # Git's checked-in bytes are the immutable source identity, not checkout CRLF.
        if original.replace(b'\r\n',b'\n') != p.read_bytes().replace(b'\r\n',b'\n'):
            raise RuntimeError('Reused source modified: '+name)
        pins[name]=hashlib.sha256(original).hexdigest()
    write('SOURCE-PINS.json',dict(thesis_base_commit=BASE,source_files=pins,
        sage_commit='8219029fd52e89157e05aebb998ab26f0ef46966',
        sage_tree='0c64066eeac97c27fee382c1879bb26968b3fd56',
        generator_sha256='0b3647a3a41435969d750ec58176ef5f92a419c4eacae2b5cda74b35e63f90da'))
    print(json.dumps({'tests':result.testsRun,'parameters':counts,'preparation_only':True}))

if __name__=='__main__': main()
