"""Byte-only off-cluster pilot verification against an authenticated aggregate."""
import argparse,json
from pathlib import Path
from diffusion_bottleneck import require,require_sha,sha256,write_report

def verify(root,aggregate,expected):
    require_sha(aggregate,expected);report=json.loads(aggregate.read_text())
    require(report['all_technical_checks_passed'] is True and report['runs']==8,'Aggregate not complete')
    names={f'ref-{ref}-repeat-{repeat}' for ref in (1269,582,525,722) for repeat in (0,1)}
    seen=set();total=0
    for remote,seals in report['seals'].items():
        name=Path(remote).name;require(name in names and name not in seen,'Bad run identity');seen.add(name)
        directory=root/name
        require({p.name for p in directory.iterdir()}=={'REPORT.json','BANKS.npz','sha256.txt'},'Local member inventory')
        require(set(seals)=={'REPORT.json','BANKS.npz'},'Canonical seal inventory')
        local={}
        for line in (directory/'sha256.txt').read_text().splitlines():
            digest,member=line.split(maxsplit=1)
            require(member in seals and member not in local,'Bad local seal');local[member]=digest
        require(local==seals,'Local seals not source matched')
        for member,digest in seals.items():
            require_sha(directory/member,digest);total+=(directory/member).stat().st_size
    require(seen==names,'Incomplete local pilot')
    return {'all_passed':True,'source_matched_runs':8,'payload_files_verified':16,'payload_bytes_verified':total,
            'aggregate_sha256':expected,'outcome_payloads_interpreted':False,'local_root':str(root)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--aggregate',type=Path,required=True)
    p.add_argument('--aggregate-sha256',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=verify(a.root,a.aggregate,a.aggregate_sha256);r['program_sha256']=sha256(Path(__file__))
    write_report(a.out,r,(a.root,));print(json.dumps(r))
