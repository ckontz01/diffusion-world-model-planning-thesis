"""Only named local metadata and user-provided guidance. No payload reads."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]


def read(relative):return json.loads((REPO/relative).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    meta='docs/local-goal-source-replication-20260920/DATA-ROLES.json'
    d=read(meta)
    roles={k:set(v) for k,v in d['exclusion_roles'].items()}
    old=set().union(*roles.values())
    assert len(old)==320
    rb2=set(d['ordered_references'])
    assert len(rb2)==512 and not old & rb2
    available=set(range(1600))-old-rb2
    assert len(available)==768
    ordered=sorted(available,key=lambda i:(hashlib.sha256(f'av0-source-role-v1|{i}'.encode()).hexdigest(),i))
    cuts={'fit':ordered[:192],'policy_development':ordered[192:288],
          'calibration':ordered[288:608],'final_development_evaluation':ordered[608:]}
    assert sum(map(len,cuts.values()))==768
    out=dict(status='PROPOSED ONLY; no reference payload read; not untouched confirmation',
             population='final-20260906-primary-v1:0-1599; historically exposed development universe',
             metadata=meta,metadata_sha256=sha(REPO/meta),
             inherited_exclusions={k:sorted(v) for k,v in roles.items()},
             inherited_union_count=len(old),rb2_exposed=sorted(rb2),
             excluded_union=sorted(old|rb2),available_count=len(available),
             allocation_rule='SHA256(av0-source-role-v1|<decimal reference>), integer tie, consecutive 192/96/320/160',
             proposed_roles=cuts,counts={k:len(v) for k,v in cuts.items()},
             protected_1600_5999='never allocated or opened',
             research_payload_reads=0)
    # Verify user manifest without executing the supplied script or changing it.
    support=Path('C:/Users/Chris/AppData/Local/Temp')
    checks=[]
    for line in (support/'MANIFEST.sha256').read_text().splitlines():
        if not line.strip():continue
        expected,name=line.split(maxsplit=1);name=name.lstrip('*')
        if name not in {'PRIMARY-SOURCES.md','README.md','analytic_check_results.json','analytic_checks.py','primary_source_ledger.json'}:
            raise ValueError('Unexpected guidance manifest path')
        actual=sha(support/name)
        checks.append(dict(name=name,expected=expected,actual=actual,match=actual==expected))
    out['guidance_manifest_verification']=checks
    assert all(c['match'] for c in checks)
    with (ROOT/'DATA-ROLES-PROPOSED.json').open('x',encoding='utf8') as f:
        json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(excluded=832,available=768,roles=out['counts'],guidance_files_verified=len(checks))))


if __name__=='__main__':main()
