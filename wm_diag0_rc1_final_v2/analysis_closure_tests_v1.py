"""New tiny synthetic closed-analysis handoff, no actual scientific payloads."""
import ast,copy,json,tempfile,time
from pathlib import Path
from . import analysis_closure_v1 as a
from .evidence_auth_v1 import USAGE
from wm_diag0_native_v3.store import seal
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except (ValueError,PermissionError,TimeoutError,FileNotFoundError):return
    raise AssertionError('required closed-analysis refusal absent')


def fixture(root):
    task=root/'analysis-0'
    for n in ('controls','logs','output'):(task/n).mkdir(parents=True)
    # Deliberately NOT JSON scientific results: output authentication must treat
    # arbitrary bytes as opaque, never interpret a scientific payload here.
    for n,b in (('RESULTS.json',b'synthetic opaque bytes, not result JSON'),('ACCEPTANCE.json',b'\xff\x00synthetic opaque output')):
        with (task/'output'/n).open('xb') as f:f.write(b)
    output=seal(task/'output',1000)
    c={'gpu_stages_authorized':False,'rc1_final':{'analysis_authorized':True,'historical_usage_receipt':{'identity':USAGE}},
       'staged_members':{a.VALIDATOR:identity(ROOT/a.VALIDATOR)}}
    contract={'bytes':100,'sha256':'a'*64}
    accepted={'accepted':True,'phase':'analysis','output_seal':output,'source_roots':120,'retained_fits':6,'active_heads':4,
              'diagnostic_parents':128,'scientific_values_emitted_to_controls':False}
    proof=dict(a.COUNTS,status='COMPLETE_ANALYSIS_INDEPENDENTLY_RECONSTRUCTED_PENDING_ARCHIVE_AND_FINAL_SSD',
        contract_sha256=contract['sha256'],analysis_output_seal=output,validator_source=c['staged_members'][a.VALIDATOR],
        historical_evidence_reauthentication={'status':'ALL59_HISTORICAL_ORIGINAL_EVIDENCE_IDENTITIES_REAUTHENTICATED',
            'authenticated_files':59,'opaque_bytes_hashed':2826430,'receipt':USAGE},
        scientific_values_emitted=False,research_model_simulator_fit_source_generation_calls=0,
        parent_publication_authorized=False,final_gate_ready=False)
    write_new(task/'controls/ACCEPTED.json',accepted);write_new(task/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json',proof)
    for name in a.LOG_NAMES.values():
        with (task/name).open('xb') as f:f.write(b'closed synthetic role log\n')
    return task,c,contract,accepted,proof


def main():
    with tempfile.TemporaryDirectory(prefix='wm-rc1-analysis-close-') as tmp:
        task,c,contract,accepted,proof=fixture(Path(tmp));p=task/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json'
        record=a.close_after_owned_children(c,contract,task,identity(p),time.monotonic()+5)
        checked=a.authenticate_closed(c,contract,task,record,time.monotonic()+5)
        if checked['scientific_payload_values_deserialized'] or checked['final_gate_ready']:raise AssertionError('no values/authority from closed record')
        for role in ('missing_log','changed_contract','boolean_parents','changed_source','publication_upgrade','wrong_seal','historical_missing','extra_control_field','extra_proof_field'):
            bad=copy.deepcopy(proof);ctl=copy.deepcopy(accepted);cc=copy.deepcopy(c);external=copy.deepcopy(record)
            if role=='missing_log':external['files'].pop('analysis');reject(lambda:a.authenticate_closed(c,contract,task,external,time.monotonic()+5));continue
            if role=='changed_contract':bad['contract_sha256']='b'*64
            if role=='boolean_parents':bad['parents']=True
            if role=='changed_source':bad['validator_source']['sha256']='0'*64
            if role=='publication_upgrade':bad['parent_publication_authorized']=True
            if role=='wrong_seal':bad['analysis_output_seal']['sha256']='0'*64
            if role=='historical_missing':bad['historical_evidence_reauthentication']['authenticated_files']=58
            if role=='extra_control_field':ctl['ignored']=True
            if role=='extra_proof_field':bad['private_value_not_allowed']=123
            reject(lambda:a.check_proof(cc,contract,ctl,bad))
        bad=copy.deepcopy(c);bad['rc1_final']['analysis_authorized']=False;reject(lambda:a.check_proof(bad,contract,accepted,proof))
        reject(lambda:a.authenticate_closed(c,contract,task,record,time.monotonic()-1))
        # Mutate only an inert local fixture; original record remains immutable.
        with (task/'logs/analysis.log').open('ab') as f:f.write(b'changed after supposed close')
        reject(lambda:a.authenticate_closed(c,contract,task,record,time.monotonic()+5))
    with tempfile.TemporaryDirectory(prefix='wm-rc1-analysis-close-output-') as tmp:
        task,c,contract,accepted,proof=fixture(Path(tmp));p=task/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json'
        record=a.close_after_owned_children(c,contract,task,identity(p),time.monotonic()+5)
        with (task/'output/RESULTS.json').open('ab') as f:f.write(b'opaque mutation')
        reject(lambda:a.authenticate_closed(c,contract,task,record,time.monotonic()+5))
    source={}
    for n in ('analysis_closure_v1.py','analysis_closure_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    result={'status':'CLOSED_COMPLETE_ANALYSIS_HANDOFF_SYNTHETIC_NATIVE_TEST_PASSED','source':source,
        'checks':['both complete controls+closed role logs+external validator identity','nonboolean120/6/4/128/138 counts',
            'same contract/validator source/output seal/historical59receipt','opaque nonJSON output bytes only',
            'missing/changed log/source/contract/parent/flags/seal/history/extra/draft/deadline/output mutation refused'],
        'scientific_payload_values_deserialized':False,'actual_historical_evidence_or_study_outputs_read':False,
        'actual_owned_research_children_or_cleanup_attested':False,'research_WSL_cluster_scheduler_SSD_calls':0,
        'real_archive_entry_CPU_submission_full_stage_gate_complete':False,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-ANALYSIS-CLOSURE-001.json',result,limit=16000)
    print(json.dumps({'status':result['status'],'scientific_values_deserialized':False,'final_gate_ready':False}))


if __name__=='__main__':main()
