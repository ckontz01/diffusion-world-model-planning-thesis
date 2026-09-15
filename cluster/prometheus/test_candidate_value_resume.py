"""Synthetic dispatcher race/resume tests. No model, data or cluster access."""
import errno
import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import candidate_value_contract as ct
import candidate_value_dispatch as dp
import candidate_value_backup_resume as br


def fixture(root):
    source=root/'source';source.mkdir();(source/ct.DOC).parent.mkdir(parents=True)
    (source/ct.DOC).write_text('unchanged synthetic protocol')
    (source/'SOURCE-MANIFEST.sha256').write_text('synthetic manifest')
    run=root/'run';run.mkdir();cap=root/'capsule.json';cap.write_text('{}')
    approval=root/'APPROVAL.json'
    ct.json_write(approval,dict(prior_allocations=[dict(job='301159',gpu=True,seconds=45,state='FAILED')]))
    specs=[ct.task('preflight',i) for i in range(2)]+[ct.task('train',i) for i in range(81)]
    secs=[80,80]+[210]*79+[267,89];events=[];rows=[]
    for i,(spec,seconds) in enumerate(zip(specs,secs)):
        job='301256' if i==82 else str(300000+i)
        events.append(dict(event='submitted',job=job,task=spec))
        if i<82:events.append(dict(event='terminal',job=job,state='COMPLETED',exit_code='0:0',seconds=seconds))
        d=run/('%s-%d'%(spec['kind'],spec['index']));d.mkdir()
        ct.json_write(d/'REPORT.json',dict(kind=spec['kind'],index=spec['index'],technical_valid=True,
                      protected_payload_reads=0,historical_decisions_changed=False,
                      source_sha256='src',capsule_sha256=ct.sha(cap)))
        ct.seal(d);rows.append(dict(job=job,task=spec,seconds=seconds,seal_sha256=ct.sha(d/'sha256.txt')))
    events.append(dict(event='technical_pilot_passed'))
    events.append(dict(event='dispatch_stopped',error_type='FileNotFoundError',active_job='301256',message='tmp-train-80/x'))
    (run/'DISPATCH.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n')
    receipt=root/'RESUME-APPROVAL.json'
    r=dict(researcher_approved=True,next_train_index=81,controller_sha256=ct.sha(dp.__file__),
           run=str(run),source_sha256='src',capsule_sha256=ct.sha(cap),approval_sha256=ct.sha(approval),
           caps=ct.CAPS,protocol_sha256=ct.sha(source/ct.DOC),dispatch_sha256=ct.sha(run/'DISPATCH.jsonl'),
           completed=rows,gpu_seconds=17151,cpu_seconds=0)
    ct.json_write(receipt,r)
    ct.json_write(root/'BACKUP-READY.json',dict(external_mount='/mnt/d',free_bytes=40000000000,source_sha256='src',utc=time.time()))
    accounting='\n'.join('%s|COMPLETED|0:0|%d|'%(x['job'],x['seconds']) for x in rows)
    return source,run,approval,cap,receipt,r,accounting


class ResumeTests(unittest.TestCase):
    def test_idle_backup_restore_exact_once_and_no_retry(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory() as d:
                base=Path(d);run=base/'runs'/'run-src';dest=base/'backups'/'run-src';dest.mkdir(parents=True)
                control=base/'control';control.mkdir();called=[];ready=[];phase=[False]
                def mapped(value):
                    if str(value)=='/mnt/d/THESIS-BACKUPS/candidate-value-learning-20260914':return dest.parent
                    return Path(value)
                def ssh(cmd):
                    if phase[0]:return b'yes'
                    return b'no'
                def remote(path,value):ready.append((path,value));phase[0]=True
                def once(*args):
                    called.append(args[-1])
                    if fail:raise RuntimeError('transport failure')
                with patch.object(br,'Path',side_effect=mapped),patch.object(ct,'RUN_PARENT',run.parent),\
                     patch.object(br.subprocess,'check_output',side_effect=['/mnt/d','THESIS_SSD']),\
                     patch.object(br.shutil,'disk_usage',return_value=types.SimpleNamespace(free=40000000000)),\
                     patch.object(br.original,'ssh',side_effect=ssh),patch.object(br.original,'remote_json',side_effect=remote),\
                     patch.object(br.original,'once',side_effect=once),patch.object(br.time,'sleep'):
                    if fail:
                        with self.assertRaises(RuntimeError):br.restore(run,control,'src')
                        self.assertEqual(called,['train'])
                    else:
                        br.restore(run,control,'src');self.assertEqual(called,list(br.STAGES))
                self.assertEqual(len(ready),1)
                self.assertTrue((dest.parent/'BACKUP-WATCH-RESUME-run-src.json').is_file())

    def test_backup_restore_rejects_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);dest=base/'run-src';dest.mkdir();(dest/'partial.tar').write_bytes(b'preserve')
            run=base/'runs'/'run-src'
            def mapped(value):
                return base if str(value)=='/mnt/d/THESIS-BACKUPS/candidate-value-learning-20260914' else Path(value)
            with patch.object(br,'Path',side_effect=mapped),patch.object(ct,'RUN_PARENT',run.parent),\
                 patch.object(br.subprocess,'check_output',side_effect=['/mnt/d','THESIS_SSD']),\
                 patch.object(br.original,'once') as once:
                with self.assertRaises(RuntimeError):br.restore(run,base,'src')
                once.assert_not_called()
            self.assertEqual((dest/'partial.tar').read_bytes(),b'preserve')

    def test_file_disappearance_and_no_swallowed_errors(self):
        with patch.object(Path,'stat',side_effect=FileNotFoundError):
            self.assertEqual(dp.file_bytes(['vanished']),0)
        for error in (PermissionError(errno.EACCES,'denied'),OSError(errno.EIO,'I/O')):
            with patch.object(Path,'stat',side_effect=error):
                with self.assertRaises(type(error)):dp.file_bytes(['unreadable'])
        with patch.object(Path,'stat',return_value=types.SimpleNamespace(st_mode=0o100644,st_size=19)) as call:
            self.assertEqual(dp.file_bytes(['file']),19);self.assertEqual(call.call_count,1)

    def test_walk_disappearance_and_permission(self):
        def gone(path,onerror):onerror(FileNotFoundError());return iter(())
        with patch.object(dp.os,'walk',side_effect=gone):self.assertEqual(dp.bytes_used('x'),0)
        def denied(path,onerror):onerror(PermissionError());return iter(())
        with patch.object(dp.os,'walk',side_effect=denied):
            with self.assertRaises(PermissionError):dp.bytes_used('x')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'file').write_bytes(b'123');(p/'dir').mkdir();(p/'dir'/'f').write_bytes(b'12')
            self.assertEqual(dp.bytes_used(p),5)

    def test_resume_exact_scope_and_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            src,run,app,cap,receipt,r,account=fixture(Path(d))
            with patch.object(dp,'command',return_value=account):
                prior,gpu,cpu,jobs=dp.resume_state(src,run,app,cap,'src',receipt,ct.sha(receipt))
                self.assertEqual((gpu,cpu,len(jobs)),(17151,0,83))
                for key,value in [('researcher_approved',False),('next_train_index',80),('controller_sha256','bad'),
                                  ('gpu_seconds',17062),('dispatch_sha256','bad')]:
                    with patch.object(ct,'json_read',side_effect=lambda p:dict(r,**{key:value}) if Path(p)==receipt else json.loads(Path(p).read_text())):
                        with self.assertRaises(RuntimeError):dp.resume_state(src,run,app,cap,'src',receipt,ct.sha(receipt))
            for bad in (account.replace('COMPLETED','RUNNING',1),account.replace('0:0','1:0',1),account+'\n'+account.splitlines()[0]):
                with patch.object(dp,'command',return_value=bad):
                    with self.assertRaises(RuntimeError):dp.resume_state(src,run,app,cap,'src',receipt,ct.sha(receipt))
            (run/'train-81').mkdir()
            with patch.object(dp,'command',return_value=account):
                with self.assertRaises(RuntimeError):dp.resume_state(src,run,app,cap,'src',receipt,ct.sha(receipt))

    def test_technical_projection_and_seal_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'REPORT.json').write_text('{\n  "kind": "train",\n  "scientific": NOT_DESERIALIZED\n}\n')
            ct.seal(p);self.assertEqual(dp.technical_report(p),{'kind':'train'})
            (p/'extra').write_text('tamper')
            with self.assertRaises(RuntimeError):dp.technical_report(p)

    def test_remaining_full_grid_and_one_use(self):
        with tempfile.TemporaryDirectory() as d:
            src,run,app,cap,receipt,r,account=fixture(Path(d));original=ct.sha(run/'DISPATCH.jsonl')
            submitted=[];last=[400000];write=ct.json_write
            def command(*args):
                if args[0]=='sbatch':
                    submitted.append((args[-2],int(args[-1])));last[0]+=1;return str(last[0])
                if ',' in args[args.index('-j')+1]:return account
                return '%d|COMPLETED|0:0|1|'%last[0]
            def report(path,kind,index,*rest):
                p=Path(path);p.mkdir();value=dict(kind=kind,index=index,advance=True)
                write(p/'REPORT.json',value);ct.seal(p);return value
            def backup_write(path,value):
                write(path,value)
                if Path(path).name.startswith('BACKUP-REQUEST-'):
                    write(run/('BACKUP-ACK-'+value['stage']+'.json'),dict(verified=True,request_sha256=ct.sha(path),archive_sha256='synthetic'))
            with patch.object(ct,'authorize'),patch.object(dp,'command',side_effect=command),\
                 patch.object(ct,'check_report',side_effect=report),patch.object(ct,'json_write',side_effect=backup_write),patch.object(dp.time,'sleep'):
                dp.launch(src,run,app,cap,'src',receipt,ct.sha(receipt))
                self.assertEqual(len(submitted),210);self.assertEqual(submitted[0],('train',81))
                self.assertEqual(submitted[:111],[('train',i) for i in range(81,192)])
                self.assertEqual(ct.sha(run/'DISPATCH.jsonl'),original)
                final=ct.json_read(run/'DISPATCH-FINAL.json')
                self.assertEqual(len(final['jobs']),293)
                self.assertEqual((final['gpu_seconds'],final['cpu_wall_seconds']),(17358,3))
                with self.assertRaises(RuntimeError):dp.launch(src,run,app,cap,'src',receipt,ct.sha(receipt))
                self.assertEqual(len(submitted),210)


if __name__=='__main__':unittest.main()
