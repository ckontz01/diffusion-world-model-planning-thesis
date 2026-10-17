"""Independent bounded streaming USTAR readback; NO extraction or execution.

Does not trust a creator's manifest alone: caller supplies a separately bound
whole-root inventory, and cluster validation independently hashes live originals.
Windows validation instead requires all expected file hashes from that separately
authenticated readback. Never allocates from an unchecked archive declaration.
"""
import hashlib,json,os,tarfile
from pathlib import Path
from .archive_v2 import (MAX_ARCHIVE,MAX_FILE,MAX_MANIFEST,BLOCK,MANIFEST,
                        canonical,check_time,checked_plan,check_bindings,token,open_regular)


def pairs_unique(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError('duplicate JSON key')
        out[key]=value
    return out


def strict_json(raw):
    def bad(x):raise ValueError('nonfinite JSON constant')
    value=json.loads(raw.decode('utf8'),object_pairs_hook=pairs_unique,parse_constant=bad)
    if canonical(value)!=raw:raise ValueError('exact canonical bounded JSON metadata')
    return value


class Reader:
    def __init__(self,f,size,deadline):
        self.f=f;self.size=size;self.deadline=deadline;self.bytes=0;self.sha=hashlib.sha256()
    def read(self,n):
        check_time(self.deadline)
        if type(n) is not int or n<0 or self.bytes+n>self.size:raise ValueError('truncated or oversized archive declaration')
        b=self.f.read(n)
        if len(b)!=n:raise ValueError('truncated archive')
        self.bytes+=n;self.sha.update(b);return b


def parse_header(raw):
    # Only the writer's regular USTAR subset; no PAX, GNU, sparse, links,
    # directories, device nodes, executable modes, global headers or base256.
    if raw[156:157]!=b'0' or raw[257:265]!=b'ustar\x0000' or raw[345:500]!=b'\0'*155:
        raise ValueError('only regular canonical USTAR payload members')
    for part in (raw[100:108],raw[108:116],raw[116:124],raw[124:136],raw[136:148]):
        if not all(c in b'01234567\x00 ' for c in part):raise ValueError('bounded octal header fields')
    try:t=tarfile.TarInfo.frombuf(raw,encoding='ascii',errors='strict')
    except (tarfile.HeaderError,UnicodeError,ValueError) as exc:
        raise ValueError('invalid bounded USTAR header: '+str(exc))
    if t.uid!=0 or t.gid!=0 or t.mtime!=0 or t.mode!=0o600 or t.uname or t.gname or t.linkname or t.pax_headers:
        raise ValueError('fixed inert archive header fields')
    if type(t.size) is not int or not 0<=t.size<=MAX_FILE:raise ValueError('bounded regular member size')
    # A byte-for-byte canonical header check also rejects hidden extra fields,
    # alternate encodings, checksum ambiguities and nonempty link names.
    clean=tarfile.TarInfo(t.name);clean.size=t.size;clean.mode=0o600;clean.mtime=0
    if clean.tobuf(format=tarfile.USTAR_FORMAT,encoding='ascii',errors='strict')!=raw:raise ValueError('noncanonical regular header')
    return t.name,t.size


def source_hash(path,size,deadline):
    before=token(path)
    if before[2]!=size:raise ValueError('independent original size changed')
    h=hashlib.sha256();remaining=size
    with open_regular(path,before) as f:
        while remaining:
            check_time(deadline);b=f.read(min(BLOCK,remaining))
            if not b:raise ValueError('independent source truncated')
            h.update(b);remaining-=len(b)
        if f.read(1):raise ValueError('independent source grew')
    if token(path)!=before:raise ValueError('independent source changed')
    return h.hexdigest()


def verify(archive,planned,binding,deadline,check_sources=True,expected_whole=None,expected_manifest=None):
    members=checked_plan(planned)
    if check_sources:check_bindings(planned,binding)
    archive=Path(archive);before=token(archive)
    if not 1024<=before[2]<=MAX_ARCHIVE:raise ValueError('bounded archive file')
    regular=[(n,row) for n,row in sorted(members.items()) if row['type']=='file']
    for name,row in members.items():
        if check_sources and 'path' not in row:raise ValueError('cluster readback requires independent originals')
        if not check_sources and row['type']=='file' and 'sha256' not in row:raise ValueError('native readback needs separately authenticated expected hashes')
    payloads={}
    with open_regular(archive,before) as f:
        r=Reader(f,before[2],deadline)
        for i,(logical,row) in enumerate(regular):
            name,size=parse_header(r.read(512));want='payload/'+str(i).zfill(6)
            if (name,size)!=(want,row['bytes']):raise ValueError('exact allowed member order/name/size; no duplicates or extras')
            h=hashlib.sha256();remaining=size
            while remaining:
                b=r.read(min(BLOCK,remaining));h.update(b);remaining-=len(b)
            pad=r.read((-size)%512)
            if any(pad):raise ValueError('canonical zero padding')
            digest=h.hexdigest()
            if check_sources:
                if source_hash(Path(row['path']),size,deadline)!=digest:raise ValueError('archive differs from independently reread original')
            elif digest!=row['sha256']:raise ValueError('native readback differs from authenticated original member')
            payloads[logical]={'type':'file','bytes':size,'sha256':digest,'payload':name}
        name,size=parse_header(r.read(512))
        if name!=MANIFEST or not 0<size<=MAX_MANIFEST:raise ValueError('exact bounded final manifest member')
        raw=r.read(size)
        if any(r.read((-size)%512)) or r.read(1024)!=b'\0'*1024 or r.bytes!=r.size:raise ValueError('exact trailer; no hidden trailing members/data')
        manifest=strict_json(raw)
        for logical,row in members.items():
            if row['type']=='symlink':
                if check_sources:
                    p=Path(row['path']);s=token(p,True)
                    if os.readlink(str(p))!=row['target'] or token(p,True)!=s:raise ValueError('independent reviewed alias changed')
                payloads[logical]={'type':'symlink','target':row['target']}
        expected={'schema':'WM-DIAG0-RC1-ARCHIVE-v2','binding':binding,'root_labels':planned['root_labels'],
                  'members':payloads,'logical_payload_bytes_no_discounts':planned['logical_payload_bytes_no_discounts'],
                  'alias_policy':'metadata-only; never followed/extracted/executed','compression_or_hardlink_savings_assumed':False}
        if manifest!=expected:raise ValueError('manifest must match externally bound inventory and independent bytes')
        whole={'bytes':r.bytes,'sha256':r.sha.hexdigest()};mid={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        if expected_whole is not None and whole!=expected_whole:raise ValueError('bound whole archive identity')
        if expected_manifest is not None and mid!=expected_manifest:raise ValueError('bound manifest identity')
    if token(archive)!=before:raise ValueError('archive changed during independent readback')
    return {'status':'WHOLE_AND_EVERY_MEMBER_INDEPENDENTLY_VERIFIED','whole':whole,'manifest':mid,
            'logical_members':len(members),'regular_payload_members':len(regular),
            'originals_independently_reread':check_sources,'files_extracted_or_executed':0,
            'member_map':payloads}


def portable_plan(planned,verified):
    """Compact expected hashes only AFTER independent original/archive readback."""
    checked_plan(planned)
    if verified.get('status')!='WHOLE_AND_EVERY_MEMBER_INDEPENDENTLY_VERIFIED' or verified.get('originals_independently_reread') is not True:
        raise ValueError('no creator-only manifest promoted to independent proof')
    rows={n:{k:v for k,v in row.items() if k!='payload'} for n,row in verified['member_map'].items()}
    out={k:v for k,v in planned.items() if k!='members'};out['members']=rows;checked_plan(out)
    return out

