"""Read the exact previously used Le-WM class source, without importing it."""
import json
from wm_diag0_preflight_v1.transport import ssh
from wm_diag0_preflight_v1.common import DOC, REMOTE, SITE, write_new

def main():
    code = '''
import hashlib,pathlib,json
root=pathlib.Path(REMOTE)/'src/hi-lewm/third_party/lewm'
result={}
for name in ('jepa.py','module.py'):
 p=root/name; raw=p.read_bytes()
 if len(raw)>200000: raise RuntimeError('source size bound')
 result[name]={'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'source':raw.decode('utf8')}
print(json.dumps(result))
'''
    result=ssh('REMOTE='+repr(REMOTE)+'\n'+code)
    if result['jepa.py']['sha256']!='41bad7fd21e0f14aea4c9c3d39a9c87037e787746d953ab62cdc0677e938ce96':
        write_new(DOC/'LEWM-SOURCE-MISMATCH.json',result)
        raise ValueError('historical accepted JEPA hash changed; no load')
    write_new(DOC/'LEWM-SOURCE-001.json',result)
    print(json.dumps({n:{k:v for k,v in r.items() if k!='source'} for n,r in result.items()},indent=2))

if __name__=='__main__': main()
