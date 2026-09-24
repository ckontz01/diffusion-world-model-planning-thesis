from pathlib import Path
import io,sys,tarfile,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]/'docs/active-counterfactual-verification-20260923/preservation-r6';sys.path.insert(0,str(ROOT))
import archive6 as a
def main():
    assert not (ROOT/'SOURCE-MANIFEST.json').exists()
    entries=a.lines(ROOT/'ATTEMPTS.jsonl');finished=[x for x in entries if x['state']=='finished']
    assert [x['label'] for x in entries if x['state']=='started']==[x['label'] for x in finished]
    assert finished[-1]['returncode']==0 and 'Ran 6 tests' in finished[-1]['stderr'] and finished[-1]['stderr'].rstrip().endswith('OK')
    total=sum(x.get('wall_seconds',0) for x in entries)+sum(x.get('wall_seconds',0) for folder in ('control-r2','control-r3','control-r4','finalization-r5') for x in a.lines(ROOT.parent/folder/'ATTEMPTS.jsonl'))
    assert total<7200
    a.write(ROOT/'FREEZE-RECEIPT.json',{'unix':time.time(),'tests':finished,'cumulative_test_seconds':total,'research_calls':0,'new_jobs':0})
    files={p.name:a.sha(p) for p in ROOT.iterdir() if p.is_file() and p.name!='ATTEMPTS.jsonl'}
    a.write(ROOT/'SOURCE-MANIFEST.json',{'schema':'ACV0-archive-only-r6-source','files':files})
    b=a.binding();template={'schema':'ACV0-archive-only-r6','authorized':False,'binding':b};a.write(ROOT/'APPROVAL-TEMPLATE.json',template)
    members={};archive=ROOT/'source-export.tar'
    with archive.open('xb') as stream:
        with tarfile.open(fileobj=stream,mode='w') as tar:
            for n in sorted(set(files)|{'SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json'}):
                data=(ROOT/n).read_bytes();info=tarfile.TarInfo(n);info.size=len(data);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(data));members[n]={'bytes':len(data),'sha256':a.hashlib.sha256(data).hexdigest()}
    trans={'bytes':archive.stat().st_size,'sha256':a.sha(archive),'members':members};a.write(ROOT/'SOURCE-TRANSPORT.json',trans)
    a.write(HERE/'EXECUTION-APPROVAL.json',dict(template,authorized=True))
    a.write(HERE/'FROZEN-PACKAGE.json',{'binding':b,'approval_sha256':a.sha(HERE/'EXECUTION-APPROVAL.json'),'transport':trans,'cumulative_test_seconds':total})
    print(a.json.dumps({'binding':b,'approval_sha256':a.sha(HERE/'EXECUTION-APPROVAL.json'),'archive_bytes':trans['bytes'],'archive_sha256':trans['sha256'],'cumulative_test_seconds':total},indent=2))
if __name__=='__main__':main()
