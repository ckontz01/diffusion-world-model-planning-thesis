"""Accounted correction-only runner; never rewrites reviewed evidence."""
import argparse,json,os,subprocess,sys,time
from dtv_efficiency_r1.control import ROOT,DOC
from dtv_efficiency_r1.profile import sha

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--native-control-only',action='store_true');args=parser.parse_args()
    if not args.label.replace('-','').isalnum():raise ValueError('exclusive receipt label required')
    output=DOC/(args.label+'.log');receipt=DOC/(args.label+'-RECEIPT.json')
    if output.exists() or receipt.exists():raise RuntimeError('preserve receipts; new label required')
    previous=sum(json.loads(p.read_text())['wall_seconds'] for p in DOC.glob('*-RECEIPT.json'))
    # Reserve a conservative 600 seconds for other local scripts/publication.
    allowance=1800-600-previous
    if allowance<=0:raise RuntimeError('correction scripted-test envelope exhausted')
    env=dict(os.environ,OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
    start=time.monotonic();timeout=min(600,allowance);error=None
    try:
        command=[sys.executable,'-m','dtv_efficiency_r1.test_control'] if args.native_control_only else ['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','/home/chris/miniforge3/envs/thesis/bin/python','-m','dtv_efficiency_r1.run_tests']
        result=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=env)
        code=result.returncode;data=result.stdout
    except subprocess.TimeoutExpired as e:
        code=124;data=e.stdout or b'';error='bounded local suite timeout; no automatic retry'
    with output.open('xb') as f:f.write(data)
    record=dict(wall_seconds=time.monotonic()-start,exit_code=code,error=error,output_sha256=sha(output),timeout_seconds=timeout,cpu_threads=4,ram_ceiling_bytes=8*1024**3,existing_environment=True,native_control_only=args.native_control_only,full_regression_suite=not args.native_control_only,research_inference=False,physics=False,gpu=False,checkpoint_deserialization=False,slurm=False)
    with receipt.open('x') as f:json.dump(record,f,indent=2)
    print(data.decode(errors='replace'));print(json.dumps(record,indent=2))
    if code:raise SystemExit(code)
if __name__=='__main__':main()
