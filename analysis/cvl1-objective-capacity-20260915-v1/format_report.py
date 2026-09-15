"""Publication-only transcription of already frozen aggregates; no fitting/statistics.

Added after completion. This does not change the frozen study.py reporting
procedure: it formats its sealed numbers and copies its reference metrics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ARCHIVE_SHA = '2545ec37b4b840a54926aa169bac16a9826174e8147d3c2edad8314522c5392d'
CONFIGS = ('original_bce', 'compact_bce', 'original_relative', 'compact_relative')
SPLITS = ('crossfit', 'training', 'validation')
LABELS = {'crossfit': 'Source-held-out cross-fit (96 references)',
          'training': 'Full-data TRAIN (96 references; in-sample)',
          'validation': 'Development VALIDATION (32 references)'}


def main(archive, output):
    archive = Path(archive); output = Path(output)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA
    with tarfile.open(archive) as t:
        prefix = 'run-d2cf5c8/results/'
        read = lambda n: json.load(t.extractfile(prefix+n))
        r = read('REPORT.json'); cf = read('CROSSFIT.json'); ledger = read('FIT-LEDGER.json')
    lines = []
    def para(text): lines.extend([text, ''])
    def table(headers, rows):
        lines.append('| '+' | '.join(headers)+' |')
        lines.append('| '+' | '.join(['---']*len(headers))+' |')
        lines.extend('| '+' | '.join(map(str, row))+' |' for row in rows)
        lines.append('')
    def val(v, percent=False):
        return '—' if v is None else (f'{100*v:+.3f}' if percent else f'{v:.5f}')
    def means(split, model): return r[split]['models'][model]['means']
    para('# CVL-1 objective × capacity v1 — completed development comparison')
    para('15 September 2026. All **60 fixed fits completed** in one CPU allocation. '
         'CVL-1 remains **`stop_no_ranking_promise`**; the original evaluator artifacts '
         'and accepted learning diagnosis remain unchanged. No downstream launch.')
    para('## Outcome and one recommendation')
    para('The original-capacity relative ensemble was nominated **before validation**, '
         'under the committed training-fold rule, with only **+0.152 percentage points** '
         'versus continuation. Its development-validation effect was **−1.497 points**. '
         'All four new ensembles were negative on validation. The nomination remains '
         '`original_relative`; we do not replace it with a validation-favored configuration or seed.')
    para('**Recommendation: retain continuation as the working baseline and do not promote '
         'a learned selector from this study.** Keep the original-relative model only as '
         'the preserved training-only nominee for researcher review. Neither this weak '
         'cross-fit advantage nor the negative validation comparison justifies an automatic '
         'closed-loop experiment, new labels, more training, or a favorable-seed substitution. '
         'This interpretation adds no retroactive CVL-1 pass/fail gate.')
    table(['Fixed ensemble', 'Cross-fit effect (pp)', 'Full TRAIN effect (pp)', 'VALIDATION effect (pp)'],
          [[k]+[val(means(sp,k)['effect'],True) for sp in SPLITS] for k in CONFIGS])
    para('Effects are paired selected empirical success minus continuation on the same '
         'labelled-eight bank, equal source → horizon → available anchor, averaging both '
         'binary continuation draws. Continuation selected success is 16.536% on TRAIN '
         'and 11.914% on VALIDATION. These are sampled-candidate, policy/budget-conditional '
         'development quantities—not closed-loop efficacy, true candidate values, an oracle, '
         'or confirmation. Negatives do not mean irrecoverability.')
    para('## Interpretation: objective and capacity')
    para('**Supported:** both relative models strongly fit the training differences. '
         'Original-relative reaches TRAIN concordance 0.978 and +15.169 points; '
         'compact-relative reaches 0.932 and +13.715 points. Thus this implementation '
         'can learn substantial in-sample ranking structure. That is not independent efficacy.')
    para('**Not established:** a reproducible source-disjoint gain from the relative objective. '
         'Original-relative versus original-BCE improves pooled cross-fit selection by '
         '0.543 points, but the fold contrasts are −1.215, −1.128, +0.174 and +4.340 points. '
         'Its positive pooled effect is not a consistent fold-wise advantage. At compact '
         'capacity the pooled objective contrast is −0.239 points; its sign also splits '
         'two positive/two negative folds. The four fits overlap in training sources, '
         'so these folds are not four independent replications.')
    para('**The simple capacity-reduction explanation is not supported by cross-fitting.** '
         'Compact minus original is −1.215 points for BCE and −1.997 for relative training. '
         'Relative compact loses to relative original in all four folds. Shrinking does '
         'improve the validation estimates (+1.237 BCE, +0.326 relative), but that reversal '
         'cannot be used to switch the frozen training-only nominee.')
    para('Validation relative-versus-BCE contrasts are +1.562 points at original capacity '
         'and +0.651 at compact capacity, yet both relative ensembles still lose to '
         'continuation. Original-relative gains 5.208 points of binary-draw outcome mass '
         'but loses 6.706; it departs in 81.641% of weighted banks. Its three seeds disagree '
         'on the winner in 83.464% of weighted validation banks. There is no single-seed '
         'rescue: the fixed ensemble is the method, and all seed outcomes are reported below.')
    para('**Unresolved:** whether a different, separately approved data/learning regime could '
         'generalize. This fixed 96-source study with two saved draws cannot separate '
         'limited outcome information, representation limitations and other generalization '
         'causes. It does not establish impossibility of value learning or justify a new '
         'encoder, feature search, label substitution, threshold sweep or redesign now.')
    para('## Scope, fitting and freeze')
    table(['Role', 'References', 'Available banks', 'Unavailable banks', 'Candidates', 'Binary draws', 'Positive draws'],
          [[role]+[r['counts'][role][k] for k in ['references','available_banks','unavailable_banks','candidate_rows','binary_draws','positive_draws']]
           for role in ('train','validation')])
    para('Four deterministic identifier-only folds, each 72 fitting /24 held-out sources; '
         '48 cross-fit fits followed by 12 all-96 fits. Seeds 8201/8202/8203; 40 epochs, '
         'AdamW lr 0.0003, weight decay 0.0001, batch 256, gradient norm cap 1. '
         'Original architecture 619→128→64→1 has 87,681 parameters; compact 619→32→1 '
         'has 19,873. No feature engineering or new labels. Fit-specific evaluator '
         'normalization uses only fitting sources, with the same eight-candidate weighted '
         'normalizer for both objectives; proposer/checkpoint scaling remains unchanged.')
    table(['Full-data objective', 'Rows/fit', 'Positive targets', 'Zero targets', 'Negative targets', 'Optimizer steps/fit'],
          [[e['configuration'], e['rows'], e['positive_targets'], e['zero_targets'], e['negative_targets'], e['optimizer_steps']]
           for e in ledger if e['stage']=='full' and e['seed']==8201])
    para('BCE retains eight candidates ×two draws per bank. Relative loss retains seven '
         'non-self candidates ×two draws, paired with the same bank/draw continuation: '
         '`(f(x_i)−f(x_b)−(y_i,d−y_b,d))²`. All 8,754 full-training zero differences '
         'remain; only the self-comparisons are omitted. Baseline advantage is exactly zero. '
         'Repeated use of a baseline is not new independent data. Across 60 fits, 81,120 '
         'optimizer steps were executed. There was no label rounding or distance target.')
    para('All new learned selectors retain continuation at an exact maximal-score tie; '
         'other maximal ties use lowest original index, with no epsilon. Original frozen '
         'controls retain their original lowest-index rule. No exact maximum ties occurred '
         'for the four new ensemble comparisons (see tie column). Relative scores are raw '
         'advantages, not probabilities; their magnitudes are not directly comparable to BCE.')
    para('The source/protocol were committed, pushed and remote-hash verified before fitting. '
         'The PRE-VALIDATION-FREEZE seals 144 pre-validation members, including all 60 models, '
         'scalers, cross-fit/full-TRAIN reports and training-fold recommendation. The reader '
         'rechecks those members before opening validation. The external backup independently '
         'matches that freeze. All validation sources remain previously exposed development data.')
    para('## Entire fixed comparison')
    para('All values below are frozen report transcriptions. Success, departure and ties are '
         'percentages; effects, gains and losses are percentage points. Gains/losses are '
         'unconditional weighted contributions, not conditional rates. Uniform is the '
         'labelled-eight expectation rather than a realized selector. TRAIN numbers for all '
         'full-data models are in-sample. Historical learned controls appearing with cross-fit '
         'results were trained on all 96 and are **not out-of-fold**; only the new models are.')
    for sp in SPLITS:
        para('### '+LABELS[sp])
        rows=[]
        order=list(CONFIGS)+['continuation','immediate','uniform_sampled8','historical_ensemble',
                            'historical_mlp8201','historical_mlp8202','historical_mlp8203',
                            'historical_linear','historical_context','historical_constant']
        for k in order:
            m=means(sp,k)
            rows.append([k, f'{100*m["selected_success"]:.3f}', val(m['effect'],True),
                val(m.get('gain'),True), val(m.get('loss'),True),
                '—' if m.get('departure') is None else f'{100*m["departure"]:.3f}', val(m.get('concordance')),
                val(m.get('brier')),val(m.get('log_loss'))])
        table(['Selector','Success %','Effect pp','Gain pp','Loss pp','Depart %','Concordance','Brier','Log loss'],rows)
    para('Concordance is conditional on informative banks with unequal empirical candidate '
         'means: 251/709 TRAIN banks and 70/242 VALIDATION banks. Score ties contribute 0.5. '
         'It does not demonstrate useful continuation departures by itself. Probability '
         'losses/calibration apply only to BCE and historical probability scorers, never '
         'relative or distance scores. Historical outcomes match the accepted diagnosis; '
         'full original-BCE has the same selected outcomes, without amending that diagnosis.')
    para('## Fixed-seed sensitivity, score variation and ties')
    for sp in SPLITS:
        para('### '+LABELS[sp])
        rows=[]
        for k in CONFIGS:
            m=means(sp,k)
            rows.append([k]+[val(means(sp,f'{k}_seed{seed}')['effect'],True) for seed in (8201,8202,8203)] +
                [val(m['effect'],True),f'{100*m["seed_winner_disagreement"]:.3f}',val(m['score_range']),
                 val(m['score_std']),val(m['score_min']),val(m['score_max']),f'{100*m["tied_maximum"]:.3f}'])
        table(['Configuration','8201 pp','8202 pp','8203 pp','Ensemble pp','Seed disagree %',
               'Mean range','Mean std','Mean min','Mean max','Max tie %'],rows)
    para('Score summaries are hierarchically averaged within-bank quantities, not global '
         'extrema. Raw per-candidate scores are in the backup. Seed rows are diagnostics, '
         'not independent samples or alternative selected models. In particular, the '
         'positive compact-relative seed 8202 validation estimate cannot replace its '
         'negative fixed ensemble or the pre-validation original-relative nomination.')
    para('## Fold effects and objective × capacity contrasts')
    table(['Held-out fold (24 sources)']+list(CONFIGS),
          [[f]+[val(x['models'][k]['means']['effect'],True) for k in CONFIGS] for f,x in cf['folds'].items()])
    keys=['objective_original','objective_compact','capacity_bce','capacity_relative','interaction']
    table(['Scope']+keys, [[f'Fold {f}']+[val(x['contrasts'][k],True) for k in keys] for f,x in cf['folds'].items()]+
          [[sp]+[val(r[sp]['contrasts'][k],True) for k in keys] for sp in SPLITS])
    para('All contrasts are pp: objective = relative−BCE, capacity = compact−original, '
         'interaction = objective_compact−objective_original. No outcome-based fold exclusions.')
    para('## Descriptive reference intervals')
    table(['Configuration','Cross-fit pp [2.5%,97.5%]','Full TRAIN pp [2.5%,97.5%]','VALIDATION pp [2.5%,97.5%]'],
          [[k]+[f'{100*r[sp]["models"][k]["descriptive_reference_interval"]["mean"]:+.3f} '
                 f'[{100*r[sp]["models"][k]["descriptive_reference_interval"]["lower"]:+.3f}, '
                 f'{100*r[sp]["models"][k]["descriptive_reference_interval"]["upper"]:+.3f}]' for sp in SPLITS] for k in CONFIGS])
    para('These are the predeclared 10,000-resample whole-reference percentile summaries. '
         'They are descriptive development intervals, not confirmatory tests or valid '
         'post-selection coverage claims. Neither candidate rows, draws, seeds nor folds '
         'are counted as independent source references.')
    para('## BCE calibration (fixed bins; no fitted calibration)')
    for sp in SPLITS:
        para('### '+LABELS[sp])
        table(['Model','Probability bin','Hierarchical mass %','Mean probability','Empirical outcome'],
              [[k,f'[{j/5:.1f},{(j+1)/5:.1f}{"]" if j==4 else ")"}',f'{100*b["mass"]:.3f}',
                val(b['probability']),val(b['outcome'])] for k in ('original_bce','compact_bce')
               for j,b in enumerate(r[sp]['models'][k]['calibration'])])
    para('Original/compact BCE validation Brier scores are 0.10890/0.10149, both worse '
         'than the unchanged training-constant 0.09538. Better probability error alone '
         'does not establish better within-bank selection.')
    para('## Every reference and evidence access')
    para('[REFERENCE-RESULTS.json](REFERENCE-RESULTS.json) includes every reference for '
         'all three reporting scopes and every fixed ensemble, seed and historical control: '
         'selected/baseline outcomes, effects, gains, losses, departures, predicted advantage '
         'and concordance. No favorable reference subset is selected. Complete bank-level '
         'metrics, each candidate score and both saved outcomes, strata and unavailable '
         'anchor identities are in the sealed backup. The compact per-reference effect '
         'tables below cover all four new ensembles; full controls/decomposition are in JSON.')
    for sp in SPLITS:
        para('### '+LABELS[sp]+' — every reference effect (pp)')
        table(['Reference']+list(CONFIGS),[[ref['reference']]+[val(ref['models'][k]['effect'],True) for k in CONFIGS]
                                         for ref in r[sp]['reference_rows']])
    para('## Resources, identities and backup')
    para('Job **301441** completed 0:0. One allocation, **201 wall seconds at 4 CPUs/8GiB**, '
         '804 allocated core-seconds (0.2233 core-hours), versus the 7,200-wall-second ceiling. '
         'Final Slurm TotalCPU is **656.057 CPU seconds**; the early receipt captured a '
         'not-yet-populated 00:00:00 and is preserved, not interpreted as zero use. Final '
         'worker telemetry: 196.668 wall seconds, 653.595 process CPU seconds, maximum RSS '
         '809,873,408 bytes. Fits used 147.028 wall seconds total, range 1.456–4.497 seconds '
         'per fit, below every 100-second reservation. All 60 completed; no failed allocation '
         'or retry. Only stderr was an informational Apptainer localtime underlay message.')
    para('New worker payload **90,840,277 bytes**; run including contemporaneous logs/launch '
         'metadata **90,851,777 bytes** before the terminal receipt, well below decimal 1GB. '
         'The terminal archive is **90,972,160 bytes**. Source/report/accounting supplements '
         'are small and remain inside the envelope. 17 synthetic tests passed before launch. '
         'No GPU, new label, simulator, LeWM, diffusion, adapter, closed-loop payload or '
         '1600–5999 payload was used. The three E12 drafts remain unchanged.')
    table(['Identity','Value'],[
        ['Frozen execution source commit','`d2cf5c8f6381dd6684403c55321210d165a33ea6`'],
        ['Source archive SHA-256','`29c2e1a6decac86c81810fb074df42cfe19a61244f1facfdab1ba2e5cc4d9a80`'],
        ['LF source manifest SHA-256','`9a3ede8d257698d62e50b3f088e64e33573d3c25de4f9d2a8f42935a4e500284`'],
        ['Protocol SHA-256','`6cc00051d539a6562e05b5b445549dc564ade43f1a39429da85fe54b0fb80647`'],
        ['Pre-validation freeze SHA-256','`'+r['pre_validation_freeze_sha256']+'`'],
        ['Final results seal SHA-256','`f76f6eb465706c048d36547015da2178f0ba00429530c1fa4b336aec168c9e9a`'],
        ['Terminal backup SHA-256','`'+ARCHIVE_SHA+'`']])
    para('Cluster run: `/lustreFS/data/superworld/ckontzias/thesis/experiments/'
         'cvl1-objective-capacity-20260915-v1/run-d2cf5c8`. External THESIS_SSD backup: '
         '`D:/THESIS-BACKUPS/cvl1-objective-capacity-20260915-v1/result-d2cf5c8.tar`, '
         'plus `source-d2cf5c8.tar`, final accounting receipt and publication supplement. '
         'Remote/local archive hashes match. All 145 root-sealed files and five 14-member '
         'model sub-seals verified (215 member checks), plus all 144 pre-validation members. '
         'Backup scope is new models/scalers, reports/predictions, source, job logs and '
         'accounting; the original simulator dataset was not copied.')
    para('Execution details: [EXECUTION.md](EXECUTION.md). Fixed definitions: '
         '[PROTOCOL.md](PROTOCOL.md). This Markdown is publication-only transcription '
         'of the sealed study aggregates, not a rerun or altered reporting procedure.')
    keep=('selected_success','continuation_success','effect','gain','loss','departure','predicted_advantage','concordance')
    refs={sp:[{'reference':ref['reference'],'models':{m:{k:v.get(k) for k in keep}
                  for m,v in ref['models'].items()}} for ref in r[sp]['reference_rows']] for sp in SPLITS}
    with (output/'REFERENCE-RESULTS.json').open('x',encoding='utf-8',newline='\n') as f:
        json.dump({'source_archive_sha256':ARCHIVE_SHA,'units':'fractions, not percentage points',
                   'historical_learned_crossfit_controls_are_in_sample':True,'scopes':refs},f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')
    with (output/'REPORT.md').open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(lines))
    print(json.dumps({'report_lines':len(lines),'reference_rows':{k:len(v) for k,v in refs.items()},
                      'no_new_statistics_or_fits':True}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();main(args.archive,args.output)
