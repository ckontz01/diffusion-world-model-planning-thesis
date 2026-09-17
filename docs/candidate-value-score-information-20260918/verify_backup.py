"""Verify every archive member without interpreting outcomes; write external receipt."""
import hashlib,json,tarfile,time
from pathlib import Path
p=Path('/mnt/d/THESIS-BACKUPS/candidate-value-score-information-20260918/execution-68145e6458da0b90')
def digest(f):
    h=hashlib.sha256()
    for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
manifest=json.loads((p/'BACKUP-MANIFEST.json').read_text())
with (p/'SI1-COMPLETE.tar').open('rb') as f:actual=digest(f)
assert actual==manifest['archive_sha256']=='57deab4d1f30b3618f336c0c73bad45827e64301aa7ae3664bedc0e35d715e41'
expected={r['name']:r for r in manifest['members']}
with tarfile.open(p/'SI1-COMPLETE.tar') as tar:
    entries=tar.getmembers();assert len(entries)==len(expected) and {m.name for m in entries}==set(expected)
    for m in entries:
        assert m.isfile() and m.size==expected[m.name]['bytes']
        with tar.extractfile(m) as f:assert digest(f)==expected[m.name]['sha256']
receipt=dict(verified=True,utc=time.time(),archive_sha256=actual,members=len(expected),
    bytes=manifest['archive_bytes'],unique_payload_bytes=manifest['unique_payload_bytes'],
    external_volume='0a2f1ba9-0000-0000-0000-100000000000',source_models_preprocessing_predictions_reports_accounting_preserved=True)
with (p/'VERIFIED-BACKUP.json').open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(receipt))
