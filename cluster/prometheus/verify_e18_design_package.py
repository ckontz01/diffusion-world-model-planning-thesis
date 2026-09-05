"""Read-only independent checks plus a generated preparatory provenance record."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import numpy as np
import scipy
from e18_design_workload import calculate


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(base):
    base=base.resolve()
    for part in ('metadata-v3','planning-v1','timing-job-300309'):
        root=base/part
        for line in (root/'sha256.txt').read_text().splitlines():
            h,name=line.split(maxsplit=1);assert sha(root/name)==h
    p=json.loads((base/'planning-v1/planning.json').read_text())
    a=json.loads((base/'metadata-v3/availability.json').read_text())
    h=json.loads((base/'metadata-v3/historical.json').read_text())
    assert p['input_sha256']['availability.json']==sha(base/'metadata-v3/availability.json')
    assert p['input_sha256']['historical.json']==sha(base/'metadata-v3/historical.json')
    assert p['data_capacity']==a
    # Reconstruct episode means independently, not through the analysis function.
    points=[]
    for ep in sorted({r['episode_id'] for r in h['rows']}):
        er=[r for r in h['rows'] if r['episode_id']==ep]
        m={arm:np.mean([int(r['success']) for r in er if r['arm']==arm])
           for arm in ('vad_continuation','vad_greedy_300','diagonal_gaussian_continuation')}
        points.append([m['vad_continuation']-m['vad_greedy_300'],
                       m['vad_continuation']-m['diagonal_gaussian_continuation']])
    np.testing.assert_allclose(np.mean(points,axis=0),p['historical']['mean'])
    np.testing.assert_allclose(np.cov(points,rowvar=False),p['historical']['covariance'])
    assert len(points)==12 and len(h['rows'])==360
    assert a['metadata_eligible_maximum']==82
    assert all(not r['feasible_from_current_authorized_metadata'] for r in p['results'] if r['n']>82)
    assert {r['n'] for r in p['results']}=={82,400,600,800}
    assert len(p['results'])==24 and p['monte_carlo_replicates']==20000
    for r in p['results']:
        for s in r['simulation'].values():
            marg=[x['rate'] for x in s['marginal']]
            assert 0<=s['joint']['rate']<=min(marg)<=1
            assert s['moment_residual']<=1e-7
    timing=json.loads((base/'timing-job-300309/timing.json').read_text())
    work=json.loads((base/'workload.json').read_text())
    assert work==json.loads(json.dumps(calculate(timing,[82,400,600,800])))
    assert len(timing['rows'])==20 and sum(len(r['rows']) for r in timing['rows'])==80
    assert not timing['episode_executed'] and timing['model_tensors_unchanged']
    assert not p['confirmation_frozen'] and not p['confirmation_launched']
    assert all(v is False for v in a['flags'].values())
    code=base.parent;repo=code.parents[1]
    protected_sources=['pusht_fresh_initialization.py','e18_fresh_driver.py',
        'gdp_cem_e18_runtime.py','gdp_cem_e18_closed_loop.py','gdp_cem_e18_specs.py']
    for name in protected_sources:
        old=subprocess.check_output(['git','show','286088e:cluster/prometheus/'+name],cwd=repo)
        assert old==(code/name).read_bytes()
    return dict(kind='preparatory_package_verification',all_passed=True,
        python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
        inherited_source_sha256={name:sha(code/name) for name in protected_sources},
        new_analysis_source_sha256={name:sha(code/name) for name in [
            'e18_design_metadata.py','e18_design_power.py','e18_design_workload.py',
            'e18_design_timing.py','test_e18_full_budget_lifecycle.py',
            'test_e18_design_feasibility.py','run_e18_design_timing.slurm',
            'verify_e18_design_package.py']},
        evidence_sha256={str(x.relative_to(base)):sha(x) for x in sorted(base.rglob('*'))
            if x.is_file() and x.name not in ('VERIFICATION.json','PACKAGE.sha256','README.md')},
        historical_decision_preserved=True,confirmation_frozen=False,
        confirmation_launched=False,protected_outcome_accessed=False,
        remaining_unavailable_certificate='Additional protected allocation eligibility has no custodian certificate; excluded from feasible N.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--record',action='store_true');a=parser.parse_args()
    result=verify(a.evidence)
    if a.record:
        path=a.evidence/'VERIFICATION.json';assert not path.exists()
        path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        files=[x for x in sorted(a.evidence.rglob('*')) if x.is_file() and x.name!='PACKAGE.sha256']
        (a.evidence/'PACKAGE.sha256').write_text(''.join(f'{sha(x)}  {x.relative_to(a.evidence)}\n' for x in files))
    print(json.dumps(result,indent=2,sort_keys=True))
