"""Bounded trusted program/stdin framing over the SAME configured SSH route."""
import ast,base64,hashlib,json,shlex,subprocess
from .common import DOC,identity,write_new
from .transport import stream

BOOTSTRAP="""import sys,hashlib
header=sys.stdin.buffer.readline(90)
n,h=header.decode('ascii').strip().split(':')
if not n.isdigit() or not 1<=int(n)<=160000:raise ValueError('bounded program frame')
raw=sys.stdin.buffer.read(int(n))
if len(raw)!=int(n) or hashlib.sha256(raw).hexdigest()!=h:raise ValueError('exact trusted program frame')
exec(compile(raw,'<reviewed-wm-final-program>','exec'),globals())
"""

def frame(code,data):
    ast.parse(code,feature_version=(3,6));raw=code.encode()
    if not 0<len(raw)<=160000:raise ValueError('finite trusted program')
    payload=json.dumps(data,separators=(',',':'),allow_nan=False).encode()
    if len(payload)>2000000:raise ValueError('finite technical JSON input')
    return (str(len(raw))+':'+hashlib.sha256(raw).hexdigest()+'\n').encode()+raw+payload

def call(label,code,data=None,seconds=60):
    if not label.isalnum():raise ValueError('exclusive operation label')
    start=DOC/(label+'.started.json');target=DOC/(label+'.json')
    if start.exists() or target.exists():raise FileExistsError('never repeat an ambiguous/completed operation')
    payload=frame(code,data)
    remote='timeout --kill-after=1s '+str(seconds-8)+'s python3 -B -c '+shlex.quote(BOOTSTRAP)
    args=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout',str(seconds-3)+'s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','ConnectionAttempts=1','prometheus',remote]
    if sum(map(len,args))>4000:raise ValueError('short native command line')
    write_new(start,{'source':identity(__file__),'program':{'bytes':len(code.encode()),'sha256':hashlib.sha256(code.encode()).hexdigest()},
        'input_bytes':len(payload),'seconds':seconds,'configured_route_unchanged':True})
    try:p=subprocess.run(args,input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    except (subprocess.TimeoutExpired,OSError) as e:
        write_new(DOC/(label+'.failure.json'),{'error':repr(e),'stdout':stream(getattr(e,'stdout',None) or b''),'stderr':stream(getattr(e,'stderr',None) or b'')});raise
    if p.returncode:
        write_new(DOC/(label+'.failure.json'),{'returncode':p.returncode,'stdout':stream(p.stdout),'stderr':stream(p.stderr)})
        raise RuntimeError('remote diagnostic retained; no blind retry')
    if len(p.stdout)>200000:raise ValueError('bounded technical reply')
    result=json.loads(p.stdout);write_new(target,result,limit=250000);return result
