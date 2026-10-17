"""Source-bound complete preservation layout; no allocation or archive entry.

Existing executed authorities and retained artificial sources define the inert
alias allowlist. The filesystem being archived never defines its own approval.
Fresh inventory_v3 traversal/content authentication is still required. Pure
POSIX paths are intentional: local Windows preparation must not reinterpret
cluster roots or resolve any alias target.
"""
import ast,copy,json
from pathlib import PurePosixPath
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new
from .inventory_v3 import safe_name,alias_literal
from .runtime_alias_binding_v1 import bind as runtime_aliases

GRID={'bytes':157676,'sha256':'da2766c3f8c33266ee54cea9fb2e3bdf650046e9a61ac39c209816f1b1e7514b'}
METADATA_SHA='4bbe9eb2b1468a6f0866f7ddffa5783e8966c39f5ec512acfb52042ee5788cc5'
OLD_ARTIFICIAL='campaign-v4-rc1-final-v1-artificial-ONE'
NEW_ARTIFICIAL='campaign-v4-rc1-final-v2-artificial-ONE'
FINAL='campaign-v4-rc1-final-v2'
OLD_ENTRY={'bytes':6841,'sha256':'b13284f2d9c295d43546a79614d300a6f38eee1dae4bba172e5f2b68598271ea'}
NEW_ENTRY={'bytes':6869,'sha256':'7b6ca72784c9c6ef7eac1ab64bd09b2cda463d230f2ddb898675216165fa8e7a'}
NEW_FIXTURE_ALIASES={'runtime/bin/python':'/opt/conda/bin/python','runtime/bin/python3':'python',
                     'runtime/lib64':'lib','runtime/up':'../not-read'}


def absolute(value):
    if not isinstance(value,str) or not value or len(value.encode('utf8'))>4096 or any(c in value for c in ('\x00','\n','\r','\\')):
        raise ValueError('bounded canonical original POSIX path')
    p=PurePosixPath(value)
    if not p.is_absolute() or '..' in p.parts or str(p)!=value or value=='/':raise ValueError('exact absolute POSIX path, never resolved')
    return p


def beneath(path,root):
    return path==root or root in path.parents


def check_paths(layout):
    if set(layout)!={'study_base','approved_children_before_final','approved_children_with_final','root_paths',
                     'approved_inert_alias_literals','final_run','analysis_task','operational_root','archive_path',
                     'supervisor_log','submission_control_root','cpu_control_root','postarchive_control_root','sidecar_root'}:
        raise ValueError('complete exact preservation layout schema')
    base=absolute(layout['study_base']);final=base/FINAL
    if layout['final_run']!=str(final) or layout['analysis_task']!=str(final/'tasks/analysis-0'):
        raise ValueError('one new separately versioned final CPU root, not the grid root')
    old=layout['approved_children_before_final'];new=layout['approved_children_with_final']
    if not isinstance(old,list) or len(old)!=19 or old!=sorted(set(old)) or FINAL in old or new!=sorted(old+[FINAL]):
        raise ValueError('all19 retained canonical lineages plus one future final root')
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


def build(c,m,old_receipt,new_started,new_receipt):
    if m['grid_contract']!=GRID:raise ValueError('executed fixed grid contract unchanged')
    base=absolute(c['run']).parent
    if base.name!='wm-diag0-a2-20261015' or c['run']!=str(base/'campaign-v4-rc1-grid-v1'):
        raise ValueError('exact current study/grid, never an obsolete controller')
    if len(m['canonical_children'])!=18 or any(x['root']!=str(base/n) for n,x in m['canonical_children'].items()):
        raise ValueError('authenticated historical complete18-root metadata')
    if old_receipt['local_entry_source']!=OLD_ENTRY or old_receipt['run']!=str(base/OLD_ARTIFICIAL) or not old_receipt['actual_POSIX_relative_alias_roundtrip']:
        raise ValueError('original artificial alias source and accepted fixture lineage')
    if new_started['source']!=NEW_ENTRY or new_started['remote']!=str(base/NEW_ARTIFICIAL) or new_receipt['root']!=str(base/NEW_ARTIFICIAL):
        raise ValueError('new artificial alias source and exact exclusive root')
    if new_receipt['status']!='ACTUAL_POSIX_INERT_ABSOLUTE_PARENT_CHAIN_DIRECTORY_ALIAS_ROUNDTRIP_PASSED' or new_receipt['whole_root_future_reservation_bytes']!=1000000:
        raise ValueError('actual artificial receipt, not production readiness')
    if m['canonical_children'][OLD_ARTIFICIAL]['aliases_metadata_only_candidates']!={'fixtures/study/old/alias':'tensor.bin'}:
        raise ValueError('original artificial metadata exactly matches authenticated source literal')
    children=sorted(list(m['canonical_children'])+[NEW_ARTIFICIAL])
    roots={'study/'+n:str(base/n) for n in children+[FINAL]}
    roots.update({'runtime/venv':c['venv'],'runtime/container.sif':c['sif'],
                  'objects/lewm-pusht.ckpt':c['lewm']['pusht']['path'],'objects/lewm-reacher.ckpt':c['lewm']['reacher']['path']})
    aliases=runtime_aliases(c,m)
    aliases['study/'+OLD_ARTIFICIAL+'/fixtures/study/old/alias']='tensor.bin'
    aliases.update({'study/'+NEW_ARTIFICIAL+'/fixtures/'+name:target for name,target in NEW_FIXTURE_ALIASES.items()})
    ops=base.parent/(base.name+'-rc1-preservation-v2')
    result={'study_base':str(base),'approved_children_before_final':children,'approved_children_with_final':sorted(children+[FINAL]),
            'root_paths':roots,'approved_inert_alias_literals':aliases,'final_run':str(base/FINAL),
            'analysis_task':str(base/FINAL/'tasks/analysis-0'),'operational_root':str(ops),
            'archive_path':str(ops/'archive/final-study.tar'),'supervisor_log':str(ops/'cpu/supervisor.log'),
            'submission_control_root':str(ops/'submission'),'cpu_control_root':str(ops/'cpu/controls'),
            'postarchive_control_root':str(ops/'postarchive/controls'),'sidecar_root':str(ops/'sidecars')}
    return check_paths(result)


def main():
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    paths={'grid':ROOT/'docs/world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json',
           'metadata':doc/'METADATA-001.json','old_receipt':ROOT/'docs/world-model-diagnostic-rc1-final-v1-20261016/ARTIFICIAL-CLUSTER-ONE.json',
           'new_started':doc/'ARTIFICIAL-POSIX-001.started.json','new_receipt':doc/'ARTIFICIAL-POSIX-001.json',
           'old_source':ROOT/'wm_diag0_rc1_final_v1/cluster_preservation_test_v1.py','new_source':ROOT/'wm_diag0_rc1_final_v2/cluster_alias_test.py'}
    if identity(paths['grid'])!=GRID or identity(paths['metadata'])['sha256']!=METADATA_SHA or identity(paths['old_source'])!=OLD_ENTRY or identity(paths['new_source'])!=NEW_ENTRY:
        raise ValueError('actual immutable contract/metadata/tested fixture source identities required')
    c,m,old,start,new=[json.loads(paths[n].read_text()) for n in ('grid','metadata','old_receipt','new_started','new_receipt')]
    layout=build(c,m,old,start,new)
    # Do not import/execute either fixture's CODE; only authenticate its exact
    # retained source bytes. Fresh inventory must reject every unknown literal.
    for role in ('archive_path','supervisor_log','cpu_control_root','postarchive_control_root','sidecar_root','operational_root'):
        bad=copy.deepcopy(layout);bad[role]=str(absolute(layout['final_run'])/'self-recursion')
        try:check_paths(bad)
        except ValueError:pass
        else:raise AssertionError('recursive operational role accepted')
    for mutate in ('drop_child','drop_model','duplicate_root','unknown_alias','move_final'):
        bad=copy.deepcopy(layout)
        if mutate=='drop_child':bad['approved_children_before_final'].remove(OLD_ARTIFICIAL)
        if mutate=='drop_model':bad['root_paths'].pop('objects/lewm-reacher.ckpt')
        if mutate=='duplicate_root':bad['root_paths']['runtime/venv']=bad['root_paths']['study/native-v3']
        if mutate=='unknown_alias':bad['approved_inert_alias_literals']['study/native-v3/new']='outside'
        if mutate=='move_final':bad['final_run']=c['run']
        try:check_paths(bad)
        except ValueError:pass
        else:raise AssertionError('invalid complete layout accepted: '+mutate)
    for p in (ROOT/'wm_diag0_rc1_final_v2/preservation_layout_v1.py',):ast.parse(p.read_text(),feature_version=(3,6))
    result={'status':'SOURCE_BOUND_COMPLETE_ROOT_ALIAS_AND_DISJOINT_CONTROL_LAYOUT_PREPARATION_ONLY',
            'source':identity(__file__),'evidence':{n:identity(p) for n,p in paths.items()},'layout':layout,
            'final_artificial_whole_root_reservation_bytes':4000000,'all_new_auxiliary_all_logical_copy_reservation_bytes':64000000,
            'production_required_implementations':{'inventory':'inventory_v3','owned_CPU_cleanup':'cpu_process_v2','native_receiver':'native_transfer_v3'},
            'fresh_current_root_member_alias_content_authentication_performed':False,'fresh_full_future_storage_proof_passed':False,
            'operational_controls_in_archive_inputs':False,'alias_targets_followed_or_executed':False,
            'checks':['19retained plus future final whole root','full external venv/SIF/two objects','all30 inert literals source-bound',
                      'all operational/archive/postarchive roles disjoint','missing root/model, overlap, extra alias and recursion rejected'],
            'network_calls':0,'scheduler_calls':0,'research_calls':0,'actual_final_source_frozen_or_published':False,'final_gate_ready':False}
    write_new(doc/'PRESERVATION-LAYOUT-001.json',result,limit=32000)
    print(json.dumps({'status':result['status'],'retained_roots':19,'roots_with_future_final':20,'inert_aliases':30,
                      'fresh_current_staging_passed':False,'actual_archive_or_allocation_run':False}))


if __name__=='__main__':main()
