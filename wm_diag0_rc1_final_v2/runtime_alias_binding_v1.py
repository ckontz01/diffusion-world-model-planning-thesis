"""Existing frozen runtime/renderer alias authority matched to historical metadata.

No alias target is resolved, followed, created or executed. This approves only
inert preservation of already-executed contract literals, NOT new execution.
Fresh full-runtime/content/whole-root staging remains mandatory.
"""
import ast,copy,json
from pathlib import Path,PurePosixPath
from .inventory_v3 import safe_name,alias_literal
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def bind(c,m):
    if m['grid_contract']!={'bytes':157676,'sha256':'da2766c3f8c33266ee54cea9fb2e3bdf650046e9a61ac39c209816f1b1e7514b'}:raise ValueError('same executed contract identity')
    if m['full_venv']['root']!=c['venv'] or m['full_venv']['aliases_metadata_only_candidates']!=c['runtime_symlinks']:
        raise ValueError('exact externally approved runtime literals, no learned allowlist')
    renderer=PurePosixPath(c['renderer_path']);native=m['canonical_children']['native-v3']
    prefix=renderer.relative_to(PurePosixPath(native['root'])).as_posix()
    if prefix!='renderer-r6' or len(c['renderer']['aliases'])!=21:raise ValueError('actual accepted original renderer root and alias count')
    expected={prefix+'/'+safe_name(name):alias_literal(target) for name,target in c['renderer']['aliases'].items()}
    if native['aliases_metadata_only_candidates']!=expected:raise ValueError('every renderer literal exactly matches existing frozen approval')
    aliases={'runtime/venv/'+safe_name(name):alias_literal(target) for name,target in c['runtime_symlinks'].items()}
    aliases.update({'study/native-v3/'+name:target for name,target in expected.items()})
    if len(aliases)!=25:raise ValueError('exact four runtime plus21renderer aliases')
    return aliases


def main():
    ast.parse(Path(__file__).read_text(),feature_version=(3,6))
    grid=ROOT/'docs/world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json'
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016';metadata=doc/'METADATA-001.json'
    if identity(grid)!={'bytes':157676,'sha256':'da2766c3f8c33266ee54cea9fb2e3bdf650046e9a61ac39c209816f1b1e7514b'} or identity(metadata)['sha256']!='4bbe9eb2b1468a6f0866f7ddffa5783e8966c39f5ec512acfb52042ee5788cc5':raise ValueError('published executed contract and exact retained metadata snapshot')
    c=json.loads(grid.read_text());m=json.loads(metadata.read_text());aliases=bind(c,m)
    for target in ('wrong','../different'):
        bad=copy.deepcopy(m);bad['full_venv']['aliases_metadata_only_candidates']['bin/python']=target
        try:bind(c,bad)
        except ValueError:pass
        else:raise AssertionError('changed runtime target must stop')
    bad=copy.deepcopy(m);bad['canonical_children']['native-v3']['aliases_metadata_only_candidates'].pop('renderer-r6/libOSMesa.so.6')
    try:bind(c,bad)
    except ValueError:pass
    else:raise AssertionError('missing chained renderer alias must stop')
    bad=copy.deepcopy(m);bad['canonical_children']['native-v3']['aliases_metadata_only_candidates']['renderer-r6/extra']='lib'
    try:bind(c,bad)
    except ValueError:pass
    else:raise AssertionError('unknown extra alias must stop')
    result={'status':'EXISTING_FROZEN_25_RUNTIME_RENDERER_ALIASES_MATCH_HISTORICAL_METADATA_NOT_FINAL_GATE',
            'executed_grid_contract':identity(grid),'metadata_snapshot':identity(metadata),'source':identity(__file__),
            'approved_inert_preservation_literals':aliases,'external_venv_archive_label':'runtime/venv',
            'external_venv_root':c['venv'],'renderer_within_whole_study_root':'study/native-v3/renderer-r6',
            'authority_basis':'existing executed GRID-CONTRACT runtime_symlinks and renderer.aliases, NOT discovery/self-declared approval',
            'target_resolution_following_creation_execution_performed':False,
            'checks':['four runtime literals exact','21renderer literals exact including chains','wrong missing extra literal rejection'],
            'artificial_lineage_aliases_still_require_separate_source_bound_allowlist':True,
            'fresh_current_alias_content_root_member_staging_still_required':True,
            'scheduler_calls':0,'network_calls':0,'research_calls':0,'scientific_values_read':False,
            'actual_runtime_ready_or_final_gate_passed':False,'final_gate_ready':False}
    write_new(doc/'RUNTIME-ALIASES-001.json',result,limit=12000)
    print(json.dumps({'status':result['status'],'inert_aliases':len(aliases),'fresh_current_staging_passed':False,'research_calls':0}))


if __name__=='__main__':main()
