"""Native Windows final transfer primitives, no real transfer entry point yet.

Only the future frozen final contract/controller may authenticate the terminal
CPU/acceptance/archive/sidecar chain and call these. No scientific results decoded,
compute submitted, remote code installed, archive extracted or network retried.
"""
import hashlib,os,queue,subprocess,threading,time
from pathlib import Path
from .archive_v1 import check_time,MAX_ARCHIVE,token
from .archive_verify_v1 import verify
from .postarchive_v1 import valid_identity


def destination():
    """Must be called before an eventual actual transfer, not in artificial tests."""
    if os.name!='nt':raise RuntimeError('native Windows SSD writer only')
    from wm_diag0_preflight_v1.preserve import volume
    v=volume()
    # Existing volume() checks exact THESIS_SSD label, approved GUID, healthy
    # status and >=40GiB free. No repair, remount or different-volume fallback.
    return Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-rc1-final-20261016'),v


def transport_command(remote_archive,approved_remote_archive,seconds):
    """Exact already-authenticated remote pathname, configured SSH route only."""
    import shlex
    if remote_archive!=approved_remote_archive or not isinstance(remote_archive,str) or not remote_archive.startswith('/lustreFS/data/superworld/ckontzias/thesis/experiments/') or not remote_archive.endswith('/final-study.tar') or '..' in remote_archive.split('/') or '\x00' in remote_archive or '\n' in remote_archive:
        raise ValueError('exact final contract-bound remote archive path')
    if type(seconds) is not int or not 1<=seconds<=7200:raise ValueError('finite separately reserved transfer wall limit; no default grant')
    return ['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout',str(seconds)+'s','ssh',
            '-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ConnectionAttempts=1','prometheus','cat -- '+shlex.quote(remote_archive)]


def stream_once(factory,partial,expected,deadline):
    """Write directly to exclusive designated partial; caller enforces volume.

    One bounded two-chunk queue makes a silent/hung source subject to wall time
    too. Reader never writes files. On failure kill ONLY this owned transport;
    keep partial bytes, caller's stderr and provenance, and do not retry.
    Future outer resource controller must include bounded cleanup/finalization.
    """
    valid_identity(expected,MAX_ARCHIVE);partial=Path(partial);check_time(deadline)
    if not partial.is_absolute() or partial.parent.is_symlink():raise ValueError('explicit nonredirected native destination')
    for p in partial.parents:
        if p.is_symlink():raise ValueError('no ancestor destination redirect')
    q=queue.Queue(maxsize=2);stop=threading.Event();p=None;thread=None;count=0;h=hashlib.sha256()
    def put(item):
        while not stop.is_set():
            try:q.put(item,timeout=.05);return
            except queue.Full:pass
    def pump():
        try:
            while not stop.is_set():
                b=p.stdout.read(1048576)
                if not b:put(('EOF',None));return
                put(('DATA',b))
        except BaseException as exc:put(('ERROR',repr(exc)))
    # Refuse existing/ambiguous partial BEFORE starting any transport.
    with partial.open('xb') as out:
        try:
            check_time(deadline);p=factory()
            if p.stdout is None:raise ValueError('owned binary transport pipe required')
            thread=threading.Thread(target=pump,name='wm-rc1-owned-transfer-reader',daemon=True);thread.start()
            while True:
                check_time(deadline)
                try:kind,b=q.get(timeout=min(.1,max(.001,deadline-time.monotonic())))
                except queue.Empty:continue
                if kind=='EOF':break
                if kind!='DATA' or not isinstance(b,bytes):raise IOError('owned source failed: '+str(b))
                if count+len(b)>expected['bytes']:raise ValueError('exact authenticated transfer byte ceiling')
                if out.write(b)!=len(b):raise IOError('short native transfer write')
                count+=len(b);h.update(b)
            check_time(deadline)
            if p.wait(timeout=max(.001,deadline-time.monotonic()))!=0:raise ValueError('transport nonzero exit; retain exact partial')
            whole={'bytes':count,'sha256':h.hexdigest()}
            if whole!=expected:raise ValueError('exact native transfer whole identity')
            out.flush();os.fsync(out.fileno());check_time(deadline)
            return {'status':'TRANSFERRED_PENDING_INDEPENDENT_MEMBER_READBACK','whole':whole,'partial':str(partial),'automatic_retry':False}
        finally:
            stop.set()
            if p is not None and p.poll() is None:
                p.kill()
                # Cleanup is bounded, not an indefinite wait or a new transfer.
                try:p.wait(timeout=2)
                except subprocess.TimeoutExpired:pass
            if thread is not None:thread.join(timeout=.1)


def verify_and_promote(partial,target,portable_inventory,binding,expected_whole,expected_manifest,deadline):
    if os.name!='nt':raise RuntimeError('native Windows non-overwriting rename required')
    partial=Path(partial);target=Path(target)
    if target.parent!=partial.parent or target.exists() or target.is_symlink():raise FileExistsError('no completed archive replacement or third copy')
    before=token(partial)
    proof=verify(partial,portable_inventory,binding,deadline,check_sources=False,
                 expected_whole=expected_whole,expected_manifest=expected_manifest)
    if token(partial)!=before:raise ValueError('partial changed after complete readback')
    # Windows rename refuses existing target; no copy/overwrite or third full
    # file. Caller records a separate compact SSD/control-chain receipt next.
    partial.rename(target);check_time(deadline)
    return {k:v for k,v in proof.items() if k!='member_map'}
