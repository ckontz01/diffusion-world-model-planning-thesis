"""Workload envelopes, explicitly separating measured and assumed costs."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def calculate(timing,ns):
    assert timing['episode_executed'] is False and timing['batch_size']==1
    arms=sorted({r['arm'] for r in timing['rows']}); detail={}
    for arm in arms:
        rows=[r for r in timing['rows'] if r['arm']==arm]
        med={r['delta']:float(np.median([x['wall_seconds'] for x in r['rows'] if not x['warmup']])) for r in rows}
        last=med[15];other=max(v for k,v in med.items() if k!=15)
        # Both schedule cycles have exactly one final chunk.
        seconds={h:2*last+(2*h//15-2)*other for h in (75,150)}
        detail[arm]=dict(median_seconds_by_delta=med,
            full_budget_planner_seconds_per_run=seconds,
            observed_load_seconds=rows[0]['load_seconds'],
            max_observed_cuda_bytes=max(x['peak_allocated_bytes'] for r in rows for x in r['rows']))
    planner_per_episode=3*sum(sum(x['full_budget_planner_seconds_per_run'].values()) for x in detail.values())
    # 15 persistent workers (arm x training seed), both H within each worker.
    # 10 s process/import overhead above measured loading is an assumption.
    setup=3*sum(x['observed_load_seconds']+10 for x in detail.values())
    table=[]
    for n in ns:
        runs=30*n;actions=6750*n;calls=450*n;planners=planner_per_episode*n
        def allocated(step_ms,fraction=1.,factor=1.):
            # Assumed reset/record I/O = 50 ms per episode-run, not timed here.
            return factor*(fraction*(planners+actions*step_ms/1000)+runs*.05+setup)/3600
        table.append(dict(n=n,episode_runs=runs,primary_arm_runs=18*n,
            secondary_arm_runs=12*n,max_primitive_actions=actions,max_planner_calls=calls,
            worker_jobs=15,planner_wall_hours_full_budget=planners/3600,
            allocated_gpu_hours_2ms_action=allocated(2),
            allocated_gpu_hours_5ms_action=allocated(5),
            allocated_gpu_hours_10ms_action=allocated(10),
            allocated_gpu_hours_50pct_work_at_5ms=allocated(5,.5),
            conservative_envelope_hours_10ms_and_2x=allocated(10,factor=2),
            three_gpu_wall_hours_at_5ms_excluding_queue=allocated(5)/3,
            secondary_half_allocation_run_count_savings_fraction=0.2))
    return dict(device=timing['device'],arms=detail,table=table,
        measured='A6000 batch1, fixed exposed 8908/53, one warmup plus three measured calls per arm/delta, outer CUDA synchronization; preparation+solve wall time.',
        assumptions=['Unmeasured intermediate remaining durations use maximum measured long-branch median.',
            'Training seed7201 timings extrapolate to unchanged same-architecture7202/7203.',
            'Native action/physics/render overhead is SCENARIO ASSUMPTION2/5/10ms, not measured by this probe.',
            'Reset/record I/O assumed50ms per run; 15 persistent arm-seed workers load once.',
            'Full budgets upper-bound counts, not guaranteed success-dependent runtime. 50% work is a separate scenario.',
            'Allocated GPU hours include CPU-wait wall time. Three GPUs give an optimistic /3 with no queue or imbalance.',
            '2x total envelope allows contention/startup variation, not a measured confidence interval.',
            'Same allocation for all five arms recommended; any secondary down-allocation needs approval.'],
        sage_reserve='No remaining P2 long episode is SAGE-test eligible; reserving any of these episodes cannot produce a training-disjoint SAGE sample. Future SAGE cost is not benchmarked or funded here.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    base=a.evidence
    availability=json.loads((base/'metadata-v3/availability.json').read_text())
    timing=json.loads((base/'timing-job-300309/timing.json').read_text())
    path=base/'workload.json';assert not path.exists()
    path.write_text(json.dumps(calculate(timing,sorted({82,400,600,800,availability['metadata_eligible_maximum']})),indent=2,sort_keys=True)+'\n')
    print(json.dumps(json.loads(path.read_text())['table'],indent=2))
