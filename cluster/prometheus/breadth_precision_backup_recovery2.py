"""WSL companion consuming a fresh native-Windows volume lease; no interop calls."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time
import breadth_precision_contract as p
import candidate_value_contract as ct
import breadth_precision_recovery2 as r
from breadth_precision_backup_recovery import probe, write_control
from candidate_value_backup import once, verify_archive

LOCAL_CONTROL = Path('/mnt/d/THESIS-BACKUPS/cvl-bp1-recovery2-20260917/controls')


def volume_valid(value, approval_sha, now):
    return (value.get('approval_sha256') == approval_sha and value.get('source_sha256') == r.SOURCE_SHA and
            value.get('native_windows') is True and value.get('volume_id') == r.VOLUME_ID and
            value.get('volume_label') == 'THESIS_SSD' and
            value.get('free_bytes', 0) >= p.CAPS['backup_free_bytes'] and
            0 <= now-value.get('utc', 0) <= 90)


def external_check(destination, approval_sha):
    destination = Path(destination)
    p.require(destination == Path('/mnt/d/THESIS-BACKUPS')/p.VERSION/('run-'+r.SOURCE_SHA[:16]),
              'Exact external backup destination')
    p.require(not (LOCAL_CONTROL/'NATIVE-VOLUME-STOP.json').exists(), 'Native volume check stopped')
    value = ct.json_read(LOCAL_CONTROL/'NATIVE-VOLUME-LIVE.json')
    p.require(volume_valid(value, approval_sha, time.time()), 'Fresh native volume identity and headroom')
    mount = subprocess.check_output(['findmnt','-n','-o','TARGET','--target','/mnt/d'],
                                    universal_newlines=True,timeout=15).strip()
    p.require(mount == '/mnt/d', 'Mounted external SSD required; no laptop fallback')
    free = shutil.disk_usage(destination).free
    p.require(free >= p.CAPS['backup_free_bytes'], '40GB actual external headroom')
    return min(free, value['free_bytes'])


def watch(recovery, recovery_sha):
    recovery = Path(recovery)
    raw = probe('cat '+shlex.quote(str(recovery)))
    p.require(hashlib.sha256(raw).hexdigest() == recovery_sha, 'Exact second recovery approval')
    approval = json.loads(raw); run = Path(approval['run']); control = recovery.parent
    r.overlay_check(Path(__file__).resolve().parent, approval['overlay_sha256'])
    p.require(approval['researcher_approved'] is True and approval['source_sha256'] == r.SOURCE_SHA and
              run.parent == p.RUN_PARENT and run.name == 'run-'+r.SOURCE_SHA[:16] and approval['caps'] == p.CAPS and
              approval['remaining_tasks'] == p.grid()[r.PREFIX:] and approval['external_volume_id'] == r.VOLUME_ID and
              approval['max_additional_replacement_attempts'] == 0, 'Exact second recovery scope')
    destination = Path('/mnt/d/THESIS-BACKUPS')/p.VERSION/run.name
    done = set(); deadline = time.monotonic()+7*86400
    try:
        free = external_check(destination, recovery_sha)
        p.require(not any((destination/(s+'.tar')).exists() or (destination/(s+'-receipt.json')).exists()
                          for s in ('train','models','evaluation','terminal')), 'No existing future-stage backup')
        for stage, identity in r.BACKUPS.items():
            archive = destination/(stage+'.tar'); receipt = destination/(stage+'-receipt.json')
            p.require(p.sha(archive) == identity['archive'] and p.sha(receipt) == identity['receipt'],
                      'Preserve prior external backups')
            request = probe('cat '+shlex.quote(str(run/('BACKUP-REQUEST-'+stage+'.json'))))
            p.require(hashlib.sha256(request).hexdigest() == identity['request'], 'Exact accepted coverage')
            verify_archive(archive,json.loads(request))
        ct.json_write(destination/'RECOVERY2-BACKUP-CLAIM.json',dict(approval_sha256=recovery_sha,automatic_transfer_retry=False))
        common = dict(approval_sha256=recovery_sha,source_sha256=r.SOURCE_SHA,external_mount='/mnt/d',free_bytes=free)
        write_control(control/'BACKUP-RECOVERY-READY.json',dict(common,
                      archives={s:v['archive'] for s,v in r.BACKUPS.items()},all_prior_backups_verified=True))
        while time.monotonic() < deadline:
            free = external_check(destination,recovery_sha)
            names = ['BACKUP-REQUEST-'+s+'.json' for s in ('train','models','evaluation','terminal')]
            names += ['DISPATCH-FINAL.json','RECOVERY2-STOP.json']
            code = 'import pathlib,json; p=pathlib.Path('+repr(str(run))+'); print(json.dumps({n:(p/n).is_file() for n in '+repr(names)+'}))'
            present = json.loads(probe('python3 -B -c '+shlex.quote(code)))
            if present['RECOVERY2-STOP.json']:
                raise RuntimeError('Second recovery stopped; no automatic restart')
            write_control(control/'BACKUP-LIVE.json',dict(common,free_bytes=free),replace=True)
            for stage in ('train','models','evaluation','terminal'):
                if stage not in done and present['BACKUP-REQUEST-'+stage+'.json']:
                    external_check(destination,recovery_sha)
                    started = time.monotonic()
                    once(run,destination,stage)  # Accepted streaming writer/seal verifier, one attempt.
                    done.add(stage)
                    timing = dict(stage=stage,transfer_and_verification_wall_seconds=time.monotonic()-started,
                                  scientific_payloads_decoded=False,slurm_allocations=0)
                    ct.json_write(destination/(stage+'-recovery2-timing.json'),timing)
                    write_control(control/('BACKUP-TIMING-'+stage+'.json'),timing)
                    write_control(control/'BACKUP-LIVE.json',dict(common,free_bytes=external_check(destination,recovery_sha)),replace=True)
            if present['DISPATCH-FINAL.json']: return
            time.sleep(30)
        raise RuntimeError('Backup lifetime exhausted; no restart')
    except BaseException as exc:
        stop = dict(type=type(exc).__name__,reason='Second backup recovery stopped; inspect technical log',automatic_retry=False)
        try: ct.json_write(destination/'RECOVERY2-BACKUP-STOP.json',stop)
        finally:
            try: write_control(control/'BACKUP-RECOVERY-STOP.json',stop)
            except Exception: pass
        raise
    finally:
        # Native helper has no network or dispatch capability and stops on this local flag.
        try: ct.json_write(LOCAL_CONTROL/'NATIVE-VOLUME-HALT.json',dict(backup_companion_finished=True))
        except Exception: pass


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    for field in ('recovery','recovery-sha'): cli.add_argument('--'+field,required=True)
    args = cli.parse_args(); watch(args.recovery,args.recovery_sha)
