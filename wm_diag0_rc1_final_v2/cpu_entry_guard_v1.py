"""Actual-input preflight for the future frozen CPU analysis child.

NO main/submission/execution authority. A complete stage/publication/SSD and
allocation gate must call this before launching the fixed analysis writer.
This guard adds exact terminal STARTED/source binding and original59-file usage
reauthentication; neither the old writer's provenance boolean nor a draft flag
is an execution gate. Full runtime/root/storage/CPU-history proofs stay separate.
"""
import copy,hashlib,os,stat
from pathlib import Path
from .archive_v2 import canonical,check_time
from .evidence_auth_v1 import bound_json,bound_bytes,authenticate_usage
from .terminal_binding_v1 import authenticate_terminal
from .cpu_schedule_v2 import validate_draft
from .preservation_layout_v1 import GRID,check_paths
from .inventory_v3 import safe_name
from wm_diag0_rc1_final_v1.analysis import authorization


def check_frozen_extension(grid,c,layout):
    if c.get('rc1_final',{}).get('analysis_authorized') is not True:raise PermissionError('separate final frozen analysis authority required, never a draft')
    # Validate every fixed grid key/resource/member with the tested strict V2
    # adapter. Only the explicit final authority bit is temporarily made draft
    # in this PRIVATE copy; the actual bound contract is never edited.
    draft=copy.deepcopy(c);draft['rc1_final']['analysis_authorized']=False
    validate_draft(grid,draft,layout)
    return c['rc1_final']


def source_closure(source,members,deadline,contract_name=None):
    source=Path(source)
    if not isinstance(members,dict) or not 0<len(members)<=5000:raise ValueError('finite explicit frozen source closure')
    allowed=set(members)
    if contract_name is not None:safe_name(contract_name);allowed.add(contract_name)
    # Source cannot silently acquire extra importable or configuration members.
    # No directory-link classification through os.walk, no following redirects.
    seen=set();pending=[source]
    while pending:
        check_time(deadline);directory=pending.pop()
        with os.scandir(str(directory)) as scan:entries=sorted(list(scan),key=lambda e:e.name)
        for entry in entries:
            p=Path(entry.path);s=entry.stat(follow_symlinks=False)
            if getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no source ancestor/member reparse redirect')
            if stat.S_ISDIR(s.st_mode):pending.append(p)
            elif stat.S_ISREG(s.st_mode):
                seen.add(p.relative_to(source).as_posix())
                if len(seen)>5001:raise ValueError('finite complete source member count')
            else:raise ValueError('no source alias/special member')
    if seen!=allowed:raise ValueError('complete exact source closure, including no extra importable member')
    total=0
    for name,want in sorted(members.items()):
        safe_name(name)
        total+=want.get('bytes',20000001)
        if total>20000000:raise ValueError('finite source byte bound; no artifact-supplied executable')
        bound_bytes(source/name,want,2000000,deadline)
    raw=canonical(members)
    return {'members':len(members),'bytes':total,'source_identity_map_sha256':hashlib.sha256(raw).hexdigest()}


def authenticate_inputs(contract,expected,layout,deadline):
    """Future Linux controller only. Returns technical identities, no results.

    Caller binds expected from the independently frozen dispatch, not from the
    contract being read. Must also authenticate full whole-root/runtime/stage/
    publication/designated-SSD/preparation/CPU-history authority before launch.
    This preflight's successful return alone MUST NOT be treated as that gate.
    """
    check_paths(layout);check_time(deadline);contract=Path(contract)
    if contract!=Path(layout['final_run'])/'source/FINAL-CONTRACT.json':raise ValueError('exact own final source contract path')
    c=bound_json(contract,expected,1000000,deadline)
    grid=bound_json(Path(c['run'])/'source/GRID-CONTRACT.json',GRID,200000,deadline)
    final=check_frozen_extension(grid,c,layout)
    authorization(c,expected['sha256'],contract,Path(layout['analysis_task']))
    closure=source_closure(contract.parent,c['staged_members'],deadline,'FINAL-CONTRACT.json')
    historical=authenticate_usage(final['historical_usage_receipt']['path'],final['historical_usage_receipt']['identity'],deadline)
    allocations=authenticate_terminal(c,Path(layout['analysis_task'])/'controls/ALL-ALLOCATIONS-TERMINAL.json',
                                      final['all_allocations_terminal'],deadline)
    check_time(deadline)
    # Reauthenticate the externally bound contract after all preflight work.
    bound_bytes(contract,expected,1000000,deadline)
    return {'status':'CPU_ANALYSIS_INPUT_SOURCE_USAGE_AND_TERMINAL_START_PREFLIGHT_VERIFIED_NOT_FULL_ENTRY_GATE',
            'contract':expected,'source_closure':closure,'historical_evidence':historical,'terminal_allocations':allocations,
            'full_runtime_root_storage_source_CPU_and_publication_SSD_allocation_gates_checked_here':False,
            'scientific_payloads_read':False,'actual_analysis_launched':False,'final_gate_ready':False}
