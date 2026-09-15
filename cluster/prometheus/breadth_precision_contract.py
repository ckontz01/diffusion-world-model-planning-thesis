"""CVL-BP1 preparation/authorization contract. Import is metadata-only."""
import hashlib
import json
from pathlib import Path
import candidate_value_contract as old

VERSION = 'candidate-value-breadth-precision-20260915'
DOC = 'docs/'+VERSION+'/PROTOCOL.md'
MANIFEST = 'docs/'+VERSION+'/DATA-ROLES.json'
ROOT = old.ROOT
RUN_PARENT = ROOT/'experiments'/VERSION
OLD_SOURCE_SHA = '521a0e6627c570ffa30d12adc63f92cf9ba76dee2c9bc4c59d24f4982f4f45f2'
OLD_CAPSULE_SHA = 'a1f152f66a1a6f1b766691b4a12c18fc6489d921f82ca7fbca29d86714b21469'
OLD_SOURCE = ROOT/'snapshots/candidate-value-learning-20260914-521a0e6627c570ff'
OLD_RUN = ROOT/'experiments/candidate-value-learning-20260914/run-521a0e6627c570ff'
FIT_SEAL = '90e491a7a186e7ef1968c70f29ecf49b3bfbe481f013ba051c10e33c77eb669c'
TRAIN_REQUEST_SHA = '85c97eb0975b67b11a617d7d9ab31249a64cce5fdaa90f0cc4501b89d669df58'
ACCEPTED = '442c9659a8f8f99e81e492cb9258488b60e12666'
SEEDS = (8201, 8202, 8203)
UPDATES = {'bce': 1800, 'relative': 1560}
CAPS = dict(gpu_seconds=309600, cpu_seconds=7200, storage_bytes=10_000_000_000,
            job_bytes=500_000_000, source_bytes=50_000_000, backup_free_bytes=40_000_000_000)
require, sha, json_read, json_write = old.require, old.sha, old.json_read, old.json_write


def allocation():
    prior = old.allocation()
    excluded = set(old.HISTORICAL) | set(sum(prior.values(), []))
    ids = sorted(set(range(1600))-excluded, key=lambda r:
                 (hashlib.sha256(f'{VERSION}|source-allocation|{r}'.encode()).hexdigest(), r))
    require(len(excluded) == 192 and len(ids) == 1408, 'Unexpected existing allocation inventory')
    return dict(original_train=prior['train'], extra_train=ids[:96], evaluation=ids[96:128],
                exclusions=dict(historical_32=list(old.HISTORICAL), **prior),
                eligible_before_new_allocation=len(ids), remaining_after_new_allocation=len(ids)-128)


def tail_seed(ref, h, t, draw):
    require(draw in range(4), 'Exactly four declared streams')
    # The high domain bit separates new seed integers; a low-bit change also
    # separates generators whose effective seed uses only the lower 32 bits.
    seed = old.tail_seeds(ref, h, t)[draw % 2]
    require(0 <= seed < (1 << 61), 'Original seed range')
    return ((seed ^ (1 << 30)) | (1 << 61)) if draw >= 2 else seed


def sampling(immediate, continuation, ref, h, t):
    """Identical original sampling algorithm/namespace; only role allowlist differs."""
    import numpy as np
    import candidate_value_learning as c
    a = allocation()
    require(ref in a['original_train']+a['extra_train']+a['evaluation'] and t in c.anchors(h), 'Source/anchor role')
    im, co = np.asarray(immediate), np.asarray(continuation)
    require(im.shape == co.shape == (64,) and np.isfinite(im).all() and np.isfinite(co).all(), 'Bank costs')
    winners = list(dict.fromkeys((int(co.argmin()), int(im.argmin()))))
    remaining = sorted(set(range(64))-set(winners), key=lambda i: (c.digest('candidate-sampling',ref,h,t,i),i))
    return dict(indices=winners+remaining[:8-len(winners)], winners=winners,
                other_slots=8-len(winners), index_coverage=8/64,
                nonwinner_inclusion_probability=(8-len(winners))/(64-len(winners)))


def grid():
    a = allocation(); groups = {}
    for kind, role, seconds in [('breadth','extra_train',600), ('precision','original_train',600), ('evaluation','evaluation',1200)]:
        groups[kind] = [dict(kind=kind,index=i,reference=r,h=h,gpu=True,seconds=seconds)
                        for i,(r,h) in enumerate((r,h) for r in a[role] for h in (75,150))]
    # The first four references of each training component are INCLUDED technical tranches.
    return (groups['breadth'][:8]+groups['precision'][:8]+groups['breadth'][8:]+groups['precision'][8:]+
            [dict(kind='fit',index=0,gpu=False,seconds=5400)]+groups['evaluation']+
            [dict(kind='analyze',index=0,gpu=False,seconds=1800)])


def task(kind, index):
    rows = [x for x in grid() if (x['kind'],x['index']) == (kind,index)]
    require(len(rows) == 1, 'Unregistered task')
    return rows[0]


def costs():
    rows = {}
    for name, refs, draws, prefix in [('breadth',96,2,1),('precision',96,2,0),('evaluation',32,4,1)]:
        trajectories = 4*8*draws+prefix
        steps = refs*trajectories*450
        rows[name] = dict(references=refs, ref_h_jobs=2*refs, new_outcomes_max=refs*2*4*8*draws,
            standalone_prefixes=2*refs*prefix, branch_episodes=refs*2*4*8*draws,
            primitive_steps_max=steps, post_anchor_steps_max=refs*8*draws*1095,
            solver_calls_max=steps//15, first_only_calls_max=refs*trajectories*4,
            new_bank_index_rows_max=0 if name=='precision' else refs*2*4*8)
    steps = sum(r['primitive_steps_max'] for r in rows.values())
    full = sum(r['solver_calls_max']-r['first_only_calls_max'] for r in rows.values())
    first = sum(r['first_only_calls_max'] for r in rows.values())
    rate = (41022+13960)/(2505797+860281)
    return dict(stages=rows, maximum_new_outcomes=32768, known_C_new_outcomes=709*8*2,
        known_availability_adjusted_new_ceiling=12288+709*8*2+8192,
        existing_A_outcomes=11344, C_total_outcomes=22688, B_total_outcomes_ceiling=23632,
        original_live_banks=709, original_final_budget_banks=157,
        C_extra_final_budget_outcome_records=157*8*2, C_final_budget_additional_stochastic_information=0,
        distinct_training_sources=dict(A=96,B=192,C=96), common_evaluation_sources=32,
        steps_max=steps, full_continuation_calls_max=full, first_only_calls_max=first,
        proposal_batches_max=2*full+first, diffusion_forwards_max=10*(2*full+first),
        gpu_jobs=448, cpu_jobs=2, fitted_models=18, optimizer_steps=9*(1800+1560),
        gpu_reserved_seconds=sum(x['seconds'] for x in grid() if x['gpu']),
        cpu_reserved_seconds=7200, caps=CAPS,
        planning_gpu_hours=dict(accepted_collection_rate=steps*rate/3600,
                               half_throughput=2*steps*rate/3600, third_throughput=3*steps*rate/3600),
        measured_rate_provenance='CVL-1 54982 allocation seconds / 3366078 physical steps; includes setup/I/O',
        planning_only=True, new_measurements=False, exact_grid=grid())


def authorize(source, run, approval):
    """A preparation manifest is never execution permission; fail before model imports."""
    a = json_read(approval)
    source, run = Path(source), Path(run).resolve()
    require(a.get('researcher_approved') is True and a.get('experiment') == VERSION and a.get('caps') == CAPS,
            'Separate exact researcher execution approval required')
    require(sha(source/'SOURCE-MANIFEST.sha256') == a['source_sha256'] and
            sha(source/DOC) == a['protocol_sha256'] and sha(source/MANIFEST) == a['role_manifest_sha256'], 'Approved source/roles/protocol')
    old.verify_source(source,a['source_sha256'])
    upstream = source/'UPSTREAM-MANIFEST.sha256'
    require(sha(upstream)==OLD_SOURCE_SHA, 'Exact original source closure')
    for line in upstream.read_text().splitlines():
        digest,name=line.split('  ',1)
        require(sha(old.child(source,name))==digest,'Unchanged inherited source: '+name)
    require(run.parent == RUN_PARENT and run.name == 'run-'+a['source_sha256'][:16], 'New-only output namespace')
    m = json_read(source/MANIFEST)
    require(m['allocation'] == allocation() and m['source_identity_verified'] is True, 'Identity-only role manifest')
    require(sha(OLD_SOURCE/'SOURCE-MANIFEST.sha256') == OLD_SOURCE_SHA and sha(OLD_RUN/'fit-0/sha256.txt') == FIT_SEAL,
            'Accepted upstream identities')
    require(sha(OLD_RUN/'BACKUP-REQUEST-train.json')==TRAIN_REQUEST_SHA,'Accepted training seal registry')
    cap_path = Path(a['old_capsule'])
    require(sha(cap_path) == OLD_CAPSULE_SHA, 'Accepted runtime capsule')
    cap = json_read(cap_path)
    # Reuse the original execution authentication; no hand audit or new model test.
    for name,digest in cap['runtime_files'].items(): require(sha(name) == digest,'Pinned runtime bytes')
    for name,digest in cap['runtime_roots'].items(): require(old.tree_hash(Path(name)) == digest,'Pinned runtime tree')
    for name,digest in cap['runtime_code_roots'].items(): require(old.tree_hash(Path(name),code_only=True) == digest,'Pinned runtime code')
    return a,m


def normalizer_path():
    directory=OLD_RUN/'fit-0'
    require(sha(directory/'sha256.txt')==FIT_SEAL,'Accepted normalizer seal')
    members={n:d for d,n in (s.split('  ',1) for s in (directory/'sha256.txt').read_text().splitlines())}
    path=directory/'normalization.npz'
    require(sha(path)==members['normalization.npz'],'Exact training-only normalization coefficients')
    return path


def reservation(used_gpu, used_cpu, used_bytes, remaining):
    return (used_gpu+sum(t['seconds'] for t in remaining if t['gpu']) <= CAPS['gpu_seconds'] and
            used_cpu+sum(t['seconds'] for t in remaining if not t['gpu']) <= CAPS['cpu_seconds'] and
            used_bytes+CAPS['source_bytes']+CAPS['job_bytes'] <= CAPS['storage_bytes'])
