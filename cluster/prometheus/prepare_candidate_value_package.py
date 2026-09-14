"""Generate ID-only design artifacts locally. Cannot dispatch/read research data."""
import json
from pathlib import Path
import candidate_value_learning as c
import candidate_value_contract as ct


def main():
    out=Path(__file__).resolve().parents[2]/'docs/candidate-value-learning-20260914'
    out.mkdir(exist_ok=True)
    allocation={'status':'PROPOSED_NOT_AUTHORIZED_FOR_EXECUTION',
                'version':c.VERSION,'namespace':c.VERSION+'|reference-allocation',
                'split_unit':'whole independently collected source reference',
                'metadata_source_identity_preflight_pending':True,
                'no_research_data_read':True,'excluded_historical_references':list(c.HISTORICAL),
                'allocation':c.allocation()}
    costs=c.cost_plan()
    costs.update(execution_grid=ct.grid(),total_jobs=len(ct.grid()),
                 neural_training_seeds=list(ct.TRAIN_SEEDS),learned_arm='fixed_probability_ensemble',
                 fitted_models=5,maximum_training_optimizer_updates=9600,
                 cpu_jobs={'fit_seconds':6000,'validate_seconds':600,'report_seconds':600},
                 cpu_training_and_analysis_wall_seconds_cap=ct.CAPS['cpu_seconds'],
                 source_and_control_storage_reservation_bytes=50000000,
                 sampled_candidate_index_rows=8192,
                 distinct_sampled_candidates_definition='8192 bank-index rows; physical action-value uniqueness is measured, not assumed',
                 exact_repeats=0,context_diagnostic_is_closed_loop_arm=False)
    full=128*65*(8+18);first=128*65*4
    planner=full*.13175849+first*.07289795
    historical_step_overhead=(2297.099-437.505-6386*.13175849-956*.07289795)/109870
    costs['planning_scenarios']={
        'full_continuation_solve_ceiling':full,'first_only_solve_ceiling':first,
        'proposal_batches':2*full+first,'diffusion_network_forwards':10*(2*full+first),
        'historical_mean_planner_only_hours':planner/3600,
        'amortized_historical_worker_plus_allocation_hours':(
            planner+costs['collection_steps']*historical_step_overhead+
            256*(437.505/64+(2963-2297.099)/64))/3600,
        'unamortized_allocation_per_step_hours':2963/109870*costs['collection_steps']/3600,
        'conservative_twice_p95_plus_20ms_step_30s_job_hours':(
            2*(full*.13226187+first*.07411497)+.02*costs['collection_steps']+256*30)/3600,
        'historical_max_each_call_plus_same_allowance_hours':(
            full*1.284026+first*.0803727+.02*costs['collection_steps']+256*30)/3600,
        'warning':'Planning extrapolations, not new workload measurements; no price tariff known'}
    for name,value in (('PROPOSED-ALLOCATION.json',allocation),('COST-PLAN.json',costs)):
        (out/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(costs,indent=2,sort_keys=True))


if __name__=='__main__':main()
