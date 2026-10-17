"""Once-only, uncompressed preservation primitive; NO research entry point.

Logical paths and reviewed aliases are recorded in ARCHIVE-MEMBERS.json. Regular
bytes use numbered, regular USTAR members, so no archive-supplied path or symlink
is ever followed/extracted/executed. Aliases are preserved as metadata, not as
executable filesystem links. This is NOT a ready/frozen finalization gate.
"""
import hashlib,json,os,stat,tarfile,time
from pathlib import Path
from .inventory import safe_name,MAX_MEMBERS,MAX_PAYLOAD,OVERHEAD

MAX_ARCHIVE=14000000000
MAX_FILE=4000000000
MAX_MANIFEST=20000000
BLOCK=1048576
MANIFEST='ARCHIVE-MEMBERS.json'


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')


def check_time(deadline):
    if not isinstance(deadline,(int,float)) or not time.monotonic()<deadline:
        raise TimeoutError('finite preservation deadline exhausted; retain partial')


def token(path,alias=False):
    path=Path(path)
    # No ancestor redirect is accepted by this primitive. Actual root/alias
    # bindings still require independent reconciliation in the future contract.
    for p in path.parents:
        if p.is_symlink():raise ValueError('symlink ancestor is not a reviewed root')
    s=path.lstat()
    if not (stat.S_ISLNK(s.st_mode) if alias else stat.S_ISREG(s.st_mode)):
        raise ValueError('exact declared regular file or metadata-only alias')
    if os.name=='nt' and not alias:
        # This runtime's Windows lstat/fstat expose different ctime semantics
        # after file writes. Use HANDLE metadata consistently for all regular
        # tokens, including before/after, rather than discarding the field.
        fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_BINARY',0))
        try:
            actual=os.fstat(fd);after=path.lstat()
            fields=('st_dev','st_ino','st_size','st_mtime_ns','st_mode')
            if any(getattr(s,k)!=getattr(actual,k) or getattr(after,k)!=getattr(actual,k) for k in fields):
                raise ValueError('Windows handle/path identity race')
            s=actual
        finally:os.close(fd)
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode)


def open_regular(path,expected):
    if token(path)!=expected:raise ValueError('input changed before open')
    fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
    f=os.fdopen(fd,'rb')
    s=os.fstat(f.fileno())
    actual=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode)
    if actual!=expected:
        f.close();raise ValueError('input inode changed at open: expected='+repr(expected)+' actual='+repr(actual))
    return f


def checked_plan(planned):
    if not isinstance(planned,dict) or set(planned)!={'members','logical_payload_bytes_no_discounts','archive_reserved_bytes','root_labels','compression_or_hardlink_savings_assumed'}:
        raise ValueError('explicit independent whole-root inventory required')
    members=planned['members']
    if not isinstance(members,dict) or not 0<len(members)<=MAX_MEMBERS:raise ValueError('bounded nonempty inventory')
    total=0
    for name,row in members.items():
        safe_name(name)
        if not isinstance(row,dict) or row.get('type') not in ('file','symlink'):raise ValueError('explicit member kind')
        if row['type']=='file':
            if set(row) not in ({'path','type','bytes'},{'type','bytes','sha256'}):raise ValueError('exact file inventory fields')
            if type(row['bytes']) is not int or not 0<=row['bytes']<=MAX_FILE:raise ValueError('bounded numeric member bytes')
            total+=row['bytes']
            if 'sha256' in row and (len(row['sha256'])!=64 or any(c not in '0123456789abcdef' for c in row['sha256'])):raise ValueError('exact SHA256')
        else:
            if set(row) not in ({'path','type','target'},{'type','target'}):raise ValueError('exact metadata-only alias fields')
            safe_name(row['target'])
    roots=planned['root_labels']
    if not isinstance(roots,list) or roots!=sorted(set(roots)) or any(not any(n==r or n.startswith(r+'/') for r in roots) for n in members):raise ValueError('explicit root labels')
    for r in roots:safe_name(r)
    if total!=planned['logical_payload_bytes_no_discounts'] or total>MAX_PAYLOAD or planned['archive_reserved_bytes']!=total+OVERHEAD or planned['compression_or_hardlink_savings_assumed'] is not False:
        raise ValueError('all logical copies and full overhead charged')
    if total+OVERHEAD>MAX_ARCHIVE or len(members)*4096+MAX_MANIFEST>OVERHEAD:raise ValueError('archive/manifest/member reservation')
    return members


def check_bindings(planned,binding):
    """Bind logical source names to exact locally approved root paths."""
    roots=binding.get('root_paths') if isinstance(binding,dict) else None
    digest=binding.get('final_contract_sha256','') if isinstance(binding,dict) else ''
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('future exact contract binding')
    if not isinstance(roots,dict) or set(roots)!=set(planned['root_labels']):raise ValueError('bound actual whole-root paths')
    for path in roots.values():
        if not isinstance(path,str) or not Path(path).is_absolute() or '..' in Path(path).parts:raise ValueError('canonical absolute source root')
    for name,row in planned['members'].items():
        label=max((r for r in roots if name==r or name.startswith(r+'/')),key=len)
        relative=name[len(label):].lstrip('/')
        expected=Path(roots[label])/relative if relative else Path(roots[label])
        if 'path' not in row or Path(row['path'])!=expected:raise ValueError('member source must match separately bound logical root')
    return roots


class BoundedWriter:
    def __init__(self,f,deadline):
        self.f=f;self.deadline=deadline;self.bytes=0;self.sha=hashlib.sha256()
    def write(self,b):
        check_time(self.deadline)
        if self.bytes+len(b)>MAX_ARCHIVE:raise ValueError('hard archive output byte limit; retain partial')
        n=self.f.write(b)
        if n!=len(b):raise IOError('short archive write; retain partial')
        self.bytes+=n;self.sha.update(b)


def header(name,size):
    t=tarfile.TarInfo(name);t.size=size;t.mode=0o600;t.uid=0;t.gid=0;t.mtime=0
    # Numbered payload names cannot require PAX/GNU extensions or traversal.
    return t.tobuf(format=tarfile.USTAR_FORMAT,encoding='ascii',errors='strict')


def create(planned,destination,binding,deadline):
    """Future allocated caller only, after all terminal acceptance/gates.

    Existing destinations/partials are never replaced or retried. A failed
    exclusive file remains evidence. No sidecar/source/control file is mutated.
    """
    members=checked_plan(planned);roots=check_bindings(planned,binding);dest=Path(destination)
    if not dest.is_absolute() or not dest.parent.is_dir() or dest.parent.is_symlink():raise ValueError('explicit existing preservation directory')
    for row in members.values():
        if 'path' not in row:raise ValueError('creator needs actual independently bound input paths')
        p=Path(row['path'])
        if not p.is_absolute() or dest==p or p in dest.parents:raise ValueError('archive outside every inventoried input')
    # The caller must bind this directory outside ALL input roots, not just
    # outside files. Enforce that independently using exact root path metadata.
    for p in roots.values():
        root=Path(p)
        if not root.is_absolute() or dest==root or root in dest.parents:raise ValueError('no self-archive recursion')
    check_time(deadline);manifest_members={};i=0
    with dest.open('xb') as f:
        w=BoundedWriter(f,deadline)
        for name,row in sorted(members.items()):
            check_time(deadline);p=Path(row['path'])
            if row['type']=='symlink':
                before=token(p,True);target=os.readlink(str(p))
                if target!=row['target'] or token(p,True)!=before:raise ValueError('reviewed alias identity changed')
                manifest_members[name]={'type':'symlink','target':target};continue
            before=token(p)
            if before[2]!=row['bytes']:raise ValueError('planned input size changed')
            payload='payload/'+str(i).zfill(6);i+=1;w.write(header(payload,row['bytes']))
            h=hashlib.sha256();remaining=row['bytes']
            with open_regular(p,before) as source:
                while remaining:
                    check_time(deadline);b=source.read(min(BLOCK,remaining))
                    if not b:raise IOError('input shortened during preservation')
                    w.write(b);h.update(b);remaining-=len(b)
                if source.read(1):raise ValueError('input grew during preservation')
            if token(p)!=before:raise ValueError('input changed during preservation')
            digest=h.hexdigest()
            if 'sha256' in row and digest!=row['sha256']:raise ValueError('pre-bound input digest changed')
            w.write(b'\0'*((-row['bytes'])%512))
            manifest_members[name]={'type':'file','bytes':row['bytes'],'sha256':digest,'payload':payload}
        manifest={'schema':'WM-DIAG0-RC1-ARCHIVE-v1','binding':binding,'root_labels':planned['root_labels'],
                  'members':manifest_members,'logical_payload_bytes_no_discounts':planned['logical_payload_bytes_no_discounts'],
                  'alias_policy':'metadata-only; never followed/extracted/executed','compression_or_hardlink_savings_assumed':False}
        raw=canonical(manifest)
        if len(raw)>MAX_MANIFEST:raise ValueError('manifest byte bound; retain partial')
        w.write(header(MANIFEST,len(raw)));w.write(raw);w.write(b'\0'*((-len(raw))%512));w.write(b'\0'*1024)
        f.flush();os.fsync(f.fileno());check_time(deadline)
        return {'whole':{'bytes':w.bytes,'sha256':w.sha.hexdigest()},'manifest':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
                'logical_members':len(members),'regular_payload_members':i,'aliases_metadata_only':len(members)-i,
                'status':'CREATED_NOT_INDEPENDENTLY_VERIFIED','source_or_control_mutations':0}
