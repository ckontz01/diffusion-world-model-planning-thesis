"""Python 3.6-compatible, standard-library-only scheduler validation boundary.

The numerical worker keeps its approved validation code. These equivalent host
checks avoid importing numerical analysis merely to validate hashes/approval.
"""
import hashlib
import json
import re
from pathlib import Path
from diffusion_extension_control import REFS, size_bytes


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha(path, expected):
    require(bool(re.fullmatch(r'[a-f0-9]{64}', expected)), 'Invalid expected SHA256')
    require(sha256(path) == expected, 'SHA256 mismatch: '+str(path))


def checked_child(root, name):
    require(isinstance(name, str) and bool(name), 'Empty/non-string artifact name')
    require('\\' not in name, 'Backslash is not an archive path separator')
    rel = Path(name)
    require(not rel.is_absolute() and '..' not in rel.parts, 'Unsafe artifact path')
    base, child = root.resolve(), (root / rel).resolve()
    require(child != base and base in child.parents, 'Artifact escapes input root')
    return child


def verify_source(root, expected):
    require_sha(root/'SOURCE-MANIFEST.sha256', expected)
    for line in (root/'SOURCE-MANIFEST.sha256').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        require_sha(checked_child(root, name), digest)


def check_approval(path, source_sha, protocol_sha):
    approval = json.loads(Path(path).read_text())
    require(approval.get('researcher_approved') is True and
            approval.get('experiment') == 'single-anchor-ranking-20260914' and
            approval.get('source_manifest_sha256') == source_sha and
            approval.get('protocol_sha256') == protocol_sha and
            approval.get('repeats') == 2 and approval.get('gpu_seconds') == 14400 and
            approval.get('job_seconds') == 900 and approval.get('storage_bytes') == 2_000_000_000,
            'Missing/mismatched researcher approval; no execution')
    return approval
