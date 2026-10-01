"""One accounted artificial CPU suite, no proposed-runtime execution."""
import json,os,resource,time,unittest
resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
started=time.monotonic();cpu=time.process_time()
import torch
# The preserved artificial scorer fixture configures Torch once on import.
# Do not configure interop a second time or edit that historical fixture.
from dtv_success_cost import test_pipeline,test_science
from dtv_efficiency import test_profile
from dtv_efficiency_r1 import test_control
# Load lazy runtime libraries before test-only sys.modules isolation so restoring
# a fixture cannot unload registered Torch operators and cause duplicate imports.
import torch._dynamo
from torchvision import tv_tensors
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_pipeline,test_science,test_profile,test_control))
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('RESOURCE_RECEIPT '+json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),wall_seconds=time.monotonic()-started,process_cpu_seconds=time.process_time()-cpu,rss_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,cpu_threads=torch.get_num_threads(),affinity_cpu_count=len(os.sched_getaffinity(0)),virtual_address_limit=8*1024**3,artificial=True,research_payloads=False,physics=False,gpu=False,slurm=False)))
raise SystemExit(0 if result.wasSuccessful() else 1)
