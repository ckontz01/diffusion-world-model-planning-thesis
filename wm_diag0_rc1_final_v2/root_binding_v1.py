"""Opaque EVERY-member byte binding with compact, independently bound roots.

Per-root digests commit to every sorted relative name, kind, byte count and hash
or inert alias literal. No payload values are decoded. This avoids persisting a
second large per-file inventory merely for precompute authentication; no member,
logical copy, archive byte or scientific artifact is omitted or discounted.
Actual source-bound roots/aliases must come from the separate layout authority.
"""
import hashlib,os
from pathlib import Path
from .archive_v2 import canonical,check_time,checked_plan,check_bindings,token
from .archive_verify_v2 import source_hash
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity

SCHEMA='WM-DIAG0-RC1-EVERY-MEMBER-ROOT-BINDING-v1'
OWNED_FINAL='study/campaign-v4-rc1-final-v2'


def accumulator(planned,root_paths,authority_sha256):
    members=checked_plan(planned)
    valid_identity({'bytes':0,'sha256':authority_sha256},0)
    if not isinstance(root_paths,dict) or set(root_paths)!=set(planned['root_labels']):raise ValueError('complete separately approved original roots')
    labels=sorted(root_paths)
    if any(a!=b and b.startswith(a+'/') for a in labels for b in labels):raise ValueError('nonoverlapping logical roots, no ambiguous member owner')
    for path in root_paths.values():
        if not isinstance(path,str) or not Path(path).is_absolute() or '..' in Path(path).parts:raise ValueError('canonical absolute original root metadata')
    state={n:{'regular_files':0,'inert_aliases':0,'logical_regular_bytes':0,'hash':hashlib.sha256()} for n in labels}
    return members,state


def add(state,name,row,digest=None):
    root=next((r for r in state if name==r or name.startswith(r+'/')),None)
    if root is None:raise ValueError('every member has an independently approved whole root')
    relative=name[len(root):].lstrip('/');s=state[root]
    if row['type']=='file':
        valid_identity({'bytes':row['bytes'],'sha256':digest},4000000000)
        record=[relative,'file',row['bytes'],digest];s['regular_files']+=1;s['logical_regular_bytes']+=row['bytes']
    else:
        record=[relative,'metadata-only-alias',row['target']];s['inert_aliases']+=1
    raw=canonical(record)
    if len(raw)>8192:raise ValueError('finite per-member digest record')
    s['hash'].update(raw);s['hash'].update(b'\n')


def finish(planned,root_paths,authority_sha256,state):
    rows={n:{'regular_files':s['regular_files'],'inert_aliases':s['inert_aliases'],
             'logical_regular_bytes':s['logical_regular_bytes'],'every_sorted_member_record_sha256':s['hash'].hexdigest()}
          for n,s in state.items()}
    if sum(s['logical_regular_bytes'] for s in rows.values())!=planned['logical_payload_bytes_no_discounts']:
        raise ValueError('every regular byte/logical copy accounted, no discount')
    proof={'schema':SCHEMA,'source_authority_sha256':authority_sha256,'root_paths':root_paths,'roots':rows,
           'logical_members':len(planned['members']),'logical_regular_bytes_no_discounts':planned['logical_payload_bytes_no_discounts'],
           'alias_policy':'inert literals only; never followed/resolved/restored/executed'}
    if len(canonical(proof))>64000:raise ValueError('compact root commitment receipt bound')
    return proof


def authenticate(planned,root_paths,authority_sha256,deadline):
    """Independently hash all actual originals through no-follow regular opens.

    Call only after inventory_v3.plan with exact whole-root/alias authority.
    Own mutable future-final inputs are NOT silently excluded by this function.
    """
    members,state=accumulator(planned,root_paths,authority_sha256)
    check_bindings(planned,{'root_paths':root_paths,'final_contract_sha256':authority_sha256})
    for name,row in sorted(members.items()):
        check_time(deadline)
        if 'path' not in row:raise ValueError('original path required for actual byte authentication')
        if row['type']=='file':
            digest=source_hash(Path(row['path']),row['bytes'],deadline)
            if 'sha256' in row and digest!=row['sha256']:raise ValueError('pre-bound original hash changed')
            add(state,name,row,digest)
        else:
            p=Path(row['path']);before=token(p,True)
            if os.readlink(str(p))!=row['target'] or token(p,True)!=before:raise ValueError('exact approved inert alias changed')
            add(state,name,row)
    check_time(deadline);return finish(planned,root_paths,authority_sha256,state)


def from_independent_portable(portable,root_paths,authority_sha256,readback,deadline):
    """Bind readback's hashes to earlier original-root commitments, not a flag.

    Caller must compare this proof to authenticate()'s independently supplied
    original proof. The status flag alone is deliberately insufficient.
    """
    if readback.get('status')!='WHOLE_AND_EVERY_MEMBER_INDEPENDENTLY_VERIFIED' or readback.get('originals_independently_reread') is not True:
        raise ValueError('actual independent archive AND original readback first')
    members,state=accumulator(portable,root_paths,authority_sha256)
    for name,row in sorted(members.items()):
        check_time(deadline)
        if 'path' in row or (row['type']=='file' and 'sha256' not in row):raise ValueError('portable expected original hashes, no path following')
        add(state,name,row,row.get('sha256'))
    check_time(deadline);return finish(portable,root_paths,authority_sha256,state)


def compare(actual,expected):
    if canonical(actual)!=canonical(expected):raise ValueError('complete roots/every-member content binding changed; preserve, no retry')


def compare_preexisting(actual,expected):
    """One EXPLICIT owned final-root addition; every historical root unchanged.

    Precompute study roots cannot include a not-yet-created final output. The
    final archive must include that complete root, whose closed new source,
    output seal and logs need their own independent controller binding.
    """
    if actual.get('schema')!=SCHEMA or expected.get('schema')!=SCHEMA or actual.get('source_authority_sha256')!=expected.get('source_authority_sha256'):
        raise ValueError('same independently bound source/root authority')
    if set(actual['roots'])!=set(expected['roots'])|{OWNED_FINAL} or OWNED_FINAL in expected['roots']:
        raise ValueError('no historical/artificial/runtime/model root may be omitted or added silently')
    for label,row in expected['roots'].items():
        if canonical(actual['roots'][label])!=canonical(row) or actual['root_paths'][label]!=expected['root_paths'][label]:
            raise ValueError('historical whole root/member/path changed: '+label)
    if set(actual['root_paths'])!=set(actual['roots']) or set(expected['root_paths'])!=set(expected['roots']):raise ValueError('complete physical root bindings')
    if actual.get('alias_policy')!=expected.get('alias_policy'):raise ValueError('inert preservation policy unchanged')
    added=actual['roots'][OWNED_FINAL]
    if actual['logical_members']!=expected['logical_members']+added['regular_files']+added['inert_aliases'] or actual['logical_regular_bytes_no_discounts']!=expected['logical_regular_bytes_no_discounts']+added['logical_regular_bytes']:
        raise ValueError('full new owned final root is added without copy/byte discounts')
    return {'historical_whole_roots_unchanged':len(expected['roots']),'new_owned_final_root_included':True,
            'final_source_output_log_authentication_still_separate':True,'final_gate_ready':False}
