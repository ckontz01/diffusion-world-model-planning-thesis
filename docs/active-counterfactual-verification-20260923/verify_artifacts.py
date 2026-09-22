"""Read every supplied output; authenticate rather than rerun sensitivity fits."""
import hashlib
import json
from pathlib import Path
import zipfile
import numpy as np
from model import JointModel,OrdinaryModel
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    archive=ROOT/'ORIGINAL-PROTOTYPE.zip'
    assert sha(archive)=='9d843e842aae5318e55d65520a21b782cbb0f1c34c50875375fad6aa46cd95b2'
    manifest=load('prototype/MANIFEST.json');checks=[]
    with zipfile.ZipFile(archive) as z:
        for name,record in manifest['files'].items():
            p=ROOT/'prototype'/name
            assert p.stat().st_size==record['bytes'] and sha(p)==record['sha256']
            assert z.read('active_counterfactual_verification/'+name)==p.read_bytes()
            checks.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
    original=load('prototype/run-v1/RESULTS.json');repro=load('prototype-reproduction/RESULTS.json')
    assert load('prototype/run-v1/CONFIG.json')==load('prototype-reproduction/CONFIG.json')
    maxerror=[0.]
    def compare(a,b):
        if isinstance(a,dict):
            assert set(a)==set(b)
            for k in a:
                if k!='seconds':compare(a[k],b[k])
        elif isinstance(a,list):
            assert len(a)==len(b)
            for x,y in zip(a,b):compare(x,y)
        elif isinstance(a,float):
            maxerror[0]=max(maxerror[0],abs(a-b));assert abs(a-b)<1e-12
        else:assert a==b
    compare(original,repro)
    assert len(original['rows'])==1470 and len(original['summary'])==49
    gaussian=load('prototype/compression-v1/RESULTS.json')
    assert gaussian['conditional_means_checked']==1024 and gaussian['max_dense_compressed_mean_error']<1e-10
    sensitivity=load('prototype/sensitivity-v1/RESULTS.json')
    assert len(sensitivity['results'])==28 and sensitivity['max_formula_error']<1e-12
    # Read/check ALL preserved sensitivity rows; no new sensitivity work launched.
    for r in sensitivity['results']:
        assert len(r['methods'])==7
        for m,v in r['methods'].items():assert 0<=v['min']<=v['mean']+1e-12<=v['max']+2e-12<=1+2e-12
    neural=load('neural-run-v1/RESULTS.json');rows=[];restore=[]
    for case in neural['results']:
        path=ROOT/'neural-run-v1'/case['case'];joint=JointModel.load(path/'joint.npz');ordinary=OrdinaryModel.load(path/'ordinary.npz',joint)
        assert case['original_fit_digest_matches'] and case['fit_joint']['updates']==192 and case['fit_ordinary']['updates']==192
        assert joint.parameter_count==5067 and ordinary.parameter_count==9921
        with np.load(path/'ordinary.npz',allow_pickle=False) as z:
            for i,p in enumerate(ordinary.params):np.testing.assert_array_equal(p,z[f'p{i}'])
        rows.append(dict(case=case['case'],values={c['control']:c['expected_success'] for c in case['controls']}))
        restore.append(dict(case=case['case'],joint_sha256=sha(path/'joint.npz'),ordinary_sha256=sha(path/'ordinary.npz'),passed=True))
    assert len(rows)==7
    by={r['case']:r['values'] for r in rows}
    informative=by['informative_contact'];reversed_case=by['unannounced_sensor_reversal']
    assert abs(informative['active']-informative['ordinary'])<1e-12
    assert abs(informative['active']-informative['correctly_specified_exact_Bayes'])<1e-12
    assert reversed_case['active']<reversed_case['static']
    assert by['unstable_contact_mode']['active']<by['unstable_contact_mode']['correctly_specified_exact_Bayes']
    assert JointModel(996,212,192).parameter_count==90795 and OrdinaryModel(996,212,192).parameter_count==106177
    plan=load('PILOT-PROPOSED.json');roles=load('DATA-ROLES-PROPOSED.json')
    assert len(plan['grid'])==339 and plan['real_authorization'] is False
    assert sum(roles['counts'].values())==112 and len(roles['records'])==112
    assert len({r['source_key'] for r in roles['records'].values()})==112
    out=dict(status='PASS',original_zip_sha256=sha(archive),original_files=checks,
             supplied_unit_tests=15,main_reproduction_rows=1470,main_reproduction_summary_rows=49,
             main_reproduction_max_numeric_difference=maxerror[0],main_seconds_intentionally_not_compared=True,
             supplied_gaussian_output=gaussian,supplied_gaussian_rerun=False,
             supplied_sensitivity=dict(cells=sensitivity['analytic_grid_cells'],fits=sensitivity['fit_count'],
                 configurations=28,all_196_method_summaries_read=True,rerun=False,max_formula_error=sensitivity['max_formula_error']),
             neural_complete_expected_law_results=rows,checkpoints_restored=restore,
             mock=load('mock-run-v1/RESULTS.json')['independent_episode_checks'],real_payload_reads=0,
             research_checkpoint_loads=0,physics_calls=0,slurm_jobs=0,gpu_allocations=0)
    with (ROOT/'VERIFICATION.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(status='PASS',original_files=len(checks),rows=1470,summary_max_error=maxerror[0],
                         supplied_sensitivity_summaries_read=196,neural_cases=7,real_runtime_executed=False)))


if __name__=='__main__':main()
