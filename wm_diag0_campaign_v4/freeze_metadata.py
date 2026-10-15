import json
from .common import DOC,canonical,write_new
from wm_diag0_source_r3.common import RUN
from wm_diag0_native_v3.transport import ssh

def main():
    r=ssh('RUN='+repr(RUN)+'\n'+'''
import hashlib,json,pathlib
r=pathlib.Path(RUN);out={}
for name in ('ALL-SOURCES-ACCEPTED.json','COMPILED-PHYSICS-BOUND.json'):
 p=r/'controls'/name;b=p.read_bytes();row=json.loads(b)
 out[name]={'identity':{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},'canonical':hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()}
print(json.dumps(out))
''')
    for name,local in (('ALL-SOURCES-ACCEPTED.json','SOURCE-GATE-001.json'),('COMPILED-PHYSICS-BOUND.json','COMPILED-PHYSICS-BOUND-001.json')):
        if r[name]['canonical']!=canonical(json.loads((DOC/local).read_text())):raise ValueError('local/remote authenticated technical control identity')
    write_new(DOC/'SOURCE-CONTROL-IDENTITIES-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
