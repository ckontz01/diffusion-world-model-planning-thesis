"""Complete logical-byte reservations, including seals, logs and tar metadata."""
import common as c
GROUP=1_000_000_000
LOG_PER_STREAM=4096
MAX_MEMBERS=120_000
TAR_OVERHEAD=MAX_MEMBERS*3072+10240

def footprint(jobs):
    eval_bytes=sum(s['byte_cap'] for s in jobs if s['gpu'])
    fits=sum(s['byte_cap'] for s in jobs if s['stage']=='fitting')
    analysis=sum(s['byte_cap'] for s in jobs if s['stage']=='analysis')
    logs=len(jobs)*4*LOG_PER_STREAM
    parts=dict(fitting_with_seals=fits,analysis_with_seal=analysis,all_four_log_streams=logs,
               source_and_reused_inputs=40_000_000,controller_claims_scheduler_faults=150_000_000,
               archive_member_manifest_request_receipts=100_000_000)
    c.require(sum(parts.values())<=GROUP,'Complete non-evaluation footprint')
    live=eval_bytes+GROUP
    archive=live+TAR_OVERHEAD
    # Remote live+archive; SSD live/package allowance + partial/final (never both after rename),
    # and another full retained failed transfer reserve. No deletion needed to fit.
    inclusive=live+3*archive+1_000_000_000
    cap=c.caps()
    c.require(live<=cap['live_bytes'] and archive<=cap['archive_bytes'] and inclusive<=cap['inclusive_bytes'],'Full future inclusive footprint')
    return dict(components=parts,nonworker_total=sum(parts.values()),nonworker_headroom=GROUP-sum(parts.values()),
                evaluation_with_seals=eval_bytes,live=live,archive=archive,inclusive=inclusive,
                max_members=MAX_MEMBERS,tar_metadata_reservation=TAR_OVERHEAD,hidden_files_count=True,failures_retained=True)

def check(source,control,run,jobs,finished):
    expected=footprint(jobs); keys={s['key']:s for s in jobs}
    eval_live=0; group=c.bytes_in(source)+c.bytes_in(control); count=0
    for p in c.files(run):
        rel=p.relative_to(run); count+=1
        if rel.parts[0]=='final-preservation': continue
        spec=keys.get(rel.parts[0]); size=p.stat().st_size
        if spec and spec['gpu']: eval_live+=size
        else: group+=size
    remaining=sum(s['byte_cap'] for s in jobs if s['gpu'] and s['key'] not in finished and not (run/s['key']).exists())
    # Started workers reserve their full cap, not just bytes written so far.
    for s in jobs:
        if s['gpu'] and (run/s['key']).exists():
            actual=c.bytes_in(run/s['key']); c.require(actual<=s['byte_cap'],'Complete worker bytes')
            if s['key'] not in finished: remaining+=s['byte_cap']-actual
    c.require(group<=GROUP and eval_live+remaining+GROUP<=c.caps()['live_bytes'],'Live + all future bytes')
    c.require(count+len(list(c.files(source)))+len(list(c.files(control)))<=MAX_MEMBERS,'Archive member count reserve')
    c.require(c.bytes_in(control)<=150_000_000,'Control/log evidence cap (no truncation or deletion)')
    return dict(group_bytes=group,evaluation_bytes=eval_live,remaining_worker_bytes=remaining,full=expected)
