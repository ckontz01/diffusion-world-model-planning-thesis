"""Complete artificial job storage through the production writer and guard."""
import copy,json,math,shutil,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import lgprb2_contract as c
import lgprb2_evaluate as ev
from lgprb2_payload import write_payload,seal_bytes
from lgprb2_worker import make_guard,write_completed
from lgp1_endpoint import verify_file
import test_lgprb2 as fixtures

SOURCE=fixtures.SOURCE

STORAGE_EVIDENCE={}

def encoded(value,compact):
    options=dict(sort_keys=True,allow_nan=False)
    options.update(separators=(',',':')) if compact else options.update(indent=2)
    return (json.dumps(value,**options)+'\n').encode('utf8')

def numeric_identity(value):
    """Compare decoded float bits (including signed zero), not loose equality."""
    if isinstance(value,float):return ('float',value.hex())
    if isinstance(value,dict):return {k:numeric_identity(v) for k,v in value.items()}
    if isinstance(value,list):return [numeric_identity(v) for v in value]
    return value

def compact_bound(value,key=None):
    """Fixed schema: finite binary64 <=24 bytes; bounded counters <=12 digits.

    Strings conservatively use at least 64 characters (256 for reference paths),
    including actual JSON escapes when longer. Keys and container punctuation
    retain exact schema lengths. This intentionally overbounds float32 outputs,
    0..299 indices and source/seed/stage integers. No value is rounded or stored
    with these replacements; it is a size calculation only.
    """
    if value is None:return 4
    if type(value) is bool:return 5
    if type(value) is int:
        assert len(str(value))<=12
        return 12
    if type(value) is float:
        assert math.isfinite(value) and len(json.dumps(value))<=24
        return 24
    if type(value) is str:return max(len(json.dumps(value).encode()),258 if key=='reference_file' else 66)
    if isinstance(value,list):return 2+max(0,len(value)-1)+sum(compact_bound(v) for v in value)
    if isinstance(value,dict):
        return 2+max(0,len(value)-1)+sum(len(json.dumps(k).encode())+1+compact_bound(v,k) for k,v in value.items())
    raise TypeError(type(value))

def long_floats(value):
    # Normal long decimal and 24-character finite extreme, both losslessly
    # encoded. Timers/round statistics are artificial; endpoint arrays untouched.
    if type(value) is float:return -1.2345678901234567e-123 if value<0 else 0.12345678901234567
    if isinstance(value,dict):return {k:long_floats(v) for k,v in value.items()}
    if isinstance(value,list):return [long_floats(v) for v in value]
    return value

class StorageTests(unittest.TestCase):
    def test_writer_exclusive_nonfinite_and_lossless(self):
        value={'z':[0.12345678901234567,-1.2345678901234567e-123,-0.0,1.7976931348623157e308],
               'a':'UTF-8 example: \u03c0\nline'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'EPISODE.json';write_payload(path,value)
            self.assertEqual(path.read_bytes(),encoded(value,True));self.assertNotIn(b'\r',path.read_bytes())
            self.assertEqual(numeric_identity(c.read(path)),numeric_identity(json.loads(encoded(value,False))))
            with self.assertRaises(FileExistsError):write_payload(path,{})
            for index,number in enumerate((float('nan'),float('inf'),-float('inf'))):
                with self.assertRaises(ValueError):write_payload(Path(tmp)/f'bad-{index}.json',{'v':number})

    def test_production_guard_rejects_actual_over_cap_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with (root/'oversized.bin').open('xb') as f:f.write(b'x'*c.CAPS['main_job_bytes'])
            guard=make_guard(root,'evaluation',0,time.monotonic(),240)
            with self.assertRaisesRegex(RuntimeError,'Worker output cap'):guard()

    def test_complete_full_budget_directory_actual_long_and_bound(self):
        bundle,_=fixtures.PackagingTests().bundle();spec=c.grid(list(range(512)))[0]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'actual';root.mkdir()
            guard=make_guard(root,'evaluation',0,time.monotonic(),240)
            with patch.object(ev,'load_bundle',return_value=bundle),patch.object(ev,'verify_file',side_effect=lambda p,r,ref:verify_file(p,r,ref,authenticate_reference=False)):
                report=ev.evaluate(SOURCE,root,spec,guard)
            self.assertEqual([r['steps'] for r in report['rows']], [2*e['horizon'] for e in spec['episodes']])
            self.assertEqual(sum(len(r['stages']) for r in report['rows']),120)
            self.assertEqual(sum(len(s['rounds']) for r in report['rows'] for s in r['stages']),2100)
            technical=dict(task=spec,complete=True,gpu_used=True,source_sha256='a'*64,approval_sha256='b'*64,
                wall_seconds=123.12345678901234,process_cpu_seconds=234.12345678901234,
                peak_rss_bytes=24*1024**3,peak_gpu_bytes=48*1024**3,
                **{k:report[k] for k in ('episodes','models_unchanged','setup_seconds','technical_checks')})
            captured=[]
            def technical_after_report():
                self.assertTrue((root/'REPORT.json').exists());captured.append(True);return technical
            write_completed(root,report,technical_after_report,guard)
            self.assertEqual(captured,[True]);guard();c.old.verify(root)
            inventory={p.relative_to(root).as_posix():p.stat().st_size for p in root.rglob('*') if p.is_file()}
            self.assertEqual(len(inventory),19) # 8 episode + 8 endpoint + report/technical/seal
            actual_bytes=c.old.size(root);self.assertLess(actual_bytes,5_000_000)
            endpoints={}
            for r in report['rows']:
                name=c.cell_name(r);path=root/name/'EPISODE.json'
                self.assertEqual(path.read_bytes(),encoded(r,True))
                self.assertEqual(numeric_identity(c.read(path)),numeric_identity(json.loads(encoded(r,False))))
                p=root/name/f"endpoint-h{r['horizon']}.npz"
                endpoints[name]=(p,c.sha(p))
            self.assertEqual(numeric_identity(c.read(root/'REPORT.json')),numeric_identity(json.loads(encoded(report,False))))
            old_pretty_bytes=sum(len(encoded(r,False)) for r in report['rows'])+len(encoded(report,False))
            self.assertGreater(old_pretty_bytes,5_000_000)
            # Same complete evidence, with deliberately long finite JSON metrics.
            long=long_floats(report)
            for r in long['rows']:
                for s in r['stages']:
                    for q in s['rounds']:q['minimum']=[-1.2345678901234567e-123]
            longroot=Path(tmp)/'long';longroot.mkdir();longguard=make_guard(longroot,'evaluation',0,time.monotonic(),240)
            for r in long['rows']:
                name=c.cell_name(r);cell=longroot/name;cell.mkdir()
                original,digest=endpoints[name];copied=cell/original.name;shutil.copyfile(original,copied)
                self.assertEqual(c.sha(copied),digest)
                with np.load(original,allow_pickle=False) as a,np.load(copied,allow_pickle=False) as b:
                    self.assertEqual(a.files,b.files)
                    for key in a.files:
                        self.assertEqual(a[key].dtype,b[key].dtype);self.assertEqual(a[key].shape,b[key].shape)
                        self.assertEqual(a[key].tobytes(),b[key].tobytes())
                verify_file(cell,r,bundle[2],authenticate_reference=False)
                write_payload(cell/'EPISODE.json',r)
                self.assertEqual(numeric_identity(c.read(cell/'EPISODE.json')),numeric_identity(json.loads(encoded(r,False))))
            longtech=long_floats(technical)
            write_completed(longroot,long,lambda:longtech,longguard);longguard();c.old.verify(longroot)
            self.assertEqual(numeric_identity(c.read(longroot/'REPORT.json')),numeric_identity(json.loads(encoded(long,False))))
            long_bytes=c.old.size(longroot)
            # Bound independent of endpoint compression or short numeric text.
            payload_bound=sum(compact_bound(r)+1 for r in long['rows'])+compact_bound(long)+1
            technical_bound=compact_bound(longtech)+1+len(encoded(longtech,False))-len(encoded(longtech,True))
            seal_bound=4096
            self.assertLessEqual(inventory['sha256.txt'],seal_bound)
            self.assertLessEqual(max(len(v['file'].encode()) for v in c.read(SOURCE/c.DOC/'INPUTS.json')['references'].values()),256)
            bound=payload_bound+technical_bound+8*c.CAPS['endpoint_bytes']+seal_bound
            self.assertLessEqual(long_bytes,bound);self.assertLess(bound,5_000_000)
            STORAGE_EVIDENCE.update(actual_complete_bytes=actual_bytes,long_finite_complete_bytes=long_bytes,
                conservative_complete_bound_bytes=bound,conservative_margin_bytes=5_000_000-bound,
                bound_components=dict(duplicated_compact_payloads=payload_bound,indented_technical=technical_bound,
                                      eight_endpoint_caps=400000,seal=seal_bound),
                original_indented_json_only_bytes=old_pretty_bytes,actual_inventory=inventory,
                stages=120,rounds=2100,actions=1800,episodes=8,artifact_files=19,
                decoded_float_bits_equal=True,endpoint_array_and_byte_identity=True,production_guard_used=True,
                over_cap_rejection_test='test_production_guard_rejects_actual_over_cap_directory')
