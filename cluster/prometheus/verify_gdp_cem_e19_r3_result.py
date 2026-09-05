"""Independent seal/cardinality/equivalence verifier; no simulator imports."""
import hashlib
import json
from pathlib import Path

ARMS={'sage':('base_cem','far_goal_prior_cem','lewm_generator','generator_prior_top','sage'),
      'e18':('vad_greedy_300','vad_greedy_576','vad_continuation','diagonal_gaussian_continuation','direct_gmm_continuation')}
NATIVE={'sage':'950265cb0bad2c1f14a2c959de35695a047f58a502f45d67b53749bf48364f6a',
        'e18':'d8d0de35aaab5b846db4e79b0fbfd6b17375178cce40a25df5301c8030ca6d68'}

def read(path):
    lines=(path.parent/'sha256.txt').read_text().splitlines()
    seals={line.split(maxsplit=1)[1].lstrip('*'):line.split(maxsplit=1)[0] for line in lines}
    assert seals[path.name]==hashlib.sha256(path.read_bytes()).hexdigest(),path
    return json.loads(path.read_text())

def validate_core(d):
    assert d['native_source_sha256']==NATIVE[d['stack']]
    assert d['all_passed'] is True and d['scenarios']==24 and d['fresh_resets']==48
    assert d['primitive_actions']==72 and d['fresh_initialization_physics_steps']==0
    for flag in ('planning','performance_metric_recorded','protected_read','holdout_read',
                 'historical_results_modified','complete_historical_state_recovery'):
        assert d[flag] is False
    rows=d['rows']
    assert {(r['case_id'],r['history'],r['repeat']) for r in rows}=={
        (c,h,r) for c in range(3) for h in ('seed32','seed33','r1r0','r1r1') for r in (0,1)}
    assert len(rows)==24
    for c in range(3):
        group=[r for r in rows if r['case_id']==c]
        assert all(r['hidden_steps']==0 and r['initialization_passed'] and r['metadata_value_invariant'] for r in group)
        for k in ('initial','pixels','goal','trajectory','config'):
            assert len({json.dumps(r[k],sort_keys=True) for r in group})==1,(c,k)

def validate_arm(d):
    stack=d['stack'];n=50 if stack=='sage' else 3
    assert d['native_source_sha256']==NATIVE[stack]
    assert d['arm'] in ARMS[stack] and d['all_passed'] is True
    assert d['worlds']==2 and d['initializations']==3+2*n
    assert d['primitive_actions']==3*(3+n) and d['physics_steps']==30*(3+n)
    assert d['hidden_initialization_steps']==0 and d['solver_invocations']==0
    for flag in ('checkpoint_parameters_modified','performance_metric_recorded','protected_read',
                 'holdout_read','historical_result_modified','diffusion_changed'):
        assert d[flag] is False
    assert d['raw_input_equivalence_checked'] and d['image_action_preprocessing_checked']
    if stack=='e18':assert d['e18_non_action_scaler_values_checked'] is False
    assert len(d['rows'])==3+2*n
    expected={(1,c,0,c) for c in range(3)} | {(n,p,i,(i+p)%3) for p in (0,1) for i in range(n)}
    assert {(r['n'],r['phase'],r['slot'],r['case_id']) for r in d['rows']}==expected
    ref={r['case_id']:r for r in d['rows'] if r['n']==1}
    for r in d['rows']:
        for k in ('initialized','raw','prepared'):
            assert r[k]==ref[r['case_id']][k],(d['arm'],r['slot'],k)
        if r['n']==1 or r['phase']==0:
            assert len(r['fixed_trajectory'])==3
            assert r['fixed_trajectory']==ref[r['case_id']]['fixed_trajectory']
        else: assert 'fixed_trajectory' not in r
    assert all(v>0 for v in d['provenance']['parameter_counts'])
    return ref

def verify(root):
    expected_sources={
        'CORE-SOURCE-MANIFEST.sha256':'30215e7fcfd0e614f2233277f3c9854abc87172a8d688ec5c3e193b0757f8ee3',
        'ARMS-SOURCE-MANIFEST.sha256':'88a476ab878979f90e6dd80de7365feac8ab39008f32fbe4047eff668f92cdd5',
        'FAILED-ARMS-SOURCE-MANIFEST.sha256':'bde5784c50fef64c60fc37f48187254bfcfb415e2b980fe77176d162eb247d46'}
    for name,expected in expected_sources.items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
    for name in ('CORE-SOURCE-MANIFEST.sha256','ARMS-SOURCE-MANIFEST.sha256'):
        for line in (root/name).read_text().splitlines():
            h,filename=line.split(maxsplit=1)
            assert hashlib.sha256((root.parent/filename).read_bytes()).hexdigest()==h,filename
    counts={'core_scenarios':0,'core_fresh_resets':0,'core_actions':0,
            'arm_initializations':0,'arm_actions':0,'arms':0}
    for stack in ARMS:
        core=read(root/'core'/stack/'validation/VALIDATION.json');validate_core(core)
        inventory=read(root/'core'/stack/'inventory/INVENTORY.json')
        assert inventory['stack']==stack and inventory['only_exposed'] is True
        assert [c['case_id'] for c in inventory['cases']]==[0,1,2]
        assert [(c['identity']['episode'],c['identity']['start']) for c in inventory['cases']]==[(8908,53),(201,6),(627,21)]
        counts['core_scenarios']+=core['scenarios'];counts['core_fresh_resets']+=core['fresh_resets']
        counts['core_actions']+=core['primitive_actions'];common=None
        for arm in ARMS[stack]:
            d=read(root/'arms'/stack/arm/'ARM-CHECK.json')
            assert d['stack']==stack and d['arm']==arm
            ref=validate_arm(d)
            simplified={c:{k:r[k] for k in ('initialized','raw','prepared','fixed_trajectory')} for c,r in ref.items()}
            if common is None:common=simplified
            else:assert common==simplified,(stack,arm,'between-arm equivalence')
            for c,r in ref.items():
                base=next(v for v in core['rows'] if v['case_id']==c)
                assert r['initialized']==base['initial']
                assert r['fixed_trajectory']==[v['physical'] for v in base['trajectory']]
            counts['arm_initializations']+=d['initializations'];counts['arm_actions']+=d['primitive_actions'];counts['arms']+=1
    assert counts=={'core_scenarios':48,'core_fresh_resets':96,'core_actions':144,
                   'arm_initializations':560,'arm_actions':885,'arms':10}
    return counts

if __name__=='__main__':
    print(json.dumps(verify(Path(__file__).parent/'e19-r3-evidence'),indent=2))
