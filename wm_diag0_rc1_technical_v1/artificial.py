"""New CPU artificial ragged-reference fixture; no real objects/data/GPU."""
import base64,hashlib,json
from .common import ROOT,DOC,RUN,HEADS_RUN,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    from wm_diag0_rc1_v1.artificial import PROGRAM
    c=json.loads((ROOT/'docs/world-model-diagnostic-rc1-heads-v1-20261016/HEADS-CONTRACT.json').read_text())
    files={'wm_diag0_rc1_technical_v1/'+n:(ROOT/'wm_diag0_rc1_technical_v1'/n).read_bytes() for n in ('__init__.py','common.py','reference.py','tests.py')}
    payload={'files':{n:base64.b64encode(b).decode() for n,b in files.items()},'identities':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in files.items()}}
    values={'TEST_ROOT':RUN+'-artificial-ONE','OLD_SOURCE':HEADS_RUN+'/source','DINO_SOURCE':HEADS_RUN+'/source/dino','VENV':c['venv'],'SIF':c['sif']}
    program=PROGRAM.replace("'wm_diag0_rc1_v1.tests'","'wm_diag0_rc1_technical_v1.tests'")
    write_new(DOC/'ARTIFICIAL-REFERENCE-001.started.json',{'source':payload['identities'],'real_inputs':False})
    z=ssh('\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+program,json.dumps(payload).encode())
    write_new(DOC/'ARTIFICIAL-REFERENCE-001.json',z);print(json.dumps(z,indent=2))
    if z['returncode']:raise RuntimeError('preserve failed artificial fixture; no blind repeat')

if __name__=='__main__':main()
