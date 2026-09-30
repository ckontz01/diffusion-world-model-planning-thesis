"""One artificial CPU suite, with resource scope reported explicitly."""
import json,os,resource,time,unittest

resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
if hasattr(os,'sched_getaffinity'):
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
started=time.monotonic();cpu=time.process_time()
from dtv_efficiency import test_profile
from dtv_efficiency_r1 import test_control

suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(module) for module in (test_profile,test_control)])
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('RESOURCE_RECEIPT '+json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),wall_seconds=time.monotonic()-started,process_cpu_seconds=time.process_time()-cpu,parent_rss_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,child_rss_high_water_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024,affinity_cpu_count=len(os.sched_getaffinity(0)),virtual_address_space_limit_bytes=8*1024**3,torch_threads=4,interop_threads=1,artificial=True,research_inference=False,gpu=False,slurm=False)))
raise SystemExit(0 if result.wasSuccessful() else 1)
