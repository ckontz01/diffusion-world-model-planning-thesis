"""Exclusive campaign source namespace; reuse only authenticated source bytes."""
import base64,hashlib,json
from .common import DOC,RUN,write_new
from .build import additions
from .small import published
from wm_diag0_native_v3.transport import ssh

def main():
    publication=published('campaign');raw=(DOC/'campaign/CONTRACT.json').read_bytes();expected=hashlib.sha256(raw).hexdigest()
    payload=json.dumps({'contract':base64.b64encode(raw).decode(),'additions':{n:base64.b64encode(b).decode() for n,b in additions().items()},'publication':publication}).encode()
    write_new(DOC/'campaign/STAGE-001.started.json',{'contract':expected,'run':RUN})
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\n'+'''
import base64,hashlib,json,os,pathlib,sys
r=pathlib.Path(RUN);data=json.load(sys.stdin);raw=base64.b64decode(data['contract']);c=json.loads(raw)
if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError('exact contract')
supplier=pathlib.Path(c['source_supplier']);old=json.loads((supplier/'source/CONTRACT.json').read_text())
if hashlib.sha256((supplier/'controls/ALL-SOURCES-ACCEPTED.json').read_bytes()).hexdigest()!=c['source_acceptance']['sha256']:raise ValueError('complete source acceptance')
r.mkdir(exist_ok=False)
for n in ('source','controls','tasks','logs','tmp'):(r/n).mkdir()
for name,x in c['staged_members'].items():
 p=r/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name in data['additions']:
  b=base64.b64decode(data['additions'][name])
  if len(b)!=x['bytes'] or hashlib.sha256(b).hexdigest()!=x['sha256']:raise ValueError('new exact source')
  with p.open('xb') as f:f.write(b)
  p.chmod(0o444)
 else:
  src=supplier/'source'/name
  if x!=old['staged_members'][name] or src.is_symlink() or src.stat().st_size!=x['bytes'] or hashlib.sha256(src.read_bytes()).hexdigest()!=x['sha256']:raise ValueError('frozen source supplier')
  os.link(str(src),str(p))
with (r/'source/CONTRACT.json').open('xb') as f:f.write(raw)
(r/'source/CONTRACT.json').chmod(0o444)
os.link(str(supplier/'controls/RUNTIME-MANIFEST.json'),str(r/'controls/RUNTIME-MANIFEST.json'))
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
row={'status':'CAMPAIGN_SOURCE_AUTHENTICATED','contract_sha256':EXPECTED,'members':len(c['staged_members']),'models_or_successful_outputs_recopied':0}
with (r/'controls/STAGE-VERIFIED.json').open('x') as f:json.dump(row,f,sort_keys=True)
with (r/'controls/PUBLICATION-AND-SMALL-SSD.json').open('x') as f:json.dump(data['publication'],f,sort_keys=True)
print(json.dumps(row))
'''
    r=ssh(code,payload=payload);write_new(DOC/'campaign/STAGE-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
