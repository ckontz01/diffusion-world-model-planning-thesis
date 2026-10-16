"""Unchanged frozen observer program; bounded explicit transport-failure receipt.

No R003 retry, remote diagnosis, research mutation or inference of cluster fault.
The next scheduled check is a new temporal snapshot, not a retry of missing data.
"""
import base64,hashlib,json,os,subprocess,sys
from .common import ROOT,DOC,identity,write_new
from wm_diag0_rc1_completion_v1.compact import program,transport_command,GRID_HASH
from wm_diag0_rc1_completion_v1.common import DOC as BUDGET

PROGRAM_SHA='6a6caa4c0eae6149bde0b45726a9ee5f7a7b0137590c648dda43047fe7f40023'
CAPTURE_PREFIX=2048


def canonical(z):return json.dumps(z,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')


def encode_record(z):
    # An explicit lossless technical-metadata schema, not scientific-data
    # compression or a storage discount. Every scheduler field is retained;
    # only the separately bound repeated dispatch prefix is represented once.
    out=dict(z);rows=[];rebuilt=[]
    for line in out.pop('scheduler').splitlines(keepends=True):
        if not line.endswith('\n'):raise ValueError('exact scheduler newline framing')
        fields=line[:-1].split('|')
        if len(fields)!=7 or not fields[0].startswith('317180_'):raise ValueError('exact bound scheduler fields')
        fields[0]=fields[0][7:];rows.append(fields)
        rebuilt.append('317180_'+'|'.join(fields)+'\n')
    if ''.join(rebuilt)!=z['scheduler']:raise ValueError('lossless scheduler representation required')
    indices=out.pop('accepted_indices')
    if indices!=sorted(set(indices)) or any(type(i) is not int or not 0<=i<124 for i in indices):raise ValueError('exact fixed accepted-index set')
    mask=sum(1<<i for i in indices)
    out.update(receipt_schema='WM-DIAG0-RC1-COMPACT-RECEIPT-v2',scheduler_rows=rows,
               accepted_indices_bitmask_hex=hex(mask),
               original_canonical_identity={'bytes':len(canonical(z)),'sha256':hashlib.sha256(canonical(z)).hexdigest()})
    if decode_record(out)!=z:raise ValueError('complete technical-record roundtrip')
    return out


def decode_record(z):
    out=dict(z)
    if out.pop('receipt_schema')!='WM-DIAG0-RC1-COMPACT-RECEIPT-v2':raise ValueError('explicit technical receipt schema')
    original=out.pop('original_canonical_identity');rows=out.pop('scheduler_rows')
    out['scheduler']=''.join('317180_'+'|'.join(row)+'\n' for row in rows)
    mask=int(out.pop('accepted_indices_bitmask_hex'),16)
    if not 0<=mask<1<<124:raise ValueError('fixed index bitmap bound')
    out['accepted_indices']=[i for i in range(124) if mask&(1<<i)]
    if {'bytes':len(canonical(out)),'sha256':hashlib.sha256(canonical(out)).hexdigest()}!=original:raise ValueError('every original technical field independently reconstructs')
    return out


def write_compact(path,z):
    raw=canonical(z)+b'\n'
    if len(raw)>10000:raise ValueError('hard serialized monitoring success-receipt bound')
    if any(p.is_symlink() or (p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400) for p in path.parents):raise ValueError('no receipt destination redirect')
    with path.open('xb') as f:
        if f.write(raw)!=len(raw):raise IOError('short compact receipt write')
        f.flush();os.fsync(f.fileno())


def failure(returncode,stdout,stderr,kind):
    if returncode is not None and type(returncode) is not int:raise ValueError('exact observed return code or unavailable')
    out={}
    for name,raw in (('stdout',stdout),('stderr',stderr)):
        if not isinstance(raw,bytes):raise ValueError('owned transport binary capture')
        out[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                   'retained_prefix_base64':base64.b64encode(raw[:CAPTURE_PREFIX]).decode('ascii'),
                   'retained_prefix_limit':CAPTURE_PREFIX,'truncated':len(raw)>CAPTURE_PREFIX}
    return {'status':'OBSERVATION_UNAVAILABLE_NO_RESEARCH_INFERENCE',
            'failure_kind':kind,'transport_returncode':returncode,'captured':out,
            'dispatch':'317180','program_sha256':PROGRAM_SHA,
            'research_failure_inferred':False,'research_jobs_or_controllers_changed':False,
            'automatic_retry':False,'scientific_values_read':False,'final_gate_ready':False}


def interpret(returncode,stdout,stderr):
    if returncode:return None,failure(returncode,stdout,stderr,'NONZERO_TRANSPORT_OR_REMOTE_NO_CAUSE_ASSUMED')
    if len(stdout)>16000 or len(stderr)>16000:return None,failure(returncode,stdout,stderr,'CAPTURED_METADATA_BOUND_STOP')
    try:
        z=json.loads(stdout)
        if not isinstance(z,dict) or z['dispatch']['array_job_id']!='317180' or z['dispatch']['contract_sha256']!=GRID_HASH or z['dispatch']['indices']!=124 or z['scientific_values_or_quality_or_aggregates_inspected'] is not False or z['research_jobs_or_controllers_changed'] is not False:raise ValueError('unchanged exact technical observer schema')
    except (ValueError,KeyError,TypeError):return None,failure(returncode,stdout,stderr,'INVALID_COMPACT_TECHNICAL_METADATA_STOP')
    return z,None


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive new scheduled temporal observation label')
    dst=BUDGET/('OBSERVE-'+label+'.json');started=BUDGET/('OBSERVE-'+label+'.started.json')
    failed=BUDGET/('OBSERVE-'+label+'.failure.json')
    if any(p.exists() for p in (dst,started,failed)):raise FileExistsError('no completed/started/failure observation retry')
    pub=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if pub['status']!='MONITOR_V2_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED':raise ValueError('new source publication/SSD gate')
    old=json.loads((BUDGET/'SSD-VERIFIED-001.json').read_text())
    if old['whole']!=pub['original_completion_package'] or old['source_commit']!='4f48225abf359eae9597488179c1e496f175f940':raise ValueError('unchanged independently preserved prior dependency package')
    for table in (old['working_source_members'],pub['working_source_members']):
        for name,want in table.items():
            if identity(ROOT/name)!=want:raise ValueError('published source/evidence changed')
    source=program()
    if hashlib.sha256(source.encode()).hexdigest()!=PROGRAM_SHA:raise ValueError('NO observer read/scheduler/control/science change')
    write_new(started,{'dispatch':'317180','program_sha256':PROGRAM_SHA,
                      'original_source_package':old['whole'],'diagnostic_wrapper_package':pub['whole'],
                      'automatic_retry':False,'one_new_temporal_snapshot':True})
    try:
        p=subprocess.run(transport_command(source),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=26)
        z,error=interpret(p.returncode,p.stdout,p.stderr)
    except subprocess.TimeoutExpired as exc:
        z=None;error=failure(None,exc.stdout or b'',exc.stderr or b'','NATIVE_TRANSPORT_TIMEOUT_NO_RESEARCH_INFERENCE')
    except OSError as exc:
        z=None;error=failure(None,b'',str(exc).encode('utf8')[:16000],'LOCAL_TRANSPORT_START_UNAVAILABLE')
    if error is not None:
        write_new(failed,error,limit=8000)
        print(json.dumps({'status':error['status'],'failure_kind':error['failure_kind'],
                          'transport_returncode':error['transport_returncode'],'receipt':identity(failed),
                          'research_failure_inferred':False,'automatic_retry':False}))
        return 125
    write_compact(dst,encode_record(z))
    print(json.dumps({'status':z['status'],'receipt':identity(dst),
                      'scientific_values_or_quality_or_aggregates_inspected':False,
                      'research_jobs_or_controllers_changed':False}))
    return 0


if __name__=='__main__':sys.exit(main())
