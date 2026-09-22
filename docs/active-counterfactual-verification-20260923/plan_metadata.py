"""Identity-only proposal. Does not read reference payloads or assign new roles.

Configured SSH is used solely for the authenticated collection registry identity
projection; no researcher outcome fields are decoded, printed or retained.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((REPO/p).read_text())
def save(name,x):
    with (ROOT/name).open('x') as f:json.dump(x,f,indent=2);f.write('\n')


def main():
    rbpath='docs/local-goal-source-replication-20260920/DATA-ROLES.json';rb=read(rbpath)
    ex={k:set(v) for k,v in rb['exclusion_roles'].items()};old=set().union(*ex.values());rbids=set(rb['ordered_references'])
    assert len(old)==320 and len(rbids)==512 and not old&rbids
    bp=read('docs/candidate-value-breadth-precision-20260915/DATA-ROLES.json')['allocation']
    for k in ('original_train','extra_train','evaluation'):assert set(bp[k])==ex['BP1-'+k]
    for k in ('train','validation','closed_loop','historical_32'):assert set(bp['exclusions'][k])==ex['BP1-recorded-'+k]
    for k in ('train','validation','closed_loop'):assert set(bp['exclusions'][k])==ex['CVL-'+k]
    si=read('docs/candidate-value-score-information-20260918/FOLDS.json')
    assert set().union(*(set(v) for v in si['held_out']))==ex['SI1-fitting-heldout']
    lg=read('docs/local-goal-proposals-20260918/DATA-ROLES.json')
    assert set(lg['development_reference_indices'])==ex['LGP1/RB1-development']
    assert set(lg['technical_reference_indices'])==ex['LGP1-technical']
    available=set(range(1600))-old-rbids;assert len(available)==768
    ordered=sorted(available,key=lambda i:(hashlib.sha256(f'acv0-development-pilot-v1|{i}'.encode()).hexdigest(),i))
    roles=dict(fit=ordered[:64],validation=ordered[64:80],final_development=ordered[80:112])
    ids=sum(roles.values(),[])
    # Reuse only the previously audited lexical identity reader, not freeze().
    reader=REPO/'cluster/prometheus/candidate_value_freeze.py';src=reader.read_text()
    fn=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='identity_projection')
    function=ast.get_source_segment(src,fn)
    registry='/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5/collection/COLLECTION.json'
    digest=rb['identity_certificate']['registry_sha256']
    remote="import json, hashlib\nfrom pathlib import Path\nfrom types import SimpleNamespace\ndef require(v,s):\n if not v: raise ValueError(s)\nct=SimpleNamespace(require=require)\n"+function
    remote+='\np=Path('+repr(registry)+')\nassert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(digest)
    remote+='\nprint(json.dumps(dict(registry_sha256='+repr(digest)+',records=identity_projection(p,'+repr(ids)+'),payload_reads=0,outcome_fields_decoded=0)))\n'
    start=time.monotonic()
    command=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',
             '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','prometheus','python3','-']
    result=subprocess.run(command,input=remote,capture_output=True,text=True,timeout=60)
    if result.returncode:raise RuntimeError('Identity-only SSH failed: '+result.stderr[:1000])
    projection=json.loads(result.stdout);assert set(map(int,projection['records']))==set(ids)
    keys=set()
    for sid,r in projection['records'].items():
        assert r['index']==int(sid) and r['file']=='reference-%05d.npz'%int(sid)
        key=r['namespace']+':'+str(r['attempt']);assert key not in keys;keys.add(key);r['source_key']=key
    proposal=dict(status='PROPOSAL_ONLY_NOT_RESERVED_NOT_AUTHORIZED_TO_READ',population='reference indices 0-1599; historically exposed development universe',
                  canonical_metadata=dict(path=rbpath,sha256=sha(REPO/rbpath)),crosschecks=13,
                  exclusion_roles={k:sorted(v) for k,v in ex.items()},rb2_exposed=sorted(rbids),
                  excluded_union=sorted(old|rbids),eligible_count=768,proposed_roles=roles,counts={k:len(v) for k,v in roles.items()},
                  unassigned_eligible_count=656,unassigned_eligible=ordered[112:],
                  selection_rule='SHA256(acv0-development-pilot-v1|<decimal reference index>), integer tie; first 64/16/32',
                  protected_1600_5999='not allocated, not opened',av0_av1='proposal-only allocation is not exposure or reservation',
                  technical_tranche_included_fit=roles['fit'][:2],max_collection_branches_per_source=16,
                  max_collection_episodes=1280,max_evaluation_episodes=256,
                  identity_reader_sha256=sha(reader),registry_path=registry,registry_sha256=digest,
                  metadata_query_seconds=time.monotonic()-start,records=projection['records'],payload_reads=0,outcome_fields_decoded=0)
    save('DATA-ROLES-PROPOSED.json',proposal)
    inp=read('docs/local-goal-source-replication-20260920/INPUTS.json')
    # Metadata pins only: unrelated historical proposer/checkpoint entries omitted.
    files={k:v for k,v in inp['files'].items() if '/envs/hi-lewm-artifact-py311-cu121-swm006/' in k}
    paths=['acid_alternative/evaluate_matched.py','acid_alternative/costs.py','pusht_fresh_initialization.py',
           'e18_fresh_driver.py','lgp1_endpoint.py','candidate_value_data.py','lgprb2_evaluate.py']
    pins=dict(status='READ_ONLY_METADATA_PINS_NOT_LOADED',lewm=inp['lewm'],decoder=inp['decoder'],container=inp['container'],
              runtime=inp['runtime'],runtime_files=files,metadata_input_sha256=sha(REPO/'docs/local-goal-source-replication-20260920/INPUTS.json'),
              inspected_local_sources={p:sha(REPO/'cluster/prometheus'/p) for p in paths})
    save('RUNTIME-PINS.json',pins)
    print(json.dumps(dict(proposed_counts=proposal['counts'],remaining_unassigned=656,exact_source_keys=len(keys),
                         registry_sha256=digest,reference_payload_reads=0,runtime_metadata_pins=len(files))))


if __name__=='__main__':main()
