"""Summarize every frozen case/seed result; no case/threshold selection."""
import json
from pathlib import Path
import statistics as s
ROOT=Path(__file__).resolve().parent


def main():
    r=json.loads((ROOT/'ARTIFICIAL-RESULTS.json').read_text())
    lines=['# Artificial results — complete predeclared suite','',
           '18 case/seed combinations; 59,904 independent artificial source situations across four disjoint roles. '
           'Each combination has 512 fit, 256 learn, 512 calibration and 2,048 test sources. '
           'Three fixed seeds per case are all retained in ARTIFICIAL-RESULTS.json. This is not research efficacy, '
           'a reproduction of author experiments, or a finite Monte Carlo proof.','',
           'The table averages the three equal-size seed runs. Columns are probabilities/differences, not percentages. '
           'Conditional harm averages only runs with overrides; null means no overrides in any run. '
           'The known expected difference uses the artificial generator probabilities, unavailable on real tasks.','',
           '| Case | Method | Success | Override | Marginal harm | Conditional harm | Improvement | Sample diff | Known expected diff |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    methods=('baseline','point','point_logged','simultaneous','ltt','pc_complete','pc_logged')
    fields=('selected_success','override_frequency','harmful_override_frequency','conditional_harm',
            'successful_improvement_frequency','sampled_outcome_difference','known_expected_outcome_difference')
    cases=list(dict.fromkeys(x['case'] for x in r['results']))
    for case in cases:
        for method in methods:
            mm=[x['metrics'][method] for x in r['results'] if x['case']==case]
            vals=[]
            for k in fields:
                v=[m[k] for m in mm if m[k] is not None]
                vals.append(f'{s.fmean(v):.4f}' if v else 'null')
            lines.append('| '+case+' | '+method+' | '+' | '.join(vals)+' |')
    lines+=['','## Coverage and degeneracy (per-seed ranges)','',
            '| Case | Simultaneous coverage | PC complete coverage | PC logged coverage | PC complete nonzero certificate | PC logged nonzero certificate |',
            '|---|---:|---:|---:|---:|---:|']
    for case in cases:
        rr=[x['metrics'] for x in r['results'] if x['case']==case]
        columns=[]
        for m,k in [('simultaneous','simultaneous_advantage_coverage'),('pc_complete','coverage'),('pc_logged','coverage'),
                    ('pc_complete','nonzero_certificate_fraction'),('pc_logged','nonzero_certificate_fraction')]:
            v=[x[m][k] for x in rr];columns.append(f'{min(v):.4f}–{max(v):.4f}')
        lines.append('| '+case+' | '+' | '.join(columns)+' |')
    lines+=['','## Interpretation and limitations','',
      '- Simultaneous bounds made zero overrides in every run, including beneficial cases. This is valid abstention, not an improvement. LTT accepted useful rules in shared-error, progress-conflict and fixed-tail sequential cases; it accepted none in optimistic-search, rare-override or sparse-binary cases. Every threshold count/p-value is in the JSON.',
      '- Rare overrides had roughly 60–73% conditional harmful-outcome frequency for point/PC despite low marginal frequency. A policy-coupled coverage certificate does not certify conditional override safety. Individual PC run coverage below .95 is retained: split-randomness and test variability matter, and three runs are too few to validate a theorem or detect a subtle implementation error.',
      '- Binary PC certificates were identically zero for optimistic-search and sparse-binary cases. Zero certificates do not necessarily mean zero overrides: PC preserves its learned policy instead of switching to baseline during calibration. This contrasts with the explicitly baseline-preserving simultaneous rule.',
      '- Shared-error uses a hidden bank-common perturbation and shared uniform outcome draws. Optimistic-search deliberately perturbs every method\'s prediction channel with independent candidate Gaussian errors. Rare-override injects a 2% optimism event. These are controlled artificial misspecifications, not claims that the fitted table is well specified in those channels. The saturated 16-context × 8-action table is an ordinary strong control for the observable discrete contexts; this does not establish sufficient capacity on Le-WM latents.',
      '- Progress conflict uses short-progress winner 1 with true full-success probability .15 versus slot 2 at .80. The sequential test adds an explicit two-step probability tree: a useful single intervention followed by the fixed baseline tail has success .80, but repeating the override in the shifted state has success .10. This is arithmetic, not a physics simulation or evidence that any real verifier behaves this way.',
      '- Logged PC uses one preassigned uniform fitting label per source; point-logged has the same restriction and capacity. Complete PC and the other full-bank controls receive the same complete fitting labels. Comparing logged PC directly to the full-bank point selector without this qualification would conflate information budgets.',
      '- Mathematical tests compare ACID scaling, whole-bank residual algebra, rank indexing, exact binomial p-values, binary PC envelope and equations 4.2/4.5. Integration tests check native observation divergence, actual returned means, duplicate aliases, fixed banks and chunk success. They do not test research checkpoints, image encoders, GPU precision, real endpoint readers or simulator cloning.','',
      '## Calibration requirements','',
      'At 95% confidence and a 5% conditional-harm target, zero harms need 59 overrides for one fixed rule or 90 for this five-rule Bonferroni family. At 2% overrides, 90/.02=4,500 sources in expectation (not a guarantee). A finite 95% simultaneous rank requires 19 sources, which says nothing about positive bounds. Uniform 1/8 logging requires 152 sources in expectation for 19 matching actions; with 320 proposed calibration sources only 40 matches are expected. Binary sparsity can remain uninformative even beyond these minimum counts.','',
      'Arithmetic erratum retained transparently: ARTIFICIAL-RESULTS.json\'s `sources_expected_at_2pct_override_five_rules=4490` rounded the continuous logarithmic threshold before imposing the integer 90-override requirement. The discrete minimum expectation is 4,500, as used here and in the real-runtime proposal. The original result file is preserved; no scenarios were rerun to alter outcomes.','']
    with (ROOT/'ARTIFICIAL-RESULTS.md').open('x',encoding='utf8') as f:f.write('\n'.join(lines))
    print('All six cases and seven decision variants reported; no favorable-case filtering.')
if __name__=='__main__':main()
