"""Independent stdlib source-file authentication; no image/scientific analysis."""
import ast
import hashlib
import json
import math
from pathlib import Path
import struct

def product(values):
    n=1
    for x in values: n*=x
    return n

def ident(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for x in iter(lambda:f.read(1048576),b''): h.update(x)
    return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}

def header(path,shape,dtype):
    with path.open('rb') as f:
        if f.read(8)!=b'\x93NUMPY\x01\x00': raise ValueError('version-one safe NPY')
        n=struct.unpack('<H',f.read(2))[0]
        if n>4096: raise ValueError('header bound')
        row=ast.literal_eval(f.read(n).decode('latin1'))
        if set(row)!={'descr','fortran_order','shape'} or row['descr']!=dtype or row['fortran_order'] or row['shape']!=shape: raise ValueError('exact numeric schema')
        start=f.tell(); item={'|u1':1,'<f4':4,'<f8':8}[dtype]
        if start+product(shape)*item!=path.stat().st_size: raise ValueError('exact array bytes')
    return start

def aid(raw,dtype,shape):
    return hashlib.sha256(json.dumps([dtype,list(shape)]).encode()+raw).hexdigest()

def accept(directory,expected,row):
    directory=Path(directory)
    if ident(directory/'MEMBERS.json')!=expected: raise ValueError('externally sealed source manifest')
    members=json.loads((directory/'MEMBERS.json').read_text())
    actual={str(p.relative_to(directory)).replace('\\','/') for p in directory.rglob('*') if p.is_file() and p.name!='MEMBERS.json'}
    if set(members)!=actual or sum(r['bytes'] for r in members.values())>12_000_000: raise ValueError('source members/output bound')
    for name,x in members.items():
        p=directory/name
        if name.startswith('/') or '..' in name.split('/') or '\\' in name or p.is_symlink() or ident(p)!=x: raise ValueError('source member identity')
    record=json.loads((directory/'record.json').read_text())
    if record['root']!=row or record['status']!='COLLECTED': raise ValueError('technical source failure')
    n=record['controller_actions']; task=row['task']; dim=7 if task=='pusht' else 2
    if not 0<=n<=44 or len(record['frames'])!=n+1 or record['available']!=(n==44): raise ValueError('collection action clock')
    expected_members={'evidence/pixels.npy','evidence/actions.npy','evidence/coordinates.npy','evidence/labels.npy','evidence/audits.json','record.json'}
    if n==44:
        expected_members|={'selector/history.npy','selector/goal.npy'}
        if row['role']!='diagnostic': expected_members|={'training/pixels.npy','training/labels.npy'}
    if set(members)!=expected_members: raise ValueError('source role-specific members')
    for name,shape,dtype in (('pixels',(n+1,224,224,3),'|u1'),('coordinates',(n+1,dim),'<f8'),('labels',(n+1,6 if task=='pusht' else 2),'<f8'),('actions',(n,2),'<f4' if task=='pusht' else '<f8')):
        p=directory/'evidence'/(name+'.npy'); start=header(p,shape,dtype)
        if name in ('pixels','coordinates'):
            row_bytes=product(shape[1:])*({'|u1':1,'<f8':8}[dtype])
            with p.open('rb') as f:
                f.seek(start)
                for i in range(n+1):
                    if aid(f.read(row_bytes),dtype,shape[1:])!=record['frames'][i][name]: raise ValueError('per-frame identity')
    audits=json.loads((directory/'evidence/audits.json').read_text())
    if len(audits)!=n+1: raise ValueError('audit clock')
    for i,x in enumerate(audits):
        if x['clock']!=i or x['wrapper_elapsed']!=i or hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()!=record['frames'][i]['audit']: raise ValueError('audit identity')
        if i<n and any(record['frames'][i][k] for k in ('success','terminated','truncated')): raise ValueError('post-terminal action')
    if n==44:
        for name,shape in (('history',(1,224,224,3)),('goal',(224,224,3))):
            p=directory/'selector'/(name+'.npy'); offset=header(p,shape,'|u1')
            with p.open('rb') as f: f.seek(offset); raw=f.read()
            if aid(raw,'|u1',(224,224,3))!=record['frames'][20 if name=='history' else 44]['pixels']: raise ValueError('same RGB source and goal')
    return {'root_id':row['root_id'],'available':n==44,'actions':n,'seal':expected,'independent_member_and_clock_verification':True}
