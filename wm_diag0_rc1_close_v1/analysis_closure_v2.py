"""Bind complete independent analysis and closed logs before archive creation.

No main/analysis execution, scientific JSON/array decoding or gate authority.
Only a trusted frozen CPU caller AFTER both owned V2 child groups are cleaned
may create this record. The record preserves identities; it does not prove that
an arbitrary caller actually ran those children. Full stage/dispatch/runtime/
root/storage/publication/SSD authentication remains separately mandatory.
"""
import os,stat
from pathlib import Path
from wm_diag0_rc1_final_v2.archive_v2 import canonical,check_time
from wm_diag0_rc1_final_v2.evidence_auth_v1 import bound_json,bound_bytes,ordinary,USAGE
from .closed_identity_v2 import identity
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity

SCHEMA='WM-DIAG0-RC1-CLOSED-COMPLETE-ANALYSIS-v1'
VALIDATOR='wm_diag0_rc1_close_v1/analysis_validate.py'
COUNTS={'sources':120,'retained_fits':6,'active_heads':4,'parents':128,'allocation_attempts':139}
LOG_NAMES={'analysis':'logs/analysis.log','independent_acceptance':'logs/independent_acceptance.log'}
CONTROL_NAMES={'accepted':'controls/ACCEPTED.json','independent':'controls/INDEPENDENT-ANALYSIS-VERIFIED.json'}


def check_proof(c,contract,accepted,proof):
    valid_identity(contract,1000000)
    if c.get('rc1_final',{}).get('analysis_authorized') is not True or c.get('gpu_stages_authorized') is not False:
        raise PermissionError('new frozen CPU-only authority, never a draft or GPU contract')
    expected_fields=set(COUNTS)|{'status','contract_sha256','analysis_output_seal','validator_source',
        'historical_evidence_reauthentication','scientific_values_emitted','research_model_simulator_fit_source_generation_calls',
        'parent_publication_authorized','final_gate_ready'}
    if not isinstance(proof,dict) or set(proof)!=expected_fields:raise ValueError('complete exact technical validator proof schema, no extra private field')
    if proof.get('status')!='COMPLETE_ANALYSIS_INDEPENDENTLY_RECONSTRUCTED_PENDING_ARCHIVE_AND_FINAL_SSD' or proof.get('contract_sha256')!=contract['sha256']:
        raise ValueError('exact complete independent-validator proof and final contract')
    for k,v in COUNTS.items():
        if type(proof.get(k)) is not int or proof[k]!=v:raise ValueError('complete nonboolean source/fit/head/parent/allocation counts')
    if proof.get('scientific_values_emitted') is not False or proof.get('parent_publication_authorized') is not False or proof.get('final_gate_ready') is not False:
        raise ValueError('no premature publication/SSD readiness upgrade')
    if type(proof.get('research_model_simulator_fit_source_generation_calls')) is not int or proof['research_model_simulator_fit_source_generation_calls']!=0:
        raise ValueError('read-only independent analysis, no new research calls')
    source=c['staged_members'].get(VALIDATOR)
    valid_identity(source,2000000)
    if canonical(proof.get('validator_source'))!=canonical(source):raise ValueError('exact executed frozen independent-validator source identity')
    historical=proof.get('historical_evidence_reauthentication',{})
    if historical.get('status')!='ALL59_HISTORICAL_ORIGINAL_EVIDENCE_IDENTITIES_REAUTHENTICATED':raise ValueError('original59 evidence reauthentication required')
    if type(historical.get('authenticated_files')) is not int or historical['authenticated_files']!=59 or type(historical.get('opaque_bytes_hashed')) is not int or historical['opaque_bytes_hashed']!=2826430:
        raise ValueError('complete actual historical evidence counts')
    if canonical(historical.get('receipt'))!=canonical(USAGE) or canonical(c['rc1_final']['historical_usage_receipt']['identity'])!=canonical(USAGE):raise ValueError('same exact pinned externally bound historical usage002 receipt')
    if accepted.get('accepted') is not True or accepted.get('phase')!='analysis' or accepted.get('scientific_values_emitted_to_controls') is not False:
        raise ValueError('exact accepted analysis control, no private values in controls')
    wanted={'source_roots':120,'retained_fits':6,'active_heads':4,'diagnostic_parents':128}
    if set(accepted)!=set(wanted)|{'accepted','phase','output_seal','scientific_values_emitted_to_controls'}:
        raise ValueError('complete exact accepted-control schema')
    for k,v in wanted.items():
        if type(accepted[k]) is not int or accepted[k]!=v:raise ValueError('nonboolean complete accepted-control counts')
    valid_identity(accepted['output_seal'],20000000)
    if canonical(proof.get('analysis_output_seal'))!=canonical(accepted['output_seal']):raise ValueError('first and independent pass exact same output seal')
    return accepted['output_seal']


def expected_paths(taskdir):
    task=Path(taskdir)
    return {**{k:task/v for k,v in CONTROL_NAMES.items()},**{k:task/v for k,v in LOG_NAMES.items()}}


def authenticate_opaque_output(taskdir,seal,deadline):
    """Exact three ordinary output files; no alias-target stat or value read."""
    root=ordinary(Path(taskdir)/'output');wanted={'RESULTS.json','ACCEPTANCE.json','MEMBERS.json'}
    if not root.is_dir():raise ValueError('one closed ordinary analysis output directory')
    with os.scandir(str(root)) as scan:entries=list(scan)
    if {e.name for e in entries}!=wanted or len(entries)!=3:raise ValueError('exact closed flat final output, no extra directory or member')
    for entry in entries:
        s=entry.stat(follow_symlinks=False)
        if not stat.S_ISREG(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no closed output alias/reparse/special member')
    members=bound_json(root/'MEMBERS.json',seal,20000000,deadline)
    if not isinstance(members,dict) or set(members)!=wanted-{'MEMBERS.json'}:raise ValueError('exact externally sealed complete output membership')
    total=0
    for name,limit in (('RESULTS.json',38000000),('ACCEPTANCE.json',1000000)):
        valid_identity(members[name],limit);total+=members[name]['bytes'];bound_bytes(root/name,members[name],limit,deadline)
    if total>39000000:raise ValueError('unchanged combined complete-analysis output bound')
    bound_bytes(root/'MEMBERS.json',seal,20000000,deadline)
    with os.scandir(str(root)) as scan:after=list(scan)
    if {e.name for e in after}!=wanted or len(after)!=3:raise ValueError('closed output membership changed during readback')
    for entry in after:
        s=entry.stat(follow_symlinks=False)
        if not stat.S_ISREG(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('closed output changed type during readback')


def authenticate_closed(c,contract,taskdir,closed,deadline):
    """Only bounded technical controls/logs and opaque member hashing.

    closed must itself be externally hashed by the owned CPU caller before it is
    supplied to an archive child. A self-declared record alone is not authority.
    The output RESULTS/ACCEPTANCE payloads are NOT decoded by this function.
    """
    check_time(deadline);valid_identity(contract,1000000);task=Path(taskdir)
    if set(closed)!={'schema','contract','analysis_output_seal','files'} or closed['schema']!=SCHEMA or canonical(closed['contract'])!=canonical(contract):
        raise ValueError('exact closed complete-analysis identity schema')
    paths=expected_paths(task)
    if not isinstance(closed['files'],dict) or set(closed['files'])!=set(paths):raise ValueError('both controls AND both closed role logs required')
    accepted=bound_json(paths['accepted'],closed['files']['accepted'],1000000,deadline)
    proof=bound_json(paths['independent'],closed['files']['independent'],16000,deadline)
    seal=check_proof(c,contract,accepted,proof)
    if canonical(seal)!=canonical(closed['analysis_output_seal']):raise ValueError('externally closed seal changed')
    for role in LOG_NAMES:bound_bytes(paths[role],closed['files'][role],100000,deadline)
    # Reads/hashes opaque output bytes via its exact manifest; does not parse
    # scientific results, array values or pickle. All aliases are forbidden.
    authenticate_opaque_output(task,seal,deadline)
    # Original controls/logs cannot change during the opaque output readback.
    for role,path in paths.items():bound_bytes(path,closed['files'][role],1000000 if role=='accepted' else 100000,deadline)
    check_time(deadline)
    return {'status':'CLOSED_COMPLETE_ANALYSIS_CONTROLS_LOGS_AND_OPAQUE_OUTPUT_REAUTHENTICATED',
        'contract':contract,'analysis_output_seal':seal,'closed_files':closed['files'],
        'scientific_payload_values_deserialized':False,'parent_publication_authorized':False,
        'actual_owned_child_cleanup_authenticated_by_this_record_alone':False,'final_gate_ready':False}


def close_after_owned_children(c,contract,taskdir,independent_identity,deadline):
    """Call only after actual V2 writer+validator process groups/logs are closed.

    The owned caller supplies independent_identity immediately after the fixed
    validator exits, not from an untrusted results field. Preexisting output or
    failed/ambiguous child attempts must have stopped before this function.
    """
    task=Path(taskdir);paths=expected_paths(task);valid_identity(independent_identity,16000)
    bound_bytes(paths['independent'],independent_identity,16000,deadline)
    files={role:identity(path,1000000 if role=='accepted' else 100000,deadline) for role,path in paths.items()}
    if canonical(files['independent'])!=canonical(independent_identity):raise ValueError('validator proof changed since owned child readback')
    accepted=bound_json(paths['accepted'],files['accepted'],1000000,deadline)
    proof=bound_json(paths['independent'],independent_identity,16000,deadline)
    seal=check_proof(c,contract,accepted,proof)
    record={'schema':SCHEMA,'contract':contract,'analysis_output_seal':seal,'files':files}
    if len(canonical(record))>8000:raise ValueError('finite closed-analysis control record')
    authenticate_closed(c,contract,task,record,deadline)
    return record
