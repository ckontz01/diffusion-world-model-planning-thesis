"""Exposed-summary cost/precision/footprint arithmetic, no efficacy rerun."""
from dtv_success_cost.common import *
from dtv_success_cost.analysis import precision

def main():
    c=load(DOC/'BINDINGS.json');old=ROOT/'docs/dtv-efficiency-20260930/evidence'
    training=[];episode=[]
    for p in sorted((old/'results/acid-alternative/scorers').rglob('summary.json')):
        r=load(p)
        parts=p.relative_to(old/'results/acid-alternative/scorers').parts
        training.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),elapsed_seconds=r.get('elapsed_seconds'),task=parts[0],seed=r.get('seed'),arm=parts[1],scope='reported process training elapsed; not independently reconciled allocation/energy',allocation_seconds=None))
    for p in sorted((old/'results/acid-alternative/latency').glob('*/end-to-end-episode/*/summary.json')):
        episode.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),summary=load(p)))
    proxy=dict(pusht=[6.432349,6.397940,6.263914,6.172595],reacher=[6.444074,6.428438,6.274270,6.152149],cube=[6.874137,6.865300,6.735570,6.596097])
    scenarios=[]
    for slowdown in (1,2,3):
        per_task={t:(2*sum(proxy[t])*slowdown+15)*N*3/3600 for t in TASKS}
        scenarios.append(dict(assumed_policy_slowdown=slowdown,assumed_authentication_model_setup_seconds_per_worker=15,task_allocation_hours_proxy=per_task,total_gpu_allocation_hours_proxy=sum(per_task.values()),queue_excluded=True,future_throughput_guarantee=False))
    worst=len(c['jobs'])*(1000000+100000)+1000000+100000+c['analysis_bytes']+100000+c['source_bytes']+c['control_bytes']+c['reused_model_bytes']
    record=dict(source_count_per_task=N,workers=len(c['jobs']),scheduled_tasks=len(c['jobs'])+2,episodes=len(c['jobs'])*8,
                physical_controller_actions=c['physical_actions'],maximum_planning_decisions=len(c['jobs'])*8*2,
                scored_populations=c['max_populations'],world_rollout_calls=c['max_populations'],candidate_sequences=c['max_candidate_sequences'],predicted_transitions=c['max_predicted_transitions'],
                learned_checker_calls=c['max_populations']*3//4,checker_transition_tuples=c['max_predicted_transitions']*3//4,
                gpu_ceiling_hours=c['gpu_seconds']/3600,cpu_allocation_ceiling_hours=c['cpu_seconds']/3600,
                host_archive_wall_ceiling_seconds=7200,native_transfer_wall_ceiling_seconds=7200,
                historical_proxy_episodes_seconds=proxy,forecast_scenarios=scenarios,precision=precision(),
                training_costs=training,raw_exposed_episode_timing_inputs=episode,worst_case_live_bytes=worst,
                live_ceiling_bytes=c['live_bytes'],archive_ceiling_bytes=c['archive_bytes'],inclusive_ceiling_bytes=c['inclusive_bytes'],
                historical_saved_input_speedup_not_extrapolated=True,old_32_acv_sources_used=False)
    if worst>c['live_bytes'] or c['live_bytes']+2*c['archive_bytes']>c['inclusive_bytes']:raise RuntimeError('complete future storage reservation does not fit')
    write(DOC/'PLANNING-EVIDENCE.json',record)
    print(dict(training_summaries=len(training),old_episode_summaries=len(episode),scenarios=scenarios,worst_live_bytes=worst))
if __name__=='__main__':main()
