"""Deterministic NEW-root manifest and revised finite workload; no physics."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/world-model-diagnostic-a2-20261004'
STUDY = 'WM-DIAG0-A2-v1'

def stream_seed(task, index, stream):
    value = f'{STUDY}|{task}|root-{index:03d}|{stream}|20261004'
    return int.from_bytes(sha256(value.encode()).digest()[:4], 'big') & 0x7fffffff

def root_plan():
    rows = []
    for task in ('pusht', 'reacher'):
        for i in range(60):
            role = 'diagnostic' if i < 32 else 'readout_fit' if i < 48 else 'readout_validation'
            frame_count = 16 if role == 'readout_fit' else 8 if role == 'readout_validation' else 0
            frames = [10 + (34*j)//(frame_count-1) for j in range(frame_count)] if frame_count else []
            rows.append({'root_id': f'{STUDY}:{task}:root-{i:03d}', 'task': task, 'role': role,
                         'root_index': i, 'status': 'PROPOSED_NOT_GENERATED',
                         'source_action_index': 20, 'goal_action_index': 44,
                         'collection_actions_cap': 44, 'readout_frame_indices': frames,
                         'history_catalog_indices': [10,15,20], 'native_input_indices': [20],
                         'seeds': {s: stream_seed(task,i,s) for s in
                                   ('native_reset','variation','collector','render','bank_lewm',
                                    'bank_dino','tail_1','tail_2','oracle')},
                         'backbones': ['lewm','dinowm_noprop']})
    if len({v for r in rows for v in r['seeds'].values()}) != 120*9:
        raise ValueError('Seed collision in declared namespaces')
    return {'study': STUDY, 'roles': 'WHOLE_NEW_TRAJECTORY', 'protected_historical_inputs': [],
            'replacement_attempts': 0, 'roots': rows}

def counts():
    roots, settings, bank, draws, source, collection = 120, 128, 16, 2, 20, 44
    oracle = settings*bank
    evaluation = oracle*draws
    cem = settings+evaluation
    # Two fixed replay/snapshot equivalence branches for each of four first setting jobs.
    restoration = 8
    # Two same-bank parity calls (cached/chunked vs independent) in each first setting.
    parity_sequences = 4*2*bank
    costs = cem*30+settings+8
    return {'status': 'PROPOSED_NOT_AUTHORIZED', 'source_generation_jobs': roots,
            'source_generated_roots_max': roots, 'collector_steps_max': roots*collection,
            'source_frames_max': roots*(collection+1), 'bank_helper_worlds': settings,
            'oracle_prefix_worlds': oracle, 'evaluation_tail_worlds': evaluation,
            'technical_restoration_worlds': restoration,
            'world_resets_max': roots+settings+oracle+evaluation+restoration,
            'replay_steps_max': (settings+oracle+evaluation+restoration)*source,
            'oracle_steps_max': oracle*25, 'evaluation_steps_max': evaluation*50,
            'all_controller_steps_max': roots*collection+(settings+oracle+evaluation+restoration)*source+oracle*25+evaluation*50,
            'controller_steps_per_task_max': (roots*collection+(settings+oracle+evaluation+restoration)*source+oracle*25+evaluation*50)//2,
            'pusht_integrator_steps_max': ((roots*collection+(settings+oracle+evaluation+restoration)*source+oracle*25+evaluation*50)//2)*10,
            'pusht_reset_internal_integrator_steps_max': (roots+settings+oracle+evaluation+restoration)//2*2,
            'reacher_dm_steps_max': ((roots*collection+(settings+oracle+evaluation+restoration)*source+oracle*25+evaluation*50)//2)*2,
            'reacher_mujoco_substeps': 'Bind compiled timestep and n_sub_steps; dm_control steps are not integrator counts',
            'native_cem_decisions_max': cem, 'native_cem_sequences_max': cem*9000,
            'bank_reforecast_sequences_max': settings*bank,
            'technical_parity_sequences_max': parity_sequences,
            'predicted_macro_sequence_transitions_max': (cem*9000+settings*bank+parity_sequences)*5,
            'cost_api_calls_max': costs,
            'lewm_predictor_batch_calls_max': (cem//2*30+settings//2+4)*5,
            'dino_predictor_chunk_calls_max': (cem//2*30*3+settings//2+4)*5,
            'context_goal_encoder_api_calls_conservative_max': costs*2,
            'context_goal_encoded_frames_conservative_max': costs*2,
            'realized_prefix_encoded_frames_max': oracle*5,
            'readout_fit_frames_all_backbones_max': 4*16*16,
            'readout_validation_frames_all_backbones_max': 4*12*8,
            'gpu_jobs': 128+4, 'cpu_jobs': 120+3, 'successful_logical_tasks_max': 255,
            'gpu_allocation_seconds_proposed_cap': 128*3600+4*1800,
            'cpu_allocation_seconds_proposed_cap': 120*60+1200+3600+1800,
            'all_failures_charged': True, 'automatic_replacements': 0}

def storage():
    parts = {'source_roots':120*12_000_000, 'lewm_parent_results_and_logs':64*11_000_000,
             'dino_parent_results_and_logs':64*61_000_000, 'lewm_readout_and_logs':2*6_000_000,
             'dino_readout_and_logs':2*141_000_000, 'cpu_logs':123*100_000,
             'preflight_analysis_conversion_evidence':60_000_000,
             'original_weights_including_reused_lewm':410_653_018,
             'safe_converted_weights_reserved':410_653_018,
             'isolated_runtime_image_reserved':4_000_000_000,
             'source_closures':20_000_000, 'controls':300_000_000}
    total = sum(parts.values())
    if total > 12_000_000_000: raise ValueError('Full live reservations')
    inclusive = 12_000_000_000+2*14_000_000_000+1_000_000_000
    return {'status':'PROPOSED_NOT_AUTHORIZED','live_members':parts,'live_reserved_bytes':total,
            'live_cap_bytes':12_000_000_000,'archive_cap_bytes':14_000_000_000,
            'inclusive_reserved_bytes':inclusive,'inclusive_cap_bytes':42_000_000_000,
            'preparation_local_and_ssd_copies_within_1GB_future_line':True,
            'downloaded_artifact_bytes':265_958_825,
            'artifact_local_plus_ssd_bytes':2*265_958_825,
            'acquisition_cap_bytes':2*1024**3,'retained_preparation_cap_bytes':5*1024**3,
            'all_partials_counted':True}

def main():
    for name, data in (('ROOT-PLAN.json',root_plan()), ('RESOURCE-PLAN.json',{'counts':counts(),'storage':storage()})):
        with (DOC/name).open('x',encoding='utf8') as f: json.dump(data,f,indent=2)
    print(json.dumps({'counts':counts(),'storage':storage()},indent=2))

if __name__ == '__main__': main()
