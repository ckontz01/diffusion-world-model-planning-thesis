"""Read-only document QA; no analyzer/bootstrap/model/endpoint-array execution."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
read = lambda n: json.loads((root / n).read_text(encoding='utf-8'))
p = read('FINAL-AGGREGATE-PROJECTION.json')
a = read('FINAL-ACCOUNTING.json')
rows = read('FINAL-EPISODES.json')
report = (root / 'FINAL-REPORT.md').read_text(encoding='utf-8')
effects = (root / 'FINAL-SOURCE-EFFECTS.md').read_text(encoding='utf-8')
assert len(rows) == 12288 and len(p['source_effects']) == 512 and len(p['strata']) == 24
assert len({(r['reference'],r['seed'],r['family'],r['populations'],r['horizon']) for r in rows}) == 12288
assert read('FINAL-PUBLICATION-CHECKS.json')['passed']
for effect in p['source_effects']:
    assert f"| {effect['reference']} |" in effects
for key, value in p['absolute'].items():
    assert f"{100*value['mean']:.4f}%" in report
for value in [p['primary']] + list(p['secondary'].values()):
    for number in [value['mean']] + value['interval95']:
        # Permit only floating-point tie ambiguity at the displayed fourth
        # decimal; sealed means can differ from exact rational values by 1 ULP.
        printed = [f'{100*number+epsilon:+.4f}'.replace('-', '−') for epsilon in (0,1e-10,-1e-10)]
        assert any(value in report for value in printed), printed
for c in a['configurations']:
    for value in [c['successes'],c['delivered_actions']] + [c['planning_totals'][k] for k in ('stages','cost_calls','candidate_trajectories','predicted_primitive_steps')]:
        assert f'{value:,}' in report
    for k in ('proposer_network_forward_calls','lewm_encode_calls','local_goal_generator_calls'):
        assert f"{c['derived_model_calls'][k]:,}" in report
    for value in [c['episode_timing_totals']['complete_episode_seconds']] + [c['planning_totals'][k] for k in ('seconds','proposal_seconds','refinement_total_seconds','scoring_seconds','bank_hash_seconds')]:
        assert f'{value:,.3f}' in report
assert a['compute_complete']['gpu_seconds'] == 138753 and a['compute_complete']['cpu_seconds'] == 161
assert a['backup']['recovery_verified'] and a['recovery_session_complete']['complete']
assert not a['backup']['first_transfer_succeeded']
manifest={}
for path in sorted(root.iterdir()):
    if path.is_file():
        with path.open('rb') as stream:
            manifest[path.name]={'bytes':path.stat().st_size,'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}
with (root / 'PUBLICATION-MANIFEST.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(dict(passed=True,research_execution=False,files=manifest,checks=['All report arm rates, contrast estimates/intervals, counts, calls and timing cells match preserved completed aggregate projection','Complete 512-source / 24-stratum / 12288-identity disclosure','Verified recovery mapping and original failure retained']),stream,indent=2,sort_keys=True)
    stream.write('\n')
print(json.dumps(dict(publication_qa_passed=True,files=len(manifest),episodes=len(rows),sources=512,strata=24)))
