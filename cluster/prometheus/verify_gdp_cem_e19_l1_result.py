#!/usr/bin/env python3
"""Validate the small L1 evidence package without models or raw episode arrays."""

import argparse
import hashlib
import json
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed(directory, expected):
    entries = {}
    for line in (directory / 'sha256.txt').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        assert name in expected and name not in entries
        assert sha(directory / name) == digest
        entries[name] = digest
    assert set(entries) == expected
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=Path(__file__).parent / 'e19-l1-evidence')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    records = sealed(args.evidence, {'LOCALIZATION.json', 'FIXED-BANK-REPLAY.json'})
    records.update(sealed(args.evidence / 'supplement', {'STAGE-AND-SENSITIVITY-SUMMARY.json'}))
    local = json.loads((args.evidence / 'LOCALIZATION.json').read_text())
    replay = json.loads((args.evidence / 'FIXED-BANK-REPLAY.json').read_text())
    summary = json.loads((args.evidence / 'supplement/STAGE-AND-SENSITIVITY-SUMMARY.json').read_text())
    assert summary['reducer_source_sha256'] == sha(Path(__file__).with_name('summarize_gdp_cem_e19_l1.py'))
    assert {r['sentinel_id'] for r in local['sentinels']} == set(range(5))
    assert len(local['inventories']) == 10
    assert sum(len(v) for v in local['inventories'].values()) == 40
    for row in local['sentinels']:
        assert row['trace']['order_exact'] and row['trace']['missing_event_count'] == 0
        assert row['trace']['opaque_repr_path_count'] == 0
        assert not row['bank']['opaque_paths_left'] and not row['bank']['opaque_paths_right']
        assert row['repeat_outcomes']['episode_count'] == 50
        assert all(v['exact'] for v in row['bank']['all_field_comparisons'] if not v['path'].startswith('info.'))
    assert replay['torch'] == '2.5.1+cu121'
    assert replay['gpu'] == 'NVIDIA RTX 6000 Ada Generation'
    assert replay['checkpoint_states_unchanged'] == {'cube': True, 'pusht': True}
    expected = {(sid, repeat) for sid in (0, 1, 3, 4) for repeat in (0, 1)}
    assert {(r['sentinel_id'], r['repeat']) for r in replay['fit_replays']} == expected
    for row in replay['fit_replays']:
        for field in ('recorded_elites_reconstruct_replay_mean', 'recorded_elites_reconstruct_replay_std',
                      'recorded_elites_reconstruct_historical_mean', 'recorded_elites_reconstruct_historical_std',
                      'replay_matches_historical_mean', 'replay_matches_historical_std',
                      'replay_matches_historical_elite_costs', 'global_cuda_rng_unchanged'):
            assert row[field] is True
        assert row['exact_original_topk_calls_captured'] == 1
        assert len(row['boundary']) == len(row['recorded_vs_actual_elites']) == 50
        assert all(v['order_exact'] and v['intersection'] == 30 for v in row['recorded_vs_actual_elites'])
        assert all(not v['exact_boundary_tie'] and not v['near_boundary_1e_6_relative'] for v in row['boundary'])
    for row in replay['fixed_cost_replays']:
        if row['sentinel_id'] == 2:
            assert row['status'] == 'not_applicable_prior_top_has_no_historical_cost_tensor'
        else:
            for field in ('two_replays', 'replay_vs_historical'):
                assert row[field]['exact'] and row[field]['max_abs'] == 0.0
                assert row[field]['elements'] == 15000
    assert len(summary['trace_stages']) == 5
    assert all(r['first_plan_recorded_computation_exact'] for r in summary['trace_stages'])
    for row, reduced in zip(replay['transport'], summary['transport']):
        assert row['sentinel_id'] == reduced['sentinel_id']
        assert row['comparison_valid'] and all(row['reconstruction_checks'].values())
        assert len(row['per_environment']) == 50
        for env in row['per_environment']:
            n = env['intersection']
            assert env['replaced_elites'] == 30 - n and env['jaccard'] == n / (60 - n)
        replaced = [v['replaced_elites'] for v in row['per_environment']]
        assert statistics.mean(replaced) == reduced['replaced_elites']['mean']
        assert sum(n > 0 for n in replaced) == reduced['environments_with_any_replacement']
        assert sum(replaced) == reduced['total_elites_replaced']
    flips = sum(r['repeat_outcomes']['changed_episode_count'] for r in local['sentinels'])
    assert flips == summary['paired_episode_flips'] == 1
    assert summary['paired_episode_comparisons'] == 250
    for report in (local, replay, summary):
        assert report['new_episode_count'] == 0 and report['protected_data_read'] is False
    result = {'all_checks_passed': True, 'artifact_sha256': records,
              'sentinel_pairs': 5, 'sealed_parent_files': 40, 'first_call_cem_banks': 8,
              'fixed_cost_arrays_replayed_twice': 8, 'transport_banks': 2,
              'paired_episode_flips': flips, 'new_episodes': 0, 'e20_authorized': False,
              'validator_source_sha256': sha(Path(__file__))}
    if args.output:
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
