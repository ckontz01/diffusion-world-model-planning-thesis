"""Allocation-only execution with new receipts, stopping at any failed stage."""
import json
import subprocess
import sys
import time
from pathlib import Path

def run(src,out,study):
    scripts=src/'cluster/prometheus'
    stages=[
        ('tests',[sys.executable,'-m','unittest','discover','-s',str(scripts),'-p','test_diffusion_*.py','-v']),
        ('canonical',[sys.executable,str(scripts/'audit_diffusion_bottleneck_preservation.py'),'canonical','--out',str(out/'canonical.json')]),
        ('paired',[sys.executable,str(scripts/'diffusion_bottleneck.py'),'--archive',str(study/'analysis-0'),'--bootstrap','10000','--out',str(out/'paired.json')]),
        ('independent',[sys.executable,str(scripts/'verify_diffusion_bottleneck_outcomes.py'),'--archive',str(study/'analysis-0'),'--report',str(out/'paired.json'),'--out',str(out/'paired-independent.json')]),
        ('traces',[sys.executable,str(scripts/'diffusion_bottleneck_traces.py'),'--study',str(study),'--out',str(out/'traces.json')]),
    ]
    receipt={'python':sys.version,'stages':[],'model_runs':0,'protected_payload_reads':0}
    for name,command in stages:
        started=time.monotonic()
        with (out/(name+'.txt')).open('x') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
        receipt['stages'].append({'stage':name,'returncode':result.returncode,'wall_seconds':time.monotonic()-started})
        if result.returncode:
            with (out/'EXECUTION-FAILED.json').open('x') as stream:json.dump(receipt,stream,indent=2)
            raise SystemExit(result.returncode)
    receipt['all_passed']=True
    with (out/'EXECUTION.json').open('x') as stream:json.dump(receipt,stream,indent=2)

if __name__=='__main__': run(*(Path(p) for p in sys.argv[1:]))
