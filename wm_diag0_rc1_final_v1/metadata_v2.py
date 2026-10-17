"""Small control/identity/stat read; avoids the timed-out full-runtime traversal.

This cannot establish a fresh full-storage bound. The unchanged grid stage must
still pass its all-lineage full-future storage proof before sbatch. Complete
runtime-member/alias inventory remains required before final archive binding.
"""
import json,sys
from wm_diag0_rc1_grid_v1.common import ROOT,TECHNICAL_RUN,write_new
from wm_diag0_native_v3.transport import ssh

READ=r'''
import hashlib,json,os,pathlib
r=pathlib.Path(RUN);cp=r/'source/TECHNICAL-CONTRACT.json'
def ident(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
if ident(cp)['sha256']!='101cd417d9a823a559a29d3813887ad17f721b450ce4f21d267b597e4ef788fd':raise ValueError('exact executed technical source/contract')
c=json.loads(cp.read_text());base=r.parent;manifest=pathlib.Path(c['recovery']['old_run'])/'controls/RUNTIME-MANIFEST.json'
if ident(manifest)!=c['runtime_manifest']:raise ValueError('runtime authority changed')
rm=json.loads(manifest.read_text());children=[]
for p in sorted(base.iterdir()):
 if p.is_symlink() or not p.is_dir():raise ValueError('unexpected canonical study root')
 children.append(p.name)
sif=pathlib.Path(c['sif']).stat().st_size;models=sum(pathlib.Path(x['path']).stat().st_size for x in c['lewm'].values())
if sif!=3139002368 or models!=144694193:raise ValueError('retained model/runtime file sizes')
v=os.statvfs(str(base))
print(json.dumps({'scope':'shallow control/resource/input-binding metadata; not full storage or model-content reauthentication',
 'technical_contract':ident(cp),'runtime_manifest':ident(manifest),'canonical_child_directories':children,
 'registered_runtime_members':len(rm['members']),'registered_runtime_member_bytes_not_full_venv':sum(x['bytes'] for x in rm['members'].values()),
 'SIF_bytes':sif,'LeWM_bytes':models,'cluster_free_bytes':v.f_bavail*v.f_frsize,'fresh_full_storage_proof':False,
 'full_runtime_alias_inventory_completed':False,'research_values_or_outcomes_or_predictions_read':False}))
'''


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive metadata label')
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v1-20261016';target=doc/('METADATA-V2-'+label+'.json')
    if target.exists():raise FileExistsError('no repeated metadata operation')
    # Compile the actual bounded program before any transport. No recursion,
    # content decoding, scheduler call, dependency or environment mutation.
    import ast
    ast.parse(READ,feature_version=(3,6))
    z=ssh('RUN='+repr(TECHNICAL_RUN)+'\n'+READ,timeout=15)
    write_new(target,z);print(json.dumps(z,indent=2))


if __name__=='__main__':main()
