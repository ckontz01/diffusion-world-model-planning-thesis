"""Bounded technical storage/runtime/lineage metadata only; no scheduler query."""
import json,sys
from wm_diag0_rc1_grid_v1.common import ROOT,TECHNICAL_RUN,identity,write_new
from wm_diag0_native_v3.transport import ssh

READ=r'''
import hashlib,json,os,pathlib,stat
r=pathlib.Path(RUN);cp=r/'source/TECHNICAL-CONTRACT.json'
def ident(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
if ident(cp)['sha256']!='101cd417d9a823a559a29d3813887ad17f721b450ce4f21d267b597e4ef788fd':raise ValueError('actual executed closure')
c=json.loads(cp.read_text());base=r.parent;lineages={};aliases={};runtime_files=0;runtime_bytes=0
for child in sorted(base.iterdir()):
 count=0;size=0;links=[]
 if child.is_symlink() or not child.is_dir():raise ValueError('unexpected top-level study entry requires review')
 for directory,dirs,names in os.walk(str(child),followlinks=False):
  for n in dirs+names:
   p=pathlib.Path(directory)/n
   if p.is_symlink():links.append({'member':str(p.relative_to(child)),'target':os.readlink(str(p))})
   elif p.is_file():count+=1;size+=p.stat().st_size
 lineages[child.name]={'logical_bytes':size,'regular_files':count,'symlinks':links}
for directory,dirs,names in os.walk(c['venv'],followlinks=False):
 for n in dirs+names:
  p=pathlib.Path(directory)/n
  if p.is_symlink():aliases[str(p.relative_to(c['venv']))]=os.readlink(str(p))
  elif p.is_file():runtime_files+=1;runtime_bytes+=p.stat().st_size
manifest=pathlib.Path(c['recovery']['old_run'])/'controls/RUNTIME-MANIFEST.json'
if ident(manifest)!=c['runtime_manifest']:raise ValueError('authenticated runtime manifest identity')
if runtime_bytes>2100000000:raise ValueError('full retained runtime reservation exceeded')
logical=sum(x['logical_bytes'] for x in lineages.values());sif=pathlib.Path(c['sif']).stat().st_size
models=sum(pathlib.Path(x['path']).stat().st_size for x in c['lewm'].values())
# Reserve all not-yet-complete technical/grid artifacts and ALL future sources,
# controls and final analysis; subtract no accepted successes or duplicate links.
live=logical+2100000000+sif+models+620000000+3840000000+127000000+60000000+20000000+300000000
if live>13500000000 or live+500000000>14000000000 or live+28000000000+2874852312>44000000000:raise ValueError('conservative all-lineage full-future storage caps')
v=os.statvfs(str(base))
print(json.dumps({'scope':'technical lineage/runtime/storage metadata only','technical_contract':ident(cp),'runtime_manifest':ident(manifest),
 'canonical_children':lineages,'full_venv_regular_bytes':runtime_bytes,'full_venv_regular_files':runtime_files,'venv_aliases_unaccepted_pending_explicit_review':aliases,
 'SIF_bytes':sif,'LeWM_bytes':models,'logical_current_study_bytes':logical,'full_future_live_bytes':live,'archive_full_future_bytes':live+500000000,
 'inclusive_full_future_bytes':live+28000000000+2874852312,'cluster_free_bytes':v.f_bavail*v.f_frsize,'quality_or_outcomes_or_predictions_read':False}))
'''


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive metadata label')
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v1-20261016'
    path=doc/('METADATA-'+label+'.json')
    if path.exists():raise FileExistsError('one exclusive metadata read')
    z=ssh('RUN='+repr(TECHNICAL_RUN)+'\n'+READ)
    write_new(path,z)
    print(json.dumps(z,indent=2))


if __name__=='__main__':main()
