"""Run only artificial tests; generate exclusive preparation evidence."""
import argparse,importlib.util,json,platform,subprocess,time,unittest
from pathlib import Path
import numpy as np
import torch
import lgp1_contract as c

def main(output,exported=False):
    torch.set_num_threads(1)
    repo=Path(__file__).resolve().parents[2];start=time.monotonic()
    if exported:c.verify(repo,'LGP1-SOURCE-MANIFEST.sha256')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n)
        for n in ('test_local_goal_proposals','test_lgp1_pipeline','lgp1_correction_tests','lgp1_lifecycle_tests','lgp1_policy_recovery_tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    c.require(result.wasSuccessful(),'Synthetic regression failure')
    p=repo/c.DOC/'review_dtype_reproducer.py'
    spec=importlib.util.spec_from_file_location('review',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    old=(c.read(repo/c.DOC/'PIPELINE-TEST-RESULTS.json')['old_preparation_reproducer'] if exported else m.run(repo))
    shell=subprocess.run(['bash','-n',str(repo/'cluster/prometheus/run_lgp1.sh')],capture_output=True,text=True)
    c.require(shell.returncode==0,shell.stderr)
    c.write(output,dict(tests=result.testsRun,failures=0,errors=0,elapsed_seconds=time.monotonic()-start,
        python=platform.python_version(),numpy=np.__version__,torch=torch.__version__,synthetic_only=True,
        artificial_optimizer_steps=6,research_optimizer_steps=0,research_payloads_opened=0,
        frozen_model_calls=0,simulator_calls=0,gpu_jobs=0,shell_syntax='pass',old_preparation_reproducer=old,
        exported_package=exported,old_reproducer_reexecuted=not exported,
        source_manifest_sha256=c.sha(repo/'LGP1-SOURCE-MANIFEST.sha256') if exported else None,
        command='python -B cluster/prometheus/lgp1_test_evidence.py --output <new-evidence-path>'+(' --exported' if exported else '')))
    if exported:c.verify(repo,'LGP1-SOURCE-MANIFEST.sha256')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--exported',action='store_true')
    a=p.parse_args();main(a.output,a.exported)
