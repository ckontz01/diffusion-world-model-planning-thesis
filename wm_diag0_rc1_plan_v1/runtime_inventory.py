"""Read-only full-environment and retained PC size check; no imports from it."""
import json, stat
from pathlib import Path
from .inventory import DOC
from wm_diag0_native_v3.common import write_new
from wm_diag0_native_v3.transport import ssh
from wm_diag0_preflight_v1.preserve import volume

PROGRAM = r'''
import json,pathlib,stat
r=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006')
total=0;files=0;links=0;dirs=0
for p in r.rglob('*'):
 s=p.lstat()
 if stat.S_ISLNK(s.st_mode):links+=1;total+=s.st_size
 elif stat.S_ISREG(s.st_mode):files+=1;total+=s.st_size
 elif stat.S_ISDIR(s.st_mode):dirs+=1;total+=s.st_size
 else:raise ValueError('special environment file')
 if files>100000 or total>2100000000:raise ValueError('whole environment exceeds proposed2.1GB bound')
print(json.dumps({'path':str(r),'logical_bytes_including_directory_and_link_metadata':total,'files':files,'symlinks':links,'directories':dirs,
 'whole_environment_reservation_bytes':2100000000,'new_environment_hash_authentication':False,'executed_or_modified':False}))
'''

def main():
    if (DOC/'RUNTIME-AND-SSD-001.json').exists():
        raise FileExistsError('exclusive receipt')
    remote = ssh(PROGRAM)
    local = []
    for rel in ('wm-diag0-a2-c0-runtime-v1', 'wm-diag0-a2-c0-prep-v1'):
        p = Path('C:/Users/Chris/thesis-vm')/rel
        total = 0; count = 0
        for f in p.rglob('*'):
            s = f.lstat()
            if stat.S_ISLNK(s.st_mode):
                raise ValueError('unexpected retained PC alias')
            if stat.S_ISREG(s.st_mode):
                total += s.st_size; count += 1
        local.append({'path':str(p),'files':count,'logical_bytes':total})
    if sum(x['logical_bytes'] for x in local)>1512400813:
        raise ValueError('retained PC runtime grew; preserve and reconcile')
    result = {'status':'WHOLE_RUNTIME_SIZE_AND_DESIGNATED_SSD_CHECKED',
              'remote_runtime':remote,'retained_PC':local,'SSD':volume(),
              'retained_preparation_full_future_reservation_bytes':2874852312,
              'no_new_SSD_package_created':True,'VM_or_environment_actions':0}
    write_new(DOC/'RUNTIME-AND-SSD-001.json', result)
    print(json.dumps(result,indent=2))

if __name__ == '__main__': main()
