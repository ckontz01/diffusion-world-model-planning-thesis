"""Accounted artificial test runner and deterministic curation correction."""
import argparse, json, subprocess, time
from pathlib import Path
from dtv_efficiency.recover import ROOT
from dtv_efficiency.profile import DOC, sha

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='INTEGRATION-FINAL');args=parser.parse_args()
    if not args.label.replace('-','').isalnum():raise ValueError('exclusive receipt label required')
    output=DOC/(args.label+'.log');receipt_path=DOC/(args.label+'-RECEIPT.json')
    if output.exists() or receipt_path.exists():raise RuntimeError('preserve existing test receipt; choose a new label')
    if not (DOC/'HISTORICAL-TIMINGS-VERIFIED.json').exists():
        rows=json.loads((DOC/'HISTORICAL-TIMINGS.json').read_text())
        for row in rows:
            if row['study']=='D1':row['task']=Path(row['artifact']).parts[3]
        with (DOC/'HISTORICAL-TIMINGS-VERIFIED.json').open('x') as f:json.dump(rows,f,indent=2)
    start=time.monotonic()
    r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','/home/chris/miniforge3/envs/thesis/bin/python','-m','dtv_efficiency.test_profile'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
    with output.open('xb') as f:f.write(r.stdout)
    receipt=dict(wall_seconds=time.monotonic()-start,exit_code=r.returncode,output_sha256=sha(output),cpu_threads=4,research_inference=False,physics=False,gpu=False,checkpoint_deserialization=False,test_environment='existing WSL thesis; artificial torch 2.13.0+cpu; not proposed CUDA runtime')
    with receipt_path.open('x') as f:json.dump(receipt,f,indent=2)
    print(r.stdout.decode());print(json.dumps(receipt,indent=2))
    if r.returncode:raise SystemExit(r.returncode)
if __name__=='__main__':main()
