"""Artificial inert-alias codec tests, no privileges/real aliases/targets used."""
import ast,copy,json,os,stat,tempfile,time
from pathlib import Path
from unittest.mock import patch
from .inventory import plan,alias_literal
from .archive_v2 import create,token,checked_plan
from .archive_verify_v2 import verify,portable_plan
from wm_diag0_rc1_completion_v1.common import ROOT,write_new,identity

def reject(fn):
    try:fn()
    except (ValueError,FileNotFoundError):return
    raise AssertionError('required rejection missing')

def main():
    for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text(),feature_version=(3,6))
    for target in ('/opt/conda/bin/python','../lib','python','lib'):assert alias_literal(target)==target
    for target in ('','x\x00y','x\ny','x'*4097,123):reject(lambda:alias_literal(target))
    with tempfile.TemporaryDirectory(prefix='wmrc1-inert-alias-') as tmp:
        root=Path(tmp);study=root/'study';(study/'old').mkdir(parents=True);(study/'new').mkdir()
        (study/'old/STOP.json').write_bytes(b'keep old stop');(study/'new/failed.partial').write_bytes(b'keep partial')
        q=plan(study,['old','new'],{},{});assert len(q['members'])==2
        reject(lambda:plan(study,['new'],{},{}))
        reject(lambda:plan(study,['old','new'],{}, {'study/old/not-present':'../x'}))
        source=root/'source';source.mkdir();(source/'ordinary').write_bytes(b'ordinary')
        # The alias path is an inert ordinary fixture. Mocks supply only its
        # lstat/readlink interface; no native symlink privilege is requested.
        alias=source/'alias';alias.write_bytes(b'inert fixture, not archived as data')
        outside=root/'outside';outside.write_bytes(b'UNACCESSED-OUTSIDE-TARGET')
        original_token=token
        def fake_token(p,alias=False):
            if Path(p)==source/'alias':
                assert alias;return (1,2,0,0,0,stat.S_IFLNK|0o777)
            return original_token(p,alias)
        for i,target in enumerate(('/opt/conda/bin/python','../outside','lib','python')):
            planned={'members':{'runtime/ordinary':{'path':str(source/'ordinary'),'type':'file','bytes':8},
                                'runtime/alias':{'path':str(alias),'type':'symlink','target':target}},
                     'logical_payload_bytes_no_discounts':8,'archive_reserved_bytes':500000008,
                     'root_labels':['runtime'],'compression_or_hardlink_savings_assumed':False}
            binding={'root_paths':{'runtime':str(source)},'final_contract_sha256':'a'*64}
            archive=root/('inert-'+str(i)+'.tar')
            def readlink(p):
                assert Path(p)==alias;return target
            with patch('wm_diag0_rc1_final_v2.archive_v2.token',side_effect=fake_token),patch('wm_diag0_rc1_final_v2.archive_verify_v2.token',side_effect=fake_token),patch('os.readlink',side_effect=readlink):
                made=create(planned,archive,binding,time.monotonic()+3)
                proof=verify(archive,planned,binding,time.monotonic()+3,expected_whole=made['whole'],expected_manifest=made['manifest'])
                portable=portable_plan(planned,proof)
                native=verify(archive,portable,binding,time.monotonic()+3,check_sources=False,expected_whole=made['whole'],expected_manifest=made['manifest'])
                assert native['logical_members']==2 and native['files_extracted_or_executed']==0
                bad=copy.deepcopy(portable);bad['members']['runtime/alias']['target']='changed'
                reject(lambda:verify(archive,bad,binding,time.monotonic()+3,check_sources=False))
            assert b'UNACCESSED-OUTSIDE-TARGET' not in archive.read_bytes()
    result={'status':'ARTIFICIAL_INERT_ABSOLUTE_PARENT_CHAIN_DIRECTORY_LITERAL_CODEC_PASSED',
            'actual_Windows_symlinks_created':False,'alias_lstat_readlink_mocks_disclosed':True,
            'external_targets_read_created_or_executed':False,'research_calls':0,'network_calls':0,
            'actual_POSIX_directory_alias_inventory_test_still_required':True,'final_gate_ready':False,
            'source':{p.name:identity(p) for p in Path(__file__).parent.glob('*.py')}}
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016';write_new(doc/'ARTIFICIAL-ALIAS-001.json',result);print(json.dumps(result))

if __name__=='__main__':main()
