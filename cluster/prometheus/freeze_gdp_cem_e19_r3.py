"""Freeze new R3 engineering sources; never touch historical snapshots."""
import hashlib
from pathlib import Path
import shutil
import sys

source=Path(sys.argv[1]); root=Path('/lustreFS/data/superworld/ckontzias/thesis/snapshots')
names=['E19-R3-INITIALIZATION-PLAN-2026-09-05.md','pusht_fresh_initialization.py',
       'test_pusht_fresh_initialization.py','gdp_cem_e19_r3_validation.py',
       'run_gdp_cem_e19_r3.slurm','freeze_gdp_cem_e19_r3.py']
manifest=''
for name in sorted(names):
    data=(source/name).read_bytes(); assert b'\r' not in data
    manifest+=hashlib.sha256(data).hexdigest()+'  '+name+'\n'
h=hashlib.sha256(manifest.encode()).hexdigest()
dest=root/('gdp-cem-e19-r3-'+h[:16]); dest.mkdir()
for name in names:
    shutil.copyfile(source/name,dest/name); (dest/name).chmod(0o444)
(dest/'SOURCE-MANIFEST.sha256').write_text(manifest)
(dest/'SOURCE-MANIFEST.sha256').chmod(0o444); dest.chmod(0o555)
print(dest); print(h)
