"""Frozen native Slurm CPU supervisor, fixed real children and disjoint controls."""
import json,os,sys,time,traceback
from pathlib import Path
from .entry_v2 import authenticate_inputs,allocation_gate
from .workflow_v2 import run_fixed_sequence
from .schedule import prospective_cpu_environment
from .closed_identity_v2 import identity
from wm_diag0_rc1_final_v2.evidence_auth_v1 import bound_json,bound_bytes
from wm_diag0_rc1_final_v2.archive_v2 import canonical,check_time
from wm_diag0_rc1_final_v2.archive_pipeline_v1 import write_bounded
from wm_diag0_rc1_final_v2.root_binding_v1 import compare_preexisting

def main():
    cp=Path(sys.argv[1]);expected=json.loads(sys.argv[2]);deadline=time.monotonic()+3590
    c=bound_json(cp,expected,1000000,deadline);f=c['rc1_final'];source=cp.parent
    layout_id=c['staged_members']['final_evidence/PRESERVATION-LAYOUT-001.json']
    layout=bound_json(source/'final_evidence/PRESERVATION-LAYOUT-001.json',layout_id,32000,deadline)['layout']
    controls=Path(layout['cpu_control_root']);ops=Path(layout['operational_root'])
    dispatch_path=Path(layout['submission_control_root'])/'DISPATCH.json'
    # Actual trusted stage supplies this exact job/contract/source receipt BEFORE
    # release. Environment strings alone cannot establish allocation authority.
    dispatch=bound_json(dispatch_path,identity(dispatch_path,200000,deadline),200000,deadline)
    if dispatch.get('contract')!=expected or dispatch.get('staged_members')!=c['staged_members'] or dispatch.get('publication')!=f['publication_anchor']:raise PermissionError('externally frozen stage/dispatch/source/publication binding')
    gate=allocation_gate(c,dispatch,deadline)
    elapsed=time.time()-gate['allocation_started_epoch']
    if not 0<=elapsed<120:raise PermissionError('fresh exact allocation start')
    began=time.monotonic()-elapsed
    expected_phases={'analysis':1200,'independent_acceptance':600,'archive':1770,'finalize':30}
    if canonical(f['phase_seconds'])!=canonical(expected_phases):raise ValueError('frozen3600 including entry/cleanup/finalization')
    def entry(end):
        proof=authenticate_inputs(cp,expected,layout,end)
        proof['actual_kernel_and_scheduler_allocation']=gate
        write_bounded(controls/'ENTRY-VERIFIED.json',canonical(proof),64000,end)
        return proof
    def archive(end):
        path=ops/'archive/ARCHIVE-READBACK.json';proof=bound_json(path,identity(path,64000,end),64000,end)
        if proof['binding']!={'root_paths':layout['root_paths'],'final_contract_sha256':expected['sha256']}:raise ValueError('same independently frozen complete archive roots')
        prior=bound_json(source/'final_evidence/PRECOMPUTE-ROOTS.json',c['staged_members']['final_evidence/PRECOMPUTE-ROOTS.json'],64000,end)
        transition=compare_preexisting(proof['every_member_root_binding'],prior)
        archive_path=Path(layout['archive_path'])
        if archive_path.lstat().st_size!=proof['whole']['bytes']:raise ValueError('archive size changed after independent child readback')
        portable=ops/'archive/portable-inventory.json'
        bound_bytes(portable,proof['portable_inventory'],12000000,end)
        # Real owned archive child stdout is closed before callback. It must
        # independently report the same whole/member/portable identities as the
        # verifier's external technical receipt, not a caller-supplied ready flag.
        log=bound_bytes(ops/'cpu/archive.log',identity(ops/'cpu/archive.log',100000,end),100000,end,retain=True)
        report=json.loads(log.decode().strip().splitlines()[-1])
        for key in ('whole','manifest','portable_inventory'):
            if report[key]!=proof[key]:raise ValueError('closed actual archive child versus independent receipt')
        return {'whole':proof['whole'],'manifest':proof['manifest'],'portable_inventory':proof['portable_inventory'],
            'readback_control':identity(path,64000,end),'historical_root_transition':transition,'archive_created_once':True}
    try:
        result=run_fixed_sequence(c,layout,expected,began,expected_phases,prospective_cpu_environment(os.environ,str(source)),entry,archive)
        result['job_id']=dispatch['job_id'];result['actual_allocation']=gate
        write_bounded(controls/'SUPERVISOR-CLOSED.json',canonical(result),100000,began+3600)
        print(json.dumps({'status':result['status'],'job_id':dispatch['job_id'],'scientific_values_emitted':False}))
    except BaseException as exc:
        # Native source/stdio/Slurm remain outside all archive input roots.
        # Never retry children or mutate any successful/research supplier.
        end=began+3600
        if time.monotonic()<end:
            write_bounded(controls/'CPU-FAILED.json',canonical({'error':repr(exc),'traceback':traceback.format_exc()[-12000:],
                'job_id':dispatch['job_id'],'automatic_retry':False,'scientific_values_emitted':False}),20000,end)
        raise

if __name__=='__main__':main()
