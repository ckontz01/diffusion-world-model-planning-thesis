"""Small artificial archive round-trip/adversarial fixtures, no research reads."""
import hashlib,io,json,tempfile,time,sys
from pathlib import Path
from unittest.mock import patch
from .inventory import plan
from . import archive_v1 as writer
from . import archive_verify_v1 as reader
from wm_diag0_rc1_grid_v1.common import ROOT,identity,write_new


def reject(fn,kind=Exception):
    try:fn()
    except kind:return
    raise AssertionError('required fail-closed rejection did not occur')


def fixture_tar(path,rows):
    # Harmless synthetic bytes only; no fixture is extracted/executed.
    with path.open('xb') as f:
        for name,raw in rows:
            f.write(writer.header(name,len(raw)));f.write(raw);f.write(b'\0'*((-len(raw))%512))
        f.write(b'\0'*1024)


def main():
    deadline=lambda:time.monotonic()+15
    with tempfile.TemporaryDirectory(prefix='wm-rc1-archive-artificial-') as tmp:
        base=Path(tmp);study=base/'study';old=study/'old';new=study/'new'
        old.mkdir(parents=True);new.mkdir()
        (old/'accepted.bin').write_bytes(b'\x00\xff\x80fixed tensor-like bits\x00')
        (old/'STOP.json').write_bytes(b'{"historical_stop":"preserved"}')
        (new/'failed.partial').write_bytes(b'failed original bytes\x00')
        (new/'empty').write_bytes(b'')
        p=plan(study,['old','new'],{},{});binding={'final_contract_sha256':'0'*64,'root_paths':{'study/new':str(new),'study/old':str(old)}}
        dest=base/'preserved.tar';made=writer.create(p,dest,binding,deadline())
        verified=reader.verify(dest,p,binding,deadline(),expected_whole=made['whole'],expected_manifest=made['manifest'])
        portable=reader.portable_plan(p,verified)
        native=reader.verify(dest,portable,binding,deadline(),check_sources=False,expected_whole=verified['whole'],expected_manifest=verified['manifest'])
        if native['logical_members']!=4 or native['whole']!=made['whole'] or verified['files_extracted_or_executed']!=0:raise AssertionError('exact original/portable whole/member round trip')
        reject(lambda:writer.create(p,dest,binding,deadline()),FileExistsError)
        reject(lambda:writer.create(p,new/'recursive.tar',binding,deadline()),ValueError)
        diverted={k:v for k,v in p.items() if k!='members'};diverted['members']={k:dict(v) for k,v in p['members'].items()}
        diverted['members']['study/new/empty']['path']=str(old/'accepted.bin')
        reject(lambda:writer.create(diverted,base/'diverted.tar',binding,deadline()),ValueError)
        reject(lambda:reader.verify(dest,diverted,binding,deadline()),ValueError)
        reject(lambda:writer.create(p,base/'late.tar',binding,time.monotonic()-1),TimeoutError)
        reject(lambda:reader.verify(dest,p,binding,time.monotonic()-1),TimeoutError)
        reject(lambda:reader.verify(dest,p,dict(binding,final_contract_sha256='1'*64),deadline()),ValueError)
        reject(lambda:reader.verify(dest,p,binding,deadline(),check_sources=False),ValueError)
        reject(lambda:reader.portable_plan(p,dict(verified,originals_independently_reread=False)),ValueError)
        rejected_copy=base/'short.tar';rejected_copy.write_bytes(dest.read_bytes()[:-512])
        reject(lambda:reader.verify(rejected_copy,p,binding,deadline()),ValueError)
        trailing=base/'trailing.tar';trailing.write_bytes(dest.read_bytes()+b'extra')
        reject(lambda:reader.verify(trailing,p,binding,deadline()),ValueError)
        changed=base/'changed.tar';raw=bytearray(dest.read_bytes());raw[512]^=1;changed.write_bytes(raw)
        reject(lambda:reader.verify(changed,p,binding,deadline()),ValueError)
        # Fresh original readback, not two implementations trusting one manifest.
        (old/'accepted.bin').write_bytes(b'changed original')
        reject(lambda:reader.verify(dest,p,binding,deadline()),ValueError)
        (old/'accepted.bin').write_bytes(b'\x00\xff\x80fixed tensor-like bits\x00')
        for i,name in enumerate(('../escape','/absolute','payload/000000','payload/999999','ARCHIVE-MEMBERS.json')):
            bad=base/('bad-member-'+str(i)+'.tar');fixture_tar(bad,[(name,b'wrong')])
            reject(lambda:reader.verify(bad,p,binding,deadline()),ValueError)
        reject(lambda:reader.strict_json(b'{"x":1,"x":2}'),ValueError)
        reject(lambda:reader.strict_json(b'{"x":NaN}'),ValueError)
        reject(lambda:reader.strict_json(b'{ "x":1}'),ValueError)
        for kind in (b'2',b'1',b'3',b'5',b'x',b'g',b'S'):
            raw=bytearray(writer.header('payload/000000',1));raw[156:157]=kind
            reject(lambda:reader.parse_header(bytes(raw)),ValueError)
        raw=bytearray(writer.header('payload/000000',1));raw[124]=128
        reject(lambda:reader.parse_header(bytes(raw)),ValueError)
        reject(lambda:reader.parse_header(writer.header('payload/000000',4000000001)),ValueError)
        # The actual streaming writer rejects before an oversized write. A
        # separate injected synthetic input failure leaves its exclusive partial.
        f=io.BytesIO();w=writer.BoundedWriter(f,deadline())
        with patch.object(writer,'MAX_ARCHIVE',8):
            w.write(b'1234567');reject(lambda:w.write(b'89'),ValueError)
        if f.getvalue()!=b'1234567':raise AssertionError('hard byte rejection before write')
        partial=base/'interrupted.tar'
        with patch.object(writer,'open_regular',side_effect=IOError('artificial input interruption')):
            reject(lambda:writer.create(p,partial,binding,deadline()),IOError)
        if not partial.is_file() or not partial.stat().st_size:raise AssertionError('failed partial evidence retained')
        reject(lambda:writer.create(p,partial,binding,deadline()),FileExistsError)
        # Alias policy is tested without requiring Windows symlink privilege:
        # only an exact externally bound descriptor may pass, never a tar link.
        alias_plan={k:v for k,v in portable.items() if k!='members'}
        alias_plan['members']=dict(portable['members'],**{'study/new/alias':{'type':'symlink','target':'empty'}})
        alias_members=dict(verified['member_map'],**{'study/new/alias':{'type':'symlink','target':'empty'}})
        alias_manifest={'schema':'WM-DIAG0-RC1-ARCHIVE-v1','binding':binding,'root_labels':p['root_labels'],
                        'members':alias_members,'logical_payload_bytes_no_discounts':p['logical_payload_bytes_no_discounts'],
                        'alias_policy':'metadata-only; never followed/extracted/executed','compression_or_hardlink_savings_assumed':False}
        alias_rows=[(v['payload'],Path(p['members'][n]['path']).read_bytes()) for n,v in sorted(alias_members.items()) if v['type']=='file']
        alias_archive=base/'alias-descriptor.tar';fixture_tar(alias_archive,alias_rows+[(writer.MANIFEST,writer.canonical(alias_manifest))])
        alias_verified=reader.verify(alias_archive,alias_plan,binding,deadline(),check_sources=False)
        if alias_verified['logical_members']!=5 or alias_verified['regular_payload_members']!=4:raise AssertionError('alias preserved as metadata only, not an extra followed payload')
        bad=base/'missing-alias.tar'
        bad.write_bytes(dest.read_bytes())
        reject(lambda:reader.verify(bad,alias_plan,binding,deadline(),check_sources=False),ValueError)
        malicious={k:v for k,v in alias_plan.items() if k!='members'}
        malicious['members']=dict(alias_plan['members'],**{'study/new/alias':{'type':'symlink','target':'../secret'}})
        reject(lambda:writer.checked_plan(malicious),ValueError)
    folder=ROOT/'wm_diag0_rc1_final_v1';source={}
    for name in ('archive_v1.py','archive_verify_v1.py','archive_tests_v1.py','inventory.py'):
        compile((folder/name).read_bytes(),name,'exec');source[name]=identity(folder/name)
    import ast
    for name in source:ast.parse((folder/name).read_text(),feature_version=(3,6))
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('new exclusive receipt label')
    write_new(ROOT/('docs/world-model-diagnostic-rc1-final-v1-20261016/ARTIFICIAL-ARCHIVE-'+label+'.json'),{
        'status':'PASSED','source':source,'research_artifacts_read':False,'research_or_simulator_calls':0,
        'checks':['whole and every member original plus portable readback','bits/zero-byte files/STOP/failure retention','external binding not creator-only manifest','exact logical member to approved source-root path binding','independent original change detection','duplicate/existing archive refusal','self-archive recursion rejection','finite deadline and hard streaming byte limits','failed partial retained and repeat refused','truncated/modified/trailing/wrong/missing/extra member rejection','duplicate/noncanonical/nonfinite JSON rejection','link/device/directory/PAX/GNU/sparse/base256/oversized header rejection','positive metadata-only alias descriptor, no followed extra payload, plus missing/unsafe alias rejection'],
        'actual_runtime_or_alias_inventory_bound':False,'real_archive_created':False,'native_SSD_transfer_implemented':False,
        'postarchive_control_sidecar_implemented':False,'final_contract_frozen':False,'final_gate_ready':False})
    print(json.dumps({'status':'ARTIFICIAL_ARCHIVE_STREAM_AND_INDEPENDENT_READBACK_PASSED','research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
