"""Publish the complete discovery report and a small new-results-only SSD delta."""
import json,subprocess
from pathlib import Path
from .common import ROOT,DOC,PKG,BRANCH,identity,write_new
from .publish import git,git_paths,source_files,zip_verified
from .freeze import payload
from wm_diag0_preflight_v1.preserve import volume

def main():
    if (DOC/'FINAL-PUBLICATION.started.json').exists():raise FileExistsError('never duplicate publication or backup')
    payload();collected=json.loads((DOC/'COLLECTED.json').read_text());report=json.loads((DOC/'REPORT-RECEIPT.json').read_text());pub=json.loads((DOC/'SOURCE-PUBLISHED.json').read_text())
    if collected['status']!='ONE_COMPLETE_SAVED_DATA_PASS_NEW_PACKAGE_WHOLE_EVERY_MEMBER_VERIFIED' or report['all_parent_rows']!=128 or identity(DOC/'RESULTS.md')!=report['report']:raise ValueError('complete independently read-back discovery report required')
    if git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('separate discovery branch')
    volume();paths=[p for p in source_files() if p.name not in ('SAVED-DATA-PACKAGE.zip','SAVED-DATA-PACKAGE.partial')]
    selected=[]
    for p in paths:
        name=p.relative_to(ROOT).as_posix();check=subprocess.run(['git','check-ignore','-q','--',name],cwd=ROOT)
        if check.returncode==1:selected.append(name)
        elif check.returncode!=0:raise ValueError('Git ignore check')
    members={p.relative_to(ROOT).as_posix():p.read_bytes() for p in paths if p.relative_to(ROOT).as_posix() not in pub['source_all_members'] and not p.name.endswith('.zip')}
    if sum(map(len,members.values()))>100000000:raise ValueError('small new result/control/report delta')
    all_sizes=sum(p.stat().st_size for p in source_files())
    runtime_bytes=sum(map(len,payload().values()))
    output_bytes=sum(p.stat().st_size for p in (DOC/'collected').rglob('*') if p.is_file())
    # Count all local files; remote source/output+ZIP; both SSD packages;
    # full raw new-tree sizes in Git objects and GitHub; explicit control margin.
    prospective=all_sizes*3+runtime_bytes+2*output_bytes+pub['whole']['bytes']+sum(map(len,members.values()))+10000000
    if prospective>1000000000:raise ValueError('all new logical copies do not fit')
    review={'status':'COMPLETE_NEW_DISCOVERY_RESULTS_READY_FOR_PUBLICATION','source_commit':pub['source_commit'],'freeze':pub['freeze'],'report':report['report'],
        'all_new_copy_conservative_bytes':prospective,'local_new_tree_bytes':all_sizes,'remote_source_bytes':runtime_bytes,'remote_compact_output_and_package_allowance':2*output_bytes,
        'Git_and_GitHub_each_full_raw_local_new_tree_counted':True,'SSD_source_package':pub['whole'],'old_study_archive_recreated_or_copied':False,'new_research_work':0,'future_pipeline_launched':False}
    write_new(DOC/'FINAL-PUBLICATION.started.json',review);selected.append((DOC/'FINAL-PUBLICATION.started.json').relative_to(ROOT).as_posix())
    git_paths(['add'],selected)
    for i in range(0,len(selected),15):git('diff','--cached','--check','--',*selected[i:i+15])
    git_paths(['commit','--only','-m','Publish complete WM-DIAG1 saved-data mechanism results and all-parent evidence'],selected)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if commit!=remote:raise ValueError('full results remote commit readback')
    for name in selected:
        if git('show',commit+':'+name)!=(ROOT/name).read_bytes():raise ValueError('full exact new published byte readback')
    members[(DOC/'FINAL-PUBLICATION.started.json').relative_to(ROOT).as_posix()]=(DOC/'FINAL-PUBLICATION.started.json').read_bytes()
    members['PACKAGE-MEMBERS.json']=json.dumps({'results_commit':commit,'frozen_source_commit':pub['source_commit'],'source_SSD_whole':pub['whole'],'members':{k:{'bytes':len(v),'sha256':__import__('hashlib').sha256(v).hexdigest()} for k,v in members.items()}},sort_keys=True).encode()
    destination=Path(pub['archive']).parent;archive=destination/('saved-data-results-'+commit+'.zip');whole=zip_verified(archive,members)
    result={'status':'COMPLETE_DISCOVERY_RESULTS_FULL_REMOTE_AND_NEW_SSD_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':pub['source_commit'],'results_commit':commit,'full_remote_hash':remote,'branch':BRANCH,
        'archive':str(archive),'whole':whole,'verified_members':len(members),'source_package_not_recopied':pub['whole'],'report':report['report'],'derived_results':report['derived_results'],
        'all_new_logical_copy_conservative_bytes':prospective,'old_monitors_resumed':False,'future_pipeline_launched':False,'old_study_archive_recreated_or_copied':False}
    write_new(DOC/'FINAL-SSD-VERIFIED.json',result);write_new(destination/'FINAL-SSD-VERIFIED.json',result)
    print(json.dumps(result))

if __name__=='__main__':main()
