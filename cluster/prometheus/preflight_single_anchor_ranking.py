"""CPU-only packaging tests. Never call a model constructor or simulator."""
import argparse
import importlib
import json
import platform
from pathlib import Path
import sys
import unittest


def main(mode, output):
    report = dict(mode=mode, executable=sys.executable, python=platform.python_version(),
                  model_constructed=False, simulator_executed=False, payload_read=False,
                  modules={}, all_passed=False)
    names = ['single_anchor_ranking_dispatch'] if mode == 'host-dispatcher' else [
        'single_anchor_ranking_dispatch', 'single_anchor_ranking_runner',
        'verify_single_anchor_ranking', 'independent_pusht_runtime',
        'independent_pusht_evaluate', 'independent_pusht_collect',
        'pusht_fresh_initialization', 'e18_fresh_driver',
        'gdp_cem_e18_runtime', 'gdp_cem_e18_closed_loop']
    try:
        for name in names:
            module = importlib.import_module(name)
            report['modules'][name] = str(Path(module.__file__).resolve())
        if mode == 'pinned-container':
            import numpy
            import torch
            report['numpy'], report['torch'] = numpy.__version__, torch.__version__
            # Explicitly forbid checkpoint loading during the synthetic tests.
            def forbidden(*args, **kwargs):
                raise RuntimeError('Real checkpoint access forbidden in CPU preflight')
            torch.load = forbidden
            suite = unittest.defaultTestLoader.loadTestsFromNames(['test_single_anchor_ranking', 'test_single_anchor_ranking_host'])
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            report.update(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors))
            report['all_passed'] = result.wasSuccessful() and result.testsRun == 22
        else:
            suite = unittest.defaultTestLoader.loadTestsFromName('test_single_anchor_ranking_host')
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            report.update(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors))
            report['all_passed'] = result.wasSuccessful() and result.testsRun == 4
    except Exception as error:
        report['error_type'], report['error'] = type(error).__name__, str(error)
    with Path(output).open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
    print(json.dumps(report, sort_keys=True))
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=('host-dispatcher', 'pinned-container'), required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    sys.exit(main(a.mode, a.out))
