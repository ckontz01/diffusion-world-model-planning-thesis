"""Targeted public metadata/source acquisition; never import remote code/pickle."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/world-model-diagnostic-a2-20261004'

def fetch(url, maximum=4_000_000):
    req = Request(url, headers={'User-Agent': 'WM-DIAG0-A2-provenance-audit'})
    with urlopen(req, timeout=45) as response:
        if int(response.headers.get('Content-Length', '0')) > maximum: raise ValueError('Download bound')
        raw = response.read(maximum + 1)
        if len(raw) > maximum: raise ValueError('Response bound')
        return raw

def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(raw)
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def pins():
    out = {'status': 'METADATA_ONLY_PIN_BEFORE_ACQUISITION', 'github': {}, 'huggingface': {}}
    gh = json.loads(fetch('https://api.github.com/repos/fafraob/point-lewm/commits/main'))
    out['github'] = {'repo': 'fafraob/point-lewm', 'commit': gh['sha']}
    tree = fetch('https://api.github.com/repos/fafraob/point-lewm/git/trees/' + gh['sha'] + '?recursive=1')
    out['github']['tree_receipt'] = save(DOC / 'public-metadata/github-tree.json', tree)
    if json.loads(tree).get('truncated'): raise ValueError('Truncated source tree')
    for task in ('pusht', 'reacher'):
        repo = 'fafraob/point-cloud-' + task
        for kind in ('models', 'datasets'):
            try:
                meta = json.loads(fetch('https://huggingface.co/api/' + kind + '/' + repo + '?blobs=true'))
            except Exception as exc:
                if getattr(exc, 'code', None) == 404: continue
                raise
            out['huggingface'][task] = {'repo': repo, 'kind': kind, 'commit': meta['sha'],
                'license': meta.get('cardData', {}).get('license'),
                'dino_members': [s for s in meta['siblings'] if s['rfilename'].startswith('dino-wm/')],
                'metadata_receipt': save(DOC / ('public-metadata/hf-' + task + '.json'),
                                        json.dumps(meta, indent=2).encode())}
            break
        else: raise ValueError('No public repository type: ' + repo)
    print(json.dumps(out, indent=2))
    save(DOC / 'PUBLIC-PINS.json', json.dumps(out, indent=2).encode())

def sources():
    pin = json.loads((DOC / 'PUBLIC-PINS.json').read_text())
    commit = pin['github']['commit']
    tree = json.loads((DOC / 'public-metadata/github-tree.json').read_text())['tree']
    # Source-only closures needed to inspect RGB DINO, native evaluator and collector.
    prefixes = ('dinowm_swm/', 'third_party/dino_wm/models/', 'third_party/dino_wm/planning/',
                'third_party/dino_wm/conf/', 'config/eval/', 'stable-worldmodel/stable_worldmodel/')
    exact = {'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'pixi.toml', 'eval.py',
             'scripts/download_checkpoints.py', '.gitmodules'}
    selected = [t for t in tree if t['type'] == 'blob' and
                (t['path'] in exact or any(t['path'].startswith(p) for p in prefixes)) and
                (t['path'].endswith(('.py', '.yaml', '.yml', '.toml', '.md')) or t['path'] in exact)]
    if sum(t.get('size', 0) for t in selected) > 4_000_000: raise ValueError('Targeted source cap')
    receipts = []
    for t in selected:
        raw = fetch('https://raw.githubusercontent.com/fafraob/point-lewm/' + commit + '/' + t['path'], 500_000)
        if len(raw) != t['size'] or hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != t['sha']:
            raise ValueError('Git source blob mismatch')
        receipt = save(DOC / 'source-audit/point-lewm' / t['path'], raw)
        receipt.update(upstream_git_blob=t['sha'], upstream_commit=commit)
        receipts.append(receipt)
    for task, row in pin['huggingface'].items():
        base = 'https://huggingface.co/' + ('datasets/' if row['kind'] == 'datasets' else '') + row['repo']
        selected = [m for m in row['dino_members'] if not m['rfilename'].endswith(('.pth', '.pt', '.ckpt', '.bin'))]
        # Configuration/normalization files only, safe text or numeric files retained opaque.
        for m in selected:
            if not m['rfilename'].endswith(('.yaml', '.yml', '.json', '.npy', '.md', '.txt', '.safetensors')): continue
            if m.get('size', 0) > 500_000: continue
            raw = fetch(base + '/resolve/' + row['commit'] + '/' + m['rfilename'], 500_000)
            receipt = save(DOC / 'source-audit' / task / m['rfilename'], raw)
            receipt['upstream_commit'] = row['commit']
            receipt['published_member'] = m
            receipts.append(receipt)
    save(DOC / 'SOURCE-AUDIT-RECEIPTS.json', json.dumps(receipts, indent=2).encode())
    print(json.dumps({'source_files': len(receipts), 'bytes': sum(r['bytes'] for r in receipts)}, indent=2))

def encoder_pin():
    commit = json.loads(fetch('https://api.github.com/repos/facebookresearch/dinov2/commits/main'))['sha']
    paths = ('dinov2/hub/backbones.py', 'hubconf.py', 'dinov2/models/vision_transformer.py', 'LICENSE')
    receipts = []
    for path in paths:
        raw = fetch('https://raw.githubusercontent.com/facebookresearch/dinov2/' + commit + '/' + path, 500_000)
        receipts.append(save(DOC / 'source-audit/dinov2' / path, raw))
    url = 'https://dl.fbaipublicfiles.com/dinov2/dinov2_vits14/dinov2_vits14_pretrain.pth'
    with urlopen(Request(url, method='HEAD'), timeout=45) as response:
        headers = dict(response.headers)
    out = {'github_commit': commit, 'model': 'dinov2_vits14', 'url': url,
           'headers': headers, 'source_receipts': receipts,
           'binding_status': 'CURRENT_PUBLIC_RELEASE_PIN_NOT_PROOF_OF_TRAINING_TIME_ENCODER_REVISION'}
    save(DOC / 'ENCODER-PIN.json', json.dumps(out, indent=2).encode())
    print(json.dumps(out, indent=2))

def artifacts():
    pins = json.loads((DOC / 'PUBLIC-PINS.json').read_text())
    ep = json.loads((DOC / 'ENCODER-PIN.json').read_text())
    targets = []
    for task, row in pins['huggingface'].items():
        member = next(m for m in row['dino_members'] if m['rfilename'].endswith('model_latest.pth'))
        url = 'https://huggingface.co/' + row['repo'] + '/resolve/' + row['commit'] + '/' + member['rfilename']
        targets.append((task, url, member['size'], member['lfs']['sha256']))
    headers = {k.lower(): v for k,v in ep['headers'].items()}
    targets.append(('dinov2_vits14', ep['url'], int(headers['content-length']), None))
    planned = sum(t[2] for t in targets)
    if planned > 2 * 1024**3: raise ValueError('Targeted artifact acquisition cap')
    retained = sum(p.stat().st_size for d in (DOC, ROOT/'wm_diag0_a2', ROOT/'wm_diag0',
                    ROOT/'docs/world-model-diagnostic-20261004') for p in d.rglob('*') if p.is_file())
    # Retain original artifacts locally, reserve one SSD copy of all acquired artifacts
    # and a 20 MB small package. Proposed future campaign topology is separate below.
    if retained + 2*planned + 20_000_000 > 5*1024**3: raise ValueError('Full retained preparation reservation')
    receipts = []
    for name, url, size, expected in targets:
        path = DOC / ('artifacts/' + name + '.pth')
        path.parent.mkdir(exist_ok=True)
        digest = hashlib.sha256(); count = 0
        with urlopen(Request(url, headers={'User-Agent': 'WM-DIAG0-A2-provenance-audit'}), timeout=45) as src, path.open('xb') as dst:
            if name == 'dinov2_vits14':
                actual = {k.lower(): v for k,v in src.headers.items()}
                for key in ('etag', 'x-amz-version-id', 'content-length'):
                    if actual.get(key) != headers.get(key): raise ValueError('Encoder object changed after pin')
            while True:
                data = src.read(1_048_576)
                if not data: break
                count += len(data)
                if count > size: raise ValueError('Published size exceeded; preserve partial')
                dst.write(data); digest.update(data)
        if count != size or (expected and digest.hexdigest() != expected): raise ValueError('Artifact authentication; preserve bytes')
        # ZIP directory only. NO pickle parsing, extraction, torch import or deserialization.
        with zipfile.ZipFile(path) as archive:
            members = [{'name': m.filename, 'bytes': m.file_size} for m in archive.infolist()]
        receipts.append({'name': name, 'url': url, 'bytes': count, 'sha256': digest.hexdigest(),
                         'published_sha256': expected, 'status': 'OPAQUE_BYTES_AUTHENTICATED_NOT_LOADED',
                         'zip_members': members})
    save(DOC / 'ARTIFACT-RECEIPTS.json', json.dumps(receipts, indent=2).encode())
    print(json.dumps({'artifacts': [{k:v for k,v in r.items() if k != 'zip_members'} for r in receipts],
                      'acquired_bytes': planned, 'unsafe_deserializations': 0}, indent=2))

if __name__ == '__main__': {'pins': pins, 'sources': sources, 'encoder_pin': encoder_pin,
                          'artifacts': artifacts}[sys.argv[1]]()
