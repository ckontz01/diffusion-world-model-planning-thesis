"""Identity-only reconciliation then deterministic PROPOSAL, never allocation.

Only remote operation: authenticate the old registry and lexically project its
0..1599 identity metadata using the existing audited allowlist reader. There
are no reference-payload reads, scheduler calls, stage/launch commands or fits.
"""
import base
import ast, json, subprocess, time

def reconcile():
    paths = ['docs/local-goal-source-replication-20260920/DATA-ROLES.json',
             'docs/candidate-value-breadth-precision-20260915/DATA-ROLES.json',
             'docs/candidate-value-score-information-20260918/FOLDS.json',
             'docs/local-goal-proposals-20260918/DATA-ROLES.json',
             'docs/active-counterfactual-verification-20260923/DATA-ROLES-PROPOSED.json']
    rb,bp,si,lg,ac=[base.read(base.REPO/p) for p in paths]
    ex={k:set(v) for k,v in rb['exclusion_roles'].items()}
    old=set().union(*ex.values()); rbids=set(rb['ordered_references'])
    assert len(old)==320 and len(rbids)==512 and not old&rbids
    for k in ('original_train','extra_train','evaluation'): assert set(bp['allocation'][k])==ex['BP1-'+k]
    for k in ('train','validation','closed_loop','historical_32'): assert set(bp['allocation']['exclusions'][k])==ex['BP1-recorded-'+k]
    for k in ('train','validation','closed_loop'): assert set(bp['allocation']['exclusions'][k])==ex['CVL-'+k]
    assert set().union(*(set(v) for v in si['held_out']))==ex['SI1-fitting-heldout']
    assert set(lg['development_reference_indices'])==ex['LGP1/RB1-development']
    assert set(lg['technical_reference_indices'])==ex['LGP1-technical']
    roles=ac['proposed_roles']; acids=set(sum(roles.values(),[]))
    assert len(acids)==112 and not acids&(old|rbids)
    assert {k:len(v) for k,v in roles.items()}==dict(fit=64,validation=16,final_development=32)
    eligible=set(range(1600))-old-rbids-acids
    assert len(eligible)==656 and eligible==set(ac['unassigned_eligible'])
    return dict(metadata_pins={p:base.digest((base.REPO/p).read_bytes()) for p in paths},
                exclusion_roles={k:sorted(v) for k,v in ex.items()},prior_union=sorted(old),
                rb2=sorted(rbids),acv0=roles,eligible_before_selection=sorted(eligible)),ac

def query(ac):
    reader=base.REPO/'cluster/prometheus/candidate_value_freeze.py'
    src=reader.read_text(); node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='identity_projection')
    code="import json,hashlib\nfrom pathlib import Path\nfrom types import SimpleNamespace\ndef require(v,s):\n if not v: raise ValueError(s)\nct=SimpleNamespace(require=require)\n"
    code+=ast.get_source_segment(src,node)
    code+='\np=Path('+repr(ac['registry_path'])+')\nassert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(ac['registry_sha256'])
    code+='\nprint(json.dumps(identity_projection(p,list(range(1600)))))\n'
    cmd=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',
         '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','prometheus','python3','-']
    response=subprocess.run(cmd,input=code,text=True,capture_output=True,timeout=60)
    if response.returncode: raise RuntimeError(response.stderr[:1000])
    records=json.loads(response.stdout); assert set(map(int,records))==set(range(1600))
    keys=set()
    for i,r in records.items():
        assert r['index']==int(i) and r['file']==f'reference-{int(i):05d}.npz'
        r['source_key']=r['namespace']+':'+str(r['attempt'])
        assert r['source_key'] not in keys; keys.add(r['source_key'])
        if i in ac['records']: assert r==ac['records'][i]
    return records,base.digest(reader.read_bytes())

def main():
    if (base.HERE/'ELIGIBILITY.json').exists(): raise FileExistsError('Proposal already prepared')
    started=time.monotonic(); audit,ac=reconcile()
    # Reconcile complete identities BEFORE selecting any new proposal references.
    records,reader=query(ac)
    eligible=audit['eligible_before_selection']
    ordered=sorted(eligible,key=lambda i:(base.digest(f'acv-mechanism-replication-v1|{i}'.encode()),i))
    selected=ordered[:512]
    assert len(selected)==512 and len({records[str(i)]['source_key'] for i in selected})==512
    audit.update(status='PROPOSAL_ONLY_NOT_RESERVED_NO_PAYLOAD_ACCESS_OR_EXECUTION_AUTHORIZED',
                 registry_path=ac['registry_path'],registry_sha256=ac['registry_sha256'],identity_reader_sha256=reader,
                 reconciliation_unix=time.time(),excluded_union_count=944,eligible_count=656,
                 selected_count=512,unselected_count=144,
                 selection_rule='SHA256(acv-mechanism-replication-v1|<decimal index>), integer tie; first512',
                 selected_references=selected,remaining_unassigned=ordered[512:],
                 records={str(i):records[str(i)] for i in selected},
                 global_0_1599_identity_projection_sha256=base.digest(json.dumps(records,sort_keys=True,separators=(',',':')).encode()),
                 identity_only_records_checked=1600,canonical_keys_unique=1600,
                 protected_1600_5999='not projected or opened',payload_reads=0,outcome_fields_decoded=0,
                 av0_av1='unlaunched proposals are not exposure/reservation; no AV1 allocated',
                 seconds=time.monotonic()-started)
    base.write(base.HERE/'ELIGIBILITY.json',audit)
    print(json.dumps({k:audit[k] for k in ('excluded_union_count','eligible_count','selected_count','unselected_count','payload_reads','seconds')}))

if __name__=='__main__': main()
