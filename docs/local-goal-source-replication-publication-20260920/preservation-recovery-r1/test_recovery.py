"""Artificial-only R1 tests. No SSH, research payload or production SSD writes."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock
import recover as r
import remote_helper as h


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='lgprb2-r1-synthetic-')
        self.root=Path(self.temp.name)
        self.data=bytes(range(256))*40+b'\x00\xff\r\n\x1aEND'
        self.path=self.root/'source.bin'; self.path.write_bytes(self.data)
    def tearDown(self): self.temp.cleanup()
    def manifest(self):
        return h.scan(self.path,123,129,hashlib.sha256(self.data).hexdigest(),hashlib.sha256(self.data[:123]).hexdigest())
    def pump(self,script,name='attempt',**kw):
        return r.pump([sys.executable,'-B','-c',script],self.root/(name+'.bin'),self.root/(name+'.stderr'),**kw)
    def test_01_non_aligned_prefix_ranges_and_final_short(self):
        m=self.manifest(); self.assertEqual(m['prefix']['length'],123)
        self.assertLess(m['ranges'][-1]['length'],129)
        self.assertEqual(sum(x['length'] for x in m['ranges']),len(self.data)-123)
        for item in m['ranges']:
            output=io.BytesIO(); h.stream_range(self.path,item,m['identity_before'],output.write)
            self.assertEqual(output.getvalue(),self.data[item['offset']:item['offset']+item['length']])
            self.assertEqual(hashlib.sha256(output.getvalue()).hexdigest(),item['sha256'])
    def test_02_successful_reconstruction_preserves_original(self):
        m=self.manifest(); original=self.root/'original'; original.write_bytes(self.data[:123])
        assembled=self.root/'assembled'; r.copy_exclusive(original,assembled)
        for item in m['ranges']:
            chunk=self.root/str(item['index']); chunk.write_bytes(self.data[item['offset']:item['offset']+item['length']])
            r.append_verified(assembled,chunk,item)
        self.assertEqual(assembled.read_bytes(),self.data)
        self.assertEqual(original.read_bytes(),self.data[:123])
    def test_03_scan_rejects_wrong_whole_or_prefix(self):
        for whole,prefix in [('0'*64,hashlib.sha256(self.data[:123]).hexdigest()),(hashlib.sha256(self.data).hexdigest(),'0'*64)]:
            with self.assertRaises(RuntimeError): h.scan(self.path,123,129,whole,prefix)
    def test_04_changed_source_rejected(self):
        m=self.manifest(); self.path.write_bytes(self.data+b'changed')
        with self.assertRaisesRegex(RuntimeError,'changed source'):
            h.stream_range(self.path,m['ranges'][0],m['identity_before'],lambda _:None)
    def test_05_changed_during_scan_rejected(self):
        real=h.identity(self.path); changed={**real,'mtime_ns':real['mtime_ns']+1}
        with mock.patch.object(h,'identity',side_effect=[real,changed]):
            with self.assertRaisesRegex(RuntimeError,'changed source'): self.manifest()
    def test_06_premature_source_eof(self):
        m=self.manifest(); item={**m['ranges'][-1],'length':999}
        with self.assertRaisesRegex(RuntimeError,'EOF'):
            h.stream_range(self.path,item,m['identity_before'],lambda _:None)
    def test_07_binary_stdout_no_conversion(self):
        result=self.pump("import os,sys;os.write(1,bytes(range(256))*3+b'\\r\\n\\x00\\xff');sys.stderr.write('diagnostic only')",maximum=772)
        self.assertEqual(result['received_bytes'],772)
        self.assertEqual((self.root/'attempt.bin').read_bytes(),bytes(range(256))*3+b'\r\n\x00\xff')
        self.assertEqual((self.root/'attempt.stderr').read_text(),'diagnostic only')
    def test_08_unexpected_stdout_no_retry(self):
        result=self.pump("import os;os.write(1,b'x'*200)",maximum=100)
        self.assertEqual(result['watchdog'],'unexpected_stdout')
        self.assertFalse(r.retryable(result,''))
    def test_09_disconnect_is_retryable_and_retained(self):
        result=self.pump("import os,sys;os.write(1,b'prefix');sys.stderr.write('connection lost');sys.exit(255)",maximum=100)
        self.assertTrue(r.retryable(result,'connection lost'))
        self.assertEqual((self.root/'attempt.bin').read_bytes(),b'prefix')
        self.pump("import os;os.write(1,b'success')",name='attempt2',maximum=100)
        self.assertEqual((self.root/'attempt.bin').read_bytes(),b'prefix')
    def test_10_authentication_and_source_errors_never_retry(self):
        result=dict(returncode=255,watchdog=None)
        for error in ['Permission denied (publickey)','Host key verification failed','REMOTE HOST IDENTIFICATION HAS CHANGED','changed source','wrong range offset','hash mismatch']:
            self.assertFalse(r.retryable(result,error))
    def test_11_idle_watchdog_only_owned_child(self):
        options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
        unrelated=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(20)'],**options)
        try:
            result=self.pump('import time;time.sleep(20)',idle=.3,absolute=3)
            self.assertEqual(result['watchdog'],'idle_timeout')
            self.assertTrue(result['owned_process_resolved']); self.assertIsNone(unrelated.poll())
        finally: unrelated.terminate(); unrelated.wait(timeout=5)
    def test_12_absolute_watchdog_even_with_output(self):
        result=self.pump("import os,time\nfor x in range(1000):\n os.write(1,b'x');time.sleep(.05)",maximum=1000,idle=2,absolute=.4)
        self.assertEqual(result['watchdog'],'absolute_timeout'); self.assertTrue(r.retryable(result,''))
    def test_13_exclusive_attempt_output(self):
        self.pump("print('one')",maximum=100)
        before=(self.root/'attempt.bin').read_bytes()
        with self.assertRaises(FileExistsError): self.pump("print('two')",maximum=100)
        self.assertEqual((self.root/'attempt.bin').read_bytes(),before)
    def test_14_wrong_length_hash_offset_preserves_assembly(self):
        m=self.manifest(); item=m['ranges'][0]; assembled=self.root/'assembled'; assembled.write_bytes(self.data[:123])
        chunk=self.root/'chunk'
        for b in [b'x',b'x'*item['length']]:
            chunk.write_bytes(b)
            with self.assertRaises(RuntimeError): r.append_verified(assembled,chunk,item)
            self.assertEqual(assembled.read_bytes(),self.data[:123])
        chunk.write_bytes(self.data[123:123+item['length']])
        with self.assertRaises(RuntimeError): r.append_verified(assembled,chunk,{**item,'offset':124})
    def test_15_no_third_attempt(self):
        s=r.Session.__new__(r.Session); s.guard=lambda:None
        s.invoke=mock.Mock(return_value=(None,{}))
        with mock.patch.object(r.time,'monotonic',side_effect=[0,31]):
            with self.assertRaisesRegex(RuntimeError,'two permitted'):
                s.operation('range',{},'fake',10,True)
        self.assertEqual(s.invoke.call_count,2)
        self.assertEqual([c.args[2] for c in s.invoke.call_args_list],['fake-attempt-1','fake-attempt-2'])
    def test_16_real_range_arithmetic(self):
        items=h.ranges(); self.assertEqual(len(items),25)
        self.assertEqual(items[-1]['length'],62771200)
        self.assertEqual(sum(x['length'] for x in items),1673383936)
        self.assertEqual(2*sum(x['length'] for x in items),r.LIMITS['remote_archive_payload_bound'])
        self.assertLess(r.TOTAL+2*sum(x['length'] for x in items)+200_000_000,8_000_000_000)
    def test_17_member_verifier_rejects_duplicates_missing_unexpected(self):
        archive=self.root/'a.tar'; content=b'artificial'; expected={'a':dict(bytes=len(content),sha256=hashlib.sha256(content).hexdigest())}
        with tarfile.open(archive,'w') as tar:
            info=tarfile.TarInfo('a'); info.size=len(content); tar.addfile(info,io.BytesIO(content))
        self.assertEqual(r.verify_archive(archive,expected)['files'],1)
        with self.assertRaises(RuntimeError): r.verify_archive(archive,{**expected,'missing':expected['a']})
        with tarfile.open(archive,'w') as tar:
            for _ in range(2):
                info=tarfile.TarInfo('a'); info.size=len(content); tar.addfile(info,io.BytesIO(content))
        with self.assertRaises(RuntimeError): r.verify_archive(archive,expected)
        with self.assertRaises(RuntimeError): r.verify_archive(archive,{'wrong':expected['a']})
    def test_18_all_phase_deadlines(self):
        s=r.Session.__new__(r.Session); s.start=100; s.final_start=None
        with mock.patch.object(r.time,'monotonic',return_value=5500):
            with self.assertRaises(RuntimeError): s.guard()
        s.final_start=5000
        with mock.patch.object(r.time,'monotonic',return_value=6800):
            with self.assertRaises(RuntimeError): s.guard()
        s.final_start=6000
        with mock.patch.object(r.time,'monotonic',return_value=7300):
            with self.assertRaises(RuntimeError): s.guard()
    def test_19_cpu_metadata_payload_caps_before_process(self):
        r.write(self.root/'SESSION.json',dict(session='0'*32))
        for field,value,is_range in [('transmissions',50,True),('payload_reserved',3346767872,True),('meta',8,False),('cpu_charged',600,False)]:
            s=r.Session(self.root,time.monotonic(),'0'*40); setattr(s,field,value)
            with mock.patch.object(r,'pump') as fake:
                with self.assertRaises(RuntimeError): s.invoke('range' if is_range else 'request',{},'fake',10,is_range)
                fake.assert_not_called()
    def test_20_local_io_and_remote_source_eof_not_retryable(self):
        self.assertFalse(r.retryable(dict(returncode=1,watchdog='local_stderr_io'),''))
        self.assertFalse(r.retryable(dict(returncode=1,watchdog=None),'',dict(ok=False,error_type='RuntimeError',error='premature local source EOF')))
    def test_21_full_length_bad_hash_even_on_disconnect_never_retries(self):
        r.write(self.root/'SESSION.json',dict(session='0'*32))
        session=r.Session(self.root,time.monotonic(),'0'*40)
        session.command=lambda op,action,quota,payload:[sys.executable,'-B','-c',"import os,sys;os.write(1,b'wrong');sys.exit(255)"]
        with self.assertRaisesRegex(RuntimeError,'complete-length hash mismatch'):
            session.operation('range',dict(sha256=hashlib.sha256(b'right').hexdigest()),'range',5,True)
        self.assertEqual(session.transmissions,1)
        self.assertEqual(session.payload_reserved,5)
        self.assertEqual(session.cpu_charged,9)
        self.assertEqual((self.root/'range-attempt-1.bin').read_bytes(),b'wrong')


if __name__=='__main__':
    began=time.monotonic(); cpu=time.process_time()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryTests)
    ids=[test.id() for test in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt=dict(passed=result.wasSuccessful(),tests_run=result.testsRun,distinct_tests=len(set(ids)),test_ids=ids,
                 seconds=time.monotonic()-began,process_cpu_seconds=time.process_time()-cpu,
                 scientific_execution=False,ssh_invocations=0,production_archive_bytes_read=0,
                 tool_sha256=r.digest(r.HERE/'recover.py'),helper_sha256=r.digest(r.HERE/'remote_helper.py'),tests_sha256=r.digest(__file__))
    if result.wasSuccessful(): r.write(r.HERE/'TEST-RESULTS.json',receipt)
    print(json.dumps(receipt,indent=2))
    sys.exit(0 if result.wasSuccessful() else 1)
