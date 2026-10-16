"""One compact publication/SSD transaction; no research dispatch or retry."""
import json,subprocess,sys
from .common import ROOT,DOC,DOCREL,write_new,identity
from wm_diag0_preflight_v1.preserve import git


def main():
    if (DOC/'PUBLICATION-001.started.json').exists():raise FileExistsError('ambiguous/completed publication must be reconciled, never repeated')
    if git('diff','--cached','--name-only').strip():raise ValueError('preserve unrelated pre-existing staged work')
    if not (DOC/'INDEPENDENT-PREFREEZE-REVIEW-001.txt').exists():raise ValueError('actual source/contract review required')
    own=['wm_diag0_rc1_grid_v1',DOCREL,
        'docs/world-model-diagnostic-rc1-technical-v1-20261016/OBSERVE-003.json',
        'docs/world-model-diagnostic-rc1-technical-v1-20261016/PROGRESS-003.json',
        'docs/world-model-diagnostic-rc1-technical-v1-20261016/OBSERVE-004.json',
        'docs/world-model-diagnostic-rc1-technical-v1-20261016/PROGRESS-004.json',
        'docs/world-model-diagnostic-rc1-technical-v1-20261016/OBSERVE-005.json']
    write_new(DOC/'PUBLICATION-001.started.json',{'source_contract':identity(DOC/'GRID-CONTRACT.json'),'explicit_paths':own,'no_model_or_other_private_files':True})
    # Do not stage the new mutable started/SSD receipts into their own package.
    files=sorted({line for prefix in own for line in git('ls-files','--cached','--others','--exclude-standard','--',prefix).decode().splitlines()})
    files=[n for n in files if not n.endswith(('PUBLICATION-001.started.json','SSD-VERIFIED-001.json'))]
    if not files or any(n.endswith(('.pth','.ckpt','.sif','.npy','.jpg','.png')) for n in files):raise ValueError('compact reviewed source/docs/metadata only')
    git('add','--',*files)
    actual=git('diff','--cached','--name-only').decode().splitlines()
    if not set(actual)<=set(files):raise ValueError('unrelated staged path')
    git('diff','--cached','--check')
    git('commit','-m','Freeze RC1 fixed124 grid after four accepted setting gates')
    commit=git('rev-parse','HEAD').decode().strip()
    git('push','origin','HEAD:refs/heads/world-model-diagnostic-preparation-20261004')
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('full immutable remote hash required')
    p=subprocess.run([sys.executable,'-B','-m','wm_diag0_rc1_grid_v1.preserve',commit],cwd=ROOT,capture_output=True,text=True)
    if p.returncode:raise RuntimeError('publication committed/pushed; SSD not verified, no dispatch; '+p.stderr)
    write_new(DOC/'PUBLICATION-001.json',{'source_commit':commit,'remote_full_hash':commit,'contract':identity(DOC/'GRID-CONTRACT.json'),'SSD_verified':True,'grid_dispatched':False})
    print(json.dumps({'source_commit':commit,'remote_full_hash':commit,'SSD':json.loads(p.stdout),'grid_dispatched':False}))


if __name__=='__main__':main()
