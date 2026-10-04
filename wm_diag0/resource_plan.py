"""Finite proposal arithmetic; NOT a dispatcher or execution authorization."""
import json

def counts():
    parents, backbones, bank, draws = 64, 2, 16, 2
    settings_sources = parents*backbones
    oracle = settings_sources*bank
    evaluation = oracle*draws
    population_calls = (settings_sources+evaluation)*30+settings_sources
    return {
        'status':'PROPOSED_NOT_AUTHORIZED',
        'diagnostic_parents':parents, 'setting_sources':settings_sources,
        'oracle_prefix_worlds':oracle, 'evaluation_tail_worlds':evaluation,
        'bank_helper_worlds':settings_sources, 'fresh_worlds':oracle+evaluation+settings_sources,
        'readout_fit_frames':4*256, 'readout_validation_frames':4*96,
        'physical_controller_steps_upper':oracle*(200+25)+evaluation*(200+50)+settings_sources*200,
        'native_cem_sequences_upper':(settings_sources+evaluation)*9000,
        'bank_rescore_sequences':settings_sources*bank,
        'predicted_transitions_upper':((settings_sources+evaluation)*9000+settings_sources*bank)*5,
        'batched_cost_calls_upper':population_calls,
        'batched_predictor_calls_upper':population_calls*5,
        'context_goal_encoder_calls_upper':population_calls*2,
        'gpu_jobs':132, 'cpu_jobs':2, 'successful_logical_tasks':134,
        'gpu_allocation_seconds_cap':128*3600+4*1800,
        'cpu_stage_allocation_wall_seconds_cap':1200+3600,
        'parent_workers_by_backbone':{'lewm':64,'dinowm_noprop':64},
        'parent_bytes_cap_by_backbone':{'lewm':10_000_000,'dinowm_noprop':70_000_000},
        'readout_workers_by_backbone':{'lewm':2,'dinowm_noprop':2},
        'readout_bytes_cap_by_backbone':{'lewm':5_000_000,'dinowm_noprop':200_000_000},
        'worker_log_bytes_cap':1_000_000,
        'all_source_bytes_cap':20_000_000, 'controls_bytes_cap':300_000_000,
        'reused_weights_bytes_cap':2_000_000_000,
        'live_bytes_cap':12_000_000_000, 'archive_bytes_cap':14_000_000_000,
        'inclusive_bytes_cap':42_000_000_000,
        'compatibility_condition':'native 300/30/30 CEM, horizon 5 grouped five controller actions; encoder <=2 calls/population; no extra calls/retries'
    }

def storage_reservations():
    c=counts(); log=c['worker_log_bytes_cap']
    workers=sum(n*(c['parent_bytes_cap_by_backbone'][b]+log) for b,n in c['parent_workers_by_backbone'].items())
    readout=sum(n*(c['readout_bytes_cap_by_backbone'][b]+log) for b,n in c['readout_workers_by_backbone'].items())
    live=workers+readout+1_000_000+50_000_000+2*log+c['all_source_bytes_cap']+c['controls_bytes_cap']+c['reused_weights_bytes_cap']
    # Future transfer streams directly to native SSD, no additional full local
    # archive. One GB covers local preparation/evidence; all partials counted.
    inclusive=c['live_bytes_cap']+2*c['archive_bytes_cap']+1_000_000_000
    if live>c['live_bytes_cap'] or inclusive>c['inclusive_bytes_cap']:
        raise ValueError('Full future storage reservation exceeds unchanged cap')
    return {'live_reserved_bytes':live,'live_slack_bytes':c['live_bytes_cap']-live,
            'inclusive_full_future_reserved_bytes':inclusive,
            'inclusive_slack_bytes':c['inclusive_bytes_cap']-inclusive,
            'topology':'cluster live + cluster archive + native SSD archive + local preparation; no full Windows staging archive'}

if __name__=='__main__': print(json.dumps({'counts':counts(),'storage':storage_reservations()},indent=2))
