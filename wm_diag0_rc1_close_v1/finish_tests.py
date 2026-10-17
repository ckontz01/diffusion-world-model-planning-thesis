"""New actual Windows whole/member/sidecar fixture, no real D: or cluster calls."""
import ast,json,time
from pathlib import Path
from .common import DOC,ROOT,identity,write_new
from . import finish
from wm_diag0_rc1_final_v2.inventory_v3 import plan
from wm_diag0_rc1_final_v2.archive_v2 import create,canonical
from wm_diag0_rc1_final_v2.archive_verify_v2 import verify,portable_plan
from wm_diag0_rc1_final_v2 import native_transfer_v3 as receiver
from wm_diag0_rc1_final_v1 import postarchive_v1 as sidecar

def main():
    root=DOC/'artificial-native-finish-001';root.mkdir(exist_ok=False);study=root/'study';old=study/'old';old.mkdir(parents=True)
    (old/'STOP.json').write_bytes(b'old failure retained, NOT scientific JSON')
    planned=plan(study,['old'],{},{});binding={'root_paths':{'study/old':str(old)},'final_contract_sha256':'a'*64}
    partial=root/'tiny.tar.partial';target=root/'tiny.tar';made=create(planned,partial,binding,time.monotonic()+10)
    checked=verify(partial,planned,binding,time.monotonic()+10,check_sources=True,expected_whole=made['whole'],expected_manifest=made['manifest'])
    portable=portable_plan(planned,checked);pid=receiver.portable_identity(portable)
    native=receiver.verify_and_promote(partial,target,portable,binding,made['whole'],made['manifest'],pid,time.monotonic()+10)
    if native['logical_members']!=1 or partial.exists() or identity(target)!=made['whole']:raise AssertionError('actual native whole/member promotion')
    bad=root/'wrong.partial';bad.write_bytes(target.read_bytes())
    try:receiver.verify_and_promote(bad,root/'must-not-promote.tar',portable,binding,dict(made['whole'],sha256='0'*64),made['manifest'],pid,time.monotonic()+10)
    except ValueError:pass
    else:raise AssertionError('wrong whole hash accepted')
    if not bad.exists() or (root/'must-not-promote.tar').exists():raise AssertionError('failed partial not retained')
    controls=root/'controls';controls.mkdir();write_new(controls/'TERMINAL.json',{'synthetic':True,'actual_allocation':False})
    expected={'TERMINAL.json':identity(controls/'TERMINAL.json')}
    sb={'final_contract_sha256':'a'*64,'archive_whole':made['whole'],'archive_manifest':made['manifest'],'analysis_output_seal':{'bytes':1,'sha256':'b'*64}}
    raw=sidecar.build(controls,expected,sb,'TERMINAL_CPU',None,time.monotonic()+5);sid=sidecar.digest(raw)
    sidecar.verify(raw,expected,sb,'TERMINAL_CPU',None,sid,time.monotonic()+5)
    try:sidecar.verify(raw+b'x',expected,sb,'TERMINAL_CPU',None,sid,time.monotonic()+5)
    except ValueError:pass
    else:raise AssertionError('changed sidecar accepted')
    for path in ('/tmp/not-approved','/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/../outside','bad\npath'):
        try:finish.binary_command(path,30)
        except ValueError:pass
        else:raise AssertionError('unbound remote binary path')
    ast.parse(finish.TERMINAL,feature_version=(3,6));ast.parse(finish.UPLOAD,feature_version=(3,6))
    receipt={'status':'NEW_ACTUAL_NATIVE_FINAL_READBACK_AND_POSTARCHIVE_FIXTURES_PASSED','finish_source':identity(finish.__file__),
        'test_source':identity(__file__),'tiny_archive':identity(target),'wrong_hash_partial_retained':identity(bad),
        'native_readback':native,'scientific_study_values_read':False,'actual_D_SSD_WSL_cluster_calls':0,
        'actual_final_SSD_gate':False,'actual_output_files':[str(target),str(bad)]}
    write_new(DOC/'ARTIFICIAL-NATIVE-FINISH-001.json',receipt)
    print(json.dumps({'status':receipt['status'],'actual_final_SSD_gate':False}))
if __name__=='__main__':main()
