"""Exclusive staging transport + CPU-only tests; no scheduler/model payloads."""
import argparse,json,subprocess
from pathlib import Path
import lgprb2_contract as c

def main(archive):
    archive=Path(archive);receipt=c.read(archive.with_suffix('.package.json'))
    c.require(c.sha(archive)==receipt['sha256'],'Export archive')
    root=(c.ROOT/'staging'/('lgprb2-synthetic-'+receipt['source_sha256'][:16])).as_posix()
    prefix=['wsl','-d','Thesis-Ubuntu','-u','chris','--','ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus']
    command=f"test ! -e {root} && mkdir {root} && cat > {root}/source.tar"
    with archive.open('rb') as f:subprocess.run(prefix+[command],stdin=f,check=True)
    command=f"cd {root} && echo '{receipt['sha256']}  source.tar' | sha256sum -c - && mkdir source && tar -xf source.tar -C source"
    subprocess.run(prefix+[command],check=True)
    base=c.ROOT.as_posix();env=base+'/envs/hi-lewm-artifact-py311-cu121-swm006';image=base+'/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'
    command=f"apptainer exec --cleanenv --bind {base}:{base}:ro --bind {root}:{root}:rw {image} env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH={root}/source/cluster/prometheus OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 {env}/bin/python -B {root}/source/cluster/prometheus/lgprb2_test_receipt.py --output {root}/TEST-RESULTS.json"
    result=subprocess.run(prefix+[command],text=True)
    report=json.loads(subprocess.check_output(prefix+['cat',root+'/TEST-RESULTS.json'],text=True))
    c.write(archive.with_suffix('.tests.json'),report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('tests','failures','errors')},indent=2))
    print('Remote synthetic-only staging: '+str(root))
    if result.returncode:raise SystemExit(result.returncode)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);main(p.parse_args().archive)
