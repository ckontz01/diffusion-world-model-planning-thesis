import json
from wm_diag0_rc1_v1.common import ROOT,DOC,identity,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    c=json.loads((ROOT/'docs/world-model-diagnostic-rc1-v1-20261016/RC1-CONTRACT.json').read_text())
    p=c['prior_source']+'/lewm/jepa.py';expected=c['prior_members']['lewm/jepa.py']
    program='import hashlib,json,pathlib\np=pathlib.Path('+repr(p)+')\nb=p.read_bytes()\n'
    program+='if {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}!='+repr(expected)+':raise ValueError("pinned source identity")\n'
    program+='if len(b)>30000:raise ValueError("bounded source")\nprint(json.dumps({"source":b.decode(),"identity":'+repr(expected)+',"model_calls":0,"objects_loaded":False}))'
    write_new(DOC/'RUNTIME-SOURCE-001.started.json',{'path':p,'identity':expected,'model_calls':0})
    z=ssh(program);write_new(DOC/'RUNTIME-SOURCE-001.json',z);print(json.dumps(z,indent=2))

if __name__=='__main__':main()
