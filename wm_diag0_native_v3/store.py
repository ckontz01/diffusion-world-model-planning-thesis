"""Numeric, hash-authenticated storage and explicit production phase access."""
import json
import math
from pathlib import Path
import numpy as np
from .common import identity, write_new

def check_relative(name):
    p=Path(name)
    if not name or '\\' in name or ':' in name or p.is_absolute() or any(x in ('','..','.') for x in name.split('/')): raise ValueError('relative member')
    return p

def authenticate(directory,seal,max_bytes,expected=None):
    root=Path(directory); manifest=root/'MEMBERS.json'
    if manifest.is_symlink() or identity(manifest)!=seal: raise ValueError('external manifest seal')
    members=json.loads(manifest.read_text(),object_pairs_hook=unique)
    if len(members)>10000 or sum(r['bytes'] for r in members.values())>max_bytes: raise ValueError('bounded exact membership')
    if expected is not None and set(members)!=set(expected): raise ValueError('exact allowed members')
    actual={str(p.relative_to(root)).replace('\\','/') for p in root.rglob('*') if p.is_file() and p!=manifest}
    if actual!=set(members): raise ValueError('extra/missing files')
    for name,row in members.items():
        p=root/check_relative(name)
        if any(q.is_symlink() for q in (p,*p.parents)) or identity(p)!=row: raise ValueError('member identity')
    return members

def unique(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError('duplicate JSON key')
        out[k]=v
    return out

def load_array(path,shape=None,dtypes=None,max_bytes=150_000_000):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>max_bytes: raise ValueError('numeric file bound')
    with path.open('rb') as f:
        version=np.lib.format.read_magic(f)
        if version not in ((1,0),(2,0)): raise ValueError('bounded supported NPY version')
        reader=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
        shp,order,dtype=reader(f,max_header_size=4096)
        if dtype.hasobject or dtype.kind not in 'biuf' or order or len(shp)>6: raise ValueError('numeric C-order arrays only')
        size=math.prod(shp)*dtype.itemsize
        if size>max_bytes or size+f.tell()!=path.stat().st_size: raise ValueError('array declaration/size')
        if shape is not None and tuple(shp)!=tuple(shape): raise ValueError('array shape')
        if dtypes is not None and dtype.str not in dtypes: raise ValueError('array dtype')
    a=np.load(path,allow_pickle=False)
    if not np.isfinite(a).all(): raise ValueError('finite numeric data')
    return a

def save_array(path,a):
    a=np.ascontiguousarray(a)
    if a.dtype.hasobject or a.dtype.kind not in 'biuf' or not np.isfinite(a).all(): raise ValueError('finite numeric arrays')
    with Path(path).open('xb') as f: np.save(f,a,allow_pickle=False)

def seal(directory,max_bytes):
    root=Path(directory)
    members={str(p.relative_to(root)).replace('\\','/'):identity(p) for p in sorted(root.rglob('*')) if p.is_file()}
    if sum(r['bytes'] for r in members.values())>max_bytes: raise ValueError('aggregate output bound')
    write_new(root/'MEMBERS.json',members)
    return identity(root/'MEMBERS.json')

class PhaseAccess:
    def __init__(self,root): self.root=Path(root); self.selection_seal=None
    def record_selection(self,row):
        if self.selection_seal is not None: raise ValueError('selection already sealed')
        write_new(self.root/'SELECTION.json',row)
        self.selection_seal=identity(self.root/'SELECTION.json')
        # External parent controls directory supplies a separately owned copy.
        return self.selection_seal
    def authorize_outcomes(self,external):
        if self.selection_seal is None or external!=self.selection_seal or identity(self.root/'SELECTION.json')!=external:
            raise PermissionError('authenticate selection before opening any outcomes')
        return self.root/'evaluation'
