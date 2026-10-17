from pathlib import PurePosixPath
from wm_diag0_rc1_final_v2.preservation_layout_v1 import absolute,beneath,FINAL
from wm_diag0_rc1_final_v2.inventory_v3 import safe_name,alias_literal
def check_paths(layout):
    if set(layout)!={'study_base','approved_children_before_final','approved_children_with_final','root_paths',
                     'approved_inert_alias_literals','final_run','analysis_task','operational_root','archive_path',
                     'supervisor_log','submission_control_root','cpu_control_root','postarchive_control_root','sidecar_root'}:
        raise ValueError('complete exact preservation layout schema')
    base=absolute(layout['study_base']);final=base/FINAL
    if layout['final_run']!=str(final) or layout['analysis_task']!=str(final/'tasks/analysis-0'):
        raise ValueError('one new separately versioned final CPU root, not the grid root')
    old=layout['approved_children_before_final'];new=layout['approved_children_with_final']
    if not isinstance(old,list) or len(old)!=21 or old!=sorted(set(old)) or FINAL in old or new!=sorted(old+[FINAL]):
        raise ValueError('all21 retained canonical lineages plus one future final root')
    for n in new:safe_name(n)
    roots=layout['root_paths']
    if not isinstance(roots,dict) or set(roots)!={'study/'+n for n in new}|{'runtime/venv','runtime/container.sif','objects/lewm-pusht.ckpt','objects/lewm-reacher.ckpt'}:
        raise ValueError('every complete lineage/runtime/model root represented exactly once')
    for n in new:
        if roots['study/'+n]!=str(base/n):raise ValueError('whole canonical child, no success-only subroot')
    physical=[absolute(p) for p in roots.values()]
    if any(a!=b and (beneath(a,b) or beneath(b,a)) for a in physical for b in physical) or len(set(physical))!=len(physical):
        raise ValueError('explicit physically disjoint whole roots; no overlap or copy discount')
    ops=base.parent/(base.name+'-rc1-preservation-v2')
    expected={'operational_root':ops,'archive_path':ops/'archive/final-study.tar',
              'supervisor_log':ops/'cpu/supervisor.log','submission_control_root':ops/'submission',
              'cpu_control_root':ops/'cpu/controls','postarchive_control_root':ops/'postarchive/controls',
              'sidecar_root':ops/'sidecars'}
    for role,want in expected.items():
        actual=absolute(layout[role])
        if actual!=want or any(beneath(actual,root) or beneath(root,actual) for root in physical):
            raise ValueError('all operational/archive/postarchive logs and controls outside ALL inputs')
    aliases=layout['approved_inert_alias_literals']
    if not isinstance(aliases,dict) or len(aliases)!=30:raise ValueError('exact25 production plus five source-bound artificial aliases')
    for name,target in aliases.items():
        safe_name(name);alias_literal(target)
        if not any(name.startswith(root+'/') for root in roots):raise ValueError('alias belongs to explicit whole root')
    return layout
