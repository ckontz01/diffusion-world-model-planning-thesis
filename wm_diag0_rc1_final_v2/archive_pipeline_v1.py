"""Once-only archive/original/root readback integration, NOT a final entry.

The future frozen CPU supervisor must authenticate complete analysis/validation,
source/publication/SSD authority, current input/root and actual preparation proofs
before calling. This library grants none of those gates and never starts compute.
Every operational output must stay outside ALL input roots. Failed partials stay.
"""
import hashlib,os
from pathlib import Path
from .archive_v2 import canonical,checked_plan,check_bindings,create,check_time
from .archive_verify_v2 import verify,portable_plan
from .root_binding_v1 import authenticate,from_independent_portable,compare,compare_preexisting
from .preservation_budget_v1 import prove,PORTABLE_LIMIT


def write_bounded(path,raw,limit,deadline):
    check_time(deadline)
    if not isinstance(raw,bytes) or len(raw)>limit:raise ValueError('pre-write finite byte limit')
    with Path(path).open('xb') as f:
        if f.write(raw)!=len(raw):raise IOError('short exclusive metadata write')
        f.flush();os.fsync(f.fileno())
    check_time(deadline);return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def outputs_outside_inputs(paths,root_paths):
    physical=[Path(p) for p in root_paths.values()]
    if len(set(map(str,paths)))!=len(paths):raise ValueError('distinct once-only archive/portable/proof outputs')
    for path in map(Path,paths):
        if not path.is_absolute() or '..' in path.parts or not path.parent.is_dir():raise ValueError('explicit existing operational parent, no implicit root creation')
        if path.exists() or path.is_symlink():raise FileExistsError('existing artifact/partial/receipt retained; no automatic retry')
        for parent in path.parents:
            if parent.is_symlink() or getattr(parent.lstat(),'st_file_attributes',0)&0x400:raise ValueError('no operational ancestor redirect')
        if any(path==root or root in path.parents or path in root.parents for root in physical):raise ValueError('operational output outside ALL complete input roots')


def preserve_authenticated_roots(planned,binding,source_authority_sha256,prior_root_binding,
                                 archive,portable_path,proof_path,rescan,preparation_full_future_bytes,deadline):
    """Trusted future CPU caller only, one create; never catch-and-retry.

    rescan is a reviewed in-process inventory_v3.plan closure, never a command or
    an artifact-supplied callable. It must cover the same whole approved roots.
    It catches additions/omissions/aliases at the end of full readback as well.
    """
    if not callable(rescan):raise ValueError('independent complete-root rescan mandatory')
    checked_plan(planned);root_paths=check_bindings(planned,binding)
    outputs_outside_inputs([Path(archive),Path(portable_path),Path(proof_path)],root_paths)
    budget=prove(planned,root_paths,binding['final_contract_sha256'],preparation_full_future_bytes)
    original=authenticate(planned,root_paths,source_authority_sha256,deadline)
    transition=compare_preexisting(original,prior_root_binding)
    if canonical(rescan())!=canonical(planned):raise ValueError('whole inventory changed during original binding; no archive created')
    made=create(planned,archive,binding,deadline)
    checked=verify(archive,planned,binding,deadline,check_sources=True,expected_whole=made['whole'],expected_manifest=made['manifest'])
    portable=portable_plan(planned,checked)
    derived=from_independent_portable(portable,root_paths,source_authority_sha256,checked,deadline)
    compare(derived,original)
    if canonical(rescan())!=canonical(planned):raise ValueError('new/missing/mutated metadata member after readback; preserve archive, no retry')
    raw=canonical(portable)
    if len(raw)!=budget['forecast_portable_bytes']:raise ValueError('exact pre-reserved portable byte forecast')
    portable_identity=write_bounded(portable_path,raw,PORTABLE_LIMIT,deadline)
    result={'status':'ONCE_ARCHIVE_WHOLE_EVERY_MEMBER_ORIGINAL_ROOT_READBACK_VERIFIED_NOT_FINAL_SSD_GATE',
            'whole':made['whole'],'manifest':made['manifest'],'portable_inventory':portable_identity,
            'archive_schema':'WM-DIAG0-RC1-ARCHIVE-v2','binding':binding,'every_member_root_binding':original,
            'preexisting_roots':transition,'byte_reservations':budget,
            'logical_members':checked['logical_members'],'regular_payload_members':checked['regular_payload_members'],
            'actual_final_analysis_or_terminal_CPU_authority_authenticated_here':False,
            'archive_created_once':True,'originals_independently_reread':True,'postreadback_full_inventory_rechecked':True,
            'automatic_retry':False,'scientific_values_deserialized':False,'files_extracted_or_executed':0,
            'publication_authorized':False,'final_gate_ready':False}
    write_bounded(proof_path,canonical(result),64000,deadline)
    return result
