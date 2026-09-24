"""End-to-end artificial archive/transfer, including a retained failed stream."""
import common as c
import io
from pathlib import Path,PurePosixPath
import tempfile
import types
from unittest.mock import patch
import preserve

def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);source=root/'source'/'nested';source.mkdir(parents=True);(source/'.hidden').write_bytes(b'artificial-source')
        control=root/'control';control.mkdir();run=root/'run';run.mkdir();job=run/'artificial';job.mkdir()
        (job/'evidence').write_bytes(b'artificial endpoint evidence');c.seal(job,dict(artificial=True))
        auth=types.SimpleNamespace(run=run,approval={'package_sha256':'artificial'},approval_sha='artificial')
        accept=control/'FINAL-ACCEPTANCE.json'
        c.write(accept,dict(tasks=8197,episodes=8192,package='artificial',approval='artificial',run=str(run),
                           receipts=[dict(key='artificial',seal=c.sha(job/'SEAL.json'))],fixture_only=True))
        with patch.object(c,'REPO',source):
            request_path=preserve.archive(auth,control,accept)
            try:preserve.archive(auth,control,accept)
            except FileExistsError:pass
            else:raise AssertionError('Archive repeated')
        original=c.read(request_path);payload=Path(original['archive']).read_bytes()
        c.require({'source','control','run'}=={n.split('/')[0] for n in original['members']},'All archive roots')
        c.require('source/.hidden' in original['members'],'Hidden source member preserved')
        volume=dict(FileSystemLabel='THESIS_SSD',UniqueId=preserve.VOLUME,SizeRemaining=100_000_000_000,artificial=True)
        transfers=[]
        for fail in (False,True):
            remote=PurePosixPath('/lustreFS/artificial')/('run-failure' if fail else 'run-success')
            request=str(remote.parent/(remote.name+'-preservation')/'BACKUP-REQUEST.json')
            item=dict(original,run=str(remote),archive=preserve.remote_archive_path(request))
            aa=types.SimpleNamespace(run=remote,approval={'package_sha256':'artificial','run':str(remote)},approval_sha='artificial')
            class Process:
                def __init__(self,*args,**kw):self.stdout=io.BytesIO(payload[:128] if fail else payload);self.stderr=io.BytesIO(b'artificial disconnect' if fail else b'')
                def poll(self):return 1 if fail else 0
                def wait(self,**kw):return self.poll()
                def kill(self):pass
            with patch.object(preserve,'DEST',root/'mock-ssd'),patch.object(preserve,'ssd',return_value=volume),patch.object(preserve,'ssh',return_value=types.SimpleNamespace(returncode=0,stdout=c.canonical(item))),patch.object(preserve.subprocess,'Popen',Process):
                if fail:
                    try:preserve.backup(aa,request)
                    except ValueError:pass
                    else:raise AssertionError('Failed transfer accepted')
                    out=root/'mock-ssd'/remote.name
                    c.require((out/'final.tar.partial').stat().st_size==128 and (out/'BACKUP-FAILURE.json').exists() and not (out/'BACKUP-VERIFIED.json').exists(),'Failed partial retained, no fake ACK')
                else:
                    out=preserve.backup(aa,request)
                    c.require(c.sha(out/'final.tar')==original['archive_identity']['sha256'] and (out/'BACKUP-VERIFIED.json').exists(),'Whole copied-byte verification')
                    c.require(not (out/'final.tar.partial').exists(),'Successful exclusive rename, no duplicate archive')
                transfers.append(dict(failure=fail,destination_files=sorted(p.name for p in out.iterdir())))
        c.write(c.ROOT/'TEST-PRESERVATION.json',dict(passed=True,artificial_only=True,source_sha256={n:c.sha(c.ROOT/n) for n in ('preserve.py','test_preservation.py')},
                    archive=original['archive_identity'],roots=['source','control','run'],hidden_member=True,repeat_archive_rejected=True,
                    whole_and_every_member_verified=True,failed_partial_retained=True,automatic_retry=False,transfers=transfers,
                    actual_ssd_access=False,network_calls=0,cluster_calls=0))
    print('Artificial archive, successful transfer and failed-partial preservation passed')
if __name__=='__main__':main()
