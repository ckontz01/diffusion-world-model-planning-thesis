"""Frozen R1 operational preservation only. Standard library, no research imports.

One exclusive production session; no resume path. The outer watchdog owns only
its child process tree. Remote helpers have independent wall/CPU limits.
"""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import shlex
import signal
import subprocess
import sys
import tarfile
import threading
import time
import uuid

HERE=Path(__file__).resolve().parent
BASE=Path('D:/THESIS-BACKUPS/local-goal-source-replication-20260920')
OLD=BASE/'run-a8fa92772272e11a'
DEST=BASE/'run-a8fa92772272e11a-recovery-r1'
SOURCE='a8fa92772272e11a279aac6c13699fc5b6da9f8160bd3264bab15e3f6bf68cec'
APPROVAL='013dfa0c2498a627e84057d7f53a758871cae010c8f51a0db4553717a697e49b'
WHOLE='fa17faef59d068b6a71d0ca40a3178b7f1be0a4e78688282a1bd846eb8a8b2aa'
REQUEST_SHA='f980786b598867e12dd9fad0589dbc9afc642bc4441136721abbfb787457af06'
PREFIX_SHA='17193e4f9303e6180cd4dde45e4bcd491095050a12508dd07b74651b35d7fb05'
FAILURE_SHA='7d89f19b8e1e425568381e8bf3d679ddc2251bb0c19621cd465269c010d7022c'
AUTH_SHA='638e57066943747d61b43dd0c8eda55b7c2157a9e37bc1d410ee7d514ca7c810'
TOTAL,PREFIX,CHUNK=2875822080,1202438144,67108864
REMOTE='/lustreFS/data/superworld/ckontzias/thesis/experiments/local-goal-source-replication-20260920/run-a8fa92772272e11a/final-preservation/final.tar'
VOLUME='0a2f1ba9-0000-0000-0000-100000000000'
TAG='lgprb2-preservation-recovery-r1'
LIMITS=dict(transmissions=50,metadata_invocations=8,remote_archive_payload_bound=3346767872,
    range_idle_seconds=90,range_wall_seconds=300,metadata_wall_seconds=600,
    transfer_phase_seconds=5400,final_phase_seconds=1800,total_seconds=7200,
    recovery_ssd_bytes=8000000000,remote_recovery_disk_bytes=64000000,
    inclusive_remote_bytes=24000000000,remote_cpu_seconds=600,retry_delay_seconds=30,
    minimum_free_ssd_bytes=40000000000)
HISTORY=[('local-goal-proposals-20260918','run-b54a55b16bcb83a5','24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd'),
         ('local-goal-search-budget-20260919','run-a0bcdb48029909e0','72c2717be4a10b0e103a05c6575710832e5ae4c9e9a21be573c8cb3c4441f175')]


def require(ok,message):
    if not ok: raise RuntimeError(message)


def digest(path,guard=lambda:None):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while True:
            guard(); block=stream.read(1<<20)
            if not block: break
            h.update(block)
    return h.hexdigest()


def read(path): return json.loads(Path(path).read_bytes())


def write(path,value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
        stream.flush(); os.fsync(stream.fileno())


def copy_exclusive(source,target,guard=lambda:None):
    with Path(source).open('rb') as src,Path(target).open('xb') as dst:
        while True:
            guard(); block=src.read(1<<20)
            if not block: break
            dst.write(block)
        dst.flush(); os.fsync(dst.fileno())


def footprint(path):
    files=[p for p in path.rglob('*') if p.is_file()]
    require(not any(p.is_symlink() for p in files),'recovery symlink')
    return sum(p.stat().st_size for p in files)


def ssd():
    require(os.name=='nt','native Windows SSD access only')
    result=subprocess.run(['powershell','-NoProfile','-Command',
        'Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress'],
        capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    v=json.loads(result.stdout)
    require(v['FileSystemLabel']=='THESIS_SSD' and VOLUME in v['UniqueId'].lower()
            and v['SizeRemaining']>=LIMITS['minimum_free_ssd_bytes'],'SSD identity/free-space gate')
    return v


def lock_original(path):
    """Read-only Windows handle with no sharing: fails if a writer still owns it."""
    import msvcrt
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    create=kernel.CreateFileW
    create.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,
                     ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
    create.restype=ctypes.c_void_p
    handle=create(str(path),0x80000000,0,None,3,0x80,None)
    if handle==ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    return os.fdopen(msvcrt.open_osfhandle(handle,os.O_RDONLY|os.O_BINARY),'rb')


def stop_owned(proc):
    if proc.poll() is not None: return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,
                       timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
    else: os.killpg(proc.pid,signal.SIGKILL)
    try: proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait(timeout=5)


def pump(command,target,stderr_path,input_bytes=b'',maximum=CHUNK,absolute=300,idle=90,guard=lambda:None):
    """Binary bounded receiver. Preserve output/log even on watchdog/I/O failure."""
    began=time.monotonic(); last=began; received=0; reason=None; stderr_error=[]
    options=dict(stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if os.name=='nt': options['creationflags']=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP
    else: options['start_new_session']=True
    # Exclusive files precede process creation, preventing duplicate invocations.
    with Path(target).open('xb') as output,Path(stderr_path).open('xb') as errors:
        proc=subprocess.Popen(command,**options); chunks=queue.Queue(maxsize=8)
        def feed():
            try: proc.stdin.write(input_bytes); proc.stdin.close()
            except (BrokenPipeError,OSError): pass
        def receive():
            try:
                while True:
                    b=os.read(proc.stdout.fileno(),65536)
                    if not b: break
                    chunks.put(b)
            finally: chunks.put(None)
        def diagnostics():
            used=0
            try:
                while True:
                    b=os.read(proc.stderr.fileno(),8192)
                    if not b: break
                    used+=len(b)
                    if used>262144: raise RuntimeError('stderr cap exceeded')
                    errors.write(b); errors.flush()
            except BaseException as error: stderr_error.append(str(error))
        threads=[threading.Thread(target=f,daemon=True) for f in (feed,receive,diagnostics)]
        for thread in threads: thread.start()
        ended=False
        try:
            while not ended or proc.poll() is None:
                guard(); now=time.monotonic()
                if now-began>=absolute: reason='absolute_timeout'; break
                if idle is not None and now-last>=idle: reason='idle_timeout'; break
                if stderr_error: reason='local_stderr_io'; break
                try: b=chunks.get(timeout=.1)
                except queue.Empty: continue
                if b is None: ended=True; continue
                received+=len(b); last=now
                if received>maximum: reason='unexpected_stdout'; break
                output.write(b)
            if reason: stop_owned(proc)
            code=proc.wait(timeout=15)
            # After normal process exit, receive() has already enqueued all bytes.
            output.flush(); os.fsync(output.fileno())
            for thread in (threads[0],threads[2]): thread.join(timeout=5)
            require(not threads[2].is_alive(),'stderr drain unresolved')
            errors.flush(); os.fsync(errors.fileno())
        except BaseException:
            stop_owned(proc)
            raise
    return dict(returncode=code,received_bytes=received,stored_bytes=Path(target).stat().st_size,
                seconds=time.monotonic()-began,watchdog=reason,owned_pid=proc.pid,owned_process_resolved=proc.poll() is not None)


def retryable(result,stderr,remote_end=None):
    denied=('permission denied','host key verification failed','remote host identification has changed',
            'authentication failed','changed source','wrong range','hash mismatch','source eof','unexpected stdout')
    if any(term in stderr.lower() for term in denied): return False
    if result.get('watchdog') in ('unexpected_stdout','local_stderr_io'): return False
    if remote_end and not remote_end['ok']:
        return remote_end.get('error_type') in ('TimeoutError','BrokenPipeError','ConnectionResetError')
    return result.get('watchdog') in ('idle_timeout','absolute_timeout') or result['returncode']==255


def verify_archive(path,expected,guard=lambda:None):
    """Accepted lgp1_preserve.verify_archive logic, with added deadline checks."""
    seen=set()
    with tarfile.open(path,'r:') as archive:
        for member in archive:
            guard()
            require(member.isfile() and member.name in expected and member.name not in seen,'Unexpected archive member')
            stream=archive.extractfile(member); h=hashlib.sha256()
            while True:
                guard(); block=stream.read(1<<20)
                if not block: break
                h.update(block)
            require(h.hexdigest()==expected[member.name]['sha256'] and member.size==expected[member.name]['bytes'],'Archive member bytes')
            seen.add(member.name)
    require(seen==set(expected),'Archive coverage')
    return dict(files=len(seen),bytes=Path(path).stat().st_size,sha256=digest(path,guard))


def append_verified(assembled,chunk,item,guard=lambda:None):
    require(chunk.stat().st_size==item['length'],'wrong chunk length')
    require(digest(chunk,guard)==item['sha256'],'complete-length hash mismatch')
    require(assembled.stat().st_size==item['offset'],'wrong pre-append offset')
    with chunk.open('rb') as src,assembled.open('ab') as dst:
        while True:
            guard(); block=src.read(1<<20)
            if not block: break
            dst.write(block)
        dst.flush(); os.fsync(dst.fileno())
    require(assembled.stat().st_size==item['offset']+item['length'],'post-append length')


class Session:
    def __init__(self,root,start,commit):
        self.root=root; self.start=start; self.commit=commit; self.final_start=None
        self.session=read(root/'SESSION.json')['session']; self.operations=[]
        self.meta=0; self.transmissions=0; self.payload_reserved=0; self.cpu_charged=0
        self.last_offset=PREFIX; self.last_range=None; self.unresolved=[]
    def guard(self):
        now=time.monotonic()
        deadline=min(self.start+7200,(self.final_start+1800 if self.final_start else self.start+5400))
        require(now<deadline,'session phase/time limit reached')
    def record(self,value):
        self.guard()
        with (self.root/'PROGRESS.jsonl').open('ab') as stream:
            stream.write((json.dumps(dict(unix=time.time(),elapsed=time.monotonic()-self.start,**value),sort_keys=True)+'\n').encode())
            stream.flush(); os.fsync(stream.fileno())
    def command(self,op,action,quota,payload):
        args=['/usr/bin/python3.9','-B','-',TAG,self.session,op,action,str(quota),json.dumps(payload,separators=(',',':'))]
        return ['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh',
                '-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ConnectionAttempts=1',
                '-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3',
                'prometheus',' '.join(shlex.quote(x) for x in args)]
    def invoke(self,action,payload,label,maximum,is_range=False):
        self.guard()
        if is_range:
            require(self.transmissions<50 and self.payload_reserved+maximum<=3346767872,'transmission/payload cap')
            self.transmissions+=1; self.payload_reserved+=maximum
        else:
            require(self.meta<8,'metadata invocation cap'); self.meta+=1
        # Reserve one extra CPU second for RLIMIT_CPU accounting granularity.
        quota=min(120 if action=='scan' else 8,math.floor(600-self.cpu_charged-1))
        require(quota>=1,'remote CPU cap exhausted')
        op=uuid.uuid4().hex; target=self.root/(label+'.bin'); log=self.root/(label+'.stderr')
        entry=dict(operation=op,action=action,label=label,cpu_quota_seconds=quota,
                   requested_maximum=maximum,is_archive_range=is_range)
        self.operations.append(entry); self.unresolved.append(op)
        self.record(dict(event='operation_started',**entry))
        try:
            result=pump(self.command(op,action,quota,payload),target,log,(HERE/'remote_helper.py').read_bytes(),
                        maximum=maximum,absolute=300 if is_range else 600,idle=90 if is_range else None,guard=self.guard)
        except BaseException as error:
            self.cpu_charged+=quota+1
            entry.update(local_exception=str(error),remote_cpu_charge_seconds=quota+1,cpu_charge_is_upper_bound=True)
            raise
        stderr=log.read_text(encoding='utf-8',errors='replace'); records=[]
        for line in stderr.splitlines():
            try:
                r=json.loads(line)
                if r.get('session')==self.session and r.get('operation')==op: records.append(r)
            except (ValueError,AttributeError): pass
        ends=[r for r in records if r.get('event')=='end']; end=ends[-1] if ends else None
        actual=end.get('process_cpu_seconds') if end else None
        self.cpu_charged+=max(0,actual) if actual is not None else quota+1
        require(self.cpu_charged<=600,'remote CPU aggregate cap')
        if end: self.unresolved.remove(op)
        entry.update(result=result,remote_records=records,remote_cpu_charge_seconds=actual if actual is not None else quota+1,
                     cpu_charge_is_upper_bound=actual is None)
        self.record(dict(event='operation_finished',**entry))
        # A full-length corrupt attempt may never become a transport retry,
        # even if SSH also failed after the final byte.
        if is_range and result['stored_bytes']==maximum:
            require(digest(target,self.guard)==payload['sha256'],'complete-length hash mismatch; no retry')
        ok=result['returncode']==0 and not result['watchdog'] and end is not None and end['ok']
        if ok:
            require(end['payload_bytes']==result['received_bytes'],'stdout/remote byte mismatch')
            return target,entry
        transient=retryable(result,stderr,end)
        if not transient: raise RuntimeError('nonretryable operation failure: '+label)
        if op in self.unresolved:
            require(action!='reconcile','reconciliation transport failed; preserve unresolved operation')
            # This necessary reconciliation consumes metadata allowance, with no
            # nested auto-retry: failure leaves the session stopped/unresolved.
            reconciled,_=self.invoke('reconcile',dict(operation=op),label+'-reconcile',65536)
            require(not read(reconciled)['remaining'],'remote operation unresolved')
            self.unresolved.remove(op)
        return None,entry
    def operation(self,action,payload,label,maximum,is_range=False):
        for attempt in (1,2):
            path,entry=self.invoke(action,payload,label+f'-attempt-{attempt}',maximum,is_range)
            if path is not None: return path,entry
            if attempt==1:
                until=time.monotonic()+30
                while time.monotonic()<until:
                    self.guard(); time.sleep(min(.25,until-time.monotonic()))
        raise RuntimeError('two permitted transient attempts exhausted: '+label)
    def summary(self):
        return dict(session=self.session,frozen_commit=self.commit,operations=self.operations,
            metadata_invocations=self.meta,suffix_transmissions=self.transmissions,
            archive_payload_transmission_upper_bound=self.payload_reserved,
            archive_payload_received=sum(e.get('result',{}).get('received_bytes',0) for e in self.operations if e['is_archive_range']),
            remote_cpu_seconds_charged=self.cpu_charged,remote_cpu_scope='Measured CPU when helper receipt exists; whole reserved hard CPU quota otherwise.',
            last_verified_offset=self.last_offset,last_incorporated_range=self.last_range,unresolved_remote_operations=self.unresolved,
            wall_seconds=time.monotonic()-self.start,network_wire_overhead_measured=False,
            payload_scope='Archive payload only, not protocol/encryption wire measurement; failed-attempt reserved bytes included conservatively.')


def validate_request(request):
    require(request['archive']==REMOTE and request['bytes']==TOTAL and request['files']==32393 and request['sha256']==WHOLE,'archive request identity')
    require(request['source_sha256']==SOURCE and request['volume_id']==VOLUME and request['backup_destination']==BASE.as_posix(),'source/SSD binding')
    require(request['historical_archives']==[list(x) for x in HISTORY],'historical union binding')
    require(len(request['members'])==32393,'member inventory count')
    require(request['members']['run/APPROVAL.json']['sha256']==APPROVAL,'approval identity')
    require(request['members']['run/COMPUTE-COMPLETE.json']['sha256']=='22768015b5421f7a050df3b3e3bfbf83e1fe2531a3681ce63d0664a49db2df0f','completion identity')


def worker(start,commit):
    cpu=time.process_time(); session=Session(DEST,start,commit); locked=None
    try:
        startup=read(DEST/'SESSION.json')
        require(start==startup['start_monotonic'] and commit==startup['frozen_commit'],'no session clock reset')
        require(set(p.name for p in DEST.iterdir())=={'SESSION.json','SUPERVISOR.stdout','SUPERVISOR.stderr'},'worker already started; no resumption')
        session.guard(); initial_ssd=ssd()
        require(set(p.name for p in OLD.iterdir())=={'BACKUP-REQUEST.json','BACKUP-FAILURE.json','final.tar.partial'},'original directory contents changed')
        original={p.name:dict(bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,sha256=digest(p,session.guard)) for p in OLD.iterdir()}
        require(original['final.tar.partial']['bytes']==PREFIX and original['final.tar.partial']['sha256']==PREFIX_SHA,'original partial identity')
        require(original['BACKUP-REQUEST.json']['sha256']==REQUEST_SHA and original['BACKUP-FAILURE.json']['sha256']==FAILURE_SHA,'original receipt identity')
        locked=lock_original(OLD/'final.tar.partial')
        locked_hash=hashlib.sha256()
        for block in iter(lambda:locked.read(1<<20),b''):
            session.guard(); locked_hash.update(block)
        require(locked_hash.hexdigest()==PREFIX_SHA,'locked original prefix hash'); locked.seek(0)
        write(DEST/'ORIGINAL-PRESERVED.json',dict(files=original,exclusive_read_lock=True,old_transfer_session_exit_code=1))
        for name in ('recover.py','remote_helper.py','test_recovery.py','TEST-RESULTS.json','AUTHORIZATION.txt','FROZEN.json'):
            copy_exclusive(HERE/name,DEST/name,session.guard)
        request_path,_=session.operation('request',{},'request',20_000_000)
        require(digest(request_path,session.guard)==REQUEST_SHA,'remote request hash')
        copy_exclusive(request_path,DEST/'BACKUP-REQUEST.json',session.guard)
        request=read(request_path); validate_request(request)
        manifest_path,_=session.operation('scan',{},'range-manifest',200_000)
        manifest=read(manifest_path)
        require(manifest['archive']==REMOTE and manifest['sha256']==WHOLE and manifest['identity_before']==manifest['identity_after'],'manifest source identity')
        require(manifest['identity_before']['size']==TOTAL and manifest['prefix']==dict(length=PREFIX,sha256=PREFIX_SHA),'manifest prefix/size')
        require(len(manifest['ranges'])==25,'range count')
        for i,item in enumerate(manifest['ranges']):
            require(item['index']==i and item['offset']==PREFIX+i*CHUNK and item['length']==(CHUNK if i<24 else 62771200),'exact frozen ranges')
        require(manifest['storage']['total_with_history_bytes']<=24_000_000_000 and manifest['remote_recovery_disk_bytes']==0,'remote storage envelope')
        copy_exclusive(manifest_path,DEST/'RANGE-MANIFEST.json',session.guard)
        write(DEST/'RANGE-MANIFEST-SEAL.json',dict(sha256=digest(DEST/'RANGE-MANIFEST.json'),request_sha256=REQUEST_SHA,authorization_sha256=AUTH_SHA))
        assembled=DEST/'final.tar.partial'
        with assembled.open('xb') as target:
            while True:
                session.guard(); b=locked.read(1<<20)
                if not b: break
                target.write(b)
            target.flush(); os.fsync(target.fileno())
        require(assembled.stat().st_size==PREFIX and digest(assembled,session.guard)==PREFIX_SHA,'copied prefix authentication')
        session.record(dict(event='prefix_authenticated',bytes=PREFIX,sha256=PREFIX_SHA))
        for item in manifest['ranges']:
            session.guard(); require(footprint(DEST)<8_000_000_000,'SSD recovery cap')
            payload=dict(index=item['index'],offset=item['offset'],length=item['length'],sha256=item['sha256'],identity=manifest['identity_before'])
            chunk,entry=session.operation('range',payload,f"range-{item['index']:02d}",item['length'],True)
            require(chunk.stat().st_size==item['length'],'wrong successful range length')
            append_verified(assembled,chunk,item,session.guard)
            session.last_offset=item['offset']+item['length']; session.last_range=item['index']
            session.record(dict(event='range_incorporated',range=item['index'],offset=session.last_offset,sha256=item['sha256']))
            print(json.dumps(dict(range=item['index'],verified_offset=session.last_offset)),flush=True)
        session.operation('identity',dict(identity=manifest['identity_before']),'final-remote-identity',65536)
        session.final_start=time.monotonic()
        write(DEST/'FINAL-PHASE.json',dict(monotonic=session.final_start,unix=time.time()))
        session.guard(); checked=verify_archive(assembled,request['members'],session.guard)
        require(checked==dict(files=32393,bytes=TOTAL,sha256=WHOLE),'whole/member final acceptance')
        historical=[]
        for study,run,expected in HISTORY:
            root=BASE.parent/study/run; r=read(root/'BACKUP-REQUEST.json'); receipt=read(root/'BACKUP-VERIFIED.json')
            require(r['sha256']==receipt['sha256']==expected,'historical receipt binding')
            actual=verify_archive(root/'final.tar',r['members'],session.guard)
            require(actual['sha256']==expected and actual['bytes']==r['bytes'] and actual['files']==r['files'],'historical complete archive')
            historical.append(dict(path=str(root/'final.tar'),request_sha256=digest(root/'BACKUP-REQUEST.json'),receipt_sha256=digest(root/'BACKUP-VERIFIED.json'),**actual))
        locked.seek(0); final_prefix=hashlib.sha256()
        for b in iter(lambda:locked.read(1<<20),b''): session.guard(); final_prefix.update(b)
        require(final_prefix.hexdigest()==PREFIX_SHA,'original prefix changed')
        require((OLD/'final.tar.partial').stat().st_mtime_ns==original['final.tar.partial']['mtime_ns'],'original partial mtime changed')
        for name in ('BACKUP-REQUEST.json','BACKUP-FAILURE.json'):
            require(digest(OLD/name)==original[name]['sha256'] and (OLD/name).stat().st_mtime_ns==original[name]['mtime_ns'],'original receipts changed')
        final_ssd=ssd(); session.guard(); size_before=footprint(DEST)
        require(size_before+1_000_000<8_000_000_000,'final recovery footprint reservation')
        target=DEST/'final.tar'; require(not target.exists(),'exclusive final destination')
        assembled.rename(target)
        summary=session.summary()
        receipt=dict(**checked,successful_destination=str(target),original_destination=str(OLD),
            request_sha256=REQUEST_SHA,source_sha256=SOURCE,approval_sha256=APPROVAL,
            original_failed_files=original,authorization_sha256=AUTH_SHA,
            frozen_manifest_sha256=digest(HERE/'FROZEN.json'),tool_sha256=digest(HERE/'recover.py'),
            helper_sha256=digest(HERE/'remote_helper.py'),range_manifest_sha256=digest(DEST/'RANGE-MANIFEST.json'),
            historical=historical,initial_ssd=initial_ssd,final_ssd=final_ssd,
            recovery_directory_bytes_before_receipt=size_before,receipt_and_seal_reservation_bytes=1_000_000,
            remote_recovery_disk_bytes=0,inclusive_remote_bytes=manifest['storage']['total_with_history_bytes'],
            local_worker_process_cpu_seconds=time.process_time()-cpu,final_verification_wall_seconds=time.monotonic()-session.final_start,
            limits=LIMITS,first_transfer_succeeded=False,recovery_verified=True,**summary)
        write(DEST/'RECOVERY-BACKUP-VERIFIED.json',receipt)
        seal={p.name:dict(bytes=p.stat().st_size,sha256=digest(p,session.guard)) for p in DEST.iterdir() if p.is_file() and p.name not in ('SUPERVISOR.stdout','SUPERVISOR.stderr')}
        write(DEST/'RECOVERY-SEAL.json',seal)
        require(footprint(DEST)<8_000_000_000,'sealed recovery footprint cap')
        print(json.dumps(dict(recovery_verified=True,receipt_sha256=digest(DEST/'RECOVERY-BACKUP-VERIFIED.json'),
                              bytes=footprint(DEST),local_total_process_cpu_seconds=time.process_time()-cpu,
                              wall_through_seal_seconds=time.monotonic()-start)),flush=True)
    except BaseException as error:
        write(DEST/'RECOVERY-FAILURE.json',dict(error_type=type(error).__name__,error=str(error),automatic_new_session=False,
              local_worker_process_cpu_seconds=time.process_time()-cpu,**session.summary()))
        raise
    finally:
        if locked is not None: locked.close()


def package_check():
    frozen=read(HERE/'FROZEN.json')
    require(frozen['limits']==LIMITS and frozen['authorization_sha256']==AUTH_SHA,'frozen limits/authority')
    for name,value in frozen['files'].items(): require(digest(HERE/name)==value,'frozen tool file '+name)
    require(read(HERE/'TEST-RESULTS.json')['passed'],'synthetic tests not passed')


def execute(commit):
    package_check(); require(not DEST.exists(),'R1 exists: stop for reconciliation; no resume')
    require(len(commit)==40 and all(x in '0123456789abcdef' for x in commit),'frozen commit')
    began=time.monotonic(); initial=ssd(); DEST.mkdir(exist_ok=False)
    write(DEST/'SESSION.json',dict(session=uuid.uuid4().hex,start_monotonic=began,start_unix=time.time(),
                                 frozen_commit=commit,initial_ssd=initial,limits=LIMITS))
    def watchdog():
        now=time.monotonic(); final=DEST/'FINAL-PHASE.json'
        deadline=began+5400
        if final.exists(): deadline=min(began+7200,read(final)['monotonic']+1800)
        require(now<deadline,'outer session phase watchdog')
    try:
        result=pump([sys.executable,'-B',str(HERE/'recover.py'),'worker','--start',str(began),'--commit',commit],
                    DEST/'SUPERVISOR.stdout',DEST/'SUPERVISOR.stderr',maximum=1_000_000,
                    absolute=7200,idle=None,guard=watchdog)
        require(result['returncode']==0 and not result['watchdog'],'R1 worker failed; see preserved logs')
        require((DEST/'RECOVERY-BACKUP-VERIFIED.json').exists() and not (DEST/'RECOVERY-FAILURE.json').exists(),'final success gate')
        last=json.loads((DEST/'SUPERVISOR.stdout').read_text().splitlines()[-1])
        write(DEST/'RECOVERY-SESSION-COMPLETE.json',dict(supervisor=result,worker=last,
              recovery_seal_sha256=digest(DEST/'RECOVERY-SEAL.json'),
              receipt_sha256=digest(DEST/'RECOVERY-BACKUP-VERIFIED.json'),
              directory_bytes_before_this_record=footprint(DEST),
              wall_seconds=time.monotonic()-began,complete=True))
        require(footprint(DEST)<8_000_000_000,'terminal storage cap')
        print(json.dumps(dict(supervisor=result,receipt=str(DEST/'RECOVERY-BACKUP-VERIFIED.json'))))
    except BaseException as error:
        write(DEST/'SUPERVISOR-FAILURE.json',dict(error=str(error),seconds=time.monotonic()-began,
              automatic_resume=False,remote_helpers='If any unknown, bounded independently to 280/580 seconds and hard per-helper CPU quota; reconcile before any separately authorized recovery.'))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=('execute','worker'))
    parser.add_argument('--commit',required=True); parser.add_argument('--start',type=float)
    args=parser.parse_args()
    if args.command=='execute': execute(args.commit)
    else:
        require(args.start is not None,'missing session start'); package_check(); worker(args.start,args.commit)
