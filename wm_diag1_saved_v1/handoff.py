"""Compact-result technical reconciliation and final evidence-only publication."""
import json,sys
from pathlib import Path
from .common import ROOT,DOC,BRANCH,identity,write_new
from .freeze import payload
from .publish import git,git_paths
from wm_diag0_preflight_v1.preserve import volume

def audit():
    payload();report=json.loads((DOC/'REPORT-FORMAT-RECEIPT.json').read_text());pub=json.loads((DOC/'SOURCE-PUBLISHED.json').read_text());status=json.loads((DOC/'STATUS002.json').read_text());collected=json.loads((DOC/'COLLECTED.json').read_text())
    out=DOC/'collected/output';members=json.loads((out/'MEMBERS.json').read_text())
    if identity(out/'MEMBERS.json')!=collected['output_seal'] or any(identity(out/name)!=want for name,want in members.items()):raise ValueError('independent complete compact output authentication')
    r=json.loads((out/'DERIVED-RESULTS.json').read_text());resource=json.loads((out/'RESOURCE.json').read_text())
    if r['status']!='ONE_COMPLETE_FIXED_SAVED_DATA_PASS' or len(r['parents'])!=128 or r['all_physical_source_parents']!=64 or len(r['settings'])!=4:raise ValueError('all parents, paired physical population, all settings')
    if r['freeze']!=pub['freeze'] or resource['source']!=json.loads((DOC/'FREEZE.json').read_text())['members']['wm_diag1_saved_v1/worker_v2.py'] or resource['new_derived_result']!=identity(out/'DERIVED-RESULTS.json'):raise ValueError('actual frozen executed worker and derived bytes')
    if status['state']!='COMPLETED' or status['job_id']!='318060' or not resource['no_model_or_simulator_modules_imported'] or r['old_estimator_or_intervals_rerun'] or r['new_model_training_inference_physics_source_collection_GPU_calls']!=0:raise ValueError('one completed saved-only allocation')
    groups={}
    for row in r['parents']:
        key=row['task']+'|'+row['backbone'];groups.setdefault(key,[]).append(row['root_index'])
        selector=out/'controls'/('SELECTORS-'+str(row['setting'])+'-'+str(row['root_index']).zfill(2)+'.json')
        if identity(selector)!=row['new_selector_seal_before_outcome_join']:raise ValueError('retained selector-before-outcome seal')
        for role in ('P0','O0','native','A','B'):
            choice=row['outcomes'][role];candidate=row['candidates'][choice['index']]
            if choice['candidate_id']!=candidate['candidate_id'] or choice['two_outcomes']!=candidate['two_full_budget_outcomes'] or len(choice['two_outcomes'])!=2:raise ValueError('all selected role/candidate/outcome rows reconciled')
    if any(sorted(v)!=list(range(32)) for v in groups.values()):raise ValueError('exact complete source indices')
    text=(DOC/'RESULTS.md').read_text(encoding='utf8')
    if text.count('### pusht / ')+text.count('### reacher / ')!=128 or identity(DOC/'RESULTS.md')!=report['report'] or identity(DOC/'MECHANISM-PROPOSAL.md')!=report['mechanism_proposal']:raise ValueError('all128 formatted parent sections and reviewed conclusion')
    result={'status':'COMPLETE_COMPACT_RESULTS_ALL128_PARENT_TECHNICAL_REVIEW_PASSED','freeze':pub['freeze'],'source_commit':pub['source_commit'],'job_id':'318060','new_CPU_jobs':1,'all_parent_rows':128,'physical_source_parents':64,
        'settings':{k:len(v) for k,v in groups.items()},'report':report['report'],'derived_results':identity(out/'DERIVED-RESULTS.json'),'resource_receipt':identity(out/'RESOURCE.json'),
        'input_arrays_reread_by_this_review':False,'scientific_estimator_or_bootstrap_rerun_by_this_review':False,'whole_study_archive_read_or_copied':False,'no_future_pipeline_or_monitor_launched':True,
        'conclusion':'Common-vector removal alone insufficient on these Reacher banks; candidate-specific correction helps Reacher/DINO, weaker Le-WM and adverse PushT; prefix/absorption qualification; no transferable repair chosen.',
        'report_presentation_fix':'Only four unescaped table labels changed; original formatter report and receipt preserved.'}
    write_new(DOC/'FINAL-TECHNICAL-REVIEW.json',result);print(json.dumps(result))

def seal():
    volume();receipt=json.loads((DOC/'FINAL-SSD-VERIFIED.json').read_text())
    if receipt['status']!='COMPLETE_DISCOVERY_RESULTS_FULL_REMOTE_AND_NEW_SSD_WHOLE_EVERY_MEMBER_VERIFIED' or identity(receipt['archive'])!=receipt['whole']:raise ValueError('actual complete new SSD result package')
    if git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('separate discovery branch')
    names=[p.relative_to(ROOT).as_posix() for p in (DOC/'FINAL-SSD-VERIFIED.json',DOC/'LOCAL-FINALPUBLISH001.json',DOC/'LOCAL-FINALPUBLISH001.started.json')]
    git_paths(['add'],names);git('diff','--cached','--check','--',*names)
    git_paths(['commit','--only','-m','Record verified WM-DIAG1 result backup and completed publication evidence'],names)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH);remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if commit!=remote:raise ValueError('final full remote identity')
    for name in names:
        if git('show',commit+':'+name)!=(ROOT/name).read_bytes():raise ValueError('published exact preservation proof')
    result={'status':'WM_DIAG1_SAVED_COMPLETE_RESULTS_REPORT_BACKUP_AND_FULL_REMOTE_HANDOFF','final_commit':commit,'full_remote_hash':remote,'results_commit':receipt['results_commit'],
        'frozen_source_commit':receipt['source_commit'],'branch':BRANCH,'SSD_results_package':receipt['whole'],'SSD_verification_published_in_final_commit':True,
        'all_parent_rows':128,'old_monitors_remain_paused':True,'future_pipeline_launched':False,'no_new_method_implemented':True}
    destination=Path(receipt['archive']).parent;write_new(DOC/'COMPLETE-HANDOFF.json',result);write_new(destination/'COMPLETE-HANDOFF.json',result)
    if identity(DOC/'COMPLETE-HANDOFF.json')!=identity(destination/'COMPLETE-HANDOFF.json'):raise ValueError('final handoff sidecar native SSD readback')
    print(json.dumps(result))

if __name__=='__main__':
    if sys.argv[1]=='audit':audit()
    elif sys.argv[1]=='seal':seal()
    else:raise ValueError('fixed audit/seal actions')
