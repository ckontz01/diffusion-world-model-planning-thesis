"""One-shot preparation manifest, not a production preservation operation."""
import recover as r

receipt=r.read(r.HERE/'TEST-RESULTS.json')
assert receipt['passed'] and receipt['tests_run']==receipt['distinct_tests']==21
assert receipt['tool_sha256']==r.digest(r.HERE/'recover.py')
assert receipt['helper_sha256']==r.digest(r.HERE/'remote_helper.py')
assert receipt['tests_sha256']==r.digest(r.HERE/'test_recovery.py')
assert r.digest(r.HERE/'AUTHORIZATION.txt')==r.AUTH_SHA
files={p.name:r.digest(p) for p in r.HERE.iterdir() if p.is_file() and p.name!='FROZEN.json'}
r.write(r.HERE/'FROZEN.json',dict(files=files,limits=r.LIMITS,authorization_sha256=r.AUTH_SHA,
    source_sha256=r.SOURCE,approval_sha256=r.APPROVAL,archive_sha256=r.WHOLE,
    request_sha256=r.REQUEST_SHA,partial_sha256=r.PREFIX_SHA,
    failed_receipt_sha256=r.FAILURE_SHA,archive_bytes=r.TOTAL,prefix_bytes=r.PREFIX,
    recovery_destination=str(r.DEST),research_execution=False))
print(r.digest(r.HERE/'FROZEN.json'))
