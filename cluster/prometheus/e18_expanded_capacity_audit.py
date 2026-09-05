"""User-authorized aggregate-only capacity audit. Never read outcome payloads.

HDF5 access is restricted to named episode identifier datasets. TSV schemas
are checked before data rows are read. Eligible identities exist only in memory;
outputs contain counts and hashes, never memberships or selected starts.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

REGISTRY_SHA = '35cd851464f4d7243c3c07b794f65db0f32caa16bbc787a83dda68388c4898f0'
ID_KEYS = ('episode_idx', 'episode_id', 'source_episode_id', 'target_episode_id', 'goal_episode_id')
COLUMNS = set('episode_id episode_length partition eval_index shard_index start_step dataset_goal_step declared_goal_offset source_global_row goal_global_row selection_hash split base_index goal_horizon'.split())
MEMBERSHIPS = {
 'D2_exposed': 'manifests/acid-alternative-v3-d2/pusht/job-297535/d2-fresh.tsv',
 'D3_exposed': 'manifests/gdp-cem-e11-d3/pusht/job-297834/d3-untouched.tsv',
 'D4_exposed': 'manifests/gdp-cem-e13-d4/pusht/job-298616/d4-untouched.tsv',
 'C1_locked': 'manifests/acid-alternative-v1/pusht/c1-locked-confirmation.tsv',
 'I1_locked': 'manifests/acid-alternative-v1/pusht/i1-confirmation-identification-episodes.tsv',
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def id_digest(ids: set[int]) -> str:
    return sha(''.join(f'{i}\n' for i in sorted(ids)).encode())

def identifiers(values, universe: set[int]) -> set[int]:
    ids = {int(v) for v in values}
    ids.discard(-1)  # explicit padding only; reject other unknown values
    if not ids <= universe:
        raise ValueError('Unknown episode identifier; values withheld')
    return ids

def read_tsv(path: Path, universe: set[int]):
    with path.open() as f:
        reader = csv.DictReader(f, delimiter='\t')
        fields = reader.fieldnames
        if not fields or 'episode_id' not in fields or set(fields) - COLUMNS:
            raise ValueError('Non-allowlisted TSV schema: ' + str(path))
        ids = identifiers((r['episode_id'] for r in reader), universe)
    return ids, {'format': 'membership_tsv', 'fields': fields,
                 'metadata_file_sha256': sha(path.read_bytes())}

def read_h5_ids(path: Path, universe: set[int]):
    import h5py
    import numpy as np
    by_key = {}
    with h5py.File(path, 'r') as f:
        for key in ID_KEYS:
            if key in f:
                d = f[key]
                if not isinstance(d, h5py.Dataset) or d.dtype.kind not in 'iu':
                    raise ValueError('Noninteger identifier dataset: ' + str(path))
                by_key[key] = identifiers(np.unique(d[:]).tolist(), universe)
    if not by_key:
        raise ValueError('No allowlisted identifier dataset: ' + str(path))
    union = set().union(*by_key.values())
    old_key = next((k for k in ('episode_idx','episode_id','source_episode_id') if k in by_key), None)
    old_ids = by_key[old_key] if old_key else set()
    return union, old_ids, {
        'format': 'hdf5_identifier_projection', 'read_dataset_keys': list(by_key),
        'identifier_key_counts': {k: len(v) for k,v in by_key.items()},
        'identifier_key_hashes': {k: id_digest(v) for k,v in by_key.items()},
        'target_or_other_ids_not_in_old_projection': len(union - old_ids),
        'whole_hdf5_hashed': False,
    }

def ledger(parts, groups, order):
    out = {}
    for part, initial in parts.items():
        remaining = set(initial); rows = []
        for name in order:
            excluded = remaining & groups[name]
            remaining -= groups[name]
            rows.append({'reason': name, 'newly_excluded': len(excluded), 'remaining': len(remaining)})
        out[part] = {'length_eligible': len(initial), 'steps': rows, 'remaining_count': len(remaining)}
    return out

def run(root: Path):
    registry_path = root/'manifests/partitions/pusht-v1/episodes-seed-20260728.tsv'
    if sha(registry_path.read_bytes()) != REGISTRY_SHA:
        raise ValueError('Partition registry identity changed')
    with registry_path.open() as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    reg = {int(r['episode_id']): r for r in rows}
    if len(reg) != len(rows): raise ValueError('Duplicate partition identifiers')
    universe = set(reg)
    parts = {p: {e for e,r in reg.items() if r['partition']==p and int(r['episode_length'])>=151} for p in ('P2','P3','P4')}
    sources = []; groups = {}; old_groups = {}
    def add(name, ids, path, details=None, old_ids=None):
        groups.setdefault(name,set()).update(ids)
        old_groups.setdefault(name,set()).update(ids if old_ids is None else old_ids)
        sources.append({'category': name, 'path': str(path), 'identifier_count': len(ids),
            'identifier_projection_sha256': id_digest(ids),
            'long_partition_intersections': {p: len(ids&s) for p,s in parts.items()}, **(details or {})})
    def tsv(name, rel):
        p = root/rel; ids, details = read_tsv(p, universe); add(name,ids,p,details)
    for name, rel in MEMBERSHIPS.items(): tsv(name, rel)
    tsv('other_named_development', 'manifests/acid-alternative-v1/pusht/d1-fresh-development.tsv')
    tsv('other_named_development', 'manifests/acid-alternative-v1/pusht/r0-official-seed42.tsv')
    tsv('later_model_development', 'experiments/gdp-cem-e14/development-run-20260823-99f92cbe/p2-manifests/33ae351f/pusht/queries.tsv')
    tsv('later_model_development', 'experiments/gdp-cem-e18/development-run-20260827-182ed1e7/p2-manifests/pusht/queries.tsv')

    legacy_path=root/'manifests/acid-alternative-v1/pusht/summary.json'
    legacy=json.loads(legacy_path.read_text())
    seen=set(); skipped=[]
    for item in legacy['legacy_sources']:
        p=Path(item.get('path',''))
        if p.suffix!='.h5':
            skipped.append({'path':str(p),'reason':'not read: outcome-bearing/non-HDF5 legacy source'})
            continue
        if not p.is_relative_to(root/'data/stablewm') or not any('/'+part+'-' in str(p) for part in ('p2','p3','p4')):
            raise ValueError('Unexpected exposure source path')
        if '/candidate-pools/' in str(p): name='candidate_pool_inputs'
        elif '/closed-loop-confirmation/' in str(p): name='earlier_P4_query_allocation'
        else: name='earlier_candidate_execution'
        ids,old,details=read_h5_ids(p,universe);add(name,ids,p,details,old);seen.add(p)

    # Previously inventoried P2 pools, plus all canonical P3/P4 pool metadata.
    poolroot=root/'data/stablewm/derived/candidate-pools/pusht-v1'
    pool_meta=[]
    for d in sorted(poolroot.iterdir()):
        if not d.is_dir() or not d.name.startswith(('p2-','p3-','p4-')): continue
        p=d/'manifest.json'
        if not p.exists(): continue
        m=json.loads(p.read_text())
        if m.get('partition') not in ('P2','P3','P4'): raise ValueError('Pool partition mismatch')
        target=Path(m['output_h5'])
        if not target.is_relative_to(poolroot): raise ValueError('Pool path outside allowlist')
        pool_meta.append({'path':str(p),'sha256':sha(p.read_bytes()),'partition':m['partition']})
        if target not in seen:
            ids,old,details=read_h5_ids(target,universe);add('candidate_pool_inputs',ids,target,details,old);seen.add(target)

    caches = {
      'E14':'data/stablewm/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/e14-variable-cache-job-298993-0/cache.h5',
      'E15':'experiments/gdp-cem-e15/data-preflight-1b97e228/pusht/cache.h5',
      'E17':'experiments/gdp-cem-e17/development-run-20260827-9fb5a8c2/cache/pusht/cache.h5',
      'E16':'experiments/gdp-cem-e16/development-run-20260827-3669dc32/stage-a-banks/pusht/vad/seed-7201/metrics.h5',
    }
    for label,rel in caches.items():
        p=root/rel; ids,old,details=read_h5_ids(p,universe)
        add('component_training_validation' if label!='E16' else 'later_model_development',ids,p,details,old)
    add('explicit_engineering', {8908,201,627}, 'published exposed R1/R3 identities')

    sage=root/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage'
    paper=set(); paper_sources=[]
    for p in sorted((sage/'data/manifests/pusht').glob('seed*/h*.json')):
        m=json.loads(p.read_text())
        ids=identifiers((r['episode_id'] for r in m['records']),universe)
        paper.update(ids);paper_sources.append({'path':str(p),'sha256':sha(p.read_bytes())})
    if len(paper_sources)!=18: raise ValueError('SAGE manifest grid changed')
    add('SAGE_paper_evaluated',paper,sage/'data/manifests/pusht',{'manifests':paper_sources})
    split_path=sage/'data/splits/pusht_episode_split_seed42.json'
    split=json.loads(split_path.read_text())
    roles={k:identifiers(split.get(k+'_episode_idx',split.get(k,[])),universe) for k in ('train','val','test')}
    if set.union(*roles.values())!=universe or sum(map(len,roles.values()))!=len(universe): raise ValueError('Invalid SAGE split')

    order=['component_training_validation','D2_exposed','D3_exposed','D4_exposed',
           'C1_locked','I1_locked','earlier_P4_query_allocation','earlier_candidate_execution',
           'candidate_pool_inputs','other_named_development','later_model_development',
           'SAGE_paper_evaluated','explicit_engineering']
    for name in order: groups.setdefault(name,set());old_groups.setdefault(name,set())
    excluded=set().union(*groups.values())
    final={p:s-excluded for p,s in parts.items()}
    combined=set.union(*final.values());expanded=final['P3']|final['P4']
    old_excluded=set().union(*old_groups.values())
    nonpool=set().union(*(v for k,v in groups.items() if k!='candidate_pool_inputs'))
    pool_only={p:(s-nonpool)&groups['candidate_pool_inputs'] for p,s in parts.items()}
    # File-location search only, never reads allocation outcomes or arbitrary files.
    d5_locations=[str(p.relative_to(root)) for p in (root/'manifests').rglob('*') if 'd5' in p.name.lower()]
    # D5 absence here is a bounded locator result, not a universal attestation.
    result={
      'kind':'authorized_count_only_capacity_audit','registry_sha256':REGISTRY_SHA,
      'source_sha256':sha(Path(__file__).read_bytes()),
      'total_partition_counts':dict(Counter(r['partition'] for r in rows)),
      'ledger':ledger(parts,groups,order),
      'remaining_by_partition':{p:{'count':len(s),'sage_roles':{k:len(s&v) for k,v in roles.items()}} for p,s in final.items()},
      'new_P3_P4_count':len(expanded),'combined_count':len(combined),
      'combined_sage_roles':{k:len(combined&v) for k,v in roles.items()},
      'reserve_scenarios':[{'sage_reserve':n,'feasible':n<=len(combined&roles['test']),
                            'E18_remainder_if_reserved':len(combined)-n if n<=len(combined&roles['test']) else None}
                           for n in (0,50,100,200)],
      'maximum_sage_test_reserve':len(combined&roles['test']),
      'E18_remainder_after_maximum_sage_reserve':len(combined-roles['test']),
      'exposure_categories':{k:{'total':len(v),'long_by_partition':{p:len(v&s) for p,s in parts.items()}} for k,v in groups.items()},
      'pool_only_conservative_exclusions':{p:len(s) for p,s in pool_only.items()},
      'legacy_primary_id_only_counterfactual':{p:len(s-old_excluded) for p,s in parts.items()},
      'extra_exclusions_from_target_identifier_union':{p:len((s-old_excluded)-final[p]) for p,s in parts.items()},
      'metadata_sources':sources,'pool_manifests':pool_meta,
      'legacy_registry_sha256':sha(legacy_path.read_bytes()),'sage_split_sha256':sha(split_path.read_bytes()),
      'skipped_legacy_non_hdf5_sources':skipped,'d5_filename_locator_matches':d5_locations,
      'limitations':[
        'Conditional on completeness of canonical registries and recorded exposure sources; no independent custodian attestation.',
        'No selected records or value validation. Missing/future/elsewhere allocations are not certified absent.',
        'No D5-named allocation found in the canonical manifest-tree search, if locator matches are empty. Existing historical records say D5 was not generated.',
        'P3/P4 counts require a separate release decision. C1/I1 and earlier P4 query allocation remain excluded.',
        'Pool-only exposure is conservatively excluded; absence of executed candidates does not prove no model inputs were inspected.',
        'Exact LeWM episode training membership remains unknown for every prospective episode.',
        'Non-HDF5 legacy outcome tables were not read. Their unrelated historical baseline identities are bounded by existing registries, not re-certified here.',
      ],
      'flags':{'membership_metadata_read':True,'protected_outcomes_read':False,'outcome_files_hashed':False,
               'prospective_state_pixel_action_read':False,'models_called':False,'episodes_released':False,
               'confirmation_manifest_created':False,'experiment_launched':False,'eligible_identity_list_emitted':False},
    }
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);args=p.parse_args()
    print(json.dumps(run(args.root),indent=2,sort_keys=True))
