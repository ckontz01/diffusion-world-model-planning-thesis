"""Independent standard-library reaggregation of the archived binary outcomes.

No NumPy or diagnostic implementation is imported. This checks the paired counts,
point estimates and reference-cluster standard errors, not bootstrap coverage.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import zipfile

ARMS = ('vad_continuation', 'vad_greedy_300', 'diagonal_gaussian_continuation',
        'vad_greedy_576', 'direct_gmm_continuation', 'sage')
TENSOR_SHA = 'afb181230eb36d0d6081477bef910814f8b2c0208d913063df48131e4e2af7e2'
SUMMARY_SHA = '305be6aa678445dce5ceddda6bae14657a730810e448121df6c8783c4318da6d'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_binary(path):
    require(digest(path) == TENSOR_SHA, 'Tensor digest mismatch')
    with zipfile.ZipFile(path) as archive:
        require(archive.namelist() == ['success.npy'], 'Unexpected ZIP entries')
        blob = archive.read('success.npy')
    require(blob[:8] == b'\x93NUMPY\x01\x00', 'Expected NPY format version 1')
    header_size = struct.unpack('<H', blob[8:10])[0]
    header = ast.literal_eval(blob[10:10 + header_size].decode('latin1').strip())
    require(header == {'descr': '<f8', 'fortran_order': False, 'shape': (1600, 2, 3, 6)},
            'Unexpected array metadata')
    raw = blob[10 + header_size:]
    require(len(raw) == 1600 * 2 * 3 * 6 * 8, 'Wrong array byte count')
    values = [value for value, in struct.iter_unpack('<d', raw)]
    require(all(v in (0., 1.) for v in values), 'Nonbinary outcome')
    return [int(v) for v in values]


def verify(archive, report_path):
    require(digest(archive / 'SUMMARY.json') == SUMMARY_SHA, 'Summary digest mismatch')
    summary = json.loads((archive / 'SUMMARY.json').read_text())
    report = json.loads(report_path.read_text())
    values = read_binary(archive / 'EPISODE-TENSOR.npz')
    def get(i, h, s, a):
        return values[((i * 2 + h) * 3 + s) * 6 + a]
    def close(a, b, name):
        require(math.isclose(a, b, rel_tol=0, abs_tol=1e-11), 'Mismatch: ' + name)
    for a, arm in enumerate(ARMS):
        total = sum(get(i, h, s, a) for i in range(1600) for h in range(2) for s in range(3))
        close(total / 9600, summary['arm_success'][arm], arm)
        for h in range(2):
            by_h = sum(get(i, h, s, a) for i in range(1600) for s in range(3)) / 4800
            close(by_h, summary['per_horizon'][arm][h], arm + '/horizon')
            for s in range(3):
                block = sum(get(i, h, s, a) for i in range(1600)) / 1600
                close(block, report['per_fixed_block_success'][arm][h][s], arm + '/block')
    pairs_checked = 0
    for a, b in itertools.combinations(range(6), 2):
        key = ARMS[a] + '__' + ARMS[b]
        for label, hs in [('all', range(2)), ('h75', [0]), ('h150', [1])]:
            counts = Counter((get(i, h, s, a), get(i, h, s, b))
                             for i in range(1600) for h in hs for s in range(3))
            row = report['method_pairs'][key][label]
            for name, coordinate in [('both_success', (1, 1)), ('left_only', (1, 0)),
                                     ('right_only', (0, 1)), ('both_failure', (0, 0))]:
                require(row[name] == counts[coordinate], 'Pair count mismatch')
            n = sum(counts.values())
            close(row['nondeployable_whole_planner_oracle_success'], 1 - counts[(0, 0)] / n, 'oracle union')
            require(row['paired_measurements'] == n, 'Pair denominator mismatch')
        nets = [sum(get(i, h, s, a) - get(i, h, s, b) for h in range(2) for s in range(3))
                for i in range(1600)]
        for name, value in [('reference_net_wins', sum(v > 0 for v in nets)),
                            ('reference_net_losses', sum(v < 0 for v in nets)),
                            ('reference_net_ties', sum(v == 0 for v in nets))]:
            require(report['method_pairs'][key][name] == value, 'Reference count mismatch')
        pairs_checked += 1
    metrics_checked = 0
    for b, arm in enumerate(ARMS[1:], 1):
        lo = [sum(get(i, 0, s, 0) - get(i, 0, s, b) for s in range(3)) / 3 for i in range(1600)]
        hi = [sum(get(i, 1, s, 0) - get(i, 1, s, b) for s in range(3)) / 3 for i in range(1600)]
        vectors = {'overall': [(l + h) / 2 for l, h in zip(lo, hi)], 'h75': lo, 'h150': hi,
                   'h150_minus_h75': [h - l for l, h in zip(lo, hi)]}
        for label, vals in vectors.items():
            key = f'vad_continuation-minus-{arm}/{label}'
            row = report['metrics'][key]
            close(row['estimate_pp'], statistics.mean(vals) * 100, key)
            close(row['reference_cluster_se_pp'], statistics.stdev(vals) / 40 * 100, key + '/se')
            if label == 'overall' and arm in summary['primary']:
                close(statistics.mean(vals), summary['primary'][arm]['difference'], 'original primary effect')
                close(statistics.stdev(vals) / 40, summary['primary'][arm]['se'], 'original primary se')
            metrics_checked += 1
    return {'all_checked_quantities_passed': True, 'implementation': 'independent standard-library ZIP/NPY decoder and integer outcome counting',
            'independent_references': 1600, 'logical_runs': 57600, 'method_pairs_checked': pairs_checked,
            'contrasts_and_cluster_standard_errors_checked': metrics_checked,
            'tensor_sha256': TENSOR_SHA, 'summary_sha256': SUMMARY_SHA,
            'report_sha256': digest(report_path), 'program_sha256': digest(Path(__file__)),
            'bootstrap_intervals_independently_recomputed': False,
            'raw_physical_success_recomputed': False, 'model_runs': 0,
            'scope': 'Numerical consistency of archived outcomes; not an independent environment experiment.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    try:
        target, source = a.out.resolve(), a.archive.resolve()
        require(target != source and source not in target.parents, 'Output inside input archive')
        require(target != a.report.resolve() and not a.out.exists(), 'Refusing to overwrite a file')
        result = verify(a.archive, a.report)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open('x', encoding='utf-8', newline='\n') as f:
            json.dump(result, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n')
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, KeyError, OSError, struct.error, zipfile.BadZipFile) as e:
        print('STOP: ' + str(e), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
