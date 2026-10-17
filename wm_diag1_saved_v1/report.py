"""Fixed complete four-setting and every-parent report; no numeric input reread."""
import json
from .common import DOC,identity,write_new

def pc(value):return '{:.3f}%'.format(100*value)
def diff(value):return '{:+.3f} pp'.format(100*value)
def newcell(record):return '{}; {} [{}, {}]; {}/{}/{}'.format(pc(record['mean_success']),diff(record['difference_vs_P0']),diff(record['ci95_percentile'][0]),diff(record['ci95_percentile'][1]),record['gains'],record['losses'],record['ties'])

def main():
    path=DOC/'collected/output/DERIVED-RESULTS.json';r=json.loads(path.read_text());narrative=(DOC/'MECHANISM-PROPOSAL.md').read_text(encoding='utf8')
    if r['status']!='ONE_COMPLETE_FIXED_SAVED_DATA_PASS' or len(r['parents'])!=128 or len(r['settings'])!=4:raise ValueError('complete fixed discovery results only')
    lines=['# WM-DIAG1-SAVED — complete outcome-informed saved-data discovery','',
        'The original completed study, estimates and intervals are unchanged. These are 64 physical source parents shared across backbones (32 per task), not 128 independent sources. Candidates and two recorded evaluation draws add no independent parents. Reacher motivated this follow-up; PushT is an exposed contrast. Both new corrections are privileged diagnostics, not deployable repairs.','',
        '## Fixed four-setting results','',
        'New columns show success; difference vs P0 [descriptive paired 95% interval]; parent gains/losses/ties. Seed 20261017, 10,000 task-paired resamples shared across backbones/corrections. No confirmatory, multiplicity-controlled or independent-training-seed claim.','',
        '| Setting | Original P0 | Original O0 | A: remove common error | B: remove candidate-specific error | A / B agreement with O0 |',
        '|---|---:|---:|---|---|---:|']
    for key,s in r['settings'].items():
        old=s['original_copied_not_reestimated'];a,b=s['new_diagnostic_selectors']['A'],s['new_diagnostic_selectors']['B']
        lines.append('| {} | {} | {} | {} | {} | {} / {} |'.format(key,pc(old['P0']),pc(old['O0']),newcell(a),newcell(b),pc(a['choice_agreement_with_O0']),pc(b['choice_agreement_with_O0'])))
    lines+=['','Original intervals below are copied verbatim, not re-estimated. Energies are descriptive latent units; no error-energy fraction is a fraction of task failures caused. Raw latent units must not be compared across backbones.','']
    for key,s in r['settings'].items():
        old=s['original_copied_not_reestimated'];e=s['all_parents']['energies'];terms=s['all_parents']['selected_pair_terms']
        lines+=['### '+key,'',
            'Original P0 interval: {}; O0 interval: {}; O0−P0: {} [{} , {}].'.format(old['P0_ci95'],old['O0_ci95'],diff(old['O0_minus_P0']['mean']),diff(old['O0_minus_P0']['ci95_percentile'][0]),diff(old['O0_minus_P0']['ci95_percentile'][1])),
            'Changed original action choices: {}; changed mean outcomes: {}; changed choices with tied outcomes: {}.'.format(s['original_choice_changes'],s['original_outcome_changes'],s['changed_choices_with_tied_outcomes']),
            'Equal-parent mean coordinate MSE: {:.9g}; common energy / coordinate: {:.9g}; specific energy / coordinate: {:.9g}.'.format(e['coordinate_MSE']['mean'],e['common_per_coordinate']['mean'],e['specific_per_coordinate']['mean']),
            'Raw mean L2 error energy: {:.9g}; common: {:.9g}; specific: {:.9g}. Mean nonzero-parent common-energy fraction: {} (not failure attribution).'.format(e['total_mean_L2_squared']['mean'],e['common_L2_squared']['mean'],e['specific_mean_L2_squared']['mean'],e['common_energy_fraction_not_failure_attribution']['mean']),
            'Selected-pair mean saved relative ordering error: {:.9g}; signed goal-direction difference: {:.9g}; squared-error difference: {:.9g}.'.format(terms['saved_relative_ordering_error']['mean'],terms['signed_goal_direction_difference']['mean'],terms['squared_error_difference']['mean']),
            'Post-stop absorbed oracle terminal candidates: {}/{}; selected P0/O0 absorbed parents: {}/{}.'.format(s['oracle_absorbed_terminal_candidates'],s['all_oracle_candidates'],s['P0_selected_absorbed_parents'],s['O0_selected_absorbed_parents']),
            '', '| Selection | Prefix-success draws | Tail-success draws | Failure draws |','|---|---:|---:|---:|']
        for name,counts in s['recorded_draw_phase_counts_not_independent_n'].items():lines.append('| {} | {} | {} | {} |'.format(name,counts['prefix_success'],counts['tail_success'],counts['failure']))
        lines+=['','Recorded success differences vs P0, split into disjoint outcome categories (not a causal partition):','']
        for name,p in s['absolute_success_difference_split_by_recorded_phase'].items():lines.append('- {}: prefix {}; tail {}.'.format(name,diff(p['prefix_success_mean']),diff(p['tail_success_mean'])))
        lines+=['','P0→O0 draw-phase transitions: `'+json.dumps(s['P0_to_O0_draw_phase_transitions'],sort_keys=True)+'`.','',
            'Original gain/loss/tie strata (all parents retained):','', '| Stratum | Parents | Mean common energy | Mean specific energy | Mean goal-direction pair term | Mean squared-error pair term |','|---|---:|---:|---:|---:|---:|']
        for name,v in s['original_gain_loss_tie_strata'].items():lines.append('| {} | {} | {} | {} | {} | {} |'.format(name,v['n'],v['energies']['common_L2_squared']['mean'],v['energies']['specific_mean_L2_squared']['mean'],v['selected_pair_terms']['signed_goal_direction_difference']['mean'],v['selected_pair_terms']['squared_error_difference']['mean']))
        lines.append('')
    lines+=['## Every parent — unchanged choices, gains, losses and ties included','',
        'Costs/ranks below are authoritative saved S0 costs; ranks use exact cost then lowest index. P0 is not assumed to be the native return. Draw labels: prefix_success, tail_success or failure, with actual success/action clocks. Absorbed identifies the selected oracle terminal feature strictly after a recorded prefix stop. Every candidate, native feature/representation identity, prefix/branch flags, float64 terms and roundoff residual remains in DERIVED-RESULTS.json.','']
    for row in r['parents']:
        d=row['decomposition'];by_index={c['index']:c for c in row['candidates']}
        lines+=['### {} / {} / source {} ({})'.format(row['task'],row['backbone'],row['root_index'],row['root_id']),'',
            'Original stratum: {}; action-choice changed: {}; O0−P0: {}. Source `{}`; accepted output seal `{}`.'.format(row['original_stratum'],d['action_choice_changed'],diff(row['original_O0_minus_P0']),row['source_id'],row['output_seal']['sha256']),
            '', '| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |','|---|---|---|---|---|---|---|']
        for role in ('P0','O0','native','A','B'):
            o=row['outcomes'][role];c=by_index[o['index']]
            clocks='; '.join('{} @ {} (elapsed {})'.format(x['phase'],x['success_clock'],x['actions']) for x in c['evaluation_draws'])
            lines.append('| {} | {} / `{}` | {:.9g} / {} | {:.9g} / {} | {} | {} | {} |'.format(role,o['index'],o['candidate_id'],c['saved_predicted_S0'],c['predicted_rank'],c['saved_realized_S0'],c['realized_rank'],o['two_outcomes'],clocks,c['oracle_prefix']['terminal_feature_post_stop_absorbed']))
        pair=d['pair_ordering'];en=d['energies']
        lines+=['','Selected-pair ordering error (saved / float64): {:.9g} / {:.9g}; goal-direction term {:.9g}; squared-error term {:.9g}; algebra residual {:.9g}; saved-minus-float64 {:.9g}.'.format(pair['saved_relative_ordering_error'],pair['float64_relative_ordering_error'],pair['signed_goal_direction_difference'],pair['squared_error_difference'],pair['identity_residual'],pair['saved_minus_float64_relative_error']),
            'Mean squared error energy {:.9g} = common {:.9g} + specific {:.9g}; coordinate MSE {:.9g}; energy identity residual {:.9g}.'.format(en['total_mean_L2_squared'],en['common_L2_squared'],en['specific_mean_L2_squared'],en['coordinate_MSE'],en['identity_residual']),'']
    lines+=['## Mechanism conclusion and at most one unlaunched proposal','',narrative,'',
        '## Provenance and limitations','',
        '- Original publication: `'+r['original_publication']+'`; frozen execution identity: `'+r['freeze']['sha256']+'`.',
        '- One saved-data-only CPU job; no old estimator or intervals rerun, no model/physics/GPU/training/source/candidate-generation calls, no latent banks persisted.',
        '- Corrected arrays use privileged tested-bank realized consequences and are cast once from float64 back to native saved dtype before the unchanged pure-array S0. Their usefulness does not establish learnability or a latent-manifold repair.',
        '- Saved native/GPU choices remain authoritative; float64 algebra is a separate identity check, with every signed roundoff residual recorded. No near-tie historical choice is changed.',
        '- Prefix absorption and early successes remain in the main result. Post-stop discrepancies are not automatically ordinary continuing-dynamics errors.',
        '- Fixed small candidate banks and two draws are noisy; hindsight maxima are not expected optimal performance. No oracle-recovery percentage or additive success-cause fraction is reported.',
        '- All current sources/settings are exposed discovery. A future practical repair needs independent new source parents, and a diagnostic-transfer claim also needs a setting excluded from recommendation development.',
        '- S1 coordinate-readout weakness does not establish that scoring cannot help. Original DINO reproduction/representation-control, Le-WM scope, uncached-reference and unsaved-role-array limitations remain unchanged.',
        '- Existing prior-art ledger only; no novelty claim or new literature search. No future pipeline or old monitor is launched.','']
    write_new(DOC/'RESULTS.md','\n'.join(lines).encode('utf8'),limit=3000000)
    write_new(DOC/'REPORT-RECEIPT.json',{'status':'COMPLETE_FOUR_SETTING_ALL128_PARENT_REPORT','derived_results':identity(path),'report':identity(DOC/'RESULTS.md'),'mechanism_proposal':identity(DOC/'MECHANISM-PROPOSAL.md'),'all_parent_rows':128})
    print(json.dumps({'status':'COMPLETE_FOUR_SETTING_ALL128_PARENT_REPORT','report':identity(DOC/'RESULTS.md')}))

if __name__=='__main__':main()
