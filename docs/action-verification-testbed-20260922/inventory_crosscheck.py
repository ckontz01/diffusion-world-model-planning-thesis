"""Read-only reconciliation of canonical metadata; no source payload access."""
import json
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]


def main():
    paths={'rb2':'docs/local-goal-source-replication-20260920/DATA-ROLES.json',
           'bp1':'docs/candidate-value-breadth-precision-20260915/DATA-ROLES.json',
           'si1':'docs/candidate-value-score-information-20260918/FOLDS.json',
           'lgp1':'docs/local-goal-proposals-20260918/DATA-ROLES.json'}
    data={k:json.loads((REPO/p).read_text()) for k,p in paths.items()}
    ex={k:set(v) for k,v in data['rb2']['exclusion_roles'].items()}
    b=data['bp1']['allocation']
    for key in ('original_train','extra_train','evaluation'):
        assert set(b[key])==ex['BP1-'+key]
    for key in ('train','validation','closed_loop','historical_32'):
        assert set(b['exclusions'][key])==ex['BP1-recorded-'+key]
    for key in ('train','validation','closed_loop'):
        assert set(b['exclusions'][key])==ex['CVL-'+key]
    si=set().union(*(set(v) for v in data['si1']['held_out']))
    assert len(si)==192 and si==ex['SI1-fitting-heldout']
    assert si==ex['BP1-original_train']|ex['BP1-extra_train']
    assert set(data['lgp1']['development_reference_indices'])==ex['LGP1/RB1-development']
    assert set(data['lgp1']['technical_reference_indices'])==ex['LGP1-technical']
    out={'passed':True,'comparisons':14,'payload_reads':0,
         'pins':{k:{'path':p,'sha256':hashlib.sha256((REPO/p).read_bytes()).hexdigest()} for k,p in paths.items()}}
    with (ROOT/'ROLE-CROSSCHECK.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(out))
if __name__=='__main__':main()
