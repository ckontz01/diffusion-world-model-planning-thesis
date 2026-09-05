"""Independent CPU gate for complete exposed-record integration evidence."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ARMS=('vad_greedy_300','vad_greedy_576','vad_continuation',
      'diagonal_gaussian_continuation','direct_gmm_continuation')
INIT='798bb6749dd30b9c6a91ac7018422edbefd356f3bb6bc322bd8ca95987506a65'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check(payload,arm):
    assert payload['arm']==arm and payload['all_passed'] is True
    for key in ('checkpoints_modified','initializer_modified','historical_results_modified',
                'protected_read','holdout_read','performance_metric_recorded','efficacy_claim','probe_fitted_scalers'):
        assert payload[key] is False,key
    assert payload['initializer_sha256']==INIT
    assert payload['fresh_initialization_physics_steps']==0
    assert payload['native_vector_batch_size']==1 and payload['interleaved_slots']==[1,3]
    assert [(c['episode'],c['start']) for c in payload['inputs']]==[(8908,53),(201,6),(627,21)]
    dep=payload['dependency_gate'];coef=payload['coefficient_gate']
    assert dep['non_action_evaluator_scalers_computationally_required'] is False
    assert dep['encoder_mapping_reads']==['pixels']
    assert dep['full_minimal_latents_bit_identical'] is True
    assert dep['raw_state_checkpoint_normalization_exact'] is True
    assert dep['world_model_episode_cache_attributes']==[]
    assert coef['fit_called'] is False and coef['planner_action_coefficients_equal_float32'] is True
    stats=coef['checkpoint_statistics']
    for field,source in [('action_mean','planner_action_mean'),('action_scale','planner_action_std')]:
        np.testing.assert_array_equal(np.asarray(coef[field],np.float32),np.asarray(stats[source],np.float32))
    campaigns=payload['campaigns']
    assert [(c['slots'],c['cases'],c['horizon']) for c in campaigns]==[
        ([0],[0],75),([0,1,2],[0,1,2],75),([0,1,2],[0,1,2],75),([0,1,2],[1,2,0],150)]
    assert campaigns[0]['rows'][0]==campaigns[1]['rows'][0]
    assert campaigns[1]['rows']==campaigns[2]['rows']
    total=calls=0
    for campaign in campaigns:
        assert len(campaign['rows'])==len(campaign['cases'])
        assert any(len(row['plans'])>=2 for row in campaign['rows'])
        for row in campaign['rows']:
            n=row['delivered'];assert 1<=n<=31
            assert row['budget_exhausted']==(n==31)
            assert len(row['actions'])==len(row['post_states'])==n
            assert [p['at'] for p in row['plans']]==list(range(0,n,15))
            assert [p['delta'] for p in row['plans']]==list(range(campaign['horizon'],campaign['horizon']-15*len(row['plans']),-15))
            assert all(p['tau']==15 for p in row['plans'])
            for digest in [row['initial'],row['inputs'],*row['fresh_rng'],*row['actions'],*row['post_states']]:
                assert len(digest)==64 and all(c in '0123456789abcdef' for c in digest)
            calls+=len(row['plans']);total+=n
    assert calls==payload['actual_planner_calls'] and total==payload['primitive_actions']
    expected=calls*(2 if 'continuation' in arm else 1)
    assert payload['proposal_decode_checks']==expected
    return dict(arm=arm,episodes=10,planner_calls=calls,primitive_actions=total)


def verify(root):
    manifest=root/'SOURCE-MANIFEST.sha256'
    assert sha(manifest)=='a9d1c26573158f93e3e17dba932129084795a05f2ac84eb7eaadb8bca881d540'
    for line in manifest.read_text().splitlines():
        digest,name=line.split(maxsplit=1)
        assert Path(name).name==name and sha(root.parent/name)==digest
    # Validate every complete output seal before opening any payload.
    paths=[root/arm/'INTEGRATION.json' for arm in ARMS]
    for path in paths:
        records=[line.split(maxsplit=1) for line in path.with_name('sha256.txt').read_text().splitlines() if line]
        assert len(records)==1 and Path(records[0][1].lstrip('*')).name=='INTEGRATION.json'
        assert sha(path)==records[0][0]
    pins_path=root/'pins/PINNED-INPUTS.json'
    assert sha(pins_path)=='cf48fd85336fbf4d65f12ef290cd3b08f3969da2c8a29842ece4c55e848f52df'
    pin_seal=(root/'pins/sha256.txt').read_text().split()
    assert pin_seal==[sha(pins_path),'PINNED-INPUTS.json']
    rows=[check(json.loads(path.read_text()),arm) for path,arm in zip(paths,ARMS)]
    payloads=[json.loads(path.read_text()) for path in paths]
    pins=json.loads(pins_path.read_text())
    assert pins['normalization_identical_all_nine_checkpoints'] is True
    assert len(pins['checkpoints'])==9
    assert {(r['family'],r['training_seed']) for r in pins['checkpoints']}=={
        (family,seed) for family in ('vad','diagonal_gaussian','direct_gmm') for seed in (7201,7202,7203)}
    assert all(pins[k] is False for k in ('dataset_read','holdout_read','protected_read','fit_performed'))
    for payload in payloads:
        assert payload['coefficient_gate']['checkpoint_statistics']==pins['statistics']
        assert payload['coefficient_gate']['action_mean']==pins['action_decoder']['mean']
        assert payload['coefficient_gate']['action_scale']==pins['action_decoder']['scale']
    # Each arm sees the same start/goal pixels and requested body state.
    for ci in range(4):
        first=payloads[0]['campaigns'][ci]['rows']
        for other in payloads[1:]:
            for a,b in zip(first,other['campaigns'][ci]['rows']):
                assert a['initial']==b['initial'] and a['inputs']==b['inputs'] and a['seed']==b['seed']
    assert sum(r['episodes'] for r in rows)==50
    return dict(decision='fresh_e18_driver_integration_passed_on_exposed_pusht_records',
                rows=rows,efficacy_claim=False,holdout_authorized=False)


if __name__=='__main__':
    print(json.dumps(verify(Path(sys.argv[1])),indent=2))
