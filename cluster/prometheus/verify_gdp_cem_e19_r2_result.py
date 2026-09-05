"""Independently check sealed local R2 evidence without a simulator."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
E=ROOT/'e19-r2-evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sealed(name,expected):
    p=E/name;assert sha(p)==expected
    assert (p.parent/'sha256.txt').read_text().strip()==expected+'  '+p.name
    return json.loads(p.read_text())
def main():
    for name,expected in [('MAIN-SOURCE-MANIFEST.sha256','a4320292c95507a900bae1dfd43ec45f188300e0efbe3d9707f8ceb17ec84e02'),
                          ('CONTACT-SOURCE-MANIFEST.sha256','ba78531c4263363877b2e2ccbbabfb5b53e33316133ffb6e67e3032780b8adfb')]:
        p=E/name;assert sha(p)==expected
        for line in p.read_text().splitlines():
            h,n=line.split(maxsplit=1);assert sha(ROOT/n)==h
    x=sealed('main/R2-REVIEW.json','cc63d198453558adb31a8b73ccc628c263aa17a4f87437ded409ece744f88a32')
    a=sealed('source-audit/SOURCE-AUDIT.json','70a206aa735b77bb4e66a4b255e3287236f09268e2b499b3086e34f45ce16aa6')
    c=sealed('contact/CONTACT-SUMMARY.json','6c437ecff00e713bb647161681de3a5662a1aa203ce1c2e3e33a2e444fade8ad')
    assert x['processes']==24 and x['post_restoration_actions']==24 and len(x['inventory'])==48
    assert len(x['singles'])==24 and len(x['pairs'])==12
    for s in x['singles']:
        assert all(v['exact'] for v in s['before'].values())
        assert s['received_seed'] is None
        if s['mode']!='native':assert s['actual_env_seed']==s['effective_seed']==int(s['mode'][4:])
        if s['mode']=='seed32':assert s['after']['block.position']['max_abs']>0.18
        if s['mode']=='seed33':assert s['after']['block.position']['exact']
    assert all(p['actions_exact'] for p in x['pairs'])
    assert a['observations_checked']==180 and a['observations_outside_native_bounds']==56
    assert a['all_match_signed_velocity_bounds'] and not a['simulator_executed']
    assert c['initializations']==8 and c['physics_steps']==32 and c['primitive_actions']==0 and len(c['inventory'])==8
    assert all(not p['restored_body_differences'] for p in c['pairs'])
    for row in c['rows']:
        assert all(d['exact'] for d in row['before_assignment_checks'].values())
        if row['geometry_repeat']==1:assert row['restored_vs_r1_bodies'] # Do not hide imperfect reconstruction.
    for data in (x,c):assert not data['production_correction'] and not data['protected_read']
    assert not x['confirmation_authorized']
    print('Verified R2: 32 initializations, 24 actions; requested assignments exact, reset-seed dependence remains; no correction/confirmation authorized.')
if __name__=='__main__':main()
