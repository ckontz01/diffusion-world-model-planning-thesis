"""Bounded source acquisition and NON-executing checkpoint opcode inventory.

No torch/pickle import, checkpoint deserialization, environment change or job.
The opcode inventory is dependency information, NOT a security certification.
"""
import hashlib
import json
from pathlib import Path
import pickletools
import time
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/world-model-diagnostic-a2-cluster-native-v1-20261015'
A2 = ROOT / 'docs/world-model-diagnostic-a2-20261004'
PIN = '7764ea0f912e53c92e82eb78a2a1631e92725fc8'


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def exclusive_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)


def fetch(url, maximum):
    with urlopen(Request(url, headers={'User-Agent': 'WM-DIAG0-A2-native-binding'}), timeout=15) as response:
        raw = response.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('Source response byte bound')
    return raw


def encoder_closure():
    """Acquire only missing Python source at the ALREADY accepted encoder pin."""
    tree_raw = fetch('https://api.github.com/repos/facebookresearch/dinov2/git/trees/' + PIN + '?recursive=1', 2_000_000)
    tree = json.loads(tree_raw)
    if tree.get('truncated') or tree.get('sha') != PIN:
        # GitHub's tree SHA may differ from the commit SHA: bind using commit API.
        commit = json.loads(fetch('https://api.github.com/repos/facebookresearch/dinov2/git/commits/' + PIN, 100_000))
        if tree.get('truncated') or commit['sha'] != PIN or tree['sha'] != commit['tree']['sha']:
            raise ValueError('Pinned complete source tree identity')
    exact = {'dinov2/__init__.py', 'dinov2/models/__init__.py',
             'dinov2/models/vision_transformer.py', 'LICENSE'}
    chosen = [r for r in tree['tree'] if r['type'] == 'blob' and
              (r['path'] in exact or (r['path'].startswith('dinov2/layers/') and r['path'].endswith('.py')))]
    if not exact.issubset({r['path'] for r in chosen}) or len(chosen) > 40 or sum(r['size'] for r in chosen) > 1_000_000:
        raise ValueError('Source selection bound')
    receipt = []
    for row in chosen:
        relative = row['path']
        if '..' in Path(relative).parts or Path(relative).is_absolute():
            raise ValueError('Source path')
        old = A2 / 'source-audit/dinov2' / relative
        raw = old.read_bytes() if old.is_file() else fetch('https://raw.githubusercontent.com/facebookresearch/dinov2/' + PIN + '/' + relative, 200_000)
        if len(raw) != row['size'] or hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != row['sha']:
            raise ValueError('Source Git blob authentication: ' + relative)
        target = DOC / 'encoder-source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        receipt.append(dict(path=target.relative_to(ROOT).as_posix(), upstream_path=relative,
                            upstream_blob=row['sha'], reused_existing_source=old.is_file(), **digest(raw)))
    return {'upstream_commit': PIN, 'tree_sha': tree['sha'], 'members': receipt,
            'training_time_checkout_verified': False, 'weights_downloaded': 0}


def pickle_inventory(path, expected):
    hash_ = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024*1024), b''):
            hash_.update(raw); size += len(raw)
    if size != expected['bytes'] or hash_.hexdigest() != expected['sha256']:
        raise ValueError('Fixed checkpoint identity: ' + str(path))
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        if len(names) != len(set(names)) or len(names) > 20_000:
            raise ValueError('Archive member bound/uniqueness')
        candidates = [m for m in members if m.filename.endswith('/data.pkl')]
        if len(candidates) != 1 or candidates[0].file_size > 2_000_000:
            raise ValueError('Pickle metadata bound')
        raw = archive.read(candidates[0])
    globals_ = set(); op_count = 0; stack_global = 0
    # genops interprets opcode syntax only; it does NOT execute GLOBAL/REDUCE.
    for op, arg, _ in pickletools.genops(raw):
        op_count += 1
        if op_count > 200_000:
            raise ValueError('Opcode bound')
        if op.name == 'GLOBAL': globals_.add(arg)
        elif op.name == 'STACK_GLOBAL': stack_global += 1
    return {'artifact': expected['name'], 'bytes': size, 'sha256': hash_.hexdigest(),
            'pickle_metadata': digest(raw), 'global_references': sorted(globals_),
            'unresolved_stack_global_count': stack_global, 'opcode_count': op_count,
            'deserialized': False, 'static_inventory_is_security_proof': False}


def main():
    start = time.monotonic()
    pending = DOC / 'PREPARE-001.started.json'
    exclusive_json(pending, {'wall_reservation_seconds': 240, 'research_execution': False,
                            'source_pin': PIN, 'started_unix': time.time()})
    result = {'status': 'FAILED', 'checkpoint_loads': 0, 'model_forwards': 0, 'physics_steps': 0}
    try:
        result['encoder_source'] = encoder_closure()
        artifacts = json.loads((A2 / 'ARTIFACT-RECEIPTS.json').read_text())
        result['artifacts'] = [pickle_inventory(A2 / 'artifacts' / (r['name'] + '.pth'), r) for r in artifacts]
        result['fixed_root_plan'] = digest((A2/'ROOT-PLAN.json').read_bytes())
        result['status'] = 'SOURCE_CLOSURE_AND_STATIC_INPUT_INVENTORY_COMPLETE'
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['elapsed_seconds'] = time.monotonic() - start
        exclusive_json(DOC / 'PREPARE-001.json', result)
        print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
