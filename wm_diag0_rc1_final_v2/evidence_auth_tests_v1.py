"""Targeted new historical gate tests; no actual research evidence is read."""
import ast,copy,hashlib,json,tempfile,time
from pathlib import Path
from . import evidence_auth_v1 as a
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except (ValueError,PermissionError,FileNotFoundError,TimeoutError):return
    raise AssertionError('required historical evidence rejection absent')


def main():
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016';receipt=doc/'HISTORICAL-USAGE-002.json'
    if identity(receipt)!=a.USAGE:raise ValueError('exact existing local technical provenance receipt')
    body=json.loads(receipt.read_text());a.validate_usage_body(body)
    bad=copy.deepcopy(body);bad['evidence'].pop(next(iter(bad['evidence'])));reject(lambda:a.validate_usage_body(bad))
    bad=copy.deepcopy(body);bad['DINO_baseline']['predictor_calls']+=1;reject(lambda:a.validate_usage_body(bad))
    bad=copy.deepcopy(body);bad['failure_disposition']['two_extra_restoration_checks_not_reached']=False;reject(lambda:a.validate_usage_body(bad))
    bad=copy.deepcopy(body);bad['LeWM_baseline']['cost_api_calls']=False;reject(lambda:a.validate_usage_body(bad))
    with tempfile.TemporaryDirectory(prefix='wm-rc1-evidence-guard-') as tmp:
        root=Path(tmp);evidence={}
        for i in range(59):
            p=root/('opaque-'+str(i)+'.bin');raw=(b'\x00synthetic opaque bytes\xff'+str(i).encode())
            with p.open('xb') as f:f.write(raw)
            evidence[str(p)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        proof=a.authenticate_evidence(evidence,root,time.monotonic()+5)
        if proof['authenticated_files']!=59 or proof['file_payloads_deserialized_or_interpreted']:raise AssertionError('complete synthetic opaque hashing')
        bad=copy.deepcopy(evidence);key=next(iter(bad));bad[key]['sha256']='0'*64
        reject(lambda:a.authenticate_evidence(bad,root,time.monotonic()+5))
        p=Path(key)
        with p.open('ab') as f:f.write(b'retained artificial mutation')
        reject(lambda:a.authenticate_evidence(evidence,root,time.monotonic()+5))
        reject(lambda:a.authenticate_evidence(evidence,root,time.monotonic()-1))
        bad=copy.deepcopy(evidence);bad[key]['bytes']=True;reject(lambda:a.authenticate_evidence(bad,root,time.monotonic()+5))
        outside=root.parent/'outside-never-read'
        reject(lambda:a.authenticate_evidence({str(outside):{'bytes':1,'sha256':'0'*64}},root,time.monotonic()+5))
        p=root/'duplicate.json';raw=b'{"x":1,"x":2}'
        with p.open('xb') as f:f.write(raw)
        reject(lambda:a.bound_json(p,identity(p),100,time.monotonic()+5))
        reject(lambda:a.authenticate_usage(p,identity(p),time.monotonic()+5))
        # A truthy flag and plausible counters without the pinned identity must
        # stop BEFORE attempting to read any declared original cluster path.
        p=root/'forged.json';forged=copy.deepcopy(body);forged['unapproved_truthy_claim']=True;write_new(p,forged)
        reject(lambda:a.authenticate_usage(p,identity(p),time.monotonic()+5))
    source={}
    for n in ('evidence_auth_v1.py','evidence_auth_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    result={'status':'TARGETED_HISTORICAL_REAUTHENTICATION_GUARD_ARTIFICIAL_PASSED','source':source,
            'original_local_receipt':identity(receipt),'synthetic_files_hashed':59,
            'checks':['exact002 identity before reading originals','baseline/failure-phase/59file completeness',
                      'actual ordinary-temp59file opaque stream authentication','changed size/hash/outside root/deadline/boolean rejection',
                      'duplicate JSON and forged independently-authenticated flag rejected'],
            'actual_cluster_evidence_reauthenticated':False,'research_artifacts_or_scientific_values_read':False,
            'network_calls':0,'scheduler_calls':0,'research_calls':0,'final_gate_ready':False}
    write_new(doc/'ARTIFICIAL-EVIDENCE-GUARD-001.json',result,limit=16000)
    print(json.dumps({'status':result['status'],'actual_cluster_reauthentication':False,'research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
