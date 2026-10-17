"""Honor repository archive ignores; preserve tiny fixture in SSD, not force-add."""
from .common import DOC,write_new
from .build import derive
def main():
    p='wm_diag0_rc1_close_v1/'
    after="""    ignored='docs/world-model-diagnostic-rc1-final-close-v1-20261017/artificial-native-finish-001/tiny.tar'
    if ignored not in delta:raise ValueError('exact newly generated ignored tiny fixture')
    fixture=json.loads((DOC/'ARTIFICIAL-NATIVE-FINISH-001.json').read_text())
    if delta[ignored]!=fixture['tiny_archive']:raise ValueError('known tested tiny artifact identity')
    git_names=[n for n in delta if n!=ignored]
    git('add','--',*git_names);git('diff','--cached','--check','--',*git_names)"""
    result=derive(p+'publication_delta_v4.py',p+'publication_delta_v5.py',[
        ("if (DOC/'PUBLICATION-DELTA-004.started.json').exists():raise FileExistsError('exclusive source delta publication')",
         "if (DOC/'PUBLICATION-DELTA-005.started.json').exists():raise FileExistsError('exclusive source delta publication')\n    failure=ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/LOCAL-FINALPUBLICATIONDELTA004.json'\n    old=json.loads(failure.read_text())\n    if old['status']!='CHILD_NONZERO' or 'following paths are ignored' not in old['stdout']:raise ValueError('exact precommit Git-ignore stop')"),
        ("write_new(DOC/'PUBLICATION-DELTA-004.started.json'","write_new(DOC/'PUBLICATION-DELTA-005.started.json'"),
        ("git('add','--',*delta);git('diff','--cached','--check','--',*delta)",after),
        ("'--',*delta)\n    commit=", "'--',*git_names)\n    commit="),
        ("payload={n:git('show',commit+':'+n) for n in delta}","payload={n:((ROOT/n).read_bytes() if n==ignored else git('show',commit+':'+n)) for n in delta}"),
        ("'actual_study_SSD_gate':False,'old_source_package_recopied':False", "'actual_study_SSD_gate':False,'old_source_package_recopied':False,'repository_ignored_tiny_fixture_preserved_in_SSD_not_force_added':ignored")])
    write_new(DOC/'GIT-IGNORE-DISPOSITION-005.json',{'status':'RESPECT_REPOSITORY_IGNORE_PRESERVE_TEST_ARCHIVE_IN_SOURCE_SSD','new_publication_source':result,
        'frozen_scientific_or_controller_source_changed':False,'gitignore_changed_or_force_added':False,'ignored_fixture_bytes_are_not_omitted_from_SSD_or_final_archive':True})
    print('Source delta publication adapter ready')
if __name__=='__main__':main()
