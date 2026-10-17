"""Targeted V3 mandatory-identity guards and one native no-copy roundtrip."""
import ast,copy,json,os,tempfile,time
from pathlib import Path
from unittest.mock import patch
from . import native_transfer_v3 as receiver
from .archive_v2 import create
from .archive_verify_v2 import verify,portable_plan
from .inventory_v3 import plan
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('mandatory new guard rejection absent')


def main():
    names=('native_transfer_v3.py','native_transfer_tests_v3.py')
    for name in names:ast.parse((Path(__file__).parent/name).read_text(),feature_version=(3,6))
    deadline=time.monotonic()+8
    fake_id={'bytes':20,'sha256':'0'*64}
    portable={'root_labels':['runtime']}
    binding={'root_paths':{'runtime':'/literal/metadata/only'},'final_contract_sha256':'0'*64}
    with patch('wm_diag0_rc1_final_v2.native_transfer_v2.verify_and_promote') as delegated:
        for field in range(3):
            for bad in (None,{},dict(fake_id,bytes=True),dict(fake_id,sha256='f'*63)):
                ids=[fake_id,fake_id,fake_id];ids[field]=bad
                reject(lambda:receiver.verify_and_promote('unused','unused',portable,binding,*ids,deadline))
        for bad in (None,dict(binding,extra=True),dict(binding,root_paths={}),dict(binding,final_contract_sha256='bad'),dict(binding,root_paths={'runtime':'bad\npath'})):
            reject(lambda:receiver.verify_and_promote('unused','unused',portable,bad,fake_id,fake_id,fake_id,deadline))
        assert delegated.call_count==0
    if os.name!='nt':raise RuntimeError('native temporary rename must be tested on Windows')
    with tempfile.TemporaryDirectory(prefix='wmrc1-v3-receiver-') as tmp:
        root=Path(tmp);base=root/'canonical';(base/'fixture').mkdir(parents=True)
        (base/'fixture/value').write_bytes(b'fixed inert V3 identity fixture')
        planned=plan(base,['fixture'],{},{});binding={'root_paths':{'study/fixture':str(base/'fixture')},'final_contract_sha256':'0'*64}
        partial=root/'archive.partial';made=create(planned,partial,binding,deadline)
        original=verify(partial,planned,binding,deadline);portable=portable_plan(planned,original)
        target=root/'archive.tar';portable_id=receiver.portable_identity(portable)
        proof=receiver.verify_and_promote(partial,target,portable,binding,made['whole'],made['manifest'],portable_id,deadline)
        assert target.exists() and not partial.exists() and proof['whole']==made['whole']
    result={'status':'ARTIFICIAL_NATIVE_V3_IDENTITY_GUARDS_PASSED',
            'source':{n:identity(Path(__file__).parent/n) for n in names},
            'V2_implementation_preserved':identity(Path(__file__).parent/'native_transfer_v2.py'),
            'checks':['None/invalid whole manifest portable identities rejected before delegation',
                      'boolean byte lengths rejected','missing extra invalid contract/root metadata rejected',
                      'actual native temporary-file whole every-member V3 validation and no-copy rename'],
            'actual_designated_SSD_or_cluster_accessed':False,'external_processes_launched':0,
            'research_calls':0,'research_values_read':False,'actual_final_contract_ready':False,
            'mandatory_production_receiver':'native_transfer_v3.verify_and_promote','final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-NATIVE-RECEIVER-002.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
