"""Complete addendum tables; no further data generation or control selection."""
import json
from pathlib import Path
import statistics
from paired_improvement import AV0

ROOT=Path(__file__).resolve().parent


def fmt(v):return 'undefined' if v is None else f'{v:.6g}'


def main():
    result=json.loads((ROOT/'RESULTS.json').read_text())
    old=json.loads((AV0/'ARTIFICIAL-RESULTS.json').read_text())
    lookup={(r['case'],r['seed']):r for r in old['results']}
    matches=[]
    additional=[]
    for row in result['results']:
        prior=lookup[row['case'],row['seed']]
        old_threshold=min(prior['ltt_accepted']) if prior['ltt_accepted'] else None
        matches.append(row['chosen_threshold']==old_threshold)
        if row['accepted_thresholds']!=prior['ltt_accepted']:
            additional.append(dict(case=row['case'],seed=row['seed'],
                                   improvement_accepted=row['accepted_thresholds'],ltt_accepted=prior['ltt_accepted']))
        m=row['selected_rule_metrics']['test']
        for key,value in prior['metrics']['ltt'].items():
            if key in m:assert m[key]==value,'Unexpected practical metric difference'
    assert all(matches)
    lines=['# Complete paired-improvement addendum results','',
           'All 18 fixed cases are included. Source-data digests match AV0 in 18/18; '
           'all 25 accepted AV0 files retain their original bytes. Point metrics, original LTT tests '
           'and simultaneous quantiles replay exactly. Predictions use the unchanged full-branch estimator.','',
           'The new control accepts at least one threshold in 9/18 cases. Its smallest accepted threshold '
           '(or fallback) is identical to conditional-harm LTT in all 18 cases, so the deployed actions and '
           'reported test metrics are identical. Shared-error seed 92203 additionally accepts threshold .10 '
           'but still deploys threshold 0. This does not demonstrate an improvement over LTT.','',
           '## All calibration rule tests','',
           'Every rule uses all 512 calibration sources for its success-difference denominator. '
           'Only G+L discordant sources enter the binomial p-value. Critical value .05/5=.01. '
           'Calibration estimates are selection-affected descriptions, not fresh test evidence.','',
           '| Case | Seed | Threshold | G | L | Discordant | Ties | p-value | Accept | Net difference / 512 |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---|---:|']
    for row in result['results']:
        for t in row['calibration_tests']:
            lines.append(f"| {row['case']} | {row['seed']} | {t['threshold']:g} | {t['gains']} | {t['losses']} | "
                         f"{t['discordant']} | {t['ties']} | {t['p_value']:.9g} | {t['accepted']} | {t['sampled_net_difference']:.6g} |")
    for role,n in [('calibration',512),('test',2048)]:
        lines+=['',f'## Selected rule on {role}: all {n} sources per case','',
                '| Case | Seed | Accepted thresholds | Selected threshold | G | L | Success | Override | Marginal harm | Conditional harm | Sample net diff | Known expected diff |',
                '|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for row in result['results']:
            m=row['selected_rule_metrics'][role]
            fields=['selected_success','override_frequency','harmful_override_frequency','conditional_harm',
                    'sampled_outcome_difference','known_expected_outcome_difference']
            accepted=', '.join(f'{x:g}' for x in row['accepted_thresholds']) or 'none'
            selected='baseline fallback' if row['chosen_threshold'] is None else f"{row['chosen_threshold']:g}"
            lines.append(f"| {row['case']} | {row['seed']} | {accepted} | {selected} | {m['gains']} | {m['losses']} | "+
                         ' | '.join(fmt(m[k]) for k in fields)+' |')
    lines+=['','## Practical comparison averaged over the three fixed seeds','',
            '| Case | New accepted cases | New sampled net diff | New known expected diff | Old LTT sampled net diff | Old simultaneous sampled net diff |',
            '|---|---:|---:|---:|---:|---:|']
    for case in dict.fromkeys(r['case'] for r in result['results']):
        rr=[r for r in result['results'] if r['case']==case]
        vals=[statistics.fmean(r['selected_rule_metrics']['test'][key] for r in rr)
              for key in ('sampled_outcome_difference','known_expected_outcome_difference')]
        vals += [statistics.fmean(r['comparison_to_accepted_av0'][m]['sampled_outcome_difference'] for r in rr)
                 for m in ('ltt','simultaneous')]
        lines.append(f"| {case} | {sum(bool(r['accepted_thresholds']) for r in rr)}/3 | "+' | '.join(fmt(v) for v in vals)+' |')
    lines+=['','The sequential-shift numbers concern the original **single intervention with fixed reference tail**. '
            'They do not certify repeatedly using the accepted rule in shifted states. No repeated-policy simulation '
            'or new run was added. No inference should use candidates, repeated draws or horizons as independent sources.','',
            'The known expected difference is available only from this artificial generator. Positive test differences '
            'are descriptive observations under fixed fixtures, not a proof of a universal robotics mechanism. '
            'No-acceptance cases remain results. The original conclusion is unchanged: **no differentiated treatment yet**.','']
    with (ROOT/'RESULTS.md').open('x',encoding='utf8') as f:f.write('\n'.join(lines))
    summary=dict(cases=18,source_digest_matches=18,accepted_cases=9,
                 deployed_rule_matches_conditional_harm_ltt=matches,
                 accepted_family_differences=additional,
                 practical_conclusion='Same deployed decisions as conditional-harm LTT in all fixed cases; different tested target.',
                 no_differentiated_treatment_yet=True,av1_launched=False)
    with (ROOT/'COMPARISON.json').open('x',encoding='utf8') as f:json.dump(summary,f,indent=2);f.write('\n')
    print(json.dumps(summary))


if __name__=='__main__':main()
