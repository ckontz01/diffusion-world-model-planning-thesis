// Documentation checks only: no models, datasets, cluster access or experiments.
// Run: node docs/readme-audit-2026-09-07/verify.mjs [repository-directory]
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
const repo = path.resolve(process.argv[2] || process.cwd());
const git = (...args) => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8', maxBuffer: 16000000 });
const sha = text => crypto.createHash('sha256').update(text).digest('hex');
const text = fs.readFileSync(path.join(repo, 'README.md'), 'utf8').replace(/\r\n/g, '\n');
const refs = new Map();
for (const m of text.matchAll(/^\[([^\]]+)\]: (\S+)$/gm)) {
  assert(!refs.has(m[1]), `Duplicate reference: ${m[1]}`);
  refs.set(m[1], m[2]);
}
const used = [...text.matchAll(/\[[^\]\n]+\]\[([^\]\n]+)\]/g)].map(m => m[1]);
for (const id of used) assert(refs.has(id), `Undefined reference: ${id}`);
const cache = new Map();
function source(ref, file) {
  const key = `${ref}:${file}`;
  if (!cache.has(key)) cache.set(key, git('show', key));
  return cache.get(key);
}
const checked = [];
for (const [id, url] of refs) {
  const match = url.match(/^https:\/\/github\.com\/ckontz01\/diffusion-world-model-planning-thesis\/(blob|tree)\/([^/]+)(?:\/([^#]+))?(?:#(.+))?$/);
  assert(match, `Unexpected repository link: ${id}`);
  const [, kind, ref, file, anchor] = match;
  if (id === 'code') { assert.equal(ref, 'independent-pusht-benchmark'); continue; }
  assert.match(ref, /^[0-9a-f]{40}$/, `Unpinned evidence: ${id}`);
  git('cat-file', '-e', `${ref}:${file}`);
  if (kind === 'blob') {
    const body = source(ref, file);
    if (anchor) assert(body.split('\n').some(line => /^#{1,6} /.test(line) && line.replace(/^#{1,6} /, '').trim().toLowerCase().replace(/ /g, '-') === anchor), `Missing anchor: ${id}`);
    checked.push({ id, ref, file, sha256: sha(body) });
  }
}
assert(fs.existsSync(path.join(repo, 'REPRODUCIBILITY-SETUP.md')));
const history = text.split('## Earlier experiments\n')[1].split('## Baselines and evaluation details')[0];
const rows = history.split('\n').filter(line => /^\| \*\*/.test(line));
assert.equal(rows.length, 61);
for (const row of rows) assert(/\[[^\]]+\]\[[^\]]+\]/.test(row), `History row lacks evidence: ${row}`);
const required = ['E0', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E6D', 'E7 / E7P', 'E8A', 'E8D', 'E9', 'E10V', 'E10M', 'E11', 'E12 Stage A', 'E12 Stage B', 'E13', 'E14', 'E15', 'E16', 'E17', 'E18', 'E19', 'E19-D2', 'E19-L1', 'E19-R1', 'E19-R2', 'E19-R3'];
for (const label of required) assert(rows.some(row => row.startsWith('| **' + label) && /[ —/]/.test(row.substring(4 + label.length, 5 + label.length))), `Missing study label: ${label}`);
assert(history.includes('no numerical E0 verdict is asserted here'));
assert(history.includes('It was cancelled before a valid evaluation'));
assert(history.includes('proposed corrected **E20**'));
const pin = 'f0cabb92d4b4214f3d423d9d19c77d3083d547da';
const summary = JSON.parse(source(pin, 'cluster/prometheus/independent-pusht-evidence/look-0/SUMMARY.json'));
assert.equal(summary.n, 1600); assert.equal(summary.complete_logical_runs, 57600);
assert.equal(summary.failures.length, 0);
assert.equal(summary.decision, 'stop_futility_strong_adverse_signal');
const arms = { 'VAD continuation': 'vad_continuation', 'Greedy VAD-300': 'vad_greedy_300', 'Gaussian continuation': 'diagonal_gaussian_continuation', 'Greedy VAD-576': 'vad_greedy_576', 'GMM continuation': 'direct_gmm_continuation', 'Released full SAGE': 'sage' };
const latest = text.split('## Latest results: independent PushT evaluation')[1].split('## Earlier experiments')[0];
for (const [label, arm] of Object.entries(arms)) {
  const row = latest.split('\n').find(line => line.startsWith('| ' + label + ' |'));
  assert(row, `Missing result row: ${label}`);
  const values = row.split('|').slice(2, 5).map(cell => Number(cell.trim().replace('%', '')));
  const expected = [...summary.per_horizon[arm], summary.arm_success[arm]].map(x => 100 * x);
  values.forEach((value, i) => assert(Math.abs(value - expected[i]) <= .005001, `Wrong percentage: ${label}`));
}
for (const [arm, displayed] of [['vad_greedy_300', 2.21], ['diagonal_gaussian_continuation', 2.94], ['sage', -4.74]]) assert(Math.abs(summary.primary[arm].difference * 100 - displayed) < .005001);
assert(Math.abs(summary.timing.sage.planner_median / summary.timing.vad_continuation.planner_median - 7.43) < .005);
assert(source(pin, 'cluster/prometheus/gdp_cem_e18_closed_loop.py').includes('score = immediate_cost'));
assert(text.includes('At the last local stage of a planning cycle'));
assert(text.includes('E12 Stage A separately ran official PRISM artifacts'));
assert(!text.includes('months of experiment labels'));
const report = { all_mechanical_checks_passed: true, checked_utc: new Date().toISOString(), readme_sha256: sha(text), history_entries: rows.length, distinct_linked_files_checked: new Set(checked.map(r => r.ref + ':' + r.file)).size, reference_definitions_checked: refs.size, latest_table_percentages_checked: 18, required_labels_checked: required.length, numeric_source: pin, scope: 'Link existence, label coverage, latest result arithmetic and narrow wording checks; not independent replication or a proof that prose is error-free.', sources: checked };
fs.writeFileSync(path.join(repo, 'docs/readme-audit-2026-09-07/checks.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ ...report, sources: undefined }, null, 2));
