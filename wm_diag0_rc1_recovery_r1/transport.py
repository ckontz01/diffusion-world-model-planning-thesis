"""One bounded existing-credential transport, lossless failure receipts."""
import ast,base64,json,shlex,subprocess,sys
from .common import DOC,digest,identity,write_new

def call(label,code,data=None,seconds=60):
    if not label.isalnum():raise ValueError('exclusive operation label')
    start=DOC/(label+'.started.json');target=DOC/(label+'.json')
    if start.exists() or target.exists():raise FileExistsError('never repeat a started/ambiguous operation')
    ast.parse(code,feature_version=(3,6))
    write_new(start,{'program':digest(code.encode()),'source':identity(__file__),'seconds':seconds})
    remote='timeout --kill-after=1s '+str(seconds-8)+'s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(code.encode()).decode())+'))')
    args=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout',str(seconds-3)+'s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','ConnectionAttempts=1','prometheus',remote]
    try:p=subprocess.run(args,input=canonical_input(data),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        write_new(DOC/(label+'.failure.json'),{'timeout':True,'stdout':stream(exc.stdout or b''),'stderr':stream(exc.stderr or b'')});raise
    if p.returncode:
        write_new(DOC/(label+'.failure.json'),{'returncode':p.returncode,'stdout':stream(p.stdout),'stderr':stream(p.stderr)});raise RuntimeError('remote failure retained; no automatic retry')
    if len(p.stdout)>120000:raise ValueError('finite technical response')
    z=json.loads(p.stdout);write_new(target,z,limit=150000);return z

def canonical_input(data):return json.dumps(data,sort_keys=True,separators=(',',':')).encode() if data is not None else None
def stream(b):return dict(digest(b),prefix_base64=base64.b64encode(b[:4096]).decode())
