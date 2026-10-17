"""Freeze exact recovery-aware final CPU closure after real Linux integration."""
import ast,copy,hashlib,json
from .common import ROOT,DOC,identity,write_new
from .integration import source_members
from wm_diag0_rc1_final_v2.archive_v2 import canonical
from wm_diag0_rc1_final_v2.cpu_schedule_v2 import CPU_V2

EVIDENCE={'PRESERVATION-LAYOUT-001.json':DOC/'LAYOUT-001.json','PRECOMPUTE-ROOTS.json':DOC/'PRECOMPUTE-ROOTS.json',
    'PREPARATION-COPIES.json':DOC/'PREPARATION-COPIES-001.json','PREPARATION-MEASUREMENT.json':DOC/'PREPARATION-MEASUREMENT-001.json',
    'ALL-ALLOCATIONS-TERMINAL.json':DOC/'ALL-ALLOCATIONS-TERMINAL.json',
    'HISTORICAL-USAGE-002.json':ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/HISTORICAL-USAGE-002.json',
    'FINALIZATION-AUTHORITY.json':DOC/'AUTHORITY-002.json','LINUX-INTEGRATION-002.json':DOC/'LINUXFINAL002.json'}

def additions():
    result=source_members()
    result.update({'final_evidence/'+n:p.read_bytes() for n,p in EVIDENCE.items()})
    return result

def main():
    binding=json.loads((DOC/'BINDING004.json').read_text());tested=json.loads((DOC/'LINUXFINAL002.json').read_text())
    if binding['status']!='ALL139_TERMINAL_ALL128_STARTS_ALL21_ROOTS_FULL_RUNTIME_EVERY_MEMBER_BOUND' or 'PASSED' not in tested['status']:raise ValueError('actual binding and Linux integration first')
    critical=('driver_v2.py','entry_v2.py','workflow_v2.py','archive_operation_v2.py','analysis_closure_v2.py','closed_identity_v2.py',
        'analysis.py','analysis_validate.py','suppliers.py','usage.py','schedule.py','layout.py','parallel_binding.py','entry_source.py','authorization.py','archive_pipeline.py','preservation_budget.py')
    for name in critical:
        path='wm_diag0_rc1_close_v1/'+name
        if identity(ROOT/path)!=tested['source_identities'][path]:raise ValueError('actual Linux-tested production source changed '+name)
    recovery_path=ROOT/'docs/world-model-diagnostic-rc1-recovery-r1-20261016/GRID-CONTRACT.json'
    recovery=json.loads(recovery_path.read_text());c=copy.deepcopy(recovery)
    new=additions()
    for name,raw in new.items():
        if name.endswith('.py'):ast.parse(raw.decode(),feature_version=(3,6))
        actual={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        if name in c['staged_members'] and c['staged_members'][name]!=actual:raise ValueError('never replace original executed staged source '+name)
        c['staged_members'][name]=actual
    if c['staged_members'].get('wm_diag0_rc1_final_v1/cpu_process_v2.py')!=CPU_V2:raise ValueError('original V2 cleanup byte identity')
    layout=json.loads((DOC/'LAYOUT-001.json').read_text())['layout'];source=layout['final_run']+'/source'
    source_commitment=hashlib.sha256(canonical(c['staged_members'])).hexdigest()
    c['rc1_final']={'analysis_authorized':True,'run':layout['final_run'],'operational_root':layout['operational_root'],'archive_path':layout['archive_path'],
        'grid_run':recovery['run'],'grid_contract':identity(recovery_path),'allocation_seconds':3600,'CPUs':4,'RAM_bytes':8589934592,'GPU_requested':0,'automatic_retry':False,
        'phase_seconds':{'analysis':1200,'independent_acceptance':600,'archive':1770,'finalize':30},
        'historical_usage_receipt':{'path':source+'/final_evidence/HISTORICAL-USAGE-002.json','identity':identity(EVIDENCE['HISTORICAL-USAGE-002.json'])},
        'all_allocations_terminal':identity(EVIDENCE['ALL-ALLOCATIONS-TERMINAL.json']),
        'publication_anchor':{'source_members_sha256':source_commitment,'human_authority':identity(DOC/'AUTHORITY-002.json')},
        'actual_GPU_attempts':139,'actual_GPU_seconds':binding['terminal']['reconciled']['GPU_charged_seconds'],
        'source_CPU_before_final':1436,'protected_conversion_reserved_seconds':1800,
        'complete_input_binding':identity(DOC/'BINDING004.json'),'native_preparation_copies':identity(EVIDENCE['PREPARATION-COPIES.json']),
        'Linux_integration':identity(DOC/'LINUXFINAL002.json'),'final_parent_publication_requires_designated_SSD':True}
    for key,value in recovery.items():
        if key!='staged_members' and canonical(c[key])!=canonical(value):raise ValueError('original science/supplier field changed')
    write_new(DOC/'FINAL-CONTRACT.json',c)
    review={'status':'RECOVERY_FINAL_CPU_SOURCE_AND_CONTRACT_INDEPENDENT_PARENT_REVIEW_PASSED',
        'scope':'Parent compared all original science/supplier fields and executed source identities; reviewed new fixed writer/independent second-pass,139 failure ledger, full runtime/root/preparation bindings, V2 process cleanup, exact CPU-only staging, dynamic closed-record archive argv and original readback. No scientific result inspected.',
        'contract':identity(DOC/'FINAL-CONTRACT.json'),'staged_members':c['staged_members'],'new_members':{n:c['staged_members'][n] for n in new},
        'actual_Linux_test':identity(DOC/'LINUXFINAL002.json'),'critical_sources_unchanged_since_actual_Linux_test':True,
        'original_scientific_fields_and_source_members_unchanged':True,'all139_GPU_terminal_seconds':97360,
        'CPU_final_seconds':3600,'protected_conversion_seconds_consumed':0,'science_or_GPU_execution_repeated':False,
        'actual_analysis_started':False,'final_gate_ready':False}
    write_new(DOC/'REVIEW-001.json',review)
    print(json.dumps({'status':review['status'],'contract':review['contract'],'members':len(c['staged_members'])}))
if __name__=='__main__':main()
