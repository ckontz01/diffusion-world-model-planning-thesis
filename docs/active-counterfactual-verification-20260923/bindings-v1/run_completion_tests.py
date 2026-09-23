"""One artificial end-to-end fixture; no original efficacy/sensitivity rerun."""
import common as c
import argparse
import copy
import io
from pathlib import Path
import tempfile
import time
import numpy as np
from artificial import FakeLeWM,FakeTorch,factory
from bridge import LeWMBridge
from episodes import collect,evaluate,save
from verify import load_verify,dataset_rows,verify_arrays
from mock import pack
from fitting import fit_job,model_freeze,load_models,assert_roles
from policy import Selector
from model import JointModel


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);arg=p.parse_args()
    out=Path(arg.output);out.mkdir(exist_ok=False)
    started=time.monotonic();role_map=c.roles();datasets={};collection_checks=[]
    small={'population':4,'elites':2,'rounds':1}
    def backend():return LeWMBridge(FakeLeWM(),FakeTorch,'artificial-cpu')
    # All80 IDs are labels for NEW artificial arrays, never references opened.
    # No old artificial efficacy generator/scenario is imported or rerun.
    for role in ('fit','validation'):
        rows=[]
        for ref in role_map[role]:
            b=backend();a,m=collect(factory(b,success_at=8),b.rollout,ref,role,settings=small)
            with tempfile.TemporaryDirectory(prefix='acv0-artificial-') as temp:
                where=Path(temp);save(where,a,m);c.seal(where,{'artificial':True,'ref':ref})
                c.verify_seal(where);aa,mm,check=load_verify(where)
                rows+=dataset_rows(aa,mm);collection_checks.append(check)
        datasets[role]=pack(rows)
        with (out/(role+'-artificial-dataset.npz')).open('xb') as f:np.savez(f,**datasets[role])
    c.require(datasets['fit']['x'].shape==(256,996),'Maximum64x4 D192 fit context')
    c.require(datasets['fit']['a'].shape==(256,4,212),'Maximum4 suffixes')
    bad={k:v.copy() for k,v in datasets['fit'].items()};bad['roles'][0]='validation'
    try:assert_roles(bad,role_map['fit'],'fit')
    except ValueError:pass
    else:raise AssertionError('Forbidden role accepted')
    fits={}
    for kind in ('joint','ordinary'):
        dest=out/('fit-'+kind);dest.mkdir()
        begin=time.monotonic()
        result=fit_job(kind,datasets['fit'],datasets['validation'],dest,out/'fit-joint')
        c.seal(dest,next(j for j in c.grid() if j['key']=='fit-'+kind))
        elapsed=time.monotonic()-begin
        c.require(result['updates']==192 and elapsed<7200,'Existing CPU allocation reservation')
        fits[kind]={'wall_seconds_including_checkpoint':elapsed,'updates':result['updates'],'parameters':result['parameters'],
                    'reservation_seconds':7200,'passed':True}
    model_freeze(out,'artificial-test-no-research')
    models=load_models(out);selector=Selector(*models)
    # Checkpoint round trip uses exact predictions, not approximate metrics.
    j=JointModel.load(out/'fit-joint/joint.npz');x=datasets['validation']['x'];a=datasets['validation']['a'];r=datasets['validation']['r']
    np.testing.assert_array_equal(j.forward(x,a,r)[0]['q'],models[0].forward(x,a,r)[0]['q'])
    evals=[]
    for mode in c.CONTROLS:
        b=backend();a,m=evaluate(factory(b,success_at=18),b.rollout,931,mode,selector,settings=small)
        dest=out/('evaluate-'+mode);dest.mkdir();save(dest,a,m)
        _,_,checked=load_verify(dest);c.seal(dest,{'artificial':True,'control':mode});evals.append(checked)
    # Full-sized stored arrays:16 branches x150 post-action states, all metadata
    # and numeric members. Full-resolution raw canonical prefix images saved.
    # Reduced search above changes only compute of interface fixtures, not these
    # artifact dimensions. Search counters below set to frozen worst-case bounds.
    b=backend();a,m=collect(factory(b),b.rollout,490,'fit',settings=small)
    c.require(len(m['branches'])==16 and all(q['steps']==150 for q in m['branches']),'Worst-case dimensions')
    for branch in m['branches']:
        branch['ledger'].update(rollout_calls=421,sequences=126016,latent_transitions=378048,
                                learned_module_forward_calls=9,integration_responses=512,outcome_queries=2052)
    # Max-width finite float64 values exercise serialization upper bounds without
    # changing real training fixtures. Numeric payloads have fixed size.
    m['reference_identity']={k:'f'*128 for k in ('source_key','sha256','file')}
    m['wall_seconds']=1799.9999999999998
    dest=out/'footprint-collection';dest.mkdir();save(dest,a,m)
    c.write(dest/'TECHNICAL.json',{'passed':True,'checks':verify_arrays(a,m),'maximum_metadata_reserve':'x'*65536})
    c.seal(dest,{'spec':c.grid()[0],'maximum_seal_identity_reserve':'x'*4096})
    collection_bytes=sum(f.stat().st_size for f in dest.iterdir())
    # Evaluation path is deliberately full budget and same max4x4 tree.
    b=backend();a,m=evaluate(factory(b),b.rollout,931,'active',selector,settings=small)
    dest=out/'footprint-evaluation';dest.mkdir();save(dest,a,m)
    c.write(dest/'TECHNICAL.json',{'passed':True,'checks':verify_arrays(a,m),'maximum_metadata_reserve':'x'*65536})
    c.seal(dest,{'spec':next(j for j in c.grid() if j['stage']=='evaluation'),'maximum_seal_identity_reserve':'x'*4096})
    evaluation_bytes=sum(f.stat().st_size for f in dest.iterdir())
    c.require(collection_bytes<10_000_000 and evaluation_bytes<2_000_000,'Complete per-job footprint including seals')
    worst_jobs=80*10_000_000+256*2_000_000
    c.require(worst_jobs+500_000_000<=2_000_000_000 and 4*(worst_jobs+500_000_000)<=8_000_000_000,'Full future reservation')
    result={'artificial_only':True,'research_loads':0,'simulator_steps':0,'gpu_allocations':0,
            'collect_fit_freeze_evaluate_saved_verify':True,'collection_checks':collection_checks,'evaluation_checks':evals,
            'fits':fits,'full_collection_bytes':collection_bytes,'full_evaluation_bytes':evaluation_bytes,
            'full_grid_live_reservation':worst_jobs+500_000_000,'live_archive_partial_reservation':4*(worst_jobs+500_000_000),
            'metadata_plus_seal_extra_margin_per_fixture':69632,'wall_seconds':time.monotonic()-started,
            'performance_win_required':False,'original_artificial_results_rerun':False,
            'real_gpu_throughput_measured':False,'cpu_timing_scope':'Local bounded D192 maximum-shaped artificial fits; cluster/runtime performance not measured'}
    c.write(out/'RESULTS.json',result)
    print(c.json.dumps({k:v for k,v in result.items() if k not in ('collection_checks','evaluation_checks')},indent=2))


if __name__=='__main__':main()
