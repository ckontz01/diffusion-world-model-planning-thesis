"""Strict externally bound identities before delegating to tested V2 readback.

V2's readback implementation is preserved. Its optional-verifier identity inputs
must not be allowed to disable whole/manifest checks with None. Future actual
controller integration MUST call this V3 adapter, not the V2 primitive directly.
No standalone real transfer/authorization command is supplied.
"""
from . import native_transfer_v2 as v2
from .archive_v2 import MAX_ARCHIVE,MAX_MANIFEST
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity

destination=v2.destination
transport_command=v2.transport_command
stream_once=v2.stream_once
portable_identity=v2.portable_identity


def verify_and_promote(partial,target,portable_inventory,binding,expected_whole,
                       expected_manifest,expected_portable,deadline):
    valid_identity(expected_whole,MAX_ARCHIVE)
    valid_identity(expected_manifest,MAX_MANIFEST)
    valid_identity(expected_portable,MAX_MANIFEST)
    if not isinstance(binding,dict) or set(binding)!={'root_paths','final_contract_sha256'}:
        raise ValueError('exact external frozen final-contract/archive root binding')
    valid_identity({'bytes':0,'sha256':binding['final_contract_sha256']},0)
    roots=binding['root_paths']
    if not isinstance(roots,dict) or set(roots)!=set(portable_inventory.get('root_labels',[])):
        raise ValueError('complete externally bound original archive roots')
    for path in roots.values():
        if not isinstance(path,str) or not path or len(path.encode('utf8'))>4096 or any(x in path for x in ('\x00','\r','\n')):
            raise ValueError('bounded original root path metadata, never resolved on Windows')
    return v2.verify_and_promote(partial,target,portable_inventory,binding,
                                  expected_whole,expected_manifest,expected_portable,deadline)
