"""Bounded stdin frames over the existing configured WSL/SSH route only."""
import ast,hashlib,json,shlex,subprocess
from pathlib import Path
from .common import DOC,identity,write_new

BOOT="""import sys,hashlib
n,h=sys.stdin.buffer.readline(90).decode('ascii').strip().split(':')
if not n.isdigit() or not 0<int(n)<=160000:raise ValueError('bounded reviewed program')
b=sys.stdin.buffer.read(int(n))
if len(b)!=int(n) or hashlib.sha256(b).hexdigest()!=h:raise ValueError('exact reviewed program')
exec(compile(b,'<wm-diag1-saved-reviewed>','exec'),globals())
"""
def call(label,code,data,seconds=50):
    if not label.isalnum() or (DOC/(label+'.started.json')).exists() or (DOC/(label+'.json')).exists():raise FileExistsError('exclusive remote action; never repeat ambiguity')
    if not Path('D:/WSL/Thesis-Ubuntu/ext4.vhdx').is_file():raise FileNotFoundError('existing configured WSL path unavailable; no alternate environment')
    ast.parse(code,feature_version=(3,6));raw=code.encode();payload=json.dumps(data,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>160000 or len(payload)>4000000:raise ValueError('small new source/metadata input only')
    frame=(str(len(raw))+':'+hashlib.sha256(raw).hexdigest()+'\n').encode()+raw+payload
    remote='timeout --kill-after=1s '+str(seconds-8)+'s python3 -B -c '+shlex.quote(BOOT)
    args=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout',str(seconds-3)+'s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','prometheus',remote]
    write_new(DOC/(label+'.started.json'),{'source':identity(__file__),'program_sha256':hashlib.sha256(raw).hexdigest(),'input_bytes':len(frame),'operation_seconds':seconds,'route_unchanged':True})
    try:p=subprocess.run(args,input=frame,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    except (OSError,subprocess.TimeoutExpired) as e:
        write_new(DOC/(label+'.failure.json'),{'error':repr(e),'stdout':getattr(e,'stdout',b'').decode('utf8',errors='replace') if getattr(e,'stdout',None) else '', 'stderr':getattr(e,'stderr',b'').decode('utf8',errors='replace') if getattr(e,'stderr',None) else ''});raise
    if p.returncode or len(p.stdout)>4000000 or len(p.stderr)>100000:
        write_new(DOC/(label+'.failure.json'),{'returncode':p.returncode,'stdout':p.stdout.decode('utf8',errors='replace'),'stderr':p.stderr.decode('utf8',errors='replace')},limit=4500000)
        raise RuntimeError('saved remote diagnostic; no automatic retry')
    result=json.loads(p.stdout);write_new(DOC/(label+'.json'),result);return result
