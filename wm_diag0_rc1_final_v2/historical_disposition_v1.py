"""Bind the exact observed failure point to disclosed source counter arithmetic.

Local metadata/source only. No second remote read, scheduler query or compute.
V1's rejected assumed cost assertion is preserved; the actual failure was the
next full-forecast assertion AFTER the same native reference had run.
"""
import ast,copy,json
from pathlib import Path
from .historical_usage_v1 import arithmetic
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def failure_point(z,raw,source_identity):
    if z['exception_classes']!=['AssertionError'] or (z['job_id'],z['array_job_id'])!=('317171','317164'):raise ValueError('exact preserved failure allocation/class')
    frames=[f for f in z['frames'] if f['file'].endswith('/wm_diag0_campaign_v4/diagnostic.py') and f['function']=='parity']
    if len(frames)!=1:raise ValueError('unique actual diagnostic parity frame')
    frame=frames[0];expression="torch.testing.assert_close(torch.from_numpy(predicted.values).to(adapter.device),native['visual'][:,1:].float(),rtol=2**-6,atol=2**-8)"
    if frame['expression']!=expression or raw.splitlines()[frame['line']-1].strip()!=expression:raise ValueError('exact saved full-forecast assertion, not V1 assumed cost assertion')
    source_key=frame['file']
    if z['evidence'][source_key]!=source_identity:raise ValueError('actual source metadata hash matches exact local inspected source')
    tree=ast.parse(raw);parity=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parity')
    native=[];restore=[]
    for node in ast.walk(parity):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='rollout':native.append(node.lineno)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='restore':restore.append(node.lineno)
    if len(native)!=1 or not parity.lineno<native[0]<frame['line'] or not restore or min(restore)<=frame['line']:
        raise ValueError('actual native forward precedes assertion and two extra restoration checks follow it')
    return {'actual_failure_expression':expression,'line':frame['line'],
            'native_reference_forward_line':native[0],'two_extra_restoration_checks_not_reached':True,
            'scope':'source arithmetic conditioned on authenticated actual failure point, NOT retrospective hooks',
            'baseline_counters_changed':False,'new_research_calls':0}


def main():
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    prior=doc/'HISTORICAL-USAGE-001.json';diagnosis=doc/'HISTORICAL-FAILURE-V2-DIAG001.json'
    if identity(prior)!={'bytes':19046,'sha256':'c9397f411d2022963958470df0b4c53a8fdf43fbd34dcb4bdcb2ca6acfffef1d'}:raise ValueError('exact unchanged first provenance receipt')
    old=json.loads(prior.read_text());z=json.loads(diagnosis.read_text())
    source=ROOT/'wm_diag0_campaign_v4/diagnostic.py';sid=identity(source)
    if sid!={'bytes':10260,'sha256':'73e26dcf8fb49cbe7979117c6dd2b828030eaafc4001c540c89dcee06b4e23b0'}:raise ValueError('exact original frozen diagnostic source')
    disposition=failure_point(z,source.read_text(),sid)
    # Targeted new negative guard checks; no old scientific suite or remote read.
    bad=copy.deepcopy(z)
    for f in bad['frames']:
        if f['function']=='parity':f['expression']='torch.testing.assert_close(first,second)'
    try:failure_point(bad,source.read_text(),sid)
    except ValueError:pass
    else:raise AssertionError('wrong assumed failure point not rejected')
    counts=arithmetic(old['R1_saved_usage'],old['V3_saved_usage'],old['RC1_saved_usage'],old['new_fit_saved_usage'])
    evidence=dict(old['evidence'])
    for path,value in z['evidence'].items():
        if path in evidence and evidence[path]!=value:raise ValueError('historical source/control evidence changed across reads')
        evidence[path]=value
    result=dict(counts,status='ACTUAL_HISTORICAL_USAGE_AND_EXACT_FAILURE_PHASE_AUTHENTICATED_NOT_FINAL_GATE',
                independently_authenticated=True,evidence=evidence,failure_disposition=disposition,
                original_receipt=identity(prior),supplemental_traceback_receipt=identity(diagnosis),
                original_failed_guard_receipt=z['original_failed_receipt'],
                source={n:identity(Path(__file__).parent/n) for n in ('historical_usage_v1.py','historical_failure_v1.py','historical_failure_v2.py','historical_disposition_v1.py')},
                source_arithmetic_is_not_hook_measurement=True,actual_final_contract_ready=False,
                scheduler_calls=0,network_calls=0,research_calls=0,scientific_values_read=False,final_gate_ready=False)
    write_new(doc/'HISTORICAL-USAGE-002.json',result,limit=64000)
    print(json.dumps({'status':result['status'],'evidence_files':len(evidence),'failure_phase':'full forecast comparison AFTER native reference BEFORE extra restoration checks','unchanged_baseline_encoded_frames':2317,'final_gate_ready':False}))


if __name__=='__main__':main()
