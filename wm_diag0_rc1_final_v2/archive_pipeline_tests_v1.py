"""New tiny complete archive/root/byte integration; no real final entry run."""
import ast,copy,json,tempfile,time
from pathlib import Path
from .inventory_v3 import plan
from .root_binding_v1 import authenticate,OWNED_FINAL
from .archive_pipeline_v1 import preserve_authenticated_roots,outputs_outside_inputs
from .preservation_budget_v1 import prove,AUX_RESERVATIONS,PORTABLE_LIMIT
from .archive_verify_v2 import verify,strict_json
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn,kind=ValueError):
    try:fn()
    except kind:return
    raise AssertionError('required once-only pipeline rejection absent')


def main():
    with tempfile.TemporaryDirectory(prefix='wm-rc1-archive-root-pipeline-') as tmp:
        base=Path(tmp);study=base/'study';old=study/'old';old.mkdir(parents=True);runtime=base/'runtime';runtime.mkdir();ops=base/'ops';ops.mkdir()
        for p,raw in ((old/'STOP.json',b'old STOP retained'),(old/'failure.partial',b'failed opaque bytes'),(runtime/'opaque',b'full runtime opaque bytes')):
            with p.open('xb') as f:f.write(raw)
        prior_plan=plan(study,['old'],{'runtime':runtime},{})
        prior_paths={'study/old':str(old),'runtime':str(runtime)}
        prior=authenticate(prior_plan,prior_paths,'a'*64,time.monotonic()+10)
        final=study/'campaign-v4-rc1-final-v2';final.mkdir()
        with (final/'closed-complete-synthetic-result').open('xb') as f:f.write(b'no real study values')
        paths=dict(prior_paths,**{OWNED_FINAL:str(final)})
        def fresh():return plan(study,['old',final.name],{'runtime':runtime},{})
        inventory=fresh();binding={'root_paths':paths,'final_contract_sha256':'b'*64}
        archive=ops/'once.tar';portable=ops/'portable.json';proof=ops/'proof.json'
        result=preserve_authenticated_roots(inventory,binding,'a'*64,prior,archive,portable,proof,fresh,3000000000,time.monotonic()+10)
        if result['whole']!=identity(archive) or result['portable_inventory']!=identity(portable) or not result['archive_created_once']:raise AssertionError('actual tiny archive/portable identities')
        portable_body=strict_json(portable.read_bytes());budget=result['byte_reservations']
        checked=verify(archive,portable_body,binding,time.monotonic()+5,check_sources=False,expected_whole=result['whole'],expected_manifest=result['manifest'])
        if checked['logical_members']!=4 or len(portable.read_bytes())!=budget['forecast_portable_bytes']:raise AssertionError('complete portable independent readback and exact pre-write forecast')
        if sum(AUX_RESERVATIONS.values())!=63928640 or budget['locked_auxiliary_margin_bytes']!=71360:raise AssertionError('finite ALL-logical-copy auxiliary reservation')
        reject(lambda:preserve_authenticated_roots(inventory,binding,'a'*64,prior,archive,portable,proof,fresh,3000000000,time.monotonic()+5),FileExistsError)
        reject(lambda:outputs_outside_inputs([old/'recursive.tar',ops/'new-portable',ops/'new-proof'],paths))
        reject(lambda:prove(inventory,paths,'b'*64,True))
        oversized=copy.deepcopy(inventory);key=next(n for n,r in oversized['members'].items() if r['type']=='file');added=13450000000-oversized['logical_payload_bytes_no_discounts']
        # Use four finite <=4GB members, never allocate/write their payloads.
        oversized['members']={}
        for i,size in enumerate((4000000000,4000000000,4000000000,1450000000)):
            oversized['members']['study/old/future-'+str(i)]={'path':str(old/('future-'+str(i))),'type':'file','bytes':size}
        oversized['logical_payload_bytes_no_discounts']=13450000000;oversized['archive_reserved_bytes']=13950000000
        reject(lambda:prove(oversized,paths,'b'*64,3000000000))
    source={}
    for n in ('preservation_budget_v1.py','archive_pipeline_v1.py','archive_pipeline_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    result={'status':'ONCE_ONLY_ARCHIVE_ORIGINAL_ROOT_PORTABLE_BYTE_INTEGRATION_ARTIFICIAL_PASSED','source':source,
            'checks':['tiny actual once-only uncompressed archive with all old STOP/failure/runtime/new owned-final files',
                      'pre-bound historical roots match independent original/archive member commitments',
                      'whole inventory re-scanned before creation and after readback','portable/manifest byte forecast before archive creation',
                      'native ordinary-temp portable whole/member readback','existing artifact refusal and recursive/boolean/over-cap rejection',
                      'unchanged64MB all-copy reservation with71360B locked margin'],
            'portable_file_writer_limit':PORTABLE_LIMIT,'auxiliary_reservations':AUX_RESERVATIONS,
            'source_docs_note':'4.5MB excludes per-check monitoring, separately charged at64KiB/check; four full logical source/doc copies, no dedup discount',
            'original_research_files_values_or_scientific_aggregates_read':False,
            'actual_final_CPU_study_archive_transfer_or_actual_preparation_volume_authentication_run':False,
            'network_calls':0,'scheduler_calls':0,'research_calls':0,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-ARCHIVE-PIPELINE-001.json',result,limit=20000)
    print(json.dumps({'status':result['status'],'research_calls':0,'actual_study_archive_run':False,'final_gate_ready':False}))


if __name__=='__main__':main()
