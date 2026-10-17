"""New original/readback root-binding tests, using ordinary tiny native files."""
import ast,copy,json,tempfile,time
from pathlib import Path
from .inventory_v3 import plan
from .archive_v2 import create
from .archive_verify_v2 import verify,portable_plan
from . import root_binding_v1 as b
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except (ValueError,TimeoutError,FileNotFoundError):return
    raise AssertionError('required complete-root binding rejection absent')


def main():
    with tempfile.TemporaryDirectory(prefix='wm-rc1-root-commitment-') as tmp:
        base=Path(tmp);study=base/'study';(study/'old').mkdir(parents=True);(study/'failed').mkdir()
        runtime=base/'runtime';runtime.mkdir();ops=base/'operations';ops.mkdir()
        for p,raw in ((study/'old/accepted.bin',b'\x00\xffaccepted synthetic opaque bytes'),
                      (study/'failed/STOP.json',b'old STOP must remain'),(study/'failed/partial.bin',b'failed partial must remain'),
                      (runtime/'payload.bin',b'\x00runtime opaque\xff')):
            with p.open('xb') as f:f.write(raw)
        roots={'study/old':str(study/'old'),'study/failed':str(study/'failed'),'runtime':str(runtime)}
        inv=plan(study,['old','failed'],{'runtime':runtime},{})
        deadline=time.monotonic()+10;original=b.authenticate(inv,roots,'a'*64,deadline)
        if original['logical_members']!=4 or original['roots']['study/failed']['regular_files']!=2:raise AssertionError('every original success/STOP/failed partial bound')
        binding={'root_paths':roots,'final_contract_sha256':'b'*64};archive=ops/'once.tar'
        made=create(inv,archive,binding,deadline)
        proof=verify(archive,inv,binding,deadline,expected_whole=made['whole'],expected_manifest=made['manifest'])
        portable=portable_plan(inv,proof);after=b.from_independent_portable(portable,roots,'a'*64,proof,deadline)
        b.compare(after,original)
        bad=copy.deepcopy(portable);bad['members']['study/failed/partial.bin']['sha256']='0'*64
        reject(lambda:b.compare(b.from_independent_portable(bad,roots,'a'*64,proof,deadline),original))
        reject(lambda:b.from_independent_portable(portable,roots,'a'*64,dict(proof,originals_independently_reread=False),deadline))
        reject(lambda:b.authenticate(inv,roots,'a'*64,time.monotonic()-1))
        changed=study/'old/accepted.bin';raw=changed.read_bytes()
        with changed.open('wb') as f:f.write(b'x'*len(raw))
        reject(lambda:b.compare(b.authenticate(inv,roots,'a'*64,deadline),original))
        # The only new root permitted by compare_preexisting is the declared
        # future final root; this still does NOT authenticate its output seal.
        final=study/'campaign-v4-rc1-final-v2';final.mkdir()
        with (final/'closed-synthetic-output.bin').open('xb') as f:f.write(b'closed complete synthetic output')
        updated=plan(study,['old','failed',final.name],{'runtime':runtime},{})
        updated_roots=dict(roots,**{b.OWNED_FINAL:str(final)})
        now=b.authenticate(updated,updated_roots,'a'*64,deadline)
        # Earlier deliberate byte mutation must reject, not be silently blessed.
        reject(lambda:b.compare_preexisting(now,original))
        expected=b.authenticate(inv,roots,'a'*64,deadline)
        transition=b.compare_preexisting(now,expected)
        if not transition['new_owned_final_root_included']:raise AssertionError('owned full final root added exactly once')
        bad=copy.deepcopy(now);bad['roots'].pop('study/failed');reject(lambda:b.compare_preexisting(bad,expected))
        bad=copy.deepcopy(now);bad['logical_regular_bytes_no_discounts']-=1;reject(lambda:b.compare_preexisting(bad,expected))
        bad=copy.deepcopy(now);bad['root_paths']['runtime']=str(study/'old');reject(lambda:b.compare_preexisting(bad,expected))
    source={}
    for n in ('root_binding_v1.py','root_binding_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    result={'status':'EVERY_MEMBER_ORIGINAL_AND_INDEPENDENT_READBACK_ROOT_BINDING_ARTIFICIAL_PASSED','source':source,
            'checks':['every sorted member name/kind/bytes/opaquehash committed per explicit root','old STOP/partial/success/runtime included',
                      'actual tiny native archive+independent original/member readback commitments identical','forged member hash/status/deadline/change rejected',
                      'only explicit whole owned-final addition allowed; changed/missing historical roots and byte discounts rejected'],
            'file_payloads_or_scientific_values_deserialized':False,'original_research_files_read':False,
            'compressed_or_deduplicated_artifact_bytes_or_logical_copy_discounts':False,
            'large_duplicate_precompute_per_member_manifest_created':False,
            'actual_cluster_binding_or_whole_study_storage_proof_passed':False,'network_calls':0,'scheduler_calls':0,'research_calls':0,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-ROOT-BINDING-001.json',result,limit=16000)
    print(json.dumps({'status':result['status'],'research_calls':0,'actual_cluster_binding':False,'final_gate_ready':False}))


if __name__=='__main__':main()
