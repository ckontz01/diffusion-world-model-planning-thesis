import hashlib
from pathlib import Path
import shutil
import sys
source=Path(sys.argv[1]);root=Path('/lustreFS/data/superworld/ckontzias/thesis/snapshots')
names=['E19-R2-CONTACT-LOCALIZATION-PLAN-2026-09-05.md','gdp_cem_e19_r2_contact.py',
       'test_gdp_cem_e19_r2_contact.py','run_gdp_cem_e19_r2_contact.slurm','freeze_gdp_cem_e19_r2_contact.py']
manifest=''
for name in sorted(names):
    data=(source/name).read_bytes();assert b'\r' not in data
    manifest+=hashlib.sha256(data).hexdigest()+'  '+name+'\n'
h=hashlib.sha256(manifest.encode()).hexdigest();dest=root/('gdp-cem-e19-r2-contact-'+h[:16]);dest.mkdir()
for name in names:
    shutil.copyfile(source/name,dest/name);(dest/name).chmod(0o444)
(dest/'SOURCE-MANIFEST.sha256').write_text(manifest);(dest/'SOURCE-MANIFEST.sha256').chmod(0o444);dest.chmod(0o555)
print(dest);print(h)
