"""Technical all-source retained-byte and free-storage reconciliation."""
import json
from .common import DOC,write_new
from wm_diag0_source_r3.common import RUN,OLD
from wm_diag0_native_v3.transport import ssh

def main():
    r=ssh('RUN='+repr(RUN)+'\nOLD='+repr(OLD)+'\n'+'''
import json,pathlib,shutil
seen=set();total=0;counts=0
for root in (pathlib.Path(OLD)/'tasks',pathlib.Path(RUN)/'tasks'):
 for p in root.rglob('*'):
  if p.is_symlink():raise ValueError('unexpected task preservation symlink')
  if p.is_file():
   x=p.stat();key=(x.st_dev,x.st_ino)
   if key not in seen:seen.add(key);total+=x.st_size;counts+=1
limit=1440000000+8304747+12300000
if total>limit:raise ValueError('source+failed+CPU-log reservation exceeded; do not borrow future slack twice')
free=shutil.disk_usage(RUN).free
if free<40000000000:raise ValueError('cluster preservation space unavailable')
print(json.dumps({'status':'ALL_SOURCE_RETAINED_BYTES_WITHIN_RESERVATION','unique_task_bytes':total,'unique_task_files':counts,'source_failed_and_CPU_log_reservation':limit,'free_cluster_bytes':free,'all_failed_temporary_files_included':True,'live_full_future_bytes':12844699989,'live_cap':13000000000,'archive_cap':14000000000,'inclusive_cap':44000000000}))
''')
    write_new(DOC/'SOURCE-STORAGE-GATE-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
