#!/usr/bin/env python3
"""Standard-library reduction of exposed L1 evidence; no model or environment."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics


RAW = Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/discrepancy-diagnostic-run-20260829-e347bc08')
L1_ROOT = Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-l1')
FIELDS = {
    'history_latents': ('input', 'output'),
    'final_goal_latents': ('input', 'output'),
    'local_goal': ('output',),
    'cube_local_goal_cache': ('output',),
    'prior_top_actions': ('output',),
    'cem_fit': ('candidates', 'costs', 'elite_indices', 'mean', 'effective_std', 'elite_costs'),
    'solver_output': ('actions', 'costs'),
}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def same(a, b):
    # Historical prior-top solver has intentional NaN cost placeholders.
    # Compare their explicit JSON spelling; do not treat NaN != NaN as drift.
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def keyed(events):
    counts = Counter()
    result = {}
    for event in events:
        group = event['plan_index'], event['kind']
        key = *group, counts[group]
        counts[group] += 1
        result[key] = event
    return result


def trace_stages(a, b):
    left, right = keyed(a['events']), keyed(b['events'])
    if list(left) != list(right):
        raise ValueError('ordered event keys differ; stage reduction cannot assume alignment')
    first = {}
    stages = defaultdict(lambda: {'solver_input_changed_keys': [], 'observed_computation_difference_counts': Counter()})
    for key, event in left.items():
        other = right[key]
        plan, kind, _ = key
        stage = stages[plan]
        if kind == 'solver_input':
            x, y = event['mapping'], other['mapping']
            stage['solver_input_changed_keys'] = [name for name in sorted(x.keys() | y.keys())
                if name not in x or name not in y or not same(x.get(name), y.get(name))]
        for name in FIELDS.get(kind, ()):
            if name not in event and name not in other:
                continue
            if same(event.get(name), other.get(name)):
                continue
            field = f'{kind}.{name}'
            stage['observed_computation_difference_counts'][field] += 1
            first.setdefault(field, {'plan_index': plan, 'round_index': event.get('round_index'),
                'sequence': event['sequence'], 'left': event.get(name), 'right': other.get(name)})
    return {'first_observed_computation_difference_by_field': first,
            'per_plan': [{'plan_index': plan, **stage} for plan, stage in sorted(stages.items())],
            'first_plan_recorded_computation_exact': not stages[0]['observed_computation_difference_counts'],
            'recorded_fields_only': True,
            'no_step_level_state_or_later_round_raw_tensors_exist_in_this_reduction': True}


def distribution(values):
    return {'n': len(values), 'min': min(values), 'median': statistics.median(values),
            'mean': statistics.mean(values), 'max': max(values)}


def transport_summary(row):
    envs = row['per_environment']
    replaced = [v['replaced_elites'] for v in envs]
    return {'sentinel_id': row['sentinel_id'], 'comparison_valid': row['comparison_valid'],
            'environments_with_any_replacement': sum(n > 0 for n in replaced),
            'total_elites_replaced': sum(replaced), 'replaced_elites': distribution(replaced),
            'replacement_histogram': dict(sorted(Counter(replaced).items())),
            'intersection': distribution([v['intersection'] for v in envs]),
            'jaccard': distribution([v['jaccard'] for v in envs]),
            **{f'{variant}_boundary_gap': distribution([v[f'{variant}_boundary']['boundary_gap'] for v in envs])
               for variant in ('jpeg', 'lossless')},
            **{f'{variant}_boundary_relative_gap': distribution([v[f'{variant}_boundary']['boundary_gap_relative'] for v in envs])
               for variant in ('jpeg', 'lossless')},
            **{f'{variant}_boundary_exact_ties': sum(v[f'{variant}_boundary']['exact_boundary_tie'] for v in envs)
               for variant in ('jpeg', 'lossless')},
            **{f'{variant}_boundary_near_1e_6': sum(v[f'{variant}_boundary']['near_boundary_1e_6_relative'] for v in envs)
               for variant in ('jpeg', 'lossless')},
            **{key: row[key] for key in ('fitted_mean_delta', 'fitted_std_delta', 'history_latent_delta', 'goal_latent_delta', 'cost_delta')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if L1_ROOT not in args.analysis.resolve().parents or L1_ROOT not in args.output.resolve().parents or args.output.exists():
        raise ValueError('requires existing L1 analysis and a fresh L1 supplement path')
    names = {'LOCALIZATION.json', 'FIXED-BANK-REPLAY.json'}
    inventory = {}
    for line in (args.analysis / 'sha256.txt').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        if name not in names or name in inventory or sha(args.analysis / name) != digest:
            raise ValueError('L1 input seal failed')
        inventory[name] = digest
    if inventory.keys() != names:
        raise ValueError('incomplete L1 seal')
    localized = json.loads((args.analysis / 'LOCALIZATION.json').read_text())
    replay = json.loads((args.analysis / 'FIXED-BANK-REPLAY.json').read_text())
    if len(localized['sentinels']) != 5 or len(replay['fit_replays']) != 8 or len(replay['transport']) != 2:
        raise ValueError('unexpected reduction identity')
    traces = []
    for sid in range(5):
        pair = []
        for repeat in (0, 1):
            path = RAW / 'sentinels' / f's{sid}' / f'r{repeat}' / 'trace.json'
            if sha(path) != localized['inventories'][f's{sid}/r{repeat}']['trace.json']:
                raise ValueError('exposed trace hash changed')
            trace = json.loads(path.read_text())
            if trace['sentinel']['sentinel_id'] != sid or trace['repeat'] != repeat:
                raise ValueError('trace identity changed')
            pair.append(trace)
        traces.append({'sentinel_id': sid, **trace_stages(*pair)})
    report = {'kind': 'e19_l1_stage_and_sensitivity_reduction', 'input_seals': inventory,
              'reducer_source_sha256': sha(Path(__file__)), 'trace_stages': traces,
              'transport': [transport_summary(row) for row in replay['transport']],
              'paired_episode_flips': sum(row['repeat_outcomes']['changed_episode_count'] for row in localized['sentinels']),
              'paired_episode_comparisons': 250, 'new_episode_count': 0,
              'new_inference_count': 0, 'parent_decisions_modified': False,
              'protected_data_read': False, 'e20_authorized': False}
    args.output.mkdir(parents=True)
    path = args.output / 'STAGE-AND-SENSITIVITY-SUMMARY.json'
    path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    path.chmod(0o444)
    (args.output / 'sha256.txt').write_text(f'{sha(path)}  {path.name}\n')
    (args.output / 'sha256.txt').chmod(0o444)
    print(json.dumps({'first_plan_recorded_computation_exact': [r['first_plan_recorded_computation_exact'] for r in traces],
                      'paired_episode_flips': report['paired_episode_flips'], 'output': str(path)}))


if __name__ == '__main__':
    main()
