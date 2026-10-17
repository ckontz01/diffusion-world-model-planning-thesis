"""Targeted new V2 receiver tests, temporary native files only; no SSD/network."""
import ast,copy,io,json,os,stat,tempfile,time
from pathlib import Path
from unittest.mock import patch
from . import native_transfer_v2 as receiver
from . import archive_v2 as archive
from .archive_verify_v2 import verify,portable_plan
from wm_diag0_rc1_final_v1 import archive_v1 as old_archive
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn,kind=ValueError):
    try:fn()
    except kind:return
    raise AssertionError('required rejection absent')


class InertOwnedTransport:
    def __init__(self,raw):self.stdout=io.BytesIO(raw);self.returncode=None
    def wait(self,timeout):self.returncode=0;return 0
    def poll(self):return self.returncode
    def kill(self):self.returncode=-9


def main():
    began=time.monotonic();deadline=began+15
    if os.name!='nt':raise RuntimeError('actual native temporary-file promotion test required')
    names=('native_transfer_v2.py','native_transfer_tests_v2.py')
    for name in names:ast.parse((Path(__file__).parent/name).read_text(),feature_version=(3,6))
    with tempfile.TemporaryDirectory(prefix='wmrc1-v2-receiver-') as tmp:
        root=Path(tmp);source=root/'source';source.mkdir()
        (source/'data').write_bytes(b'small fixed stdlib fixture; not research')
        alias=source/'alias';alias.write_bytes(b'inert placeholder; not an OS alias')
        payload=(source/'data').read_bytes()
        planned={'members':{'runtime/data':{'path':str(source/'data'),'type':'file','bytes':len(payload)},
                            'runtime/alias':{'path':str(alias),'type':'symlink','target':'/opt/conda/bin/python'}},
                 'root_labels':['runtime'],'logical_payload_bytes_no_discounts':len(payload),
                 'archive_reserved_bytes':len(payload)+500000000,'compression_or_hardlink_savings_assumed':False}
        binding={'root_paths':{'runtime':str(source)},'final_contract_sha256':'0'*64}
        original_token=archive.token
        def alias_token(path,alias_flag=False):
            if Path(path)==alias:
                assert alias_flag;return (1,2,0,0,0,stat.S_IFLNK|0o777)
            return original_token(path,alias_flag)
        def readlink(path):
            assert Path(path)==alias;return '/opt/conda/bin/python'
        archive_path=root/'source.tar'
        with patch('wm_diag0_rc1_final_v2.archive_v2.token',side_effect=alias_token),patch('wm_diag0_rc1_final_v2.archive_verify_v2.token',side_effect=alias_token),patch('os.readlink',side_effect=readlink):
            made=archive.create(planned,archive_path,binding,deadline)
            checked=verify(archive_path,planned,binding,deadline)
            portable=portable_plan(planned,checked)
        portable_id=receiver.portable_identity(portable)
        reject(lambda:receiver.portable_identity(planned))
        # Actual native ordinary-file stream and rename, not the designated D:
        # and no native alias privilege, outside target or external process.
        partial=root/'study.tar.partial';target=root/'study.tar'
        receiver.stream_once(lambda:InertOwnedTransport(archive_path.read_bytes()),partial,made['whole'],deadline)
        bad=copy.deepcopy(portable);bad['members']['runtime/alias']['target']='../different'
        reject(lambda:receiver.verify_and_promote(partial,target,bad,binding,made['whole'],made['manifest'],portable_id,deadline))
        assert partial.exists() and not target.exists()
        reject(lambda:receiver.verify_and_promote(partial,target,bad,binding,made['whole'],made['manifest'],receiver.portable_identity(bad),deadline))
        assert partial.exists() and not target.exists()
        reject(lambda:receiver.verify_and_promote(partial,target,portable,binding,dict(made['whole'],sha256='f'*64),made['manifest'],portable_id,deadline))
        reject(lambda:receiver.verify_and_promote(partial,target,portable,binding,made['whole'],made['manifest'],portable_id,time.monotonic()-1),TimeoutError)
        proof=receiver.verify_and_promote(partial,target,portable,binding,made['whole'],made['manifest'],portable_id,deadline)
        assert not partial.exists() and target.is_file() and proof['whole']==made['whole']
        assert proof['archive_schema']=='WM-DIAG0-RC1-ARCHIVE-v2' and proof['files_extracted_or_executed']==0
        reject(lambda:receiver.verify_and_promote(archive_path,target,portable,binding,made['whole'],made['manifest'],portable_id,deadline),FileExistsError)
        assert archive_path.exists() and target.read_bytes()==archive_path.read_bytes()
        # A V1 archive cannot pass the V2 receiver even when expected byte hashes
        # and portable ordinary-member inventory are otherwise supplied exactly.
        ordinary=copy.deepcopy(planned);ordinary['members'].pop('runtime/alias')
        old_path=root/'old-schema.tar';old=old_archive.create(ordinary,old_path,binding,deadline)
        ordinary_portable=copy.deepcopy(ordinary)
        ordinary_portable['members']={'runtime/data':{'type':'file','bytes':len(payload),'sha256':identity(source/'data')['sha256']}}
        reject(lambda:receiver.verify_and_promote(old_path,root/'wrong-final.tar',ordinary_portable,binding,old['whole'],old['manifest'],receiver.portable_identity(ordinary_portable),deadline))
        assert old_path.exists() and not (root/'wrong-final.tar').exists()
        # Disclosed reparse-attribute mock; never create a junction or request
        # additional native symlink privileges merely to exercise this guard.
        actual_lstat=Path.lstat
        def reparse(path):
            s=actual_lstat(path)
            if path!=root:return s
            class Redirect:
                st_file_attributes=0x400
            return Redirect()
        with patch.object(Path,'lstat',reparse):
            reject(lambda:receiver.nonredirected(root/'new.partial'))
    sources={n:identity(Path(__file__).parent/n) for n in names}
    result={'status':'ARTIFICIAL_NATIVE_V2_RECEIVER_PASSED','source':sources,
            'source_preparation_only':True,'new_schema_explicitly_bound':True,
            'checks':['whole and every original-member hash before actual Windows rename',
                      'externally bound complete portable inventory','inert absolute alias literal preserved',
                      'wrong alias even with matching forged portable identity rejected by archive',
                      'wrong whole identity/deadline/existing target rejected; partial retained',
                      'V1 archive rejected by V2 schema','no-copy same-directory non-overwriting native rename',
                      'mocked Windows ancestor reparse attribute rejected'],
            'alias_lstat_readlink_and_reparse_mocks_disclosed':True,
            'actual_native_aliases_or_reparse_points_created':False,
            'designated_SSD_or_cluster_accessed':False,'external_processes_launched':0,
            'research_calls':0,'research_values_read':False,'actual_terminal_CPU_authentication':False,
            'actual_final_contract_or_transfer_ready':False,'final_gate_ready':False,
            'elapsed_test_seconds':time.monotonic()-began}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-NATIVE-RECEIVER-001.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
