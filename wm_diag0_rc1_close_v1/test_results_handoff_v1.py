"""Tiny synthetic report and ordinary local Git path-isolation regression."""
import hashlib,json,subprocess
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from . import report_v1,publish_results_v1

def main():
    fixture=DOC/'artificial-results-handoff-001'
    fixture.mkdir(exist_ok=False)
    native=fixture/'synthetic-SSD';native.mkdir()
    def write(p,v):
        with p.open('xb') as out:out.write((json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
    gate={'status':'COMPLETE_STUDY_INDEPENDENT_ACCEPTANCE_AND_FINAL_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_GATE_PASSED',
        'archive':str(native/'SYNTHETIC-NOT-STUDY.tar'),'terminal_CPU_job':'SYNTHETIC-NOT-SCHEDULER',
        'contract':{'bytes':1,'sha256':'a'*64},'source_commit':'SYNTHETIC-NOT-PUBLISHED','whole':{'bytes':0,'sha256':'b'*64}}
    write(fixture/'FINAL-SSD-VERIFIED.json',gate);write(native/'FINAL-SSD-VERIFIED.json',gate)
    contrasts={k:{'mean':0.,'ci95_percentile':[-.1,.1],'gains':0,'losses':0,'ties':32} for k in ('O0-P0','P1-P0','O1-O0','interaction')}
    group={'n_independent_parents':32,'cells':dict.fromkeys(('P0','P1','O0','O1'),.5),
        'cell_ci95':{k:[.25,.75] for k in ('P0','P1','O0','O1')},'native_reference':.5,'initial_success_count':0,
        'hindsight_optimistic_parent':[.5]*32,'split_draw_hindsight_parent':[.5]*32,'contrasts':contrasts}
    result={'settings':{str(k):group for k in range(4)},'pooled_by_backbone':{'synthetic':group},'head_quality':{'fixture':'NOT SCIENTIFIC DATA'},'limitations':['SYNTHETIC FIXTURE ONLY']}
    acceptance={'status':'ALL120_SOURCES_6_RETAINED_FITS_4_ACTIVE_HEADS_128_PARENTS_INDEPENDENTLY_ACCEPTED','parent_output_seals':dict.fromkeys(map(str,range(128)),{})}
    write(fixture/'RESULTS.json',result);write(fixture/'ACCEPTANCE.json',acceptance)
    write(fixture/'RESULTS-RELEASED.json',{'final_gate':identity(fixture/'FINAL-SSD-VERIFIED.json'),'RESULTS':identity(fixture/'RESULTS.json'),'ACCEPTANCE':identity(fixture/'ACCEPTANCE.json')})
    original=report_v1.DOC
    try:
        report_v1.DOC=fixture;report_v1.main()
        text=(fixture/'PRO-RESULTS-HANDOFF.txt').read_text(encoding='utf8')
        assert 'Those 128 evaluations are not 128 independent source parents' in text and 'SYNTHETIC FIXTURE ONLY' in text
        assert text.count('gains/losses/ties=')==16
    finally:report_v1.DOC=original
    repo=fixture/'git-fixture';repo.mkdir()
    def git(*args,**options):
        return subprocess.check_output(['git','-c','core.autocrlf=false','-c','user.name=Artificial fixture','-c','user.email=fixture@example.invalid',*args],cwd=repo,timeout=15,**options)
    git('init','-q')
    for name in ('selected evidence.txt','unrelated user.txt'):
        with (repo/name).open('xb') as out:out.write(b'INITIAL SYNTHETIC FILE\n')
    git('add','--','selected evidence.txt','unrelated user.txt');git('commit','-q','-m','synthetic base')
    with (repo/'selected evidence.txt').open('wb') as out:out.write(b'NEW SELECTED SYNTHETIC EVIDENCE\n')
    with (repo/'unrelated user.txt').open('wb') as out:out.write(b'UNRELATED STAGED USER FIXTURE\n')
    git('add','--','unrelated user.txt')
    payload=b'selected evidence.txt\0'
    git('add','--pathspec-from-file=-','--pathspec-file-nul',input=payload)
    git('commit','-q','--only','-m','synthetic explicit-only publication','--pathspec-from-file=-','--pathspec-file-nul',input=payload)
    assert git('show','HEAD:unrelated user.txt')==b'INITIAL SYNTHETIC FILE\n'
    assert git('diff','--cached','--name-only').decode().strip()=='unrelated user.txt'
    assert git('show','HEAD:selected evidence.txt')==b'NEW SELECTED SYNTHETIC EVIDENCE\n'
    proof={'status':'NEW_SYNTHETIC_COMPLETE_REPORT_AND_EXPLICIT_GIT_PATH_ISOLATION_PASSED',
        'source':identity(__file__),'report_source':identity(ROOT/'wm_diag0_rc1_close_v1/report_v1.py'),
        'publisher_source':identity(ROOT/'wm_diag0_rc1_close_v1/publish_results_v1.py'),
        'report':identity(fixture/'PRO-RESULTS-HANDOFF.txt'),'synthetic_only':True,'actual_research_or_SSD_or_network_reads':False,
        'unrelated_staged_fixture_preserved_not_committed':True,'actual_final_gates_claimed':False}
    write_new(DOC/'ARTIFICIAL-RESULTS-HANDOFF-001.json',proof);print(json.dumps(proof))

if __name__=='__main__':main()
