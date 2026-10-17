"""Seal final handoff after actual SSD, GitHub publication and monitor pause."""
import json,subprocess,tomllib
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .publish_results_v1 import git,git_paths,BRANCH
from wm_diag0_preflight_v1.preserve import volume

def main():
    pub=json.loads((DOC/'RESULTS-PUBLISHED-001.json').read_text());gate=json.loads((DOC/'FINAL-SSD-VERIFIED.json').read_text())
    ssd=Path(gate['archive']).parent;review=json.loads((DOC/'REPORT-REVIEW-001.json').read_text())
    config=tomllib.loads(Path('C:/Users/Chris/.codex/automations/monitor-wm-diag0-rc1-and-recover-technical-faults/automation.toml').read_text(encoding='utf8'))
    if config['id']!='monitor-wm-diag0-rc1-and-recover-technical-faults' or config['status']!='PAUSED':raise ValueError('same completed monitor paused with history retained')
    for name in ('FINAL-SSD-VERIFIED.json','RESULTS-PUBLISHED-001.json'):
        if identity(DOC/name)!=identity(ssd/name):raise ValueError('actual matching host/SSD completion controls')
    if pub['status']!='COMPLETE_VALIDATED_RESULTS_PUBLISHED_GITHUB_FULL_REMOTE_AND_SMALL_SSD_REPORT_VERIFIED' or pub['commit']!=pub['remote_full_hash']:raise ValueError('complete published result readback')
    if review['report']!=identity(DOC/'PRO-RESULTS-HANDOFF.txt') or review['results']!=identity(DOC/'RESULTS.json'):raise ValueError('reviewed exact complete results/report')
    if identity(pub['small_report_SSD_archive'])!=pub['small_report_SSD_whole'] or identity(pub['postarchive_native_test_SSD_archive'])!=pub['postarchive_native_test_whole']:raise ValueError('same verified small SSD packages')
    if Path(gate['archive']).lstat().st_size!=gate['whole']['bytes']:raise ValueError('same full study archive size')
    volume()
    if git('rev-parse','HEAD').decode().strip()!=pub['commit'] or git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]!=pub['commit']:raise ValueError('expected actual published predecessor')
    base='https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/'+pub['commit']+'/'
    result={'status':'WM_DIAG0_A2_RC1_COMPLETE_VALIDATED_PRESERVED_PUBLISHED_AND_MONITOR_PAUSED',
        'ordinary_runs_accepted':124,'task_backbone_parent_evaluations':128,'independent_diagnostic_source_parents_shared_across_backbones':64,
        'source_roots':120,'retained_fits':6,'active_heads':4,'all_allocated_GPU_attempts_including_failures':139,
        'scientific_results_commit':pub['commit'],'report_URL':base+pub['report_path'],'results_URL':base+pub['results_path'],
        'report':identity(DOC/'PRO-RESULTS-HANDOFF.txt'),'results':identity(DOC/'RESULTS.json'),'acceptance':identity(DOC/'ACCEPTANCE.json'),
        'report_review':identity(DOC/'REPORT-REVIEW-001.json'),'final_study_SSD_gate':identity(DOC/'FINAL-SSD-VERIFIED.json'),
        'study_archive':gate['archive'],'study_archive_whole':gate['whole'],'Pro_upload_bundle':pub['small_report_SSD_archive'],
        'Pro_upload_bundle_whole':pub['small_report_SSD_whole'],'monitor_id':config['id'],'monitor_status':'PAUSED','monitor_history_retained':True,
        'successful_research_repeated':False,'new_experiment_or_science_change':False,'Pro_message_sent_automatically':False,
        'external_peer_review_claimed':False,'unrelated_work_committed':False}
    write_new(DOC/'FINAL-HANDOFF.json',result);write_new(ssd/'FINAL-HANDOFF.json',result)
    history=ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016'
    paths=[DOC/'FINAL-HANDOFF.json',DOC/'RESULTS-PUBLISHED-001.json',history/'CONTINUATION-023.txt',history/'LOCAL-FINALRESULTSPUBLISH001.json',ROOT/'wm_diag0_rc1_close_v1/complete_handoff_v1.py']
    names=[p.relative_to(ROOT).as_posix() for p in paths]
    git_paths(['add'],names);git('diff','--cached','--check','--',*names)
    git_paths(['commit','--only','-m','Seal final RC1 results handoff and paused-monitor completion'],names)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('final handoff full remote hash')
    pushed={'status':'FINAL_HANDOFF_PUSH_FULL_REMOTE_VERIFIED_MONITOR_PAUSED','handoff_commit':commit,'remote_full_hash':remote,
        'scientific_results_commit':pub['commit'],'handoff':identity(DOC/'FINAL-HANDOFF.json'),'final_SSD_gate':identity(DOC/'FINAL-SSD-VERIFIED.json')}
    write_new(DOC/'HANDOFF-PUSH-VERIFIED.json',pushed);write_new(ssd/'HANDOFF-PUSH-VERIFIED.json',pushed)
    print(json.dumps(dict(result,final_handoff_commit=commit)))

if __name__=='__main__':main()
