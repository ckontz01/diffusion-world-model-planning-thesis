"""Freeze the new tested control closure and separate delegated authority once."""
from pathlib import Path
import io
import sys
import tarfile
import time
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ROOT=REPO/'docs/active-counterfactual-verification-20260923/control-r4'
sys.path.insert(0,str(ROOT))
import r4_core as r
import transport4 as transport

def main():
    r.require(not (ROOT/'SOURCE-MANIFEST.json').exists(),'No refreeze or overwrite')
    attempts=r.lines(ROOT/'ATTEMPTS.jsonl');started=[v['label'] for v in attempts if v['state']=='started'];finished=[v for v in attempts if v['state']=='finished']
    r.require(started==[v['label'] for v in finished] and finished[-1]['returncode']==0,'Reconciled passing final tests')
    r.require('Ran 17 tests' in finished[-1]['stderr'] and finished[-1]['stderr'].rstrip().endswith('OK'),'Complete final regression suite')
    total=sum(v['wall_seconds'] for v in finished)+sum(v.get('wall_seconds',0) for folder in ('control-r2','control-r3') for v in r.lines(ROOT.parent/folder/'ATTEMPTS.jsonl'))
    r.require(total<7200,'Combined R2/R3/R4 cumulative testing budget')
    old=ROOT.parent/'bindings-r1';sys.path.insert(0,str(old));import common as c
    r.require(c.sha(old/'SOURCE-MANIFEST.json')==r.SCIENCE_MANIFEST,'Original scientific manifest')
    for name,h in c.read(old/'SOURCE-MANIFEST.json')['files'].items():r.require(c.sha(c.REPO/name)==h,'Original source altered')
    for folder in ('control-r2','control-r3'):
        old2=ROOT.parent/folder
        for name,h in r.read(old2/'SOURCE-MANIFEST.json')['files'].items():r.require(r.sha(old2/name)==h,'Historical closure altered: '+folder)
    r.require(r.sha(ROOT/'MONITORING-AUTHORIZATION.md')==r.read(ROOT/'CONTRACT.json')['monitoring_authority_sha256'],'Direct monitoring authority record')
    r.write(ROOT/'FREEZE-RECEIPT.json',{'unix':time.time(),'authority':'Direct advance user technical-recovery authority; narrowly fixes the R3 exact observed PENDING allocation placeholder, resumes only302 unsubmitted tasks',
        'tests':finished,'test_attempts_sha256':r.sha(ROOT/'ATTEMPTS.jsonl'),'cumulative_test_wall_seconds':total,
        'original_scientific_manifest':r.SCIENCE_MANIFEST,'original_scientific_closure_unchanged':True,'scientific_model_or_physics_calls':0,
        'gpu_or_slurm_test_allocations':0,'existing_successful_task_recomputations':0,'helper_freeze_script_sha256':r.sha(Path(__file__))})
    files={p.name:r.sha(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name!='ATTEMPTS.jsonl'}
    r.require(all(Path(n).name==n for n in files),'Flat new control closure')
    r.write(ROOT/'SOURCE-MANIFEST.json',{'schema':'ACV0-control-only-r4-source','files':files,'original_scientific_manifest':r.SCIENCE_MANIFEST})
    manifest=r.sha(ROOT/'SOURCE-MANIFEST.json');binding=r.binding(manifest)
    template={'schema':'ACV0-control-only-r4','authorized':False,'instruction':'','binding':binding}
    r.write(ROOT/'APPROVAL-TEMPLATE.json',template)
    archive=ROOT/'source-export.tar';members={}
    with archive.open('xb') as out:
        with tarfile.open(fileobj=out,mode='w',format=tarfile.PAX_FORMAT) as tar:
            for name in sorted(set(files)|{'SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json'}):
                data=(ROOT/name).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0
                tar.addfile(info,io.BytesIO(data));members[name]={'bytes':len(data),'sha256':r.hashlib.sha256(data).hexdigest()}
    trans={'bytes':archive.stat().st_size,'sha256':r.sha(archive),'members':members,'control_manifest':manifest}
    r.write(ROOT/'SOURCE-TRANSPORT.json',trans);transport.verify_archive(archive,trans)
    instruction=transport.instruction()
    r.require(r.hashlib.sha256(instruction.encode('utf8')).hexdigest()==binding['instruction_sha256'],'Exact authority bytes including original line endings')
    approval=dict(template,authorized=True,instruction=instruction);r.write(HERE/'EXECUTION-APPROVAL.json',approval)
    r.write(HERE/'AUTHORIZATION-PROVENANCE.json',{'basis':'Direct advance user monitoring and technical-recovery instruction recorded at ace242ee5ea14af284401ad857fc3a49b30e1b58; not a fresh signature or reasoning approval; original scientific authority/caps unchanged',
        'instruction_sha256':binding['instruction_sha256'],'reviewed_status_commit':binding['reviewed_status_commit'],'control_manifest':manifest,
        'enabled_approval_sha256':r.sha(HERE/'EXECUTION-APPROVAL.json'),'original_scientific_manifest':r.SCIENCE_MANIFEST,'original_worker_approval_sha256':r.WORKER_APPROVAL,
        'scope':'Reuse all37 completed suppliers including304237; carry4862GPU seconds;302 never-submitted tasks starting256; exact bounded placeholder polling, separate R4 ledger/finalizer with complete R1/R2/R3 history; zero new allocation retries/replacements/scientific changes',
        'full_binding':binding,'original_false_template_preserved':True,'new_false_template_preserved':True,'no_additional_general_approval_required':True})
    r.write(HERE/'FROZEN-PACKAGE.json',{'control_manifest':manifest,'approval_sha256':r.sha(HERE/'EXECUTION-APPROVAL.json'),'archive':trans,
        'cumulative_test_wall_seconds':total,'tests_passed':17,'original_science_unchanged':True,'launch_occurred':False})
    print(r.json.dumps({'control_manifest':manifest,'approval_sha256':r.sha(HERE/'EXECUTION-APPROVAL.json'),'archive_bytes':trans['bytes'],
        'archive_sha256':trans['sha256'],'members':len(members),'cumulative_test_wall_seconds':total},indent=2))

if __name__=='__main__':main()
