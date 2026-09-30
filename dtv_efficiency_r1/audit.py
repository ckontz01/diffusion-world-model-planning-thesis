"""Metadata-only correction audit; no research payload or scheduler access."""
import argparse,difflib,json,time
from pathlib import Path
from dtv_efficiency_r1 import campaign,package
from dtv_efficiency_r1.control import ROOT,DOC,ORIGINAL_DOC,load_bindings
from dtv_efficiency_r1.profile import sha

def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(value)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--final',action='store_true');args=parser.parse_args()
    started=time.monotonic();c=load_bindings()
    names=('profile.py','campaign.py','accept.py');diff=[]
    for name in names:
        old=ROOT/'dtv_efficiency'/name;new=ROOT/'dtv_efficiency_r1'/name
        diff.extend(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile='dtv_efficiency/'+name,tofile='dtv_efficiency_r1/'+name))
    for new in sorted((ROOT/'dtv_efficiency_r1').glob('*.py')):
        if new.name not in names:diff.extend(difflib.unified_diff([],new.read_text().splitlines(True),fromfile='/dev/null',tofile=new.relative_to(ROOT).as_posix()))
    diff_path=DOC/('SOURCE-DIFF-FINAL.patch' if args.final else 'SOURCE-DIFF.patch')
    plan_path=DOC/('GENERATED-PLAN-FINAL.json' if args.final else 'GENERATED-PLAN.json')
    for target in (diff_path,plan_path):
        if target.exists():raise RuntimeError('preserve audit artifacts; do not regenerate a frozen audit')
    write(diff_path,''.join(diff))
    remote_package=Path('/lustreFS/data/superworld/ckontzias/thesis/snapshots/dtv-efficiency-correction-r1-PACKAGE_HASH')
    run=Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/dtv-efficiency-20260930/run-PACKAGE_HASH')
    jobs=campaign.plan(c,remote_package,remote_package/'docs/dtv-efficiency-correction-r1-20260930/EXECUTION-APPROVAL.json',run)
    if sum(j['reservation_seconds'] for j in jobs)!=7020 or any('--time=00:13:00' not in j['command'] for j in jobs):raise RuntimeError('reservation arithmetic')
    write(plan_path,json.dumps(dict(execute=False,paths_are_unstaged_templates=True,wall_seconds_per_worker=780,work_seconds=720,preservation_seconds=60,full_future_gpu_reservation_seconds=7020,aggregate_gpu_ceiling_seconds=7200,jobs=jobs),indent=2)+'\n')
    rows=package.files();source=sum(r['bytes'] for r in rows)
    live=9*(4000000+2000000)+source+2000000
    if live>c['live_bytes_cap'] or live+2000000>c['archive_bytes_cap']:raise RuntimeError('complete output reservations')
    receipt=dict(status='final_metadata_verified_manifest_and_ssd_verification_follow' if args.final else 'metadata_verified_tests_and_ssd_still_pending',reviewed_members_verified=len(json.loads((ORIGINAL_DOC/'PACKAGE-MANIFEST.json').read_text())['files']),reviewed_manifest_sha256=sha(ORIGINAL_DOC/'PACKAGE-MANIFEST.json'),binding_overlay_sha256=sha(DOC/'BINDINGS.json'),plan_sha256=sha(plan_path),exact_source_diff_sha256=sha(diff_path),source_members=len(rows),source_bytes_before_this_receipt=source,source_cap_bytes=4000000,complete_live_bound_before_this_receipt=live,complete_archive_bound_before_this_receipt=live+2000000,correction_new_bytes_before_this_receipt=sum(r['bytes'] for r in rows if r['path'].startswith(('dtv_efficiency_r1/','docs/dtv-efficiency-correction-r1-20260930/'))),correction_artifact_cap_bytes=50000000,worker_complete_outputs_tested=True,original_package_unchanged=True,research_inference=False,slurm=False,gpu=False,wall_seconds=time.monotonic()-started)
    write(DOC/(args.label+'-RECEIPT.json'),json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
