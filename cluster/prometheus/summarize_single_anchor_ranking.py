"""Render descriptive reporting inputs from the verified complete backup only.

No changes to frozen inference, analysis, endpoints, confidence intervals or data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import tarfile

ARCHIVE_SHA = 'a25fe9f329605129ffdbc01ef116b19b6fec5706c2cd85a9103ab2b3528ad95b'
ANALYSIS_SHA = '1ee1ffb3123a44db63a4be3cb6c568554f8c0e3496f6fe7b666c1f5815f72959'
MANIFEST_SHA = 'f217b032e85fdd888fad64ad8dfbf2ab1437f5072237641fa1ab061f85f2f5f8'


def digest(stream):
    h=hashlib.sha256()
    for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def describe(values):
    return dict(min=min(values),median=statistics.median(values),max=max(values),sum=sum(values))


def main(archive, out):
    with archive.open('rb') as stream:assert digest(stream)==ARCHIVE_SHA
    with tarfile.open(archive,'r') as tar:
        encoded=tar.extractfile('BACKUP-MANIFEST.json').read()
        assert hashlib.sha256(encoded).hexdigest()==MANIFEST_SHA
        manifest=json.loads(encoded)
        members={m.name:m for m in tar.getmembers()}
        assert len(members)==len(tar.getmembers()) and set(members)==set(manifest['files'])|{'BACKUP-MANIFEST.json'}
        for name,pin in manifest['files'].items():
            assert members[name].isfile() and members[name].size==pin['bytes']
            assert digest(tar.extractfile(name))==pin['sha256']
        data=tar.extractfile('run/analysis/ANALYSIS.json').read()
        assert hashlib.sha256(data).hexdigest()==ANALYSIS_SHA
        a=json.loads(data)
        assert a['all_passed'] and a['runs']==64 and a['logical_branches']==512
        reports=[json.load(tar.extractfile(name)) for name in manifest['files']
                 if name.startswith('run/ref-') and name.endswith('/REPORT.json')]
        assert len(reports)==64 and all(r['all_technical_checks_passed'] for r in reports)
    arms={}
    for arm in ('continuation','immediate'):
        points=[x[arm] for x in a['anchors']]
        calls=[c for r in reports if r['repeat']==0 for row in r['rows'] if row['arm']==arm for c in row['calls']]
        postcalls=[c for r in reports if r['repeat']==0 for row in r['rows'] if row['arm']==arm
                   for c in row['calls'] if c['at']>=row['anchor']]
        arms[arm]=dict(success=sum(x['success'] for x in points),first_success=sum(x['first_success'] for x in points),
            first_terminal=sum(x['first_terminal'] for x in points),
            first_margin_mean=statistics.mean(x['first_margin'] for x in points),
            handoff_active=sum(x['handoff_margin'] is not None for x in points),
            active_handoff_margin_mean=statistics.mean(x['handoff_margin'] for x in points if x['handoff_margin'] is not None),
            full_margin_mean=statistics.mean(x['closest_margin'] for x in points),
            delivered=sum(x['delivered'] for x in points),planning_calls_including_prefix=len(calls),
            planning_calls_after_anchor=len(postcalls),native_truncated=sum(x['native_truncated'] for x in points),
            budget_exhausted=sum(x['budget_exhausted'] for x in points))
    pairs=[x for x in a['anchors'] if all(x[k]['handoff_margin'] is not None for k in arms)]
    handoff=dict(pairs=len(pairs),paired_improvement=statistics.mean(x['continuation']['handoff_margin']-x['immediate']['handoff_margin'] for x in pairs),
                 interpretation='Descriptive survivor-pair subset only; not the primary estimand.')
    refs=[]
    for r in a['analysis']['reference_effects']:
        points=[x for x in a['anchors'] if x['reference']==r['reference']]
        refs.append(dict(r,first_margin_improvement=statistics.mean(x['continuation']['first_margin']-x['immediate']['first_margin'] for x in points)))
    horizons=[]
    for h in (75,150):
        points=[x for x in a['anchors'] if x['horizon']==h]
        horizons.append(dict(horizon=h,continuation_success=sum(x['continuation']['success'] for x in points),
            immediate_success=sum(x['immediate']['success'] for x in points),points=len(points),
            first_margin_improvement=statistics.mean(x['continuation']['first_margin']-x['immediate']['first_margin'] for x in points),
            full_margin_improvement=statistics.mean(x['continuation']['closest_margin']-x['immediate']['closest_margin'] for x in points)))
    discordant=[dict(reference=x['reference'],horizon=x['horizon'],anchor=x['anchor'],
        continuation_success=x['continuation']['success'],immediate_success=x['immediate']['success'])
        for x in a['anchors'] if x['continuation']['success']!=x['immediate']['success']]
    allocations=[x for x in manifest['slurm_rows'] if '.' not in x['JobID']]
    gpu=[x for x in allocations if x['JobID'] not in ('301088','301090','301157')]
    batch=[x for x in manifest['slurm_rows'] if x['JobID'].endswith('.batch') and x['JobID'].split('.')[0] in {x['JobID'] for x in gpu}]
    def rss(value):
        units={'K':1024,'M':1024**2,'G':1024**3,'T':1024**4}
        return int(float(value[:-1])*units[value[-1]]) if value else None
    calls=[c for r in reports for row in r['rows'] for c in row['calls']]
    result=dict(archive_verified=True,archive_sha256=ARCHIVE_SHA,archive_bytes=archive.stat().st_size,
        archive_member_files_verified=len(manifest['files']),manifest_sha256=MANIFEST_SHA,analysis_sha256=ANALYSIS_SHA,
        frozen_analysis=a['analysis'],arms=arms,handoff=handoff,reference_effects=refs,horizons=horizons,discordant_success=discordant,
        first_margin_reference_positive=sum(x['first_margin_improvement']>0 for x in refs),
        first_margin_improvement=statistics.mean(x['first_margin_improvement'] for x in refs),
        resources=dict(run_bytes=manifest['run_bytes'],gpu_allocation_seconds=manifest['gpu_allocation_seconds'],
            gpu_job_seconds=describe([int(x['ElapsedRaw']) for x in gpu]),
            gpu_allocated_cpu_seconds=sum(int(x['ElapsedRaw'])*int(x['AllocCPUS']) for x in gpu),
            batch_maxrss_bytes=describe([rss(x['MaxRSS']) for x in batch]),
            pytorch_peak_allocated_bytes=describe([r['gpu_peak_allocated_bytes'] for r in reports]),
            pytorch_peak_reserved_bytes=describe([r['gpu_peak_reserved_bytes'] for r in reports]),
            worker_wall_seconds=describe([r['wall_seconds_including_construction'] for r in reports]),
            model_construction_seconds=describe([r['model_construction_seconds'] for r in reports]),
            physical_steps=sum(x['steps'] for x in a['counts']),planning_calls=len(calls),
            continuation_calls=sum(c['diagnostics']['delta']>=30 for c in calls),
            first_only_calls=sum(c['diagnostics']['delta']<30 for c in calls),
            cpu_jobs=[x for x in allocations if x not in gpu]),
        slurm_rows=manifest['slurm_rows'])
    with out.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ('slurm_rows','reference_effects','frozen_analysis')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();main(args.archive,args.out)
