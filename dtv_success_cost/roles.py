"""Byte-only source-assignment inventory guard; no reference payload decoder."""
import json
import subprocess
import time
from dtv_success_cost.common import *

def inventory(root=REMOTE):
    root=Path(root);paths=set((root/'manifests').rglob('*.tsv'))
    paths.update((root/'data/stablewm/derived/candidate-pools/pusht-v1').glob('*/manifest.json'))
    for study in ('gdp-cem-e14','gdp-cem-e16','gdp-cem-e18'):
        paths.update((root/'experiments'/study).glob('*/p2-manifests/**/queries.tsv'))
    return [dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(paths) if p.is_file()]

def verify(c,root=REMOTE):
    if inventory(root)!=c['role_inventory']:raise RuntimeError('intervening source-role inventory assignment; reconcile before access, never replace IDs')

def main():
    out=DOC/'ROLE-INVENTORY.json'
    if out.exists():raise RuntimeError('exclusive role inventory receipt already exists')
    script='import hashlib,json,pathlib,time\n'+__import__('inspect').getsource(sha)+'\n'+__import__('inspect').getsource(inventory).replace('root=REMOTE','root='+repr(str(REMOTE)))+'\nprint(json.dumps(inventory()))\n'
    script=script.replace('Path(', 'pathlib.Path(')
    start=time.monotonic()
    r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus','python3.9 -'],input=script.encode(),capture_output=True,timeout=90,check=True)
    rows=json.loads(r.stdout)
    write(out,dict(files=rows,local_wall_seconds=time.monotonic()-start,metadata_only=True,payload_reads=0,role_allocation=False))
    print(json.dumps(dict(files=len(rows),bytes=sum(v['bytes'] for v in rows),paths=[v['path'] for v in rows])))

if __name__=='__main__':main()
