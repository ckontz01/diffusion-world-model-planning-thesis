"""Render the completed authenticated aggregate; no fitting or model calls."""
import json,hashlib
from pathlib import Path
d=Path(__file__).resolve().parent;r=json.loads((d/'FINAL-AGGREGATE.json').read_text())
f=json.loads((d/'FOLDS.json').read_text());models=r['models']['models']
assert len(r['fits'])==24 and sum(x['updates'] for x in r['fits'])==43200
assert len(r['models']['reference_rows'])==192
assert {(x['fold'],x['condition'],x['seed']) for x in r['fits']}=={(i,c,s) for i in range(4) for c in ('control','scores') for s in (8201,8202,8203)}
for x in r['fits']:
    assert x['updates']==1800 and x['parameters']==87937
    assert set(x['fitting_refs'])==set(sum(f['held_out'],[]))-set(f['held_out'][x['fold']])
lines=['# SI1 completed development result','',
'**Retain continuation; promote no model.** Adding the saved immediate/continuation costs did not improve the observed source-held-out selection mean. Treatment minus control was -0.065 percentage points, with a descriptive reference-bootstrap interval [-0.792, +0.716] pp. This is not evidence of equivalence or proof that these scores cannot help another evaluator.','',
'All results use 192 out-of-fold sources, equal source/horizon/available-anchor weighting, the fixed three-seed ensembles and two saved outcomes per sampled candidate. Seeds, rows and draws are not independent sources. All 24 fits and 43,200 updates completed; no model was selected.','',
'## Overall selection','',
'| Selector | Selected success % | Effect vs continuation pp | Descriptive interval pp | Gained % | Lost % | Departure % |',
'|---|---:|---:|---|---:|---:|---:|']
for name in ('continuation','immediate','control','scores'):
    m=models[name]['means'];q=models[name]['descriptive_reference_interval']
    lines.append('| %s | %.3f | %+.3f | [%+.3f, %+.3f] | %.3f | %.3f | %.3f |'%(name,m['selected_success']*100,m['effect']*100,q['lower']*100,q['upper']*100,m['gain']*100,m['loss']*100,m['departure']*100))
lines+=['','Gained/lost values are weighted paired binary-outcome fractions, not counts of independent episodes. Treatment changes the selected candidate relative to control on 20.703% of weighted banks; paired gains are 1.172%, losses 1.237%. Against continuation it departs less often (76.172% versus control 81.250%) but still loses more outcomes than it gains.','',
'## Secondary quantities','',
'| Selector | Concordance | Brier | Log loss | Tied maxima % |','|---|---:|---:|---:|---:|']
for name in ('continuation','immediate','control','scores'):
    m=models[name]['means'];fmt=lambda x:'—' if x is None else '%.6f'%x
    lines.append('| %s | %s | %s | %s | %.3f |'%(name,fmt(m['concordance']),fmt(m['brier']),fmt(m['log_loss']),m['tied_maximum']*100))
lines+=['','Concordance is defined on 480 of 1,426 banks with empirical candidate-outcome variation; undefined banks are not scored as zero. All four selectors have unique maxima on all banks. Costs are not probabilities, so Brier/log loss do not apply to the two non-neural controls. Slightly better probability error does not establish better selection.','',
'## Fold effects (percentage points versus continuation)','',
'| Fold | Sources | Immediate | Control | Treatment | Treatment − control |','|---|---:|---:|---:|---:|---:|']
names=('immediate','control','scores','treatment_minus_control')
for k,v in sorted(r['fold_summaries'].items()):lines.append('| %s | 48 | %s |'%(k,' | '.join('%+.3f'%(v['models'][n]['means']['effect']*100) for n in names)))
lines+=['','## Horizon / anchor-slot effects (percentage points)','',
'| Stratum | Available banks | Immediate | Control | Treatment | Treatment − control |','|---|---:|---:|---:|---:|---:|']
for k,v in sorted(r['models']['strata'].items()):lines.append('| %s | %d | %s |'%(k,v['control']['banks'],' | '.join('%+.3f'%(v[n]['means']['effect']*100) for n in names)))
lines+=['','Slots retain the original fixed schedule and availability. Stratum summaries condition on available sources; averaging this table equally does not reproduce the primary hierarchical weighting. No favorable fold or stratum was selected.','',
'## Execution, preservation and resources','',
'- Slurm 301953: COMPLETED, exit 0:0; one allocation, no retries. Partition defq, account superworld, 4 CPUs, 8 GiB, no GPU TRES or passthrough. Queue approximately 1 second; allocation 102 seconds (408 reserved CPU-core-seconds).',
'- Worker reported 97.203 seconds wall and 339.093 process CPU seconds; Slurm TotalCPU 341.640 seconds. Worker peak RSS 967,847,936 bytes; Slurm sampled batch MaxRSS 697,768 KiB. These measure different scopes/sampling and are reported separately.',
'- Exactly 24 fits × 1,800 updates = 43,200. Total row presentations: 10,994,304 (includes repeated minibatches, not new labels or independent samples). Per-fit row presentations, timings and fitting-source IDs are in FINAL-AGGREGATE.json.',
'- 1,426 available banks; 110 unavailable slots; 11,408 candidate-index rows; 22,816 original binary records. No new labels, tail streams or model-based rollouts. Deterministic-tail repetitions remain repeated records, not added independent evidence.',
'- Worker seal verified all 40 members. Complete archive verified all 68 members: source including disabled template, separate execution approval, all 24 weights, four normalizers/freeze records/prediction files, reports, Slurm logs, accounting and operational launcher versions.',
'- Unique archived payload: 20,442,378 bytes; archive: 20,500,480 bytes. Remote payload plus archive at sealing: 40,942,858 bytes, before small manifest/receipt/documentation additions. All are far below the 1 GB ceiling; final inventory accompanies the handoff.',
'- External backup: D:/THESIS-BACKUPS/candidate-value-score-information-20260918/execution-68145e6458da0b90 on verified THESIS_SSD. SI1-COMPLETE.tar SHA-256: 57deab4d1f30b3618f336c0c73bad45827e64301aa7ae3664bedc0e35d715e41.',
'- Source manifest: 68145e6458da0b90255dd98e4fa2b9469dea12907797d7830c9bd233314be35c. Worker seal: 73384f244abd42067fc13ae64318abfa6a1c3036708fc45bc34ec8cdc4e7c3e3.',
'- Execution approval: 9cbddb0a9e19ab162961a38253efc0fefcc3e8936ec70a84cedbbe4955a23cef. Final aggregate SHA-256: '+hashlib.sha256((d/'FINAL-AGGREGATE.json').read_bytes()).hexdigest()+'.','',
'## Bounded interpretation','',
'Access to these two saved lookahead costs was not sufficient to improve this fixed BCE selector on the evaluated source-held-out development banks. The result supports retaining continuation, not promoting either learned ensemble. It does not isolate the individual costs, demonstrate equivalence, establish a general limitation of learned evaluation, or measure closed-loop efficacy. Intervals are descriptive: fold training sets overlap and this is historically exposed development data. No follow-up study, threshold tuning, seed selection, additional labels or closed-loop launch is authorized by this result. Historical decisions and E12 drafts are unchanged.','',
'## All 192 source effects (percentage points)','',
'Continuation effect is zero for every source. Full selected outcomes and secondary metrics for every source, fold and stratum are also preserved in FINAL-AGGREGATE.json.','',
'| Source | Immediate | Control | Treatment | Treatment − control |','|---:|---:|---:|---:|---:|']
for row in r['models']['reference_rows']:lines.append('| %d | %s |'%(row['reference'],' | '.join('%+.3f'%(row['models'][n]['effect']*100) for n in names)))
with (d/'FINAL-REPORT.md').open('x') as out:out.write('\n'.join(lines)+'\n')
print('Validated and rendered all 192 sources and 24 fixed fits.')
