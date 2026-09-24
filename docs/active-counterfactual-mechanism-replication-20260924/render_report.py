"""Render the ONE saved-data analysis, without re-reading research artifacts."""
import base
from statistics import mean

def main():
    r=base.read(base.HERE/'SAVED-DATA-MECHANISM.json'); s=r['summary']
    lines=['# ACV0 saved-data mechanism report — 24 September 2026','',
           'Post-hoc, CPU-only description of the completed, preserved ACV0 pilot. Original result commit: `5d8666754ad8aa0507730f86cf3ee6caa32c105a`. No old estimate or controller is changed. No new final-source outcomes are assigned to the added control.','',
           '## Actual paired choices on all32 final-development sources','',
           'Active and no_update have byte-identical candidate trees, selected prefixes, and actual first-five action/state/latent/dynamics/pixel-hash/flag histories on all32 sources. Their suffix choice differs on20 sources. Among these:13 both fail,6 both succeed,1 active-only success (847),0 no_update-only successes. On the12 unchanged-suffix sources there are3 joint successes and9 joint failures. Thus feedback frequently changes actions, but changes native binary success only once in these paired executions. Action changes with equal endpoints are not evidence of equivalence or proof of benefit.','',
           'The160 deployed static/passive/active/no_update/ordinary decisions were reproduced from saved candidate features and the unchanged small predictors, including original prefix scores and actual-response suffix selection. Bayesian decisions below are authenticated saved choices, not newly replayed predictions. Vanilla and early replanning have no fixed-tree suffix index; their original endpoints remain in the machine-readable report.','',
           'Active and static selected different prefixes on 12 sources: 931, 623, 847, 175, 5, 1236, 1160, 784, 1247, 1031, 1005 and 1598. This is the observed decision-level distinction between anticipated-feedback selection and committed selection. The new control\'s old-final outcomes remain unassigned: these prefix differences do not supply its missing suffix/outcome observations.','',
           'Cells below are `prefix/suffix; native success`. Indices only compare within a source; exact action arrays/hashes and every arm’s endpoint/steps are in `SAVED-DATA-MECHANISM.json`.','',
           '| Source | Static | Passive | Active | No update | Ordinary | Bayesian | Suffix changed |','|---|---|---|---|---|---|---|---|']
    for row in r['final_development']:
        cells=[]
        for arm in ('static','passive','active','no_update','ordinary','bayesian'):
            x=row['actual'][arm]; cells.append(f"{x['prefix']}/{x['suffix']}; {x['native_success']}")
        lines.append('| '+str(row['reference'])+' | '+' | '.join(cells)+' | '+str(row['response_changed_suffix'])+' |')
    lines+=['','## Predicted prefix-value decomposition','',
            'For prefix p, terminal probabilities are S_p,F_p,A_p and unconditional suffix predictions are q̄_pj. Define j*=argmax_j q̄_pj with original content-based ties. Committed active value C_p=A_p q̄_pj*. Terminal-prefix contribution T_p=S_p (terminal failure contributes zero). The unchanged finite-integration score is V_p=S_p+A_p Σw_r max_j q_pj(r). Anticipated feedback increment B_p=A_p[Σw_r max_j q_pj(r)−q̄_pj*]. Exactly V_p=T_p+C_p+B_p; total committed outcome is T_p+C_p.','',
            'B_p also splits into nonnegative same-draw feedback gain A_p Σw_r[max_j q_pj(r)−q_pj*(r)] and signed quadrature correction A_p[Σw_r q_pj*(r)−q̄_pj*]. The latter must not be interpreted as a benefit of observing feedback. All original128 component-stratified antithetic responses/seed94021 are retained, not increased or optimized.','',
            '| Role / prefixes summarized | Terminal T | Committed-active C | Anticipated B | Same-draw gain | Quadrature correction | Active V |','|---|---:|---:|---:|---:|---:|---:|']
    for role in ('final_development','validation'):
        rows=[p for x in r['predicted_prefix_decomposition'] if x['role']==role for p in x['prefixes']]
        keys=('terminal_success','committed_active_value','anticipated_feedback_increment','same_draw_feedback_increment','quadrature_correction','active_value')
        lines.append('| '+role+f' / {len(rows)} | '+' | '.join(f'{mean(x[k] for x in rows):.6f}' for k in keys)+' |')
    final_decomp={x['reference']:x['prefixes'] for x in r['predicted_prefix_decomposition'] if x['role']=='final_development'}
    selected=[final_decomp[x['reference']][x['actual']['active']['prefix']] for x in r['final_development']]
    lines.append('| actual active-selected /32 | '+' | '.join(f'{mean(x[k] for x in selected):.6f}' for k in keys)+' |')
    lines+=['','These are predicted native-success values, not observed causal components. All32 actual active/no_update prefixes remained nonterminal; nonzero predicted terminal contributions are model outputs, not observed prefix successes. Across-source prefix changes bundle physical effects, observation changes and different suffix sets; they do not isolate information gathering. The JSON contains every prefix’s components, probabilities, selected committed suffix and action identity for both roles.','',
            '## Sixteen validation banks: same candidates, separate role','',
            'All saved suffix outcomes are used on each active prefix, with physical prefix replay checked. Prefix metrics average over suffixes, then prefixes within source, then the16 sources; branch rows are not independent observations. No fitting-data bank was decoded. Validation remains report-only and is not pooled with the32 final-development sources. Scores use identical saved candidates and actual responses, avoiding selected-branch population differences.','',
            '| Predictor | Same-candidate BCE | Same-candidate Brier |','|---|---:|---:|']
    for name,metrics in s['validation_same_candidate_scores'].items(): lines.append(f"| {name} | {metrics['bce']:.6f} | {metrics['brier']:.6f} |")
    lines+=['','On these banks, the joint conditional predictor scores worse than its own unconditional prior, although better than this fixed ordinary predictor. This is descriptive, not universal calibration dominance, and does not invalidate the ordinary comparator.','',
            '| Validation source | Static | Committed feedback (new) | No update | Active | Ordinary |','|---|---|---|---|---|---|']
    for row in r['validation']:
        cells=[]
        for arm in ('static','committed_feedback','no_update','active','ordinary'):
            x=row['descriptive_saved_bank_choices'][arm]; cells.append(f"{x['prefix']}/{x['suffix']}; {x['success']}")
        lines.append('| '+str(row['reference'])+' | '+' | '.join(cells)+' |')
    lines+=['','Totals out of16: '+', '.join(f'{k}={v}' for k,v in s['validation_saved_bank_successes'].items())+'.',
            'This table applies fixed predictors/rules to already-executed validation branches; it is not a newly executed final evaluation or evidence of training-seed robustness. No unexecuted old-final source/control outcome is inferred, even if a new rule might choose a previously seen branch.','',
            '## Conclusion and audit boundary','',
            'The existing evidence supports response-dependent action changes and one observed final-cohort endpoint gain versus no_update. It does not establish that anticipated feedback is a robust reason to choose the prefix. The new control completes the missing comparison needed to examine that question prospectively. The same-candidate validation diagnostics also caution against equating conditional updates with uniformly better predictions. No robotics mechanism, novelty, safety guarantee, model promotion or general superiority is established.','',
            f"The one saved-data computation took {r['resources']['wall_seconds']:.3f}s wall / {r['resources']['process_cpu_seconds']:.3f}s process CPU. Four-thread ceiling;0 Le-WM forwards,0 physics steps,0 fits,0 reference-payload reads,0 GPU jobs. Selected members were authenticated against the existing verified SSD request; no archive/backup cycle was repeated. Original REPORT SHA: `{r['authentication']['original_report_sha256']}`.",'']
    base.write(base.HERE/'SAVED-DATA-MECHANISM.md','\n'.join(lines).encode())
    print('Rendered all32 choices, all16 bank comparisons, every decomposition available in JSON.')

if __name__=='__main__': main()
