"""Run focused artificial-only regressions; write evidence outside sealed source."""
import argparse,json,os,platform,resource,time,unittest
from pathlib import Path
import numpy as np
import torch
import lgprb2_contract as c

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=Path(__file__).resolve().parents[2]
    c.require(source not in a.output.resolve().parents,'Never write into tested export')
    c.require(not os.environ.get('CUDA_VISIBLE_DEVICES'),'CPU-only synthetic tests')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    began=time.monotonic();cpu=time.process_time()
    suite=unittest.defaultTestLoader.loadTestsFromNames(['test_lgprb2','lgprb2_storage_tests','test_lgprb1.BudgetTests','lgp1_correction_tests','lgp1_lifecycle_tests'])
    ids=[]
    def collect(s):
        for v in s:
            if isinstance(v,unittest.TestSuite):collect(v)
            else:ids.append(v.id())
    collect(suite);c.require(len(ids)==len(set(ids)),'No duplicate synthetic test IDs')
    r=unittest.TextTestRunner(verbosity=2).run(suite)
    result=dict(passed=r.wasSuccessful(),tests_run=r.testsRun,tests=ids,
        failures=[(x.id(),s) for x,s in r.failures],errors=[(x.id(),s) for x,s in r.errors],
        python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,
        wall_seconds=time.monotonic()-began,process_cpu_seconds=time.process_time()-cpu,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        cuda_initialized=torch.cuda.is_initialized(),research_inference_calls=0,optimizer_steps=0,simulator_calls=0,
        source_sha256=c.sha(source/c.MANIFEST) if (source/c.MANIFEST).exists() else None,
        description='Actual sampler/CEM/policy/fresh driver with artificial neural weights and vector pool; authenticated criterion/decoder source tests; no research weights or data.')
    from lgprb2_storage_tests import STORAGE_EVIDENCE
    result['storage_correction']=STORAGE_EVIDENCE
    c.write(a.output,result)
    if not r.wasSuccessful():raise SystemExit(1)
    c.require(not torch.cuda.is_initialized(),'No GPU test execution')

if __name__=='__main__':main()
