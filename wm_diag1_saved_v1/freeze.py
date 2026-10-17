"""Freeze the complete new specification/source before any derived-result run."""
import ast,json
from .common import ROOT,DOC,PKG,OLD,identity,write_new

DEPENDENCIES=('wm_diag0/__init__.py','wm_diag0/core.py','wm_diag0_rc1_final_v1/__init__.py','wm_diag0_rc1_final_v1/cpu_process_v2.py','wm_diag0_rc1_final_v1/archive_v1.py','wm_diag0_rc1_final_v1/inventory.py')

def payload():
    freeze=json.loads((DOC/'FREEZE.json').read_text());result={}
    for name,physical in freeze['physical_members'].items():
        p=ROOT/physical
        if identity(p)!=freeze['members'][name]:raise ValueError('frozen source/spec/input changed '+name)
        result[name]=p.read_bytes()
    result['FREEZE.json']=(DOC/'FREEZE.json').read_bytes();return result

def main():
    test=json.loads((DOC/'ARTIFICIAL-002.json').read_text())
    if test['status']!='PASSED' or test['tests']!=10:raise ValueError('all new synthetic tests required')
    for name in ('numerics.py','worker_v2.py','tests_v2.py'):
        key='wm_diag1_saved_v1/'+name
        if identity(ROOT/key)!=test['sources'][key]:raise ValueError('tested scientific source changed before freeze')
    operations=json.loads((DOC/'ARTIFICIAL-OPERATIONS-001.json').read_text())
    if operations['status']!='PASSED' or operations['tests']!=6:raise ValueError('new operational negative tests required')
    for name in ('driver.py','stage.py','collect.py','publish.py','final_publish.py','operational_tests.py'):
        key='wm_diag1_saved_v1/'+name
        if identity(ROOT/key)!=operations['sources'][key]:raise ValueError('tested operational source changed before freeze')
    c=json.loads((OLD/'FINAL-CONTRACT-002.json').read_text());physical={}
    for name in DEPENDENCIES:
        p=ROOT/name
        if identity(p)!=c['staged_members'][name]:raise ValueError('unchanged original pure-array/process dependency '+name)
        target=DOC/'runtime-source'/name;write_new(target,p.read_bytes());physical[name]=target.relative_to(ROOT).as_posix()
    for p in PKG.glob('*.py'):physical[p.relative_to(ROOT).as_posix()]=p.relative_to(ROOT).as_posix()
    for name in ('AUTHORITY.json','HUMAN-ADOPTED-INSTRUCTIONS.txt','ACTIVATION.json','ANALYSIS-PLAN.md','INPUT-MANIFEST.json','ARTIFICIAL-002.json','ARTIFICIAL-OPERATIONS-001.json'):
        physical[name]=(DOC/name).relative_to(ROOT).as_posix()
    for name,path in physical.items():
        if name.endswith('.py'):ast.parse((ROOT/path).read_text(encoding='utf8'),feature_version=(3,11))
    for name in ('driver.py','common.py'):
        ast.parse((PKG/name).read_text(),feature_version=(3,6))
    manifest=json.loads((DOC/'INPUT-MANIFEST.json').read_text())
    if len(manifest['parents'])!=128 or manifest['new_numeric_derived_analysis_executed']:raise ValueError('accepted complete pre-result input manifest')
    freeze={'status':'FROZEN_POST_RESULT_DISCOVERY_BEFORE_FIRST_DERIVED_RESULT_PASS','members':{name:identity(ROOT/path) for name,path in physical.items()},'physical_members':physical,
        'formulas_and_ties':identity(DOC/'ANALYSIS-PLAN.md'),'scientific_tests':identity(DOC/'ARTIFICIAL-002.json'),'completed_publication':'4837834b15cffae1fd848108b8737187f4caee06',
        'saved_data_jobs':1,'allocation_wall_seconds':1800,'CPUs':4,'RAM_bytes':8589934592,'GPU_requested':0,'new_model_training_physics_inference_calls':0,
        'new_all_copy_bytes_cap':1000000000,'prospective_new_all_copy_bytes':768000000,'source_spec_manifest_four_copies_reserved_bytes':32000000,'compact_outputs_five_copies_reserved_bytes':500000000,
        'controls_logs_four_copies_reserved_bytes':40000000,'artificial_fixtures_all_copies_reserved_bytes':32000000,'old_monitors_resumed':False,'new_derived_result_computed':False}
    write_new(DOC/'FREEZE.json',freeze)
    write_new(DOC/'PRE-RUN-REVIEW.json',{'status':'FIXED_FOUR_SETTING_SAVED_DATA_SPEC_AND_SOURCE_REVIEWED','freeze':identity(DOC/'FREEZE.json'),
        'scope':'Required accepted subset only; original supplier/RC1 heads/recovery; unchanged pure-array S0; separate authoritative native choices and float64 algebra; fixed A/B-only selectors sealed before outcome joins; complete parent/absorption/clock evidence; source-paired new bootstrap; one CPU job and no model/physics/GPU; immutable originals and small new all-copy preservation.',
        'old_scientific_results_reestimated':False,'new_derived_results_computed':False})
    print(json.dumps({'status':freeze['status'],'freeze':identity(DOC/'FREEZE.json'),'runtime_members':len(physical)}))

if __name__=='__main__':main()
