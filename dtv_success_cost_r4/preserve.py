"""Lineage-correct independent finalization; original transfer verifier reused."""
import argparse
import json
import time
from dtv_success_cost.common import *
from dtv_success_cost.preserve import inventory,make_archive
from dtv_success_cost_r4.common import recovery_gate

def archive(c,run):
    from dtv_success_cost_r4.accept import accept_grid,accounting
    if run!=run_namespace(c):raise RuntimeError('wrong study run')
    if not (run/'COMPUTE-COMPLETE.json').exists():raise RuntimeError('compute incomplete')
    read_seal(run/'analysis','analysis');_,accepted=accept_grid(c,run);allocation=accounting(run,c,True)
    location=run/'final-preservation'
    if location.exists():raise RuntimeError('final preservation namespace already exists; retain archive/partials')
    roots=dict(source=ROOT,run=run)
    # Package closure only, not unrelated repository/history or other studies.
    rows=[]
    for r in load(DOC/'PACKAGE-MANIFEST.json')['files']:
        rows.append(dict(path='source/'+r['path'],source=str(ROOT/r['path']),bytes=r['bytes'],sha256=r['sha256']))
    rows.append(dict(path='source/PACKAGE-MANIFEST.json',source=str(DOC/'PACKAGE-MANIFEST.json'),bytes=(DOC/'PACKAGE-MANIFEST.json').stat().st_size,sha256=sha(DOC/'PACKAGE-MANIFEST.json')))
    rows+=inventory(dict(run=run))
    for i,r in enumerate(c['preservation_inputs']):
        if sha(r['path'])!=r['sha256']:raise RuntimeError('reused model preservation binding')
        rows.append(dict(path=f'reused-models/{i:02d}-'+Path(r['path']).name,source=r['path'],bytes=r['bytes'],sha256=r['sha256']))
    if sum(r['bytes'] for r in rows)+2048*len(rows)+10240>c['archive_bytes']:raise RuntimeError('full archive payload/header reservation exhausted')
    location.mkdir();start=time.perf_counter();info=make_archive(location/'final.tar',rows)
    if info['bytes']>c['archive_bytes']:raise RuntimeError('complete archive ceiling; evidence retained')
    request=dict(study='DTV-EFF1',run=str(run),remote_archive=str(location/'final.tar'),archive=info,inventory=rows,
                 acceptance=accepted,allocation=allocation,bindings_sha256=sha(DOC/'BINDINGS.json'),package_sha256=sha(DOC/'PACKAGE-MANIFEST.json'),cohort_sha256=sha(DOC/'COHORT.json'),archive_wall_seconds=time.perf_counter()-start)
    write(location/'BACKUP-REQUEST.json',request);return request

def archive_bounded(c,run):
    # Host-only POSIX signal interrupts inventory, tar, hashing and readback,
    # not just a per-member estimate. It never retries or deletes a partial.
    import signal
    def expired(*args):raise TimeoutError('7200-second host preservation deadline; retain evidence, no retry')
    previous=signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,7200)
    try:return archive(c,run)
    except Exception as e:
        target=Path(run)/'ARCHIVE-FAILURE.json'
        if not target.exists():write(target,dict(error=repr(e),automatic_retry=False,partials_retained=True))
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',type=Path,required=True);a=p.parse_args()
    c,r=recovery_gate(a.approval)
    print(json.dumps(archive_bounded(c,run_namespace(c)),default=str))
if __name__=='__main__':main()
