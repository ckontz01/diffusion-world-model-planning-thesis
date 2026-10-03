"""Read exact completed report members only after actual native SSD verification."""
import hashlib
import json
import tarfile
from pathlib import Path
from dtv_success_cost.common import gate, sha, write
from dtv_success_cost.preserve import VOLUME, validate_request

HERE = Path(__file__).resolve().parent
folder = Path('D:/THESIS-BACKUPS/dtv-success-cost-20261001/run-bc3b36c71362f172')
request_path = folder / 'REQUEST.json'
request = json.loads(request_path.read_bytes())
verified = json.loads((folder / 'VERIFIED.json').read_bytes())
c = gate(HERE.parent / 'execution-v1/EXECUTION-APPROVAL-WINDOWS.json')
validate_request(request, request['run']+'/final-preservation/BACKUP-REQUEST.json', c)
if (verified.get('status') != 'verified' or verified.get('whole_and_members') is not True
    or verified.get('request_sha256') != sha(request_path)
    or verified.get('archive_sha256') != request['archive']['sha256']
    or verified.get('bytes') != request['archive']['bytes']
    or verified.get('members') != request['archive']['members']
    or verified.get('volume', {}).get('UniqueId', '').lower() != VOLUME.lower()):
    raise RuntimeError('required actual SSD gate absent')
rows = {row['path']: row for row in request['inventory']}
with tarfile.open(folder / 'final.tar', 'r:') as archive:
    for name in ('REPORT.json', 'ACCEPTANCE.json'):
        key = 'run/analysis/' + name
        member = archive.getmember(key)
        data = archive.extractfile(member).read()
        expected = rows[key]
        if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            raise RuntimeError('preserved report member changed')
        with (HERE / name).open('xb') as output:
            output.write(data)
write(HERE / 'FINAL-ALLOCATION.json', request['allocation'])
write(HERE / 'SSD-VERIFIED.json', verified)
report = json.loads((HERE / 'REPORT.json').read_bytes())
print(json.dumps(dict(report_keys=list(report), report_bytes=(HERE/'REPORT.json').stat().st_size,
                      report_sha256=sha(HERE/'REPORT.json'), allocation=request['allocation'].get('actual_attempts'),
                      keys={k:(list(v)[:20] if isinstance(v,dict) else len(v) if isinstance(v,list) else v)
                            for k,v in report.items() if k!='worker_setup_and_authentication'}), default=str))
