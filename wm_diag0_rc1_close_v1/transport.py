"""Existing configured transport, exclusive final-close receipts; no retry."""
import ast,base64,json,shlex,subprocess
from pathlib import Path
from .common import DOC,identity,write_new

def call(label,code,data=None,seconds=60):
    if not label.isalnum():raise ValueError('exclusive label')
    target=DOC/(label+'.json');start=DOC/(label+'.started.json')
    if start.exists() or target.exists():raise FileExistsError('never repeat started/ambiguous operation')
    ast.parse(code,feature_version=(3,6));raw=code.encode()
    import hashlib
    write_new(start,{'program':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'source':identity(__file__),'seconds':seconds})
    remote='timeout --kill-after=1s '+str(seconds-8)+'s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(raw).decode())+'))')
    args=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout',str(seconds-3)+'s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','ConnectionAttempts=1','prometheus',remote]
    try:p=subprocess.run(args,input=json.dumps(data,separators=(',',':')).encode() if data is not None else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    except subprocess.TimeoutExpired as e:
        write_new(DOC/(label+'.failure.json'),{'timeout':True,'stdout':stream(e.stdout or b''),'stderr':stream(e.stderr or b'')});raise
    if p.returncode:
        write_new(DOC/(label+'.failure.json'),{'returncode':p.returncode,'stdout':stream(p.stdout),'stderr':stream(p.stderr)})
        raise RuntimeError('saved remote failure; no automatic retry')
    if len(p.stdout)>150000:raise ValueError('finite technical stdout')
    z=json.loads(p.stdout);write_new(target,z,limit=200000);return z

def stream(raw):
    import hashlib
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'prefix_base64':base64.b64encode(raw[:4096]).decode()}
