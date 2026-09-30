"""Final standard-library-only preparation audit; no runtime inference imports."""
import json,subprocess,sys,time
from pathlib import Path
from dtv_efficiency.profile import DOC,sha
from dtv_efficiency.package import files

def main():
    began=time.monotonic();root=DOC.parents[1]
    for path in (root/'dtv_efficiency').glob('*.py'):
        compile(path.read_bytes(),str(path),'exec')
    c=json.loads((DOC/'BINDINGS.json').read_text())
    plan=subprocess.run([sys.executable,'-m','dtv_efficiency.campaign','--run','/lustreFS/data/superworld/ckontzias/thesis/experiments/dtv-efficiency-20260930/run-PREPARATION-ONLY'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    value=json.loads(plan.stdout)
    assert value['execute'] is False and len(value['jobs'])==9 and value['full_future_gpu_reservation_seconds']==7200
    plan_path=DOC/'DISABLED-DISPATCH-PLAN.json'
    if plan_path.exists():assert plan_path.read_bytes()==plan.stdout
    else:
        with plan_path.open('xb') as f:f.write(plan.stdout)
    refusal=subprocess.run([sys.executable,'-m','dtv_efficiency.profile','--job','pusht-6101','--output',str(DOC/'MUST-NOT-EXIST')],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    assert refusal.returncode!=0 and b'research execution disabled' in refusal.stdout and not (DOC/'MUST-NOT-EXIST').exists()
    refusal_path=DOC/'DISABLED-WORKER-RECEIPT.txt'
    if refusal_path.exists():assert refusal_path.read_bytes()==refusal.stdout
    else:
        with refusal_path.open('xb') as f:f.write(refusal.stdout)
    rows=json.loads((DOC/'HISTORICAL-TIMINGS-VERIFIED.json').read_text())
    assert len(rows)==129 and {r['task'] for r in rows if r['study']=='D1'}=={'pusht','reacher','cube'}
    doc=(DOC/'HISTORICAL-TIMING-RECONCILIATION.md').read_text()
    for task in ('pusht','reacher','cube'):
        for arm in ('acid','diffusion'):
            for scope in ('verifier_only','total_cost_call','full_released_cem_solve'):
                matches=[r for r in rows if r['study']=='D1' and r['task']==task and r['arm']==arm and r['scope']==scope]
                assert len(matches)==1,(task,arm,scope)
                assert f"{matches[0]['measurement']['median_ms']:.6f}" in doc,(task,arm,scope)
    payloads=[r for r in files() if r['path'].endswith(('.pt','.ckpt','.h5','.hdf5'))]
    assert not payloads
    totals=sum(r['bytes'] for r in files())
    assert totals<4000000 and 9*6000000+totals+2000000<=c['live_bytes_cap']
    authority=json.loads((DOC/'PREPARATION-AUTHORITY.json').read_text())
    assert sha(authority['attachment'])==authority['attachment_sha256'] and authority['execution_authorized'] is False
    known=[('evidence/RECOVERY.json','local_wall_seconds'),('PREPARATION-PASS.json','local_wall_seconds'),('FINAL-RECOVERY.json','local_wall_seconds'),('METADATA-AUDIT.json','local_wall_seconds'),('TEST-RECEIPT.json','wall_seconds'),('INTEGRATION-FINAL-RECEIPT.json','wall_seconds')]
    measured=[dict(receipt=name,seconds=json.loads((DOC/name).read_text())[key]) for name,key in known]
    # This is an intentionally conservative accounting charge, not a claim
    # to have reconstructed uninstrumented wall time. It also reserves all
    # remaining standard-library publication/backup checks up to 600 s.
    account=dict(study='DTV-EFF0',cap_seconds=7200,instrumented_receipts=measured,measured_seconds=sum(r['seconds'] for r in measured),additional_conservative_charge_seconds=3600,remaining_publication_backup_reservation_seconds=600,cpu_threads_cap=4,ram_cap_bytes=8589934592,artifact_bytes_at_audit=totals,artifact_cap_bytes=250000000,unmeasured_wall_time_reconstructed=False,scope_note='Conservative charge covers earlier uninstrumented metadata/shell/transport/startup/test checks; it is not an exact stopwatch observation. Receipt intervals are not added to overlapping subtest CPU/wall intervals.',research_inference=False,gpu_allocations=0,physics=False,research_checkpoint_deserializations=0,original_archives_copied=0)
    account['charged_plus_remaining_seconds']=account['measured_seconds']+3600+600
    assert account['charged_plus_remaining_seconds']<7200
    with (DOC/'PREPARATION-ACCOUNTING.json').open('x') as f:json.dump(account,f,indent=2)
    receipt=dict(status='passed',source_compile=True,disabled_worker_refused_before_payload_access=True,disabled_plan_jobs=9,raw_d1_display_values_verified=True,metadata_only=True,new_package_bytes=totals,local_wall_seconds=time.monotonic()-began)
    with (DOC/'FINAL-PREPARATION-AUDIT.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
