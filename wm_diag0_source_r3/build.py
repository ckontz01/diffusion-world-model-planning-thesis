import hashlib,json
from .common import ROOT,DOC,R2,RUN,OLD,identity,write_new

def additions():
    supervisor=(ROOT/'wm_diag0_native_v3/supervisor.py').read_bytes()
    old=b"        binds.append(c['renderer_path']+':/renderer:ro')"
    new=old+b"\n        for name in c['source_recovery']['failed_partial']:\n            original=c['source_recovery']['partial_supplier']+'/'+name\n            binds.append(original+':'+original+':ro')"
    if supervisor.count(old)!=1:raise ValueError('exact reviewed supervisor mount insertion')
    return {'wm_diag0_native_v3/entry.py':(ROOT/'wm_diag0_source_r2/entry.py').read_bytes(),
            'wm_diag0_native_v3/supervisor.py':supervisor.replace(old,new),
            'wm_diag0_source_r2/__init__.py':(ROOT/'wm_diag0_source_r2/__init__.py').read_bytes(),
            'wm_diag0_source_r2/writer.py':(ROOT/'wm_diag0_source_r2/writer.py').read_bytes()}

def bounds(authority,reconciliation):
    a=authority; r=reconciliation
    if (a['exact_failed_job'],a['exact_root'],a['genuinely_failed_replacements_max'],a['successful_roots_to_recompute'])!=('317102','WM-DIAG0-A2-v1:reacher:root-000',1,0):raise ValueError('one exact technical retry authority')
    extra=(a['additional_controller_actions'],a['additional_source_frames'],a['additional_world_resets'],a['additional_Reacher_dm_steps'])
    if extra!=(44,45,1,88) or r['failed_physical_work']!={'controller_actions':44,'world_resets':1,'Reacher_dm_steps':88}:raise ValueError('exact physical increment only')
    if r['CPU_total_with_preflight']+9000>13800:raise ValueError('unchanged CPU full-future cap')
    live=12836395242+r['failed_retained_bytes']
    if live>13000000000:raise ValueError('unchanged all-failure-inclusive storage cap')
    return {'collector_steps_max':5324,'source_frames_max':5445,'world_resets_max':6401,'all_controller_steps_max':386924,'reacher_dm_steps_max':386968}

def main():
    a=json.loads((DOC/'AUTHORITY.json').read_text());r=json.loads((R2/'RECONCILIATION-001.json').read_text())
    fresh=json.loads((DOC/'RECHECK-001.json').read_text())
    if fresh['status']!='EXACT_OLD_ALLOCATIONS_AND_SUPPLIERS_UNCHANGED' or fresh['original_reconciliation']!=identity(R2/'RECONCILIATION-001.json'):raise ValueError('fresh reconciliation')
    physical=bounds(a,r)
    c=json.loads((ROOT/'docs/world-model-diagnostic-a2-campaign-v4-20261015/source-import-r1/CONTRACT.json').read_text())
    c['run']=RUN
    for n,b in additions().items():
        compile(b,n,'exec',dont_inherit=True)
        c['staged_members'][n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    c.update(cpu_charged_before=r['CPU_total_with_preflight'],cpu_full_future_reserved=9000,
             live_full_future_bytes=12836395242+r['failed_retained_bytes'],replacements=1,source_attempts_max=121)
    c['physical_all_attempt_maxima']=physical
    c['source_recovery']={'authority':identity(DOC/'AUTHORITY.json'),'fault':'pretty audit JSON exceeded writer size guard; lossless compact metadata only',
        'old_run':OLD,'failed_job_id':'317102','failed_array_id':'317041','failed_cpu_seconds':13,
        'failed_physical_work':r['failed_physical_work'],'failed_partial':r['failed_partial'],
        'partial_supplier':OLD+'/tasks/reacher-000/output','accepted_suppliers':r['accepted_suppliers'],
        'authorized_indices':list(range(60,120)),'new_native_source_attempts_max':60,'new_genuinely_failed_replacement_attempts_max':1,
        'previously_unstarted_roots':59,'successful_roots_to_recompute':0,'logical_source_roots':120,
        'all_attempt_source_allocations_max':121,'failed_retained_bytes':r['failed_retained_bytes'],
        'old_STOP_and_failed_partials_untouched':True,'reconciliation':identity(R2/'RECONCILIATION-001.json'),
        'fresh_reconciliation':identity(DOC/'RECHECK-001.json'),'old_accepted_outputs_copied_or_recomputed':0,
        'scope':'60-119%1 on gpu06; original root000 arrays must be bit-identical; no other replacement'}
    write_new(DOC/'CONTRACT.json',c)
    print(json.dumps({'contract':identity(DOC/'CONTRACT.json'),'new_source_allocations':60,'failed_replacements':1,
                      'CPU_charged_plus_full_future':c['cpu_charged_before']+9000,'live_full_future':c['live_full_future_bytes'],'physical_maxima':physical,'GPU_authorized':False}))

if __name__=='__main__':main()
