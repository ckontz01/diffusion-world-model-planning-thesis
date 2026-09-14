"""Post-verification archive and actual accounting; no model/physics execution."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import sys

ROOT = Path('/lustreFS/data/superworld/ckontzias/thesis')
SRC = ROOT/'snapshots/single-anchor-ranking-20260914-ba2eb02b2e860648'
RUN = ROOT/'experiments/single-anchor-ranking-20260914/run-ba2eb02b'
STAGE = ROOT/'staging/single-anchor-ranking-20260914'
sys.path.insert(0, str(SRC/'cluster/prometheus'))
from single_anchor_ranking_host import REFS, require, sha256, verify_source, require_sha


def main():
    verify_source(SRC, 'ba2eb02b2e860648a0642c39cb97f3409ab9cb7dcc975a4110b5e2db05297704')
    require_sha(RUN/'analysis/ANALYSIS.json', '1ee1ffb3123a44db63a4be3cb6c568554f8c0e3496f6fe7b666c1f5815f72959')
    complete = json.loads((RUN/'DISPATCH-COMPLETE.json').read_text())
    require(complete['all_64_completed'] and len(set(complete['jobs'])) == 64, 'Completion')
    jobs = complete['jobs'] + ['301088', '301090', '301157']
    columns = ['JobID','State','ExitCode','ElapsedRaw','AllocCPUS','ReqMem','MaxRSS',
               'TotalCPU','ReqTRES','AllocTRES','Start','End','NodeList']
    raw = subprocess.check_output(['sacct','-n','-P','-j',','.join(jobs),
                                   '--format='+','.join(columns)]).decode()
    accounting = [dict(zip(columns, line.split('|'))) for line in raw.splitlines() if line.strip()]
    allocations = {r['JobID']:r for r in accounting if '.' not in r['JobID']}
    require(set(allocations) == set(jobs), 'Exact accounting identities')
    for job in complete['jobs']+['301090','301157']:
        require(allocations[job]['State']=='COMPLETED' and allocations[job]['ExitCode']=='0:0', 'Job failed')
    charged = sum(int(allocations[j]['ElapsedRaw']) for j in complete['jobs'])
    require(charged == complete['allocation_seconds'] and charged <= 14400, 'Allocation charge')
    for ref in REFS:
        for repeat in (0,1):
            d=RUN/('ref-{}-repeat-{}'.format(ref,repeat))
            for line in (d/'sha256.txt').read_text().splitlines():
                digest,name=line.split(maxsplit=1)
                require(name in ('BANKS.npz','REPORT.json'), 'Seal path')
                require_sha(d/name,digest)
    files = {}
    for p in sorted(RUN.rglob('*')):
        require(not p.is_symlink(), 'Unexpected symlink')
        if p.is_file():files['run/'+str(p.relative_to(RUN))]=p
    require(sum(p.stat().st_size for p in files.values()) <= 2000000000, 'Storage watermark')
    files.update({'source/source-2f7c941.tar':STAGE/'source-2f7c941.tar',
                  'approval/EXECUTION-APPROVAL-ba2eb02b.json':STAGE/'EXECUTION-APPROVAL-ba2eb02b.json',
                  'launch/final_verify_single_anchor_ranking.sh':STAGE/'final_verify_single_anchor_ranking.sh'})
    manifest = {name:dict(bytes=p.stat().st_size,sha256=sha256(p)) for name,p in sorted(files.items())}
    report = dict(all_64_successful=True, final_verifier='301157', gpu_allocation_seconds=charged,
                  run_bytes=sum(v['bytes'] for k,v in manifest.items() if k.startswith('run/')),
                  files=manifest, slurm_rows=accounting,
                  archive_scope='Complete new run including analysis/logs/seals plus exact source archive, approval and verifier launcher. Historical datasets/checkpoints are hash-pinned inputs, not duplicated.',
                  protected_inputs_read=False, model_or_physics_executed=False)
    encoded = (json.dumps(report,sort_keys=True,indent=2)+'\n').encode()
    archive = STAGE/'final-evidence-301157.tar'
    with archive.open('xb') as stream:
        with tarfile.open(fileobj=stream, mode='w') as tar:
            for name,p in sorted(files.items()):tar.add(str(p),arcname=name,recursive=False)
            info=tarfile.TarInfo('BACKUP-MANIFEST.json');info.size=len(encoded);info.mode=0o444
            tar.addfile(info,io.BytesIO(encoded))
    for name,p in files.items():require_sha(p,manifest[name]['sha256'])
    with (STAGE/'FINAL-BACKUP-MANIFEST.json').open('xb') as stream:stream.write(encoded)
    summary=dict(archive=str(archive),bytes=archive.stat().st_size,sha256=sha256(archive),
                 manifest_sha256=hashlib.sha256(encoded).hexdigest(),files=len(files),
                 gpu_allocation_seconds=charged,run_bytes=report['run_bytes'])
    with (STAGE/'FINAL-BACKUP-RECEIPT.json').open('x') as stream:json.dump(summary,stream,indent=2,sort_keys=True)
    print(json.dumps(summary,sort_keys=True))


if __name__ == '__main__':main()
