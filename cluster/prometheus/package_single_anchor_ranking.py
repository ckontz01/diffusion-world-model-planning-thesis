"""Export approved Git bytes and their local import closure; no dataset access."""
import argparse
import ast
import hashlib
import io
import json
import subprocess
import tarfile


def git(*args):
    return subprocess.check_output(['git', *args])


def package(approved, support, output):
    files = set(git('ls-tree', '-r', '--name-only', approved).decode().splitlines())
    base = 'cluster/prometheus/'
    pending = [base+n for n in (
        'single_anchor_ranking.py', 'single_anchor_ranking_runner.py',
        'single_anchor_ranking_dispatch.py', 'verify_single_anchor_ranking.py',
        'test_single_anchor_ranking.py', 'gdp_cem_e18_runtime.py',
        'independent_pusht_runtime.py', 'independent_pusht_evaluate.py',
        'independent_pusht_collect.py', 'pusht_fresh_initialization.py',
        'e18_fresh_driver.py')]
    payload = {}
    while pending:
        path = pending.pop()
        if path in payload:
            continue
        data = git('show', approved+':'+path)
        payload[path] = data
        for node in ast.walk(ast.parse(data, filename=path)):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                target = base+name.split('.')[0]+'.py'
                if target in files and target not in payload:
                    pending.append(target)
    extras = [base+'run_single_anchor_ranking.sh', base+'INDEPENDENT-PINNED-INPUTS.json',
              'docs/bottleneck/BRANCH-PILOT-SELECTION.json',
              'docs/bottleneck/receipts/EXTENSION-COMBINED-301071.json']
    extras += sorted(p for p in files if p.startswith('docs/single-anchor-ranking-20260914/'))
    for path in extras:
        payload[path] = git('show', approved+':'+path)
    for name in ('package_single_anchor_ranking.py', 'preflight_single_anchor_ranking.py',
                 'preflight_single_anchor_ranking.sh', 'single_anchor_ranking_host.py',
                 'single_anchor_ranking_dispatch.py', 'test_single_anchor_ranking_host.py'):
        payload[base+name] = git('show', support+':'+base+name)
    for path, data in payload.items():
        if path.endswith('.sh') and b'\r' in data:
            raise ValueError('CR in frozen shell: '+path)
    meta = dict(approved_commit=approved, launch_support_commit=support,
                scientific_source_changed=False, payload_accessed=False,
                source_files=len(payload), dispatcher_interpreter='/usr/bin/python3',
                worker_interpreter='pinned hi-lewm-artifact-py311-cu121-swm006 in approved Apptainer image')
    payload['PACKAGE.json'] = (json.dumps(meta, indent=2, sort_keys=True)+'\n').encode()
    manifest = ''.join(hashlib.sha256(data).hexdigest()+'  '+path+'\n'
                       for path, data in sorted(payload.items())).encode()
    payload['SOURCE-MANIFEST.sha256'] = manifest
    with open(output, 'xb') as destination:
        with tarfile.open(fileobj=destination, mode='w') as archive:
            for path, data in sorted(payload.items()):
                info = tarfile.TarInfo(path)
                info.size, info.mtime, info.mode = len(data), 0, 0o444
                archive.addfile(info, io.BytesIO(data))
    print(json.dumps(dict(source_manifest_sha256=hashlib.sha256(manifest).hexdigest(),
                          protocol_sha256=hashlib.sha256(payload['docs/single-anchor-ranking-20260914/PROTOCOL.md']).hexdigest(),
                          archive_sha256=hashlib.sha256(open(output, 'rb').read()).hexdigest(),
                          files=len(payload)), sort_keys=True))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('approved', 'support', 'out'):
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    package(a.approved, a.support, a.out)
