"""R1 single-process, read-only archive helper; sent through SSH stdin."""
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path('/lustreFS/data/superworld/ckontzias/thesis')
RUN = ROOT/'experiments/local-goal-source-replication-20260920/run-a8fa92772272e11a'
ARCHIVE = RUN/'final-preservation/final.tar'
REQUEST = RUN/'final-preservation/BACKUP-REQUEST.json'
SOURCE = ROOT/'snapshots/local-goal-source-replication-20260920-a8fa92772272e11a'
WHOLE = 'fa17faef59d068b6a71d0ca40a3178b7f1be0a4e78688282a1bd846eb8a8b2aa'
REQUEST_SHA = 'f980786b598867e12dd9fad0589dbc9afc642bc4441136721abbfb787457af06'
PREFIX_SHA = '17193e4f9303e6180cd4dde45e4bcd491095050a12508dd07b74651b35d7fb05'
TOTAL, PREFIX, CHUNK = 2875822080, 1202438144, 67108864
TAG = 'lgprb2-preservation-recovery-r1'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def identity(path):
    s = os.stat(path, follow_symlinks=False)
    require(path.is_file() and not path.is_symlink(), 'not a regular nonsymlink file')
    return dict(device=s.st_dev, inode=s.st_ino, size=s.st_size,
                mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)


def ranges(total=TOTAL, prefix=PREFIX, chunk=CHUNK):
    return [dict(index=i, offset=offset, length=min(chunk,total-offset))
            for i,offset in enumerate(range(prefix,total,chunk))]


def scan(path, prefix=PREFIX, chunk=CHUNK, expected_whole=WHOLE, expected_prefix=PREFIX_SHA):
    before = identity(path)
    items = ranges(before['size'],prefix,chunk)
    whole, head = hashlib.sha256(), hashlib.sha256()
    with path.open('rb') as stream:
        remaining = prefix
        while remaining:
            block = stream.read(min(1<<20,remaining))
            require(block, 'premature EOF in prefix')
            whole.update(block); head.update(block); remaining -= len(block)
        for item in items:
            digest = hashlib.sha256(); remaining = item['length']
            while remaining:
                block = stream.read(min(1<<20,remaining))
                require(block, 'premature EOF in suffix')
                whole.update(block); digest.update(block); remaining -= len(block)
            item['sha256'] = digest.hexdigest()
        require(not stream.read(1), 'extra source bytes')
    after = identity(path)
    require(before == after, 'changed source')
    require(whole.hexdigest() == expected_whole, 'whole hash mismatch')
    require(head.hexdigest() == expected_prefix, 'prefix hash mismatch')
    return dict(archive=str(path), identity_before=before, identity_after=after,
                sha256=whole.hexdigest(), prefix=dict(length=prefix,sha256=head.hexdigest()),ranges=items)


def stream_range(path, item, expected_identity, writer):
    require(identity(path) == expected_identity, 'changed source before range')
    with path.open('rb') as stream:
        stream.seek(item['offset']); remaining = item['length']
        while remaining:
            block = stream.read(min(65536,remaining))
            require(block, 'premature local source EOF')
            writer(block); remaining -= len(block)
    require(identity(path) == expected_identity, 'changed source after range')


def own_processes(session, operation):
    found = []
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit() or int(folder.name) == os.getpid():
            continue
        try:
            args = (folder/'cmdline').read_bytes().split(b'\0')
            marker = [TAG.encode(), session.encode(), operation.encode()]
            if args[3:6] == marker and args[0] == b'/usr/bin/python3.9' and folder.stat().st_uid == os.getuid():
                stat = (folder/'stat').read_text().rsplit(')',1)[1].split()
                found.append(dict(pid=int(folder.name),start_ticks=int(stat[19])))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return found


def reconcile(session, operation):
    initial = own_processes(session,operation)
    for item in initial:
        if item in own_processes(session,operation):
            os.kill(item['pid'],signal.SIGTERM)
    until = time.monotonic()+5
    while own_processes(session,operation) and time.monotonic()<until:
        time.sleep(.1)
    for item in own_processes(session,operation):
        if item in initial:
            os.kill(item['pid'],signal.SIGKILL)
    until=time.monotonic()+5
    while own_processes(session,operation) and time.monotonic()<until:
        time.sleep(.1)
    remaining=own_processes(session,operation)
    require(not remaining,'owned remote sender unresolved')
    return dict(initial=initial,remaining=remaining)


def main():
    import resource
    # python -B - TAG session operation action cpu_limit payload_JSON
    tag,session,operation,action,cpu_limit,payload = sys.argv[1:]
    require(tag == TAG and len(session)==32 and len(operation)==32,'invalid operation identity')
    cpu_limit=int(cpu_limit); require(1<=cpu_limit<=120,'CPU quota')
    resource.setrlimit(resource.RLIMIT_CPU,(cpu_limit,cpu_limit))
    wall=280 if action=='range' else 580
    def expired(*_): raise TimeoutError('remote wall watchdog')
    signal.signal(signal.SIGALRM,expired); signal.alarm(wall)
    start=time.monotonic(); cpu=time.process_time(); sent=0
    ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
    def record(event, **kw):
        print(json.dumps(dict(event=event,session=session,operation=operation,pid=os.getpid(),
                              start_ticks=ticks,**kw)),file=sys.stderr,flush=True)
    def send(block):
        nonlocal sent
        view=memoryview(block)
        while view:
            n=os.write(sys.stdout.fileno(),view); sent+=n; view=view[n:]
    record('start',action=action,cpu_limit=cpu_limit,wall_limit=wall)
    try:
        options=json.loads(payload)
        if action=='request':
            b=REQUEST.read_bytes()
            require(hashlib.sha256(b).hexdigest()==REQUEST_SHA,'request hash mismatch')
            send(b)
        elif action=='scan':
            require(identity(ARCHIVE)['size']==TOTAL,'archive size mismatch')
            result=scan(ARCHIVE)
            sys.path.insert(0,str(SOURCE/'cluster/prometheus'))
            import lgprb2_contract as contract
            result['storage']=contract.storage(SOURCE,RUN)
            result['remote_recovery_disk_bytes']=0
            send(json.dumps(result,sort_keys=True).encode())
        elif action=='range':
            items=ranges(); index=options['index']
            require(type(index) is int and 0<=index<len(items),'range index')
            item=items[index]
            require(item['offset']==options['offset'] and item['length']==options['length'],'wrong range offset/length')
            stream_range(ARCHIVE,item,options['identity'],send)
        elif action=='identity':
            require(identity(ARCHIVE)==options['identity'],'changed source final identity')
            send(json.dumps(identity(ARCHIVE)).encode())
        elif action=='reconcile':
            send(json.dumps(reconcile(session,options['operation'])).encode())
        else: raise RuntimeError('unknown action')
        record('end',ok=True,payload_bytes=sent,process_cpu_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-start)
    except BaseException as error:
        record('end',ok=False,error_type=type(error).__name__,error=str(error),payload_bytes=sent,
               process_cpu_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-start)
        raise
    finally: signal.alarm(0)


if __name__=='__main__': main()
