"""Preserve exact failed preparation phases and charges; no remote calls."""
import ast,json,sys
from .common import ROOT,DOC,identity,write_new
from wm_diag0_rc1_completion_v1.common import DOC as METER,CAPS,charge

def main():
    label=sys.argv[1];own=METER/('LOCAL-'+label+'.started.json')
    pending=[p for p in METER.glob('LOCAL-*.started.json') if not (METER/p.name.replace('.started.json','.json')).exists()]
    if pending!=[own]:raise ValueError('only own exact pending handoff')
    declaration=json.loads(own.read_text())
    if declaration['component']!='handoff' or declaration['reserved_seconds']!=30:raise ValueError('exact own reservation')
    receipts=[json.loads(p.read_text()) for p in METER.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    charges={k:sum(charge(z) for z in receipts if z['component']==k) for k in CAPS};charges['handoff']+=30
    failed={}
    for name,needle in [('FINALWHOLEBIND001',"NameError: name 'Path' is not defined"),('FINALWHOLEBIND002','[WinError 206]')]:
        p=METER/('LOCAL-'+name+'.json');z=json.loads(p.read_text())
        if z['status']!='CHILD_NONZERO' or needle not in z['stdout']:raise ValueError('saved exact new failure')
        failed[name]={'LOCAL':identity(p),'started':identity(METER/('LOCAL-'+name+'.started.json')),
            'full_reserved_charge_seconds':z['charged_seconds'],'diagnosis':needle}
    if (DOC/'BINDING001.started.json').exists() or (DOC/'BINDING002.json').exists() or (DOC/'BINDING002.failure.json').exists():raise ValueError('never invent remote success/failure')
    if charges['binding_staging']!=1155 or sum(charges.values())>21600:raise ValueError('exact remaining staging authority')
    source={}
    for p in (ROOT/'wm_diag0_rc1_close_v1').glob('*.py'):
        ast.parse(p.read_text(),feature_version=(3,6));source[p.relative_to(ROOT).as_posix()]=identity(p)
    obs=ROOT/'docs/world-model-diagnostic-rc1-recovery-r1-20261016/OBSERVER029.json';z=json.loads(obs.read_text())
    if z['accepted_grid_total']!=124 or z['active_process_records'] or z['faults'] or z['STOP'] is not None or z['GPU_terminal_all_attempts']!=97360:raise ValueError('complete saved experiment snapshot')
    result={'status':'FINALIZATION_SOURCE_PREPARATION_PRESERVED_ACTUAL_ANALYSIS_ARCHIVE_AND_SSD_NOT_STARTED',
        'authority':identity(DOC/'AUTHORITY-001.json'),'source':source,'original_139_terminal_snapshot':identity(obs),
        'retained_failures':failed,'remote_child_result_for_BINDING002':'NONE; native CreateProcess failed before WSL launch',
        'current_charges_including_this_handoff':charges,'total_charged':sum(charges.values()),
        'remaining_components':{k:CAPS[k]-charges[k] for k in CAPS},
        'new_preparation_measurement':identity(DOC/'PREPARATION-MEASUREMENT-001.json'),
        'new_recovery_final_tests':identity(DOC/'ARTIFICIAL-CLOSE-001.json'),
        'new_local_repair_tests':identity(DOC/'BINDING-REPAIR-001.json'),
        'next_technical_change':'New separately versioned transport passes bounded trusted program and JSON over existing SSH stdin, not over Windows command line; retain both failed versions and labels. Test framing and actual CLI before transport.',
        'remaining_actual_gates':'complete root/runtime/terminal/start binding; recovery-aware frozen CPU supervisor/exact dispatch/stage/native tree resources; actual Linux integration; source review/publication/new small SSD; once-only final CPU analysis/second pass/archive/original readback; terminal CPU/sidecars/native SSD; results publication and Pro handoff',
        'human_proposal_only_not_activated':{'transfer_seconds':300,'from_monitoring_cap':7200,'to_monitoring_cap':6900,'new_max_monitor_checks':230,
            'from_binding_staging_cap':1200,'to_binding_staging_cap':1500,'outer_35700_and_future_21600_unchanged':True,
            'science_GPU_time_overall_storage_unchanged':True},
        'actual_final_CPU_analysis_studyarchive_SSD_GitHub_results':False,'parent_scientific_payloads_read':False,'final_gate_ready':False}
    write_new(DOC/'HANDOFF-001.json',result,limit=20000)
    print(json.dumps({'status':result['status'],'remaining_binding_staging':45,'total_charged':sum(charges.values()),'final_gate_ready':False}))

if __name__=='__main__':main()
