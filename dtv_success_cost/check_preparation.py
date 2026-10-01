"""Exclusive receipts, all unsuccessful local suites preserved and charged."""
import argparse,json,os,subprocess,time
from dtv_success_cost.common import *

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label.replace('-','').isalnum():raise RuntimeError('exclusive receipt label')
    log=DOC/(a.label+'.log');receipt=DOC/(a.label+'-RECEIPT.json')
    if log.exists() or receipt.exists():raise RuntimeError('test receipt already exists')
    spent=sum(load(p).get('wall_seconds',load(p).get('local_wall_seconds',0)) for p in DOC.rglob('*RECEIPT.json'))+1200 # conservatively charge uninstrumented auxiliary scripts/transport faults/small export
    if spent+600>14400:raise RuntimeError('cumulative preparation ceiling')
    source=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted((ROOT/'dtv_success_cost').glob('*.py'))]
    bindings=sha(DOC/'BINDINGS.json');start=time.monotonic();env=dict(os.environ,OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
    try:
        r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','/home/chris/miniforge3/envs/thesis/bin/python','-m','dtv_success_cost.run_tests'],cwd=ROOT,capture_output=True,timeout=600,env=env);data=r.stdout+r.stderr;code=r.returncode
    except subprocess.TimeoutExpired as e:data=(e.stdout or b'')+(e.stderr or b'');code=124
    with log.open('xb') as f:f.write(data)
    if bindings!=sha(DOC/'BINDINGS.json') or any(sha(ROOT/r['path'])!=r['sha256'] for r in source):code=125
    record=dict(wall_seconds=time.monotonic()-start,exit_code=code,log_sha256=sha(log),source=source,bindings_sha256=bindings,bounded_seconds=600,cpu_threads=4,ram_bytes=8*1024**3,existing_environment=True,artificial_only=True,research_payload_reads=0,physics=False,gpu=False,slurm=False)
    write(receipt,record);print(json.dumps(record));print(data.decode(errors='replace')[-8000:])
    if code:raise SystemExit(code)
if __name__=='__main__':main()
