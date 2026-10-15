"""Repair remote control quoting; reuse all authenticated R4/R5 suppliers."""
import hashlib,json,zlib
from pathlib import Path
from .common import DOC,RUN,identity,write_new
from .transport import ssh
from wm_diag0_preflight_v1.common import SIF,VENV

def receive_code():
    return 'RUN='+repr(RUN)+'\n'+'''
import hashlib,json,os,pathlib,sys,zlib
root=pathlib.Path(RUN);libs=root/'renderer-r6';libs.mkdir(exist_ok=False)
header=sys.stdin.buffer.readline(100000);m=json.loads(header)
packet=sys.stdin.buffer.read(65000001)
if len(packet)>65000000:raise ValueError('compressed transfer bound')
dec=zlib.decompressobj();raw=dec.decompress(packet,200000001)
if not dec.eof or dec.unused_data or dec.unconsumed_tail or len(raw)!=m['regular_library_bytes'] or len(raw)>200000000:raise ValueError('finite library bytes')
offset=0
for name,x in sorted(m['members'].items()):
 if '/' in name or chr(92) in name or not name.startswith('lib') or x['bytes']>160000000:raise ValueError('library allowlist')
 b=raw[offset:offset+x['bytes']];offset+=len(b)
 if len(b)!=x['bytes'] or hashlib.sha256(b).hexdigest()!=x['sha256']:raise ValueError('library identity')
 p=libs/name
 with p.open('xb') as f:f.write(b)
 p.chmod(0o444)
for name,target in m['aliases'].items():
 if any('/' in v or chr(92) in v or not v.startswith('lib') for v in (name,target)):raise ValueError('relative library alias')
 seen=set();t=target
 while t in m['aliases']:
  if t in seen:raise ValueError('alias cycle')
  seen.add(t);t=m['aliases'][t]
 if t not in m['members']:raise ValueError('alias escapes reviewed closure')
 (libs/name).symlink_to(target)
with (root/'controls/RENDERER-R6-MANIFEST.json').open('xb') as f:f.write(header.rstrip(bytes([10])))
libs.chmod(0o555)
print(json.dumps({'status':'AUTHENTICATED_READONLY_LIBRARY_LAYER_STAGED','regular_bytes':len(raw),'members':len(m['members']),'aliases':len(m['aliases']),'copied_model_bytes':0}))
'''

def main():
    observed=ssh('RUN='+repr(RUN)+'\n'+'''
import json,pathlib
r=pathlib.Path(RUN)
print(json.dumps({'r5_exists':(r/'renderer-r5').exists(),'r5_manifest_exists':(r/'controls/RENDERER-R5-MANIFEST.json').exists(),'r6_exists':(r/'renderer-r6').exists(),'r6_manifest_exists':(r/'controls/RENDERER-R6-MANIFEST.json').exists(),'prior_failure':'remote Python syntax error before code executed'}))
''')
    write_new(DOC/'RENDERER-R6-RECONCILIATION.json',observed)
    if any(v for k,v in observed.items() if k.endswith('exists')):raise RuntimeError('reconcile unexpected stage before action')
    m=json.loads((DOC/'RENDERER-R5-MANIFEST.json').read_text());paths={}
    for name,row in m['members'].items():
        p=DOC/'delivery/renderer-r4/libraries'/name
        if not p.is_file():p=DOC/'delivery/renderer-r5-supplement'/name
        if identity(p)!=row:raise ValueError('authenticated successful library supplier')
        paths[name]=p
    payload=json.dumps(m).encode()+b'\n'+zlib.compress(b''.join(paths[n].read_bytes() for n in sorted(paths)),1)
    if len(payload)>65_000_000:raise ValueError('transfer bound')
    write_new(DOC/'RENDERER-R6-STAGE-001.started.json',{'manifest':identity(DOC/'RENDERER-R5-MANIFEST.json'),'payload_bytes':len(payload),'old_failure_preserved':True})
    result=ssh(receive_code(),payload=payload,timeout=120);write_new(DOC/'RENDERER-R6-STAGE-001.json',result);print(json.dumps(result))

if __name__=='__main__':main()
