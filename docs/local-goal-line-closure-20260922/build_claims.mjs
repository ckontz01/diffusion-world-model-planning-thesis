// Plain six-column CSV, authored/checked through Artifact Tool; no workbook deliverable.
import fs from 'node:fs/promises';
import { Workbook } from '@oai/artifact-tool';
const base = new URL('./', import.meta.url);
const host = 'https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/';
const sources = {
  LGP1: ['07aa9bbe30a3bd89dcae6f3ad1f713979f2048c1','docs/local-goal-proposals-20260918/FINAL-REPORT.md'],
  RB1: ['8a79e267cb0cb7b6243900cb3bc194e0eb069a85','docs/local-goal-search-budget-20260919/FINAL-REPORT.md'],
  RB2: ['0b6507fc7398eb0624d0755035db22e666de74d5','docs/local-goal-source-replication-publication-20260920/completion-v6/FINAL-REPORT.md'],
  RB2A: ['0b6507fc7398eb0624d0755035db22e666de74d5','docs/local-goal-source-replication-publication-20260920/completion-v6/FINAL-AGGREGATE-PROJECTION.json'],
  R1: ['28cbcf18ec16bcb496132c7c9bd0204a7cf2eca9','docs/local-goal-source-replication-publication-20260920/preservation-recovery-r1/LOCATION-AND-RECEIPT.md'],
  E11: ['f0cabb92d4b4214f3d423d9d19c77d3083d547da','cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-RESULT-2026-08-18.md'],
  E11P: ['f0cabb92d4b4214f3d423d9d19c77d3083d547da','cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md'],
  IPT: ['f0cabb92d4b4214f3d423d9d19c77d3083d547da','cluster/prometheus/INDEPENDENT-PUSHT-RESULT-2026-09-07.md'],
  IPTP: ['f0cabb92d4b4214f3d423d9d19c77d3083d547da','cluster/prometheus/INDEPENDENT-PUSHT-PROTOCOL.md'],
  DECISION: ['150035cfb6dc2aaa1038c187dbb983ddfeb4fb0e','docs/local-goal-line-closure-20260922/DECISION.md'],
  AUTHORITY: ['150035cfb6dc2aaa1038c187dbb983ddfeb4fb0e','docs/local-goal-line-closure-20260922/AUTHORIZATION.txt']
};
const rows = [];
function claim(wording, refs, section, population, category, unsupported) {
  rows.push([wording, refs.map(s => host + sources[s].join('/')).join(' ; '), section, population, category, unsupported]);
}
claim('The development-selected five-population diffusion lead did not replicate on the 512-source development cohort.', ['RB1','RB2'], 'Native success and paired contrasts; All four arms', 'RB1: 32 exposed sources; RB2: 512 distinct development sources; diffusion5 versus matched GMM5', 'interpretation', 'A previously confirmed diffusion advantage was disproved universally.');
claim('RB2 does not establish diffusion superiority, equality, equivalence or noninferiority.', ['RB2'], 'All four arms; Limits and next handoff', '512 sources, fixed three seed blocks and two horizons; D5-G5 and D30-G30', 'limitation', 'Diffusion and GMM are equivalent, or GMM is universally superior.');
claim('The family-by-budget interaction hypothesis was unsupported, with estimate +0.0326 pp and interval [-1.9531,+2.0508] pp.', ['RB2'], 'All four arms', '512 sources; (D5-G5)-(D30-G30)', 'reported result', 'There is no interaction, or CEM erased the diffusion advantage.');
claim('Both families showed lower measured episode time and lower point-estimated success at five than at thirty populations.', ['RB2'], 'All four arms; Timing, allocation and memory', '512 sources; within-family five versus thirty', 'interpretation', 'Five populations are statistically Pareto-optimal or causally equally effective.');
claim('Neither continuation nor native SAGE was a live RB2 arm; matched local GMM is not native SAGE.', ['LGP1','RB2'], 'What was actually compared; Fixed question and population', 'Shared local-goal planner; GMM/diffusion at five and thirty', 'limitation', 'RB2 proves continuation or diffusion beats native SAGE.');
claim('RB2 is outcome-informed recent-method-role-disjoint development replication, not untouched confirmation or universally source-unseen evaluation.', ['RB2'], 'Fixed question and population', '512 selected from 1280 eligible exposed IDs after excluding 320 registered role IDs', 'limitation', 'Every component was trained and selected without any prior exposure to this population.');
claim('LGP1 did not establish a matched thirty-population diffusion advantage: -1.0417 pp, original interval [-7.292,+5.208] pp.', ['LGP1'], 'Primary native closed-loop result', '32 exposed sources; 192 episodes per family; matched GMM versus diffusion30', 'reported result', 'LGP1 established equality or universal diffusion inferiority.');
claim('Diffusion lower offline best-of-300 action error did not translate into higher LGP1 native success.', ['LGP1'], 'Supporting measurements, not alternative endpoints', 'Six fixed models; common validation rows; 32 exposed evaluation sources', 'interpretation', 'The offline metric caused failure, or the world model was proven defective.');
claim('RB1 at five populations gave D-G +3.1250 pp [-3.6458,+9.8958]; at thirty -1.0417 pp [-7.8125,+5.2083].', ['RB1'], 'Native success and paired contrasts', 'Same 32 sources; five new, thirty reused; no independent replication of thirty', 'reported result', 'Five-population superiority was confirmed on independent data.');
claim('RB1 reuses thirty-population outcomes but its own published interval does not amend LGP1 original interval.', ['RB1','LGP1'], 'Native success and paired contrasts; Primary native closed-loop result', 'Same 32 sources, different frozen bootstrap seeds in original reports', 'limitation', 'The two thirty-population intervals are interchangeable or newly computed here.');
claim('RB1 changes in the family difference relative to thirty included zero at both one and five populations.', ['RB1'], 'Native success and paired contrasts', '32 exposed sources; budget1-minus30 and budget5-minus30 interactions', 'reported result', 'Positive budget1 family contrast proved the interaction mechanism.');
claim('Each RB2 arm contains 3072 episodes, but the source reference is the independent statistical unit.', ['RB2'], 'All four arms', '512 sources x two horizons x three fixed seed blocks per arm', 'limitation', 'RB2 has 12288 independent source or model replications.');
claim('RB2 used six unchanged LGP1 models, no fitting, and four fixed arms with fresh episode-owned state.', ['RB2'], 'Fixed question and population', '1536 GPU source/seed jobs, 12288 fresh episodes', 'reported result', 'RB2 trained new models or repeated successful evaluations to improve outcomes.');
claim('RB2 native success requires combined position norm <20 and angle <pi/9 at the same post-action step, excluding t0.', ['RB2'], 'Fixed question and population', 'All four RB2 arms; native-state endpoint', 'reported result', 'An initial state or an offline reconstruction score counted as success.');
claim('RB2 rates are G5 15.1042%, D5 14.3555%, G30 17.9036%, D30 17.1224%.', ['RB2'], 'All four arms', '512 sources; all four arms; 3072 episodes each', 'reported result', 'Only the best arm or subgroup is relevant.');
claim('RB2 primary D5-G5 is -0.7487 pp [-2.0833,+0.5859].', ['RB2'], 'All four arms', '512 sources; primary fixed five-population comparison', 'reported result', 'The primary proves exact equality.');
claim('RB2 D30-G30 is -0.7813 pp [-2.3438,+0.7813].', ['RB2'], 'All four arms', '512 sources; prespecified thirty-population secondary', 'reported result', 'Thirty populations establish a general GMM advantage.');
claim('RB2 D5-D30 is -2.7669 pp [-4.4596,-1.0409] and D5-G30 is -3.5482 pp [-5.2083,-1.8229].', ['RB2'], 'All four arms', '512 sources; descriptive cross-budget secondaries', 'reported result', 'These are multiplicity-adjusted discoveries of a diffusion-specific causal fault.');
claim('Mean complete-episode seconds are published totals divided by 3072: G5 3.254, D5 3.620, G30 11.014, D30 11.368.', ['RB2','RB2A'], 'Timing, allocation and memory; configurations[].episode_timing_totals', 'All RB2 episodes; separate arm totals; arithmetic only', 'arithmetic derivation', 'These are pure model latency, time confidence intervals or matched deployment costs.');
claim('Complete-episode timing includes instrumentation/evidence handling and excludes shared backend/model setup.', ['RB2'], 'Timing, allocation and memory', 'RB2 complete-episode timer; shared setup 14409.113 seconds separately', 'limitation', 'The episode mean includes every allocation and shared setup cost.');
claim('Scoring lies inside refinement; bank fingerprint timing overlaps planning/refinement.', ['RB2'], 'Timing, allocation and memory', 'RB2 measured timing components', 'limitation', 'Adding every timer gives total time, or subtracting all hashing gives deployment latency.');
claim('Increasing populations from five to thirty increased observed success by 2.7995 pp for GMM and 2.7669 pp for diffusion.', ['RB2'], 'All four arms', '512 sources; differences of published arm means; no added interval', 'arithmetic derivation', 'Both gains have a newly established adjusted significance claim.');
claim('RB2 used 138753 GPU allocation seconds and 161 CPU allocation-wall seconds; worker process CPU is a separate 122546.557 seconds.', ['RB2'], 'Timing, allocation and memory', 'All 1537 successful unique research jobs', 'reported result', 'Arm-specific GPU allocations are measured, or zero Slurm TotalCPU means no CPU work.');
claim('Python RSS and Torch allocated memory are scoped measurements, not whole-tree or whole-device residency.', ['RB2'], 'Timing, allocation and memory', 'Peak worker Python RSS 1647009792 B; Torch allocated 294831104 B', 'limitation', 'These peaks certify the entire node memory footprint.');
claim('Earlier E11 positive evidence remains valid on its original three-task, fixed-seed suite against the specified controls and ACID reconstruction.', ['E11'], 'Frozen verdict; Diffusion-specific mechanism gate; Honest scientific interpretation', '400 D3 starts per task; PushT/Reacher/Cube; Gaussian and published-equation ACID reconstruction', 'interpretation', 'RB2 invalidates E11, or E11 proves universal or official-ACID superiority.');
claim('E11 used each released task callable for binary success; its inference/evaluation timing excludes proposal training.', ['E11','E11P'], 'Inference-time compute; protocol section 7 Outcomes and inference', 'Short-horizon untouched D3 suite under original interface', 'limitation', 'Its rates and elapsed-time ratio are directly comparable to RB2 instrumented episodes.');
claim('Independent PushT internal continuation gains passed, but the all-three objective failed and the registered SAGE futility rule stopped the study.', ['IPT'], 'Registered primary comparisons; Timing and interpretation', '1600 weak-policy references, six methods, H75/H150, three blocks; live native SAGE', 'reported result', 'Continuation was confirmed superior or noninferior to SAGE.');
claim('Independent PushT uses its post-action native position/angle endpoint and sequential spending bounds; its solver-call median ratio is not end-to-end speed.', ['IPT','IPTP'], 'Registered primary comparisons; Timing and interpretation; protocol Execution', '1600 reference clusters; 57600 arm/horizon/seed runs', 'limitation', 'All studies use interchangeable success definitions, confidence intervals or timing boundaries.');
claim('The separate studies must not be displayed as a cross-study absolute-rate performance time series.', ['LGP1','RB2','E11','IPT'], 'What was actually compared; Fixed question and population; Frozen verdict; Timing and interpretation', 'Different populations, interfaces, comparators and timing boundaries', 'limitation', 'The change in absolute success proves the method deteriorated over time.');
claim('RB2 computation and preservation succeeded; R1 did not change scientific outcomes or erase the failed first transfer.', ['RB2','R1'], 'Authentication, storage and preservation; Exact location mapping', 'Complete RB2 archive and preserved LGP1/RB1 union', 'reported result', 'The original transfer succeeded, or recovery reran the research.');
claim('Retain continuation, promote neither proposer, and close this line for now without declaring the overall thesis finished.', ['DECISION','AUTHORITY','RB2'], 'Closure decision; DELIVERABLES 1; Limits and next handoff', 'Prospective priority decision after completed LGP1/RB1/RB2', 'prospective research decision', 'The thesis is finished or continuation won a live RB2 comparison.');
claim('This decision authorizes no further round-count, seed, return-rule, sampler or training search.', ['DECISION','AUTHORITY'], 'Closure decision; DELIVERABLES 1 and RETURN', 'Current local-goal proposer-and-budget line', 'prospective research decision', 'Negative results authorize automatic tuning or another experiment.');
const headers = ['exact_proposed_wording','immutable_supporting_files','supporting_sections','population_and_comparator','category','stronger_unsupported_wording'];
const matrix = [headers, ...rows];
const wb = Workbook.create();
const sheet = wb.worksheets.add('Claims');
sheet.getRange(`A1:F${matrix.length}`).values = matrix;
sheet.getRange(`A1:F${matrix.length}`).format.wrapText = true;
sheet.getRange(`A1:F${matrix.length}`).format.font = {name:'Arial',size:10};
sheet.getRange('A1:F1').format = {fill:'#24364B',font:{name:'Arial',color:'#FFFFFF',bold:true},wrapText:true};
sheet.getRange('A1:F1').format.rowHeight = 34;
sheet.getRange('A2:F33').format.rowHeight = 110;
sheet.getRange('A1:F33').format.columnWidth = 52;
sheet.showGridLines = false;
wb.recalculate();
const actual = sheet.getRange(`A1:F${matrix.length}`).values;
if (JSON.stringify(actual) !== JSON.stringify(matrix)) throw Error('CSV matrix mismatch');
const csv = actual.map(row => row.map(v => '"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
await fs.writeFile(new URL('CLAIMS-AND-EVIDENCE.csv',base), csv);
const reopened = await Workbook.fromCSV(csv,{sheetName:'Check'});
if (JSON.stringify(reopened.worksheets.getItemAt(0).getRange(`A1:F${matrix.length}`).values) !== JSON.stringify(matrix)) throw Error('CSV round-trip mismatch');
const preview = await wb.render({sheetName:'Claims',range:'A1:C3',scale:1,format:'png'});
await fs.writeFile(new URL('CLAIMS-PREVIEW.png',base),new Uint8Array(await preview.arrayBuffer()));
await fs.writeFile(new URL('CLAIMS-CHECKS.json',base), JSON.stringify({rows:rows.length,columns:6,exact_matrix:true,csv_roundtrip:true,plain_csv_no_formulas:true,preview:'A1:C3',sources},null,2)+'\n');
console.log(JSON.stringify({claims:rows.length,roundtrip:true}));
