"""Local immutable thin source transport. Does NOT stage, load or launch."""
import common as c
import tarfile


def main():
    members={}
    files=dict(c.read(c.ROOT/'SOURCE-MANIFEST.json')['files'])
    for name in ('SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json'):
        files[(c.ROOT/name).relative_to(c.REPO).as_posix()]=c.sha(c.ROOT/name)
    archive=c.ROOT/'source-export.tar'
    with archive.open('xb') as f:
        with tarfile.open(fileobj=f,mode='w',format=tarfile.PAX_FORMAT) as tar:
            for name,sha in sorted(files.items()):
                path=c.REPO/name;c.require(c.sha(path)==sha,'Source identity')
                info=tar.gettarinfo(str(path),arcname=name);info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
                with path.open('rb') as stream:tar.addfile(info,stream)
                members[name]={'sha256':sha,'bytes':path.stat().st_size}
    from preserve import verify_tar
    verify_tar(archive,members)
    c.write(c.ROOT/'SOURCE-TRANSPORT.json',{'sha256':c.sha(archive),'bytes':archive.stat().st_size,'members':members,
                                         'research_payloads_included':0,'execution_authorized':False})
    print('Verified thin source archive:',archive.stat().st_size,'bytes;',len(members),'members; not staged or launched')


if __name__=='__main__':main()
