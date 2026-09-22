"""Emit/check a finite proposal and job grid. There is deliberately no submit."""
import json
from pathlib import Path
ROOT=Path(__file__).parent


def main():
    roles=json.loads((ROOT/'DATA-ROLES-PROPOSED.json').read_text())['proposed_roles']
    controls=['vanilla','static','passive','active','no_update','ordinary','bayesian','early-replan']
    jobs=[]
    for role in ('fit','validation'):
        for r in roles[role]:jobs.append(dict(key=f'collect-{role}-{r}',stage='collection',role=role,reference=r,
                                            max_episodes=16,max_steps=2400,gpu=1,cpus=4,ram_gib=24,seconds=1800))
    for kind,seed in [('joint',94011),('ordinary',94012)]:
        jobs.append(dict(key='fit-'+kind,stage='fitting',init_seed=seed,epochs=12,batch_sources=64,updates=12,
                         sources=64,gpu=0,cpus=4,ram_gib=8,seconds=7200))
    # Last-layer closed-form fit is included in ordinary CPU job, no extra labels.
    for i,r in enumerate(roles['final_development']):
        order=controls[i%8:]+controls[:i%8]
        for arm in order:jobs.append(dict(key=f'evaluate-{r}-{arm}',stage='evaluation',reference=r,control=arm,
                                          max_episodes=1,max_steps=150,gpu=1,cpus=4,ram_gib=24,seconds=300))
    jobs.append(dict(key='analysis',stage='analysis',gpu=0,cpus=4,ram_gib=8,seconds=7200))
    assert len(jobs)==339 and len({j['key'] for j in jobs})==339
    per_tree=5*300*30+16;per_tail=9*300*30
    collect=80*(per_tree+16*per_tail)
    evaluation=32*(6*(per_tree+per_tail)+90000+99000)
    plan=dict(status='REVIEW_REQUIRED_REAL_RUNTIME_DISABLED',controls=controls,grid=jobs,
              goal_horizon=75,total_action_budget=150,prefix_actions=5,continuation_actions=10,tail_start_absolute=15,
              proposal_seed_rule='SeedSequence([94041,reference_index,absolute_clock]); no arm/outcome IDs',
              constrained_seed_rule='SeedSequence([94001,first_32_bits_SHA256_exact_prefix]); no observed outcomes',
              integration_seed=94021,integration_responses_per_prefix=128,integration_responses_per_episode=512,
              integration_rule='32 antithetic normals per component, stratified pi/32 weights, common samples',
              fitting_shuffle_seed=94013,bootstrap_seed=94301,bootstrap_resamples=10000,
              primary_comparisons=[['active','ordinary'],['active','bayesian'],['active','early-replan']],
              primary_endpoint='Any native post-action success by original primitive 150',
              source_count_evaluation=32,powered_confirmation=False,
              maximum_collection_episodes=1280,maximum_evaluation_episodes=256,maximum_physical_steps=230400,
              tree_sequences=per_tree,tree_batch_rollout_calls=151,matched_episode_sequences=per_tree+per_tail,
              matched_episode_batch_rollout_calls=421,vanilla_sequences=90000,early_replan_sequences=99000,
              collection_sequences=collect,evaluation_sequences=evaluation,total_sequences=collect+evaluation,
              total_latent_transitions=3*(collect+evaluation),
              collection_batch_rollout_calls=80*(151+16*270),evaluation_batch_rollout_calls=32*(6*421+300+330),
              max_image_encoder_calls=1536*152,max_learned_candidate_predictions_per_matched_episode=2068,
              max_learned_module_forward_calls_per_matched_episode=9,max_response_context_rows_per_episode=517,
              gpu_allocation_seconds=sum(j['seconds'] for j in jobs if j['gpu']),
              cpu_only_allocation_seconds=sum(j['seconds'] for j in jobs if not j['gpu']),serial_gpu_concurrency=1,
              gpu_kind='A6000',collection_job_bytes=10000000,evaluation_job_bytes=2000000,
              learned_models_source_control_analysis_bytes=500000000,new_live_bytes=2000000000,
              new_live_archive_partial_preservation_bytes=8000000000,ssd_free_required=40000000000,
              technical_tranche_included=[j['key'] for j in jobs[:2]],automatic_retry=False,requeue=False,
              case_replacement=False,automatic_followup=False,real_authorization=False)
    assert plan['gpu_allocation_seconds']==220800 and plan['cpu_only_allocation_seconds']==21600
    assert 80*16*150+32*8*150==plan['maximum_physical_steps']
    assert plan['collection_batch_rollout_calls']+plan['evaluation_batch_rollout_calls']==458672
    with (ROOT/'PILOT-PROPOSED.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
    print(json.dumps({k:plan[k] for k in ('status','maximum_physical_steps','total_sequences','total_latent_transitions',
                                         'gpu_allocation_seconds','cpu_only_allocation_seconds')}))


if __name__=='__main__':main()
