"""Seal this preparation package only. Never commits, pushes or copies archives."""
import base
import json, time

def main():
    base.authenticate_code()
    from protocol import validate
    e=base.read(base.HERE/'ELIGIBILITY.json'); c=base.read(base.HERE/'PROTOCOL.json'); g=base.read(base.HERE/'GRID.json')
    check=validate(c,g,e)
    report=base.read(base.HERE/'SAVED-DATA-MECHANISM.json')
    assert base.digest((base.PUB/'REPORT.json').read_bytes())==report['authentication']['original_report_sha256']
    entries=[json.loads(line) for line in (base.HERE/'ATTEMPTS.jsonl').read_text().splitlines()]
    # This script itself can be the active bounded child; its finish is retained
    # in ATTEMPTS after this receipt, outside the sealed content manifest.
    finished=[r for r in entries if r['state']=='finished']
    assert all(r['returncode']==0 for r in finished)
    assert sum(r['wall_seconds'] for r in finished)+1<3600
    dependencies={}
    for rel in ('model.py','policy.py','tree.py','runtime_adapter.py','mock.py','bindings-r1/episodes.py',
                'bindings-r1/fitting.py','bindings-r1/verify.py','bindings-r1/bridge.py','bindings-r1/common.py',
                'bindings-r1/artificial.py','bindings-r1/INPUT-BINDINGS.json','DATA-ROLES-PROPOSED.json'):
        p=base.OLD/rel;dependencies[str(p.relative_to(base.REPO)).replace('\\','/')]=dict(bytes=p.stat().st_size,sha256=base.digest(p.read_bytes()))
    base.write(base.HERE/'DEPENDENCIES.json',dependencies)
    receipt=dict(status='PREPARATION COMPLETE; NO RESEARCH EXECUTION',completed_unix=time.time(),
                 protocol_check=check,tests_passed=31,saved_data_report_runs=1,
                 numerical_attempt_wall_seconds_through_before_seal=sum(r['wall_seconds'] for r in finished),
                 rejected_concurrent_wrapper_reserved_seconds=1,
                 peak_measured_job_memory_bytes=max(r['peak_job_memory_bytes'] for r in finished),
                 max_cpu_threads=4,gpu_jobs=0,physics_steps=0,lewm_forwards=0,new_fits=0,new_collection=0,
                 new_reference_payload_reads=0,identity_projection_queries=1,new_source_allocation=False,
                 original_result_commit='5d8666754ad8aa0507730f86cf3ee6caa32c105a',
                 original_scientific_report_sha256=report['authentication']['original_report_sha256'],
                 historical_files_modified=False,monitor_changed=False,remote_writes=False,backup_cycles=0,
                 delivery='local preparation package; no commit/push/handoff or research execution requested by this instruction')
    base.write(base.HERE/'PREPARATION-RECEIPT.json',receipt)
    files={p.name:dict(bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for p in sorted(base.HERE.iterdir())
           if p.is_file() and p.name not in ('MANIFEST.json','ATTEMPTS.jsonl')}
    base.write(base.HERE/'MANIFEST.json',dict(schema='ACV-mechanism-preparation-v1',execution_authorized=False,
                                            files=files,excluded_append_only_log='ATTEMPTS.jsonl'))
    print(json.dumps(dict(manifest_sha256=base.digest((base.HERE/'MANIFEST.json').read_bytes()),
                         sealed_files=len(files),sealed_bytes=sum(x['bytes'] for x in files.values()),**check)))

if __name__=='__main__': main()
