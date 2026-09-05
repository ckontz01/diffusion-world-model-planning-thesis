"""Copy-only immutable integration wrapper snapshot; does not submit jobs."""
import hashlib
from pathlib import Path
import shutil
import sys

source=Path(sys.argv[1]);root=Path('/lustreFS/data/superworld/ckontzias/thesis/snapshots')
names=['E18-FRESH-DRIVER-INTEGRATION-PLAN-2026-09-05.md','e18_fresh_driver.py',
       'check_e18_fresh_integration.py','test_e18_fresh_driver.py',
       'freeze_e18_fresh_integration.py','run_e18_fresh_integration.slurm',
       'pusht_fresh_initialization.py','gdp_cem_e19_r3_validation.py','gdp_cem_e19_r3_arms.py']
core=root/'gdp-cem-e19-r3-30215e7fcfd0e614'
assert (source/'pusht_fresh_initialization.py').read_bytes()==(core/'pusht_fresh_initialization.py').read_bytes()
manifest=''
for name in sorted(names):
    data=(source/name).read_bytes();assert b'\r' not in data
    if name.endswith('.py'):compile(data,name,'exec')
    manifest+=hashlib.sha256(data).hexdigest()+'  '+name+'\n'
h=hashlib.sha256(manifest.encode()).hexdigest()
dest=root/('e18-fresh-integration-'+h[:16]);dest.mkdir()
for name in names:
    shutil.copyfile(source/name,dest/name);(dest/name).chmod(0o444)
(dest/'SOURCE-MANIFEST.sha256').write_text(manifest)
(dest/'SOURCE-MANIFEST.sha256').chmod(0o444);dest.chmod(0o555)
print(dest);print(h)
