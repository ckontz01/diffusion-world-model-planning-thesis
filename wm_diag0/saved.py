"""Exclusive artificial array bundles with member hashes and independent loading."""
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def save_artificial(path, record):
    if record['domain'] != 'artificial': raise PermissionError('Research persistence disabled')
    path = Path(path)
    path.mkdir(exist_ok=False)
    meta = dict(record)
    members = {}
    for name in ('actions','observations'):
        with (path/f'{name}.npy').open('xb') as f:
            np.save(f,meta.pop(name),allow_pickle=False)
        members[f'{name}.npy'] = sha(path/f'{name}.npy')
    with (path/'record.json').open('x',encoding='utf8') as f:
        json.dump(meta,f,sort_keys=True,allow_nan=False)
    members['record.json'] = sha(path/'record.json')
    with (path/'members.json').open('x',encoding='utf8') as f: json.dump(members,f,sort_keys=True)
    return members


def load_artificial(path, expected_manifest_sha256):
    path = Path(path)
    if sha(path/'members.json') != expected_manifest_sha256: raise ValueError('Saved manifest changed')
    members = json.loads((path/'members.json').read_text())
    if set(members) != {'actions.npy','observations.npy','record.json'}:
        raise ValueError('Unexpected saved members')
    for name, identity in members.items():
        if sha(path/name) != identity: raise ValueError('Saved array/action/endpoint bytes changed')
    record = json.loads((path/'record.json').read_text())
    if record['domain'] != 'artificial': raise PermissionError('Research persistence disabled')
    for name in ('actions','observations'):
        record[name] = np.load(path/f'{name}.npy',allow_pickle=False)
    record['endpoint_flags'] = tuple(record['endpoint_flags'])
    return record
