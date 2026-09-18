"""Deterministic complete source closure; always emits disabled approval."""
import argparse,hashlib,json
from pathlib import Path
import lgp1_contract as c

REPO=Path(__file__).resolve().parents[2]
def files():
    code=REPO/'cluster/prometheus'
    names=set()
    for pattern in ('lgp1_*.py','local_goal_*.py','test_lgp1_pipeline.py','test_local_goal_proposals.py',
                    'prepare_lgp1_inputs.py','run_lgp1.sh'):
        names.update(p.relative_to(REPO).as_posix() for p in code.glob(pattern))
    names.update('cluster/prometheus/'+n for n in ('e18_fresh_driver.py','pusht_fresh_initialization.py',
        'independent_pusht_runtime.py','INDEPENDENT-PINNED-INPUTS.json'))
    names.update(p.relative_to(REPO).as_posix() for p in (REPO/c.DOC).iterdir()
                 if p.is_file() and p.name not in ('LAUNCH-PACKAGE.json','LGP1-SOURCE-MANIFEST.sha256'))
    return sorted(names)

def build(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);lines=[]
    for name in files():
        data=(REPO/name).read_bytes().replace(b'\r\n',b'\n')
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
        lines.append(hashlib.sha256(data).hexdigest()+'  '+name+'\n')
    with (output/'LGP1-SOURCE-MANIFEST.sha256').open('x',newline='\n') as f:f.writelines(lines)
    c.require(c.size(output)<20_000_000,'Source package cap')
    approval=dict(study='LGP1',execution_authorized=False,source_sha256=c.sha(output/'LGP1-SOURCE-MANIFEST.sha256'),
        input_sha256=c.sha(output/c.DOC/'INPUTS.json'),caps=c.CAPS,fits=6,updates=72000,main_episodes=384,
        technical_episodes=8,gpu_allocations=203,cpu_allocations=1,backup_volume_id='0a2f1ba9-0000-0000-0000-100000000000',
        backup_destination='D:/THESIS-BACKUPS/local-goal-proposals-20260918')
    c.write(output/'APPROVAL-TEMPLATE.json',approval)
    c.verify(output,'LGP1-SOURCE-MANIFEST.sha256')
    return dict(source_sha256=approval['source_sha256'],input_sha256=approval['input_sha256'],files=len(lines),
                bytes=c.size(output),execution_authorized=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--record',type=Path)
    a=p.parse_args();result=build(a.output)
    if a.record:c.write(a.record,result)
    print(json.dumps(result))
