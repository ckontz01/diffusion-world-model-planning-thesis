"""Fixed recovery-aware CPU-only commands; original V2 cleanup/clock retained."""
from wm_diag0_rc1_final_v2.cpu_schedule_v2 import CPU_V2,PhaseClock
from wm_diag0_rc1_final_v2.cpu_schedule_v1 import moment,prospective_cpu_environment as original_environment
from .layout import check_paths

def prospective_cpu_environment(parent,source):
    env=original_environment(parent,source)
    for key in ('SLURM_JOB_ID','SLURM_CPUS_PER_TASK','SLURM_MEM_PER_NODE','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST'):
        if key in parent:env['APPTAINERENV_'+key]=parent[key]
    return env

def prospective_analysis_argv(c,layout,expected,phase,deadline):
    check_paths(layout);moment(deadline)
    if phase not in ('analysis','independent_acceptance'):raise ValueError('fixed two analysis roles')
    source=layout['final_run']+'/source';task=layout['analysis_task']
    cmd=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',source]
    for p in sorted({layout['study_base'],source,c['venv'],c['renderer_path']}|{x['path'] for x in c['lewm'].values()}):cmd+=['--bind',p+':'+p+':ro']
    cmd+=['--bind',c['renderer_path']+':/renderer:ro','--bind',task+':'+task+':rw','--bind',task+'/tmp:/tmp:rw',c['sif'],c['venv']+'/bin/python','-B']
    cmd+=['-m','wm_diag0_rc1_close_v1.analysis' if phase=='analysis' else 'wm_diag0_rc1_close_v1.validate_entry',
          source+'/FINAL-CONTRACT.json',expected,task]
    if phase!='analysis':cmd+=[str(deadline)]
    return cmd
