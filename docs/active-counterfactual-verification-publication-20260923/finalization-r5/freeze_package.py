"""Exclusive freeze of tested finalization-only technical recovery."""
from pathlib import Path
import io,sys,tarfile,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-verification-20260923/finalization-r5'
sys.path.insert(0,str(ROOT))
import r5_core as r
import transport5 as t
def main():
    r.require(not (ROOT/'SOURCE-MANIFEST.json').exists(),'Never refreeze')
    entries=r.lines(ROOT/'ATTEMPTS.jsonl');finished=[v for v in entries if v['state']=='finished']
    r.require([v['label'] for v in entries if v['state']=='started']==[v['label'] for v in finished],'Every synthetic attempt charged')
    last=finished[-1];r.require(last['returncode']==0 and 'Ran 11 tests' in last['stderr'] and last['stderr'].rstrip().endswith('OK'),'Complete11-test pass')
    total=sum(v.get('wall_seconds',0) for v in entries)+sum(v.get('wall_seconds',0) for folder in ('control-r2','control-r3','control-r4') for v in r.lines(ROOT.parent/folder/'ATTEMPTS.jsonl'))
    r.require(total<7200,'Cumulative preparation cap')
    for folder in ('bindings-r1','control-r2','control-r3','control-r4'):
        old=ROOT.parent/folder
        for n,h in r.read(old/'SOURCE-MANIFEST.json')['files'].items():r.require(r.sha((r.REPO/n) if folder=='bindings-r1' else old/n)==h,'Unchanged old closure')
    r.write(ROOT/'FREEZE-RECEIPT.json',{'unix':time.time(),'tests':finished,'tests_passed':11,'test_attempts_sha256':r.sha(ROOT/'ATTEMPTS.jsonl'),
        'cumulative_test_wall_seconds':total,'original_science_unchanged':True,'research_calls':0,'test_allocations':0,'new_jobs_authorized':0,
        'authority_commit':r.read(ROOT/'CONTRACT.json')['authority_commit'],'freeze_script_sha256':r.sha(Path(__file__))})
    files={p.name:r.sha(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name!='ATTEMPTS.jsonl'}
    r.write(ROOT/'SOURCE-MANIFEST.json',{'schema':'ACV0-finalization-only-r5-source','files':files,'original_scientific_manifest':r.SCIENCE_MANIFEST})
    manifest=r.sha(ROOT/'SOURCE-MANIFEST.json');binding=r.binding(manifest)
    template={'schema':'ACV0-finalization-only-r5','authorized':False,'instruction':'','binding':binding};r.write(ROOT/'APPROVAL-TEMPLATE.json',template)
    members={};archive=ROOT/'source-export.tar'
    with archive.open('xb') as out:
        with tarfile.open(fileobj=out,mode='w',format=tarfile.PAX_FORMAT) as tar:
            for n in sorted(set(files)|{'SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json'}):
                data=(ROOT/n).read_bytes();info=tarfile.TarInfo(n);info.size=len(data);info.mode=0o644;info.mtime=0
                tar.addfile(info,io.BytesIO(data));members[n]={'bytes':len(data),'sha256':r.hashlib.sha256(data).hexdigest()}
    trans={'bytes':archive.stat().st_size,'sha256':r.sha(archive),'members':members,'control_manifest':manifest}
    r.write(ROOT/'SOURCE-TRANSPORT.json',trans);t.verify_archive(archive,trans)
    r.write(HERE/'EXECUTION-APPROVAL.json',dict(template,authorized=True,instruction=t.instruction()))
    r.write(HERE/'AUTHORIZATION-PROVENANCE.json',{'basis':'Direct standing technical-recovery authority at ace242ee5ea14af284401ad857fc3a49b30e1b58; not a new signature',
        'scope':'One metadata-only acceptance, one archive, one native SSD transfer. Zero research jobs, replacements, reanalysis or scientific changes.',
        'control_manifest':manifest,'enabled_approval_sha256':r.sha(HERE/'EXECUTION-APPROVAL.json'),'full_binding':binding,
        'original_false_templates_preserved':True,'all_original_stops_preserved':True,'original_fault_queue_stdout_preserved':False})
    r.write(HERE/'FROZEN-PACKAGE.json',{'control_manifest':manifest,'approval_sha256':r.sha(HERE/'EXECUTION-APPROVAL.json'),
        'archive':trans,'cumulative_test_wall_seconds':total,'tests_passed':11,'execution_occurred':False})
    payload={'archive':t.base64.b64encode(archive.read_bytes()).decode(),'approval':t.base64.b64encode((HERE/'EXECUTION-APPROVAL.json').read_bytes()).decode(),'delivery':{},'provenance':r.read(HERE/'AUTHORIZATION-PROVENANCE.json')}
    envelope=t.envelope(t.STAGE,r.canonical(payload));r.require(len(envelope)<8000000,'Actual full stage envelope fits')
    print(r.json.dumps({'manifest':manifest,'approval':r.sha(HERE/'EXECUTION-APPROVAL.json'),'source_archive_bytes':trans['bytes'],
        'source_archive_sha256':trans['sha256'],'members':len(members),'cumulative_test_seconds':total,'stage_envelope_bytes':len(envelope)},indent=2))
if __name__=='__main__':main()
