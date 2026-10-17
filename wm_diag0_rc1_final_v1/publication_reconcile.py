"""Authenticate successful missing publication receipt; never reupload/rebackup."""
import json,zipfile
from wm_diag0_rc1_grid_v1.common import ROOT,DOC,identity,write_new
from wm_diag0_rc1_grid_v1.preserve import published
from wm_diag0_native_v3.preserve import verify
from wm_diag0_preflight_v1.preserve import digest,git


def main():
    r=published()
    if r['source_commit']!='27ca345933fcb4eef3e5a9fc5769a2a8201523f0' or r['whole']!={'bytes':90421,'sha256':'891c033b9ac3f279a6796d8f37316403faee1adfa27ba036d899d2498d7c58a2'}:
        raise ValueError('exact successful small package, not a replacement')
    if git('rev-parse','HEAD').decode().strip()!=r['source_commit']:raise ValueError('current source tip')
    c=json.loads((DOC/'GRID-CONTRACT.json').read_text())
    with zipfile.ZipFile(r['archive']) as z:
        raw=z.read('PACKAGE-MEMBERS.json');meta=json.loads(raw)
        if meta['source_commit']!=r['source_commit'] or meta['original_packages_or_models_recopied']!=0:raise ValueError('original exact source package')
        expected=dict(meta['members']);expected['PACKAGE-MEMBERS.json']=digest(raw)
        if len(expected)!=r['members']:raise ValueError('exact package member count')
        for n,x in c['staged_members'].items():
            if n.startswith('wm_diag0_rc1_grid_v1/'):
                if identity(ROOT/n)!=x or digest(z.read(n))!=x:raise ValueError('published/SSD/runtime frozen source byte agreement')
        if digest(z.read('docs/world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json'))!=r['contract']:raise ValueError('published frozen contract bytes')
    verify(r['archive'],expected)
    dest=__import__('pathlib').Path(r['archive']).parent/'SSD-VERIFIED-001.json'
    if identity(dest)!=identity(DOC/'SSD-VERIFIED-001.json'):raise ValueError('identical completed host/SSD receipts')
    write_new(DOC/'PUBLICATION-RECOVERED-001.json',{'status':'SUCCESSFUL_PUBLICATION_AND_SSD_AUTHENTICATED_NO_RECOMPUTATION',
        'source_commit':r['source_commit'],'remote_full_hash':r['source_commit'],'contract':r['contract'],'whole':r['whole'],'members_verified':r['members'],
        'original_SSD_receipt':identity(DOC/'SSD-VERIFIED-001.json'),'old_timeout_receipt':identity(ROOT/'docs/world-model-diagnostic-rc1-prep-routing-v1-20261016/LOCAL-RC1GRIDPUBLICATION001.json'),
        'reconciliation_source':identity(ROOT/'wm_diag0_rc1_final_v1/publication_reconcile.py'),'archives_recreated_or_recopied':0,'research_jobs_repeated':0})
    print(json.dumps({'status':'PUBLICATION_RECEIPT_RECOVERED_BY_IDENTITY','source_commit':r['source_commit'],'remote_full_hash':r['source_commit'],'whole':r['whole'],'members_verified':r['members'],'rebackup':False}))


if __name__=='__main__':main()
