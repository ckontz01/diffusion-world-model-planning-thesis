"""New-schema native readback primitive; NO actual transfer entry point.

The future frozen final controller must authenticate terminal CPU, analysis seal,
archive and portable-inventory identities independently. These functions compare
those supplied identities, not establish their provenance. Preserve old V1.
"""
import hashlib,os
from pathlib import Path
from .archive_v2 import canonical,checked_plan,check_time,MAX_MANIFEST,token
from .archive_verify_v2 import verify
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity
from wm_diag0_rc1_final_v1.native_transfer_v1 import destination,transport_command,stream_once


def portable_identity(planned):
    """Bind the complete inert portable inventory, not a creator-only manifest."""
    checked_plan(planned)
    if any('path' in row or (row['type']=='file' and 'sha256' not in row)
           for row in planned['members'].values()):
        raise ValueError('portable inventory requires authenticated original member hashes, no source paths')
    raw=canonical(planned)
    if len(raw)>MAX_MANIFEST:raise ValueError('portable inventory pre-write byte reservation')
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def nonredirected(path):
    """Reject Windows junction/reparse ancestors as well as ordinary symlinks."""
    p=Path(path)
    if not p.is_absolute():raise ValueError('absolute native path required')
    for q in (p,)+tuple(p.parents):
        try:s=q.lstat()
        except FileNotFoundError:continue
        if getattr(s,'st_file_attributes',0)&0x400 or q.is_symlink():
            raise ValueError('no native destination reparse/alias redirect')
    return p


def verify_and_promote(partial,target,portable_inventory,binding,expected_whole,
                       expected_manifest,expected_portable,deadline):
    """Independent V2 whole/member readback followed by Windows no-copy rename.

    No destination discovery, process launch, network, extraction or retry. Real
    caller must separately check exact designated SSD volume and free capacity,
    frozen contract and terminal CPU/sidecar chain, finite resource reservation.
    A failed partial is retained. An existing final target is never replaced.
    """
    if os.name!='nt':raise RuntimeError('native Windows non-overwriting rename required')
    check_time(deadline)
    valid_identity(expected_portable,MAX_MANIFEST)
    if portable_identity(portable_inventory)!=expected_portable:
        raise ValueError('externally bound independent portable-inventory identity')
    partial=nonredirected(partial);target=nonredirected(target)
    if target.parent!=partial.parent or target==partial or target.exists():
        raise FileExistsError('same directory, distinct absent target; no third full copy')
    before=token(partial)
    proof=verify(partial,portable_inventory,binding,deadline,check_sources=False,
                 expected_whole=expected_whole,expected_manifest=expected_manifest)
    if token(partial)!=before:raise ValueError('partial changed after complete V2 readback')
    check_time(deadline)
    # Native Windows Path.rename fails if another writer creates target after
    # the absence check. No replace/copy or third complete archive is used.
    partial.rename(target);check_time(deadline)
    out={k:v for k,v in proof.items() if k!='member_map'}
    out['portable_inventory']=expected_portable
    out['archive_schema']='WM-DIAG0-RC1-ARCHIVE-v2'
    out['automatic_retry']=False
    return out
