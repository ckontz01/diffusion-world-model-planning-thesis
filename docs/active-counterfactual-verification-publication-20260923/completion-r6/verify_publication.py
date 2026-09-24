"""Read-only checks of publication arithmetic and preserved metadata; no new analysis."""
import hashlib, json, time
from pathlib import Path

start = time.monotonic()
here = Path(__file__).resolve().parent
ssd = Path('D:/THESIS-BACKUPS/active-counterfactual-verification-pilot-v1/run-c2c6fcbe8c41fed2')
def read(name):
    return json.loads((here / name).read_text(encoding='utf8'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
r = read('REPORT.json')
s = read('SUMMARY.json')
c = read('CAMPAIGN-ACCOUNTING.json')
p = read('PRESERVATION.json')
req = json.loads((ssd / 'REQUEST.json').read_text())
gate = read('BACKUP-VERIFIED.json')
assert sha(here / 'REPORT.json') == s['report_sha256'] == req['members']['run/analysis/REPORT.json']['sha256']
assert sha(ssd / 'REQUEST.json') == p['request_sha256']
assert sha(here / 'BACKUP-VERIFIED.json') == sha(ssd / 'BACKUP-VERIFIED.json') == p['backup_receipt_sha256']
assert gate['status'] == 'VERIFIED' and gate['archive'] == p['archive_sha256'] == req['sha256']
assert gate['members'] == len(req['members']) == 3308
assert gate['bytes'] == (ssd / 'final.tar').stat().st_size == 814663680
arms = r['controls']
refs, rows = r['source_ids'], r['binary_outcomes_by_source']
assert len(refs) == len(set(refs)) == len(rows) == 32 and len(arms) == 8
assert r['bootstrap_seed'] == 94301 and r['resamples'] == 10000
for i, arm in enumerate(arms):
    assert sum(row[i] for row in rows) / 32 == r['success_mean'][arm]
    chosen = [x for x in r['chosen_branches_and_endpoints'] if x['control'] == arm]
    assert len(chosen) == 32
    assert sum(x['steps'] for x in chosen) == s['decisions'][arm]['steps_sum']
for name, v in r['primary_comparisons'].items():
    arm = name.removeprefix('active-minus-')
    effects = [row[arms.index('active')] - row[arms.index(arm)] for row in rows]
    assert v['source_effects'] == effects and v['mean'] == sum(effects) / 32
    assert (v['gains'], v['losses'], v['ties']) == (effects.count(1), effects.count(-1), effects.count(0))
for arm, effects in r['supporting_active_minus'].items():
    assert effects == [row[arms.index('active')] - row[arms.index(arm)] for row in rows]
    assert sum(effects) / 32 == s['supporting_comparisons'][arm]['mean']
assert read('ALL-CHOICES-AND-ENDPOINTS.json') == r['chosen_branches_and_endpoints']
assert read('ALL-PREDICTIVE-DIAGNOSTICS.json') == r['observed_prefix_predictive_diagnostics']
assert c['campaign_allocations'] == len(c['allocations']) == 340
assert c['successful_unique_tasks'] == 339 and c['gpu_seconds'] == 19365 and c['cpu_stage_seconds'] == 52
resources = s['resources']
assert resources['all_successful_workers']['allocation_seconds'] == 19342 + 52
assert sum(resources[a]['counts']['physical_steps'] for a in arms) == 31735
assert resources['collection']['counts']['physical_steps'] == 167528
assert resources['all_successful_workers']['counts']['physical_steps'] == 199263
assert s['bootstrap_rerun'] is False and s['model_or_physics_invoked'] is False
print(json.dumps({'status':'PASSED', 'unix':time.time(), 'wall_seconds':time.monotonic()-start,
    'scope':'Read-only publication arithmetic and hashes; not a new bootstrap, experiment, transfer or whole-archive verification cycle',
    'sources':32, 'arms':8, 'choices':256, 'successful_tasks':339, 'attempts':340,
    'report_sha256':s['report_sha256'], 'archive_sha256':p['archive_sha256'],
    'publication_generator_note':'RESULTS-20260924.md includes editorial scope notes added after generation; sealed REPORT.json is unmodified'}, sort_keys=True, indent=2))
