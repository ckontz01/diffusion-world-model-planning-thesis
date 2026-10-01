"""Independent authentication of the original closure and dated R1 resolution."""
import os
from pathlib import Path
from dtv_success_cost.common import DOC, ROOT, gate, load, sha, read_seal, run_namespace

RECOVERY=Path(__file__).resolve().parents[1]
MANIFEST=RECOVERY/'docs/dtv-success-cost-publication-20261001/recovery-r1/PACKAGE-MANIFEST.json'
STOP_SHA='b4eef86b148e1badb99a1f69c5061e4459210b2bd9874fe3bb2538901cec638d'
LEDGER_SHA='be97ca02e9cdb8f58b164210820910db09f867a87f318f51f46f2cc52c05c81e'
SEAL_SHA='1e199f70d9b35d98500b50571de68850b584771c7dd6d21ef87af8a7b1452fe7'
AUTH_SHA='f7754ffea9db87a8813f8f709c84d2421e3cba14e39a26f8ba8a3bbba1c69f63'
ROW=['312920','dtveff1-preflight','COMPLETED','0:0','178','cpu=4,mem=8G,node=1','gpu03']

def verify_resolution(run,r):
    run=Path(run);location=run/'recovery-r1'
    if (location/'STOP-R1.json').exists():raise RuntimeError('new unresolved R1 STOP; no restart or finalization')
    if sha(run/'STOP.json')!=STOP_SHA or sha(run/'DISPATCH.jsonl')!=LEDGER_SHA:raise RuntimeError('original STOP/ledger changed')
    read_seal(run/'preflight','preflight')
    if sha(run/'preflight/SEAL.json')!=SEAL_SHA or sha(run/'preflight/INPUT-AUTHENTICATION.json')!=AUTH_SHA:
        raise RuntimeError('carried preflight seal/authentication changed')
    resolution=load(location/'STOP-RESOLUTION.json')
    expected=dict(original_stop_sha256=STOP_SHA,original_dispatch_sha256=LEDGER_SHA,
                  preflight_seal_sha256=SEAL_SHA,preflight_input_sha256=AUTH_SHA,
                  terminal_row=ROW,recovery_manifest_sha256=r['recovery_manifest_sha256'],
                  authorization_sha256=r['authorization_sha256'],cpu_seconds=178,gpu_seconds=0,
                  successful_preflight_recomputed=False,scientific_changes=False)
    if any(resolution.get(k)!=v for k,v in expected.items()):raise RuntimeError('dated control STOP resolution differs')
    if not isinstance(resolution.get('observed_unix'),(float,int)):raise RuntimeError('resolution lacks actual timestamp')
    return resolution

def recovery_gate(approval):
    r=load(approval)
    if r.get('study')!='DTV-EFF1-R1' or r.get('execute') is not True:raise RuntimeError('R1 execution disabled')
    if sha(MANIFEST)!=r.get('recovery_manifest_sha256'):raise RuntimeError('R1 source manifest changed')
    for row in load(MANIFEST)['files']:
        p=(RECOVERY/row['path']).resolve()
        if not p.is_relative_to(RECOVERY) or not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:
            raise RuntimeError('R1 member authentication failed')
    authority=Path(r['authorization_record'])
    if sha(authority)!=r['authorization_sha256']:raise RuntimeError('R1 authority changed')
    a=load(authority)
    keys=('study','execute','recovery_manifest_sha256','worker_approval','worker_approval_sha256','run',
          'remaining_gpu_workers','remaining_cpu_analysis','carried_preflight_allocation',
          'carried_cpu_seconds','additional_research_attempts','scientific_changes','resource_expansion')
    if any(a.get(k)!=r.get(k) for k in keys):raise RuntimeError('R1 authorization/contract mismatch')
    if (r['remaining_gpu_workers'],r['remaining_cpu_analysis'],r['carried_preflight_allocation'],r['carried_cpu_seconds'],
        r['additional_research_attempts'],r['scientific_changes'],r['resource_expansion'])!=(2880,1,'312920',178,0,False,False):
        raise RuntimeError('finite control-only scope changed')
    if sha(r['worker_approval'])!=r['worker_approval_sha256'] or r['worker_approval_sha256']!='8768e82f12746010f460d0e45ed29d58dc21e98375c04fb574cf722116d34c03':
        raise RuntimeError('original worker approval changed')
    c=gate(Path(r['worker_approval']))
    if str(ROOT)!=r['scientific_source'] or str(RECOVERY)!=r['recovery_source'] or str(run_namespace(c))!=r['run']:
        raise RuntimeError('source/run namespace changed')
    verify_resolution(run_namespace(c),r)
    return c,r

