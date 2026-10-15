"""Read-only whole/member verification. Never extract or execute archive files."""
import hashlib,json,posixpath,tarfile
from pathlib import Path,PurePosixPath

def ident(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return {'bytes':Path(p).stat().st_size,'sha256':h.hexdigest()}

def verify(path,expected,contract):
    if expected['bytes']>14000000000 or ident(path)!=expected:raise ValueError('whole final archive identity')
    found={};manifest=None
    with tarfile.open(path,'r:') as tar:
        for m in tar:
            p=PurePosixPath(m.name)
            if m.name in found or p.is_absolute() or '\\' in m.name or ':' in m.name or any(x in ('..','.') for x in p.parts) or m.size<0 or m.size>4000000000:raise ValueError('bounded unique safe archive member')
            if len(found)>100000:raise ValueError('archive member count bound')
            if m.name=='ARCHIVE-MEMBERS.json':
                if not m.isfile() or m.size>20000000 or manifest is not None:raise ValueError('archive manifest')
                def unique(pairs):
                    out={}
                    for k,v in pairs:
                        if k in out:raise ValueError('duplicate JSON key')
                        out[k]=v
                    return out
                manifest=json.loads(tar.extractfile(m).read(),object_pairs_hook=unique);continue
            if m.isfile():
                h=hashlib.sha256();size=0;f=tar.extractfile(m)
                for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
                if size!=m.size:raise ValueError('exact member length')
                found[m.name]={'type':'file','bytes':size,'sha256':h.hexdigest()}
            elif m.islnk():
                if m.linkname not in found or found[m.linkname]['type']!='file':raise ValueError('prior regular hardlink target')
                found[m.name]={'type':'hardlink','target':m.linkname}
            elif m.issym():
                resolved=posixpath.normpath(posixpath.join(str(p.parent),m.linkname))
                if '/renderer-r6/' not in m.name or '/renderer-r6/' not in resolved or PurePosixPath(m.linkname).is_absolute():raise ValueError('explicit renderer-only relative alias')
                found[m.name]={'type':'symlink','target':m.linkname}
            else:raise ValueError('unexpected executable/device/archive member type')
    if manifest is None or manifest['members']!=found or manifest['contract_sha256']!=contract:raise ValueError('every exact archived member/contract')
    return {'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','whole':expected,'members_verified':len(found)+1,'contract_sha256':contract,'extracted_or_executed_files':0}
