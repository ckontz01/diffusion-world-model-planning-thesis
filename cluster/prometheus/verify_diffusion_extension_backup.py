"""Byte-only source-matched backup of new56 and separately preserved pilot8."""
import argparse,json
from pathlib import Path
from diffusion_bottleneck import require,require_sha,sha256,write_report
from diffusion_extension_control import REFS

def verify(new_root,pilot_root,report,expected):
    require_sha(report,expected);r=json.loads(report.read_text())
    require(r['all_combined_checks_passed'] is True and r['runs']==64 and r['new_runs']==56,'Unaccepted report')
    names={f'ref-{ref}-repeat-{rep}':ref in REFS[:4] for ref in REFS for rep in (0,1)}
    seen=set();new_bytes=pilot_bytes=0
    for remote,seals in r['seals'].items():
        name=Path(remote).name;require(name in names and name not in seen,'Duplicate/unexpected run');seen.add(name)
        root=pilot_root if names[name] else new_root;directory=root/name
        require(not directory.is_symlink(),'Backup directory symlink')
        require({p.name for p in directory.iterdir()}=={'REPORT.json','BANKS.npz','sha256.txt'},'Member inventory')
        require(set(seals)=={'REPORT.json','BANKS.npz'},'Source seal inventory')
        local={}
        for line in (directory/'sha256.txt').read_text().splitlines():
            digest,member=line.split(maxsplit=1);require(member in seals and member not in local,'Local seal identity')
            local[member]=digest
        require(local==seals,'Local seal differs from canonical accepted report')
        size=0
        for member,digest in seals.items():
            require(not (directory/member).is_symlink(),'Payload symlink')
            require_sha(directory/member,digest);size+=(directory/member).stat().st_size
        if names[name]:pilot_bytes+=size
        else:new_bytes+=size
    require(seen==set(names),'Missing backups')
    return {'all_passed':True,'new_runs_verified':56,'reused_pilot_runs_verified':8,
        'new_payload_bytes':new_bytes,'pilot_payload_bytes':pilot_bytes,'canonical_report_sha256':expected,
        'new_root':str(new_root),'pilot_root':str(pilot_root),'payload_outcomes_interpreted':False,
        'program_sha256':sha256(Path(__file__))}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('new-root','pilot-root','report','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected',required=True);a=p.parse_args()
    write_report(a.out,verify(a.new_root,a.pilot_root,a.report,a.expected),(a.new_root,a.pilot_root))
