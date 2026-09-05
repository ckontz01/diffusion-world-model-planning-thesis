"""Count-only feasibility audit. No prospective states, pixels, actions or models.

Only the global, non-secret partition registry is used to select P2. Entire P3
and P4 partitions are excluded; protected study membership files are never read.
No selected-episode list, start, or confirmation manifest is emitted.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import h5py
import numpy as np

ROOT = Path('/lustreFS/data/superworld/ckontzias/thesis')
E18 = ROOT/'experiments/gdp-cem-e18/development-run-20260827-182ed1e7'
E19 = ROOT/'experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988'
SAGE = ROOT/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def seal_check(directory):
    # Only called for the explicit historical E18 / identifier-only E19 audits.
    for line in (directory/'sha256.txt').read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        path = directory/name.lstrip('*')
        assert path.resolve().parent == directory.resolve()
        assert sha(path) == expected, path


def json_read(p):
    return json.loads(p.read_text())


def id_hash(ids):
    return hashlib.sha256(''.join(f'{x}\n' for x in sorted(ids)).encode()).hexdigest()


def read_ids(p, key=None):
    # HDF5 has strict key allowlisting; never hash its other payloads.
    with h5py.File(p, 'r') as f:
        if key is None:
            key = next(k for k in ('episode_idx', 'episode_id', 'source_episode_id') if k in f)
        assert key in ('episode_idx', 'episode_id', 'source_episode_id')
        return set(map(int, np.unique(f[key][:])))


def tsv_ids(p):
    assert p.name in ('queries.tsv', 'd1-fresh-development.tsv', 'r0-official-seed42.tsv')
    with p.open() as f:
        return {int(x['episode_id']) for x in csv.DictReader(f, delimiter='\t')}


def audit():
    registry = ROOT/'manifests/partitions/pusht-v1/episodes-seed-20260728.tsv'
    assert sha(registry) == '35cd851464f4d7243c3c07b794f65db0f32caa16bbc787a83dda68388c4898f0'
    counts = Counter(); long_counts = Counter(); p2 = {}; all_lengths = []
    with registry.open() as f:
        for row in csv.DictReader(f, delimiter='\t'):
            counts[row['partition']] += 1
            if int(row['episode_length']) >= 151: long_counts[row['partition']] += 1
            all_lengths.append(int(row['episode_length']))
            if row['partition'] == 'P2':
                p2[int(row['episode_id'])] = int(row['episode_length'])
    dataset = ROOT/'data/stablewm/pusht_expert_train.h5'
    with h5py.File(dataset, 'r') as f:
        lengths = np.asarray(f['ep_len'][:], dtype=np.int64)
        fields = {k:dict(shape=list(f[k].shape), dtype=str(f[k].dtype)) for k in f}
    assert sorted(all_lengths) == sorted(lengths.tolist())
    assert all(lengths[e] == n for e,n in p2.items())
    eligible = {e for e,n in p2.items() if n >= 151}
    initial = set(eligible)
    exclusions = []
    sources = []
    def exclude(name, ids, source):
        nonlocal eligible
        overlap = eligible & ids
        exclusions.append(dict(name=name, source_episode_count=len(ids),
            intersect_p2_long_count=len(initial & ids), incremental_excluded=len(overlap)))
        eligible -= ids
        sources.append(dict(name=name, path=str(source), identifier_set_sha256=id_hash(ids)))
    # The frozen earlier exposure inventory points to identifier arrays in P2
    # execution stores. Nothing under P3/P4/confirmation is opened or hashed.
    old = ROOT/'manifests/acid-alternative-v1/pusht'
    old_summary = json_read(old/'summary.json')
    prior = set(); prior_paths=[]
    for s in old_summary['legacy_sources']:
        path = s.get('path', '')
        if ('/pusht-v1/p2-' in path or '/repro/p2-' in path) and path.endswith('.h5'):
            p=Path(path); ids=read_ids(p); prior |= ids
            prior_paths.append(dict(path=path, id_count=len(ids), id_sha256=id_hash(ids)))
    assert len(prior_paths)==128, 'earlier P2 exposure inventory changed'
    # Include pool identifiers too, including pools without executed candidates.
    pool_root=ROOT/'data/stablewm/derived/candidate-pools/pusht-v1'
    for name in ('p2-real-frame-job-295087','p2-real-frame-job-295089',
                 'p2-real-frame-job-294647','p2-stratum3-b0-d75-h2-job-294604'):
        m=json_read(pool_root/name/'manifest.json')
        assert m['partition']=='P2'
        p=Path(m['output_h5']); ids=read_ids(p); prior |= ids
        prior_paths.append(dict(path=str(p),id_count=len(ids),id_sha256=id_hash(ids)))
    exclude('earlier_P2_pool_and_execution_exposure', prior, old/'summary.json')
    for name in ('d1-fresh-development.tsv','r0-official-seed42.tsv'):
        exclude(name, tsv_ids(old/name), old/name)
    e14=ROOT/'experiments/gdp-cem-e14/development-run-20260823-99f92cbe'
    for name,p in [('E14_E15_P2', e14/'p2-manifests/33ae351f/pusht/queries.tsv'),
                   ('E18_P2', E18/'p2-manifests/pusht/queries.tsv')]:
        exclude(name,tsv_ids(p),p)
    caches = {
        'E14_training_validation': ROOT/'data/stablewm/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/e14-variable-cache-job-298993-0/cache.h5',
        'E15_training_validation':ROOT/'experiments/gdp-cem-e15/data-preflight-1b97e228/pusht/cache.h5',
        'E17_training_validation':ROOT/'experiments/gdp-cem-e17/development-run-20260827-9fb5a8c2/cache/pusht/cache.h5',
        'E16_development':ROOT/'experiments/gdp-cem-e16/development-run-20260827-3669dc32/stage-a-banks/pusht/vad/seed-7201/metrics.h5',
    }
    component_ids=set()
    for name,p in caches.items():
        ids=read_ids(p);exclude(name,ids,p)
        if name!='E16_development': component_ids |= ids
    # Original full paper grid and all later sentinels/R1--R3 reuse its records.
    paper=set()
    for seed in (32,42,52):
        for h in (25,50,75,100,125,150):
            p=SAGE/f'data/manifests/pusht/seed{seed}/h{h}.json'
            paper |= {int(x['episode_id']) for x in json_read(p)['records']}
    exclude('SAGE_paper_and_reused_sentinel_exposure',paper,SAGE/'data/manifests/pusht')
    exclude('explicit_R1_R3_driver_counterexamples',{8908,201,627},'accepted R3/integration exposed IDs')
    split=json_read(SAGE/'data/splits/pusht_episode_split_seed42.json')
    roles={k:set(map(int,split.get(k+'_episode_idx',split.get(k,[])))) for k in ('train','val','test')}
    assert len(set.union(*roles.values())) == len(lengths)
    assert not (roles['train'] & roles['val'] or roles['train'] & roles['test'] or roles['val'] & roles['test'])
    seal_check(E19/'data-overlap-audit')
    audit19=json_read(E19/'data-overlap-audit/DATA-OVERLAP-AUDIT.json')
    common = eligible & roles['test']
    return dict(kind='preparatory_count_only_not_a_confirmation_manifest',
        partition_registry_sha256=sha(registry), partition_counts=dict(counts),
        partition_h150_metadata_count_upper_bounds=dict(long_counts),
        metadata_fields=fields, p2_h150_compatible_count=len(initial),
        p2_too_short_count=len(p2)-len(initial), ordered_exclusions=exclusions,
        metadata_eligible_maximum=len(eligible),
        sage_training_role_in_eligible={k:len(eligible & v) for k,v in roles.items()},
        common_sage_test_reserve_maximum=len(common),
        maximum_after_reserving_all_common_sage_test=len(eligible-common),
        previous_579_is_not_current_eligibility=audit19['overlap']['pusht']['common_untouched_candidates']['count'],
        known_e18_component_training_overlap_in_remaining=len(eligible & component_ids),
        lewm_exact_episode_training_exposure='unknown; model card identifies the training dataset, not exact realized episode membership',
        lewm_training_unknown_count=len(eligible),
        strict_all_models_training_unseen_certified_count=0,
        status='metadata_capacity_subject_to_exposure_ledger_completeness_and_future_value_validation',
        limitations=['No prospective numeric values loaded: finite state/value checks deferred.',
            'P2 pool inventory predates D1; subsequent listed evaluations reuse D1/E14/E18/paper/sentinel sets.',
            'No custodian certificate obtained for any additional protected allocation; P3/P4 contribute zero here.',
            'Any unregistered model-input exposure would reduce this capacity.'],
        prior_p2_identifier_sources=prior_paths, exclusion_sources=sources,
        flags=dict(prospective_model_run=False,prospective_state_pixel_action_read=False,
            protected_outcome_read=False,protected_membership_manifest_read=False,
            d5_read_or_hashed=False,confirmation_manifest_created=False))


def historical():
    directory=E18/'analysis'; seal_check(directory)
    audit=json_read(directory/'E18-AUDIT.json')
    assert audit['source_manifest_sha256']=='182ed1e7d1e9994638ab1fbc773c79cac8d68858b716e67ff8969e5b2e74e29c'
    assert audit['cell_count']==240 and audit['episode_row_count']==720
    with (directory/'ALL-EPISODES.tsv').open() as f:
        rows=[r for r in csv.DictReader(f,delimiter='\t') if r['task']=='pusht']
    assert len(rows)==360
    return dict(kind='already_exposed_E18_PushT_planning_inputs',
        source_sha256=sha(directory/'ALL-EPISODES.tsv'), audit_sha256=sha(directory/'E18-AUDIT.json'),
        historical_decision=audit['decision'], rows=rows,
        historical_timing=audit['timing_and_adapter_domain']['task_horizon']['pusht'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    for name, result in [('availability.json',audit()),('historical.json',historical())]:
        (a.out/name).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (a.out/'sha256.txt').write_text(''.join(f'{sha(x)}  {x.name}\n' for x in sorted(a.out.glob('*.json'))))
