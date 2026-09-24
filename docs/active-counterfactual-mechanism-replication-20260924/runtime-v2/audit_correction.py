"""Preparation-only exact scope/diff receipt; no cluster, data or model access."""
import common as c
import difflib
import subprocess

def main():
    old=c.ROOT.parent/'runtime-v1'
    source=c.read(old/'SOURCE-MANIFEST.json')
    for name,h in source['files'].items():c.require(c.sha(c.REPO/name)==h,'Reviewed source/export member changed')
    changed=[];same=[];added=[];diff=[]
    for path in sorted(list(c.ROOT.glob('*.py'))+list(c.ROOT.glob('*.sh'))):
        prior=old/path.name
        before=prior.read_text(encoding='utf8').splitlines(keepends=True) if prior.exists() else []
        after=path.read_text(encoding='utf8').splitlines(keepends=True)
        item=dict(name=path.name,sha256=c.sha(path))
        if prior.exists():
            item['prior_sha256']=c.sha(prior)
            (same if c.sha(prior)==c.sha(path) else changed).append(item)
        else:added.append(item)
        diff.extend(difflib.unified_diff(before,after,fromfile='runtime-v1/'+path.name if prior.exists() else '/dev/null',tofile='runtime-v2/'+path.name))
    c.require({r['name'] for r in changed}=={'dispatch.py','worker.py','acceptance.py','analysis.py','bounded_run.py','seal_package.py'},'Narrow allowed changes only')
    bindings={}
    for name in ('INPUT-BINDINGS.json','ROLES.json','MODEL-REUSE.json','CONTROLLER-RUNTIME.json','RECONCILIATION-LIVE.json','RECONCILIATION.json','REPORTING-CONTRACT.json','COST-FORECAST.json','FOOTPRINT.json'):
        c.require(c.sha(old/name)==c.sha(c.ROOT/name),'Frozen metadata/resource binding changed');bindings[name]=c.sha(c.ROOT/name)
    # Git history itself is also unchanged; only the new runtime directory is permitted.
    names=subprocess.check_output(['git','diff','--name-only','bb181cc6b6c60770898afacdcca3fb9e604c90c1'],cwd=c.REPO,text=True).splitlines()
    c.require(not names,'Tracked reviewed/historical files changed')
    with (c.ROOT/'SOURCE-DIFF.patch').open('xb') as f:f.write(''.join(diff).encode('utf8'))
    c.write(c.ROOT/'SCOPE-AUDIT.json',dict(reviewed_commit='bb181cc6b6c60770898afacdcca3fb9e604c90c1',
       old_source_manifest_sha256=c.sha(old/'SOURCE-MANIFEST.json'),old_export_sha256=c.sha(old/'SOURCE-PACKAGE.tar'),
       prior_manifest_members_unchanged=len(source['files']),tracked_history_unchanged=True,changed=changed,unchanged=same,added=added,
       carried_bindings=bindings,diff_sha256=c.sha(c.ROOT/'SOURCE-DIFF.patch'),
       grid_sha256=c.sha(c.PROPOSAL/'GRID.json'),protocol_sha256=c.sha(c.PROPOSAL/'PROTOCOL.json'),
       historical_initializer_sha256=c.sha(c.REPO/'cluster/prometheus/pusht_fresh_initialization.py'),
       inherited_verifier_sha256=c.sha(c.OLD/'verify.py'),execution_enabled=False))
    print(c.json.dumps(dict(changed=[x['name'] for x in changed],unchanged=len(same),added=[x['name'] for x in added],science_changed=False)))
if __name__=='__main__':main()
