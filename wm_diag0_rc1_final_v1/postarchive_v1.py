"""Bounded immutable postarchive control sidecars; NOT a ready final gate.

The future controller must independently authenticate exact terminal CPU/control
identities. A sidecar preserves those supplied controls, not their truth. No
sidecar contains its own hash; final external readback receipt anchors it.
"""
import base64,hashlib,os
from pathlib import Path
from .archive_v1 import canonical,check_time,token,open_regular
from .archive_verify_v1 import strict_json
from .inventory import safe_name

MAX_FILES=64
MAX_FILE=1100000
MAX_RAW=2000000
MAX_SIDECAR=4000000


def digest(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def valid_identity(x,limit):
    if not isinstance(x,dict) or set(x)!={'bytes','sha256'} or type(x['bytes']) is not int or not 0<=x['bytes']<=limit:
        raise ValueError('exact bounded byte identity')
    s=x['sha256']
    if not isinstance(s,str) or len(s)!=64 or any(c not in '0123456789abcdef' for c in s):raise ValueError('exact SHA256')


def inputs(binding,phase,previous,expected):
    if not isinstance(binding,dict) or set(binding)!={'final_contract_sha256','archive_whole','archive_manifest','analysis_output_seal'}:
        raise ValueError('external final contract/archive/acceptance binding')
    valid_identity({'bytes':0,'sha256':binding['final_contract_sha256']},0)
    valid_identity(binding['archive_whole'],14000000000);valid_identity(binding['archive_manifest'],20000000)
    valid_identity(binding['analysis_output_seal'],20000000)
    if phase not in ('TERMINAL_CPU','SSD_TRANSFER'):raise ValueError('fixed postarchive control phases')
    if phase=='TERMINAL_CPU' and previous is not None:raise ValueError('first sidecar has no invented predecessor')
    if phase=='SSD_TRANSFER':valid_identity(previous,MAX_SIDECAR)
    if not isinstance(expected,dict) or not 0<len(expected)<=MAX_FILES:raise ValueError('explicit complete bounded control allowlist')
    total=0
    for name,x in expected.items():
        safe_name(name);valid_identity(x,MAX_FILE);total+=x['bytes']
    if total>MAX_RAW:raise ValueError('postarchive control reservation')


def build(root,expected,binding,phase,previous,deadline):
    """Read only explicit postarchive metadata, never scientific result files."""
    inputs(binding,phase,previous,expected);root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('exact postarchive control root')
    found={}
    for directory,dirs,names in os.walk(str(root),followlinks=False):
        check_time(deadline)
        if any((Path(directory)/n).is_symlink() for n in dirs):raise ValueError('no postarchive symlink directory')
        for name in names:
            path=Path(directory)/name;rel=path.relative_to(root).as_posix();safe_name(rel)
            if rel not in expected or rel in found or path.is_symlink():raise ValueError('unknown/duplicate/redirected control must be reconciled')
            before=token(path)
            if before[2]!=expected[rel]['bytes']:raise ValueError('exact independently bound control size')
            with open_regular(path,before) as f:
                check_time(deadline);raw=f.read(MAX_FILE+1)
            if token(path)!=before or digest(raw)!=expected[rel]:raise ValueError('terminal control changed from supplied authentication')
            found[rel]={'identity':expected[rel],'base64':base64.b64encode(raw).decode('ascii')}
    if set(found)!=set(expected):raise ValueError('no missing postarchive controls')
    raw=canonical({'schema':'WM-DIAG0-RC1-POSTARCHIVE-v1','binding':binding,'phase':phase,'previous_sidecar':previous,'controls':found})
    if len(raw)>MAX_SIDECAR:raise ValueError('bounded compact sidecar')
    check_time(deadline);return raw


def verify(raw,expected,binding,phase,previous,expected_identity,deadline):
    inputs(binding,phase,previous,expected);valid_identity(expected_identity,MAX_SIDECAR);check_time(deadline)
    if not isinstance(raw,bytes) or len(raw)>MAX_SIDECAR or digest(raw)!=expected_identity:raise ValueError('exact externally authenticated sidecar bytes')
    body=strict_json(raw)
    if set(body)!={'schema','binding','phase','previous_sidecar','controls'} or body['schema']!='WM-DIAG0-RC1-POSTARCHIVE-v1' or body['binding']!=binding or body['phase']!=phase or body['previous_sidecar']!=previous or not isinstance(body['controls'],dict) or set(body['controls'])!=set(expected):
        raise ValueError('exact external sidecar chain and complete controls')
    for name,row in body['controls'].items():
        check_time(deadline)
        if not isinstance(row,dict) or set(row)!={'identity','base64'} or row['identity']!=expected[name] or not isinstance(row['base64'],str) or len(row['base64'])>4*((MAX_FILE+2)//3):raise ValueError('bounded exact control schema')
        try:content=base64.b64decode(row['base64'].encode('ascii'),validate=True)
        except (ValueError,UnicodeError) as exc:raise ValueError('invalid inert control encoding: '+str(exc))
        if digest(content)!=expected[name]:raise ValueError('every original control byte independently matched')
    return {'status':'POSTARCHIVE_WHOLE_AND_EVERY_CONTROL_VERIFIED','identity':expected_identity,'phase':phase,
            'controls_verified':len(expected),'decoded_controls_executed':0,'scientific_results_inspected':False}


def write_exclusive(path,raw,deadline,control_root):
    if len(raw)>MAX_SIDECAR:raise ValueError('sidecar byte limit')
    path=Path(path);root=Path(control_root);check_time(deadline)
    if not path.is_absolute() or not root.is_absolute() or path==root or root in path.parents:raise ValueError('sidecar outside its explicit input-control root')
    if any(p.is_symlink() for p in path.parents):raise ValueError('no sidecar ancestor redirect')
    with path.open('xb') as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    check_time(deadline);return digest(raw)
