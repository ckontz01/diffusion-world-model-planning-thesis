"""Future staging/CPU gate: reauthenticate every historical evidence byte.

No collector, network, scheduler, deserializer, model or analysis entry point.
The exact combined receipt is pinned independently; its boolean provenance flag
alone never authorizes anything. Old source-arithmetic limitations remain intact.
"""
import hashlib,json,os,stat
from pathlib import Path
from .archive_v2 import token,open_regular,check_time,canonical
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity

USAGE={'bytes':18914,'sha256':'4fa900858fdadb31d978341b20e10a6568a8796e4d5dddcf22ed36a405666373'}
STUDY='/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015'
KEYS=('visual_encoder_calls','encoded_frames','proprio_encoder_calls','action_encoder_calls','predictor_calls','cost_api_calls')
DINO=dict(zip(KEYS,(923,1613,1018,115,485,37)))
LEWM=dict(zip(KEYS,(88,704,0,0,0,0)))
MAX_FILES=59
MAX_FILE=2000000
MAX_TOTAL=3000000


def ordinary(path):
    p=Path(path)
    if not p.is_absolute() or '..' in p.parts:raise ValueError('explicit canonical absolute evidence path')
    for q in (p,)+tuple(p.parents):
        s=q.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no evidence or ancestor alias/reparse redirect')
    return p


def bound_bytes(path,expected,limit,deadline,retain=False):
    valid_identity(expected,limit);check_time(deadline);p=ordinary(path);before=token(p)
    if before[2]!=expected['bytes']:raise ValueError('exact externally bound evidence size before open')
    h=hashlib.sha256();count=0;parts=[]
    with open_regular(p,before) as f:
        while count<expected['bytes']:
            check_time(deadline);raw=f.read(min(1048576,expected['bytes']-count))
            if not raw:raise ValueError('historical evidence truncated')
            count+=len(raw);h.update(raw)
            if retain:parts.append(raw)
        if f.read(1):raise ValueError('historical evidence grew')
    if token(p)!=before or {'bytes':count,'sha256':h.hexdigest()}!=expected:raise ValueError('historical evidence content or identity changed')
    check_time(deadline)
    return b''.join(parts) if retain else expected


def unique(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ValueError('duplicate evidence JSON key')
        out[k]=v
    return out


def bound_json(path,expected,limit,deadline):
    raw=bound_bytes(path,expected,limit,deadline,retain=True)
    def nonfinite(value):raise ValueError('nonfinite evidence JSON')
    return json.loads(raw.decode('utf8'),object_pairs_hook=unique,parse_constant=nonfinite)


def validate_usage_body(body):
    if body.get('status')!='ACTUAL_HISTORICAL_USAGE_AND_EXACT_FAILURE_PHASE_AUTHENTICATED_NOT_FINAL_GATE':raise ValueError('exact completed historical evidence disposition')
    if body.get('DINO_baseline')!=DINO or body.get('LeWM_baseline')!=LEWM:raise ValueError('unchanged historical counters, no new instrumentation')
    for name in ('DINO_baseline','LeWM_baseline'):
        if set(body[name])!=set(KEYS) or any(type(v) is not int or v<0 for v in body[name].values()):raise ValueError('exact nonboolean invocation counts')
    if type(body.get('baseline_encoded_frames_all_six_fits_and_failed_diagnostics')) is not int or body['baseline_encoded_frames_all_six_fits_and_failed_diagnostics']!=2317:
        raise ValueError('all retained fits plus failed diagnostic frames')
    if body.get('source_arithmetic_is_not_hook_measurement') is not True or body.get('new_retroactive_hooks_or_model_calls')!=0:
        raise ValueError('source arithmetic disclosure cannot become retrospective hooks')
    phase=body.get('failure_disposition',{})
    if phase.get('line')!=98 or phase.get('two_extra_restoration_checks_not_reached') is not True or phase.get('baseline_counters_changed') is not False:
        raise ValueError('original failure phase and unperformed work retained')
    evidence=body.get('evidence')
    if not isinstance(evidence,dict) or len(evidence)!=MAX_FILES or sum(x.get('bytes',MAX_TOTAL+1) for x in evidence.values())!=2826430:
        raise ValueError('exact complete59-file failure-inclusive evidence set and bytes')
    return evidence


def authenticate_evidence(evidence,approved_root,deadline):
    """Opaque stream hashes only; no NPY/array/pickle/result interpretation."""
    root=ordinary(approved_root)
    if not root.is_dir() or not isinstance(evidence,dict) or not 0<len(evidence)<=MAX_FILES:raise ValueError('one bounded explicit evidence root and file map')
    total=0
    for name,want in sorted(evidence.items()):
        valid_identity(want,MAX_FILE);p=Path(name)
        if str(p)!=name or not p.is_absolute() or root not in p.parents:raise ValueError('every source/control/partial belongs to the canonical study')
        total+=want['bytes']
        if total>MAX_TOTAL:raise ValueError('finite aggregate historical authentication bytes')
        bound_bytes(p,want,MAX_FILE,deadline)
    raw=canonical(evidence)
    return {'authenticated_files':len(evidence),'opaque_bytes_hashed':total,
            'complete_expected_evidence_map':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
            'file_payloads_deserialized_or_interpreted':False}


def authenticate_usage(receipt,expected,deadline):
    """Production callers must also bind this exact identity in final contract.

    A local synthetic test does not call this against real cluster paths. This
    function is for the separately frozen actual stage and CPU validator only.
    """
    if expected!=USAGE:raise PermissionError('only exact combined historical002 receipt, not a self-declared ready flag')
    body=bound_json(receipt,expected,32768,deadline);evidence=validate_usage_body(body)
    proof=authenticate_evidence(evidence,STUDY,deadline)
    if proof['authenticated_files']!=59 or proof['opaque_bytes_hashed']!=2826430:raise ValueError('no missing failed source/control/log/partial evidence')
    proof.update(status='ALL59_HISTORICAL_ORIGINAL_EVIDENCE_IDENTITIES_REAUTHENTICATED',receipt=expected,
                 original_uncached_PushT='FAILED',original_uncached_Reacher='UNTESTED',
                 research_calls=0,analysis_authority_granted=False,final_gate_ready=False)
    return proof
