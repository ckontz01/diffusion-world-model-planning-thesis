"""Format the preserved, fixed ACVM1 result without rerunning its estimator."""
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf8'))


def main():
    report, summary = read('REPORT.json'), read('SUMMARY.json')
    preservation, accounting = read('PRESERVATION.json'), read('ACCOUNTING.json')
    accepted, freeze, fits = read('FINAL-ACCEPTANCE.json'), read('MODEL-FREEZE.json'), read('FIT-RECORDS.json')
    assert preservation['opened_after_verified_preservation']
    assert summary['report_sha256'] == hashlib.sha256((HERE / 'REPORT.json').read_bytes()).hexdigest()
    assert accounting['attempts'] == 8199 and accounting['successful_unique_tasks'] == 8197
    assert len(report['evidence']) == len({tuple(v['identity']) for v in report['evidence']}) == 8192
    assert len(report['estimator']['contrasts']) == 7 and report['estimator']['source_is_unit']
    assert report['estimator']['bootstrap_seed'] == 94431 and report['estimator']['bootstrap_resamples'] == 10000
    contrast_names = ['active-minus-no_update', 'active-minus-committed_feedback', 'committed_feedback-minus-static',
                      'no_update-minus-static', 'feedback-by-prefix-interaction', 'active-minus-ordinary', 'active-minus-early-replan']
    lines = []
    def p(value=''):
        lines.append(value)
    def table(headers, rows):
        p('| ' + ' | '.join(headers) + ' |')
        p('|' + '|'.join('---' for _ in headers) + '|')
        for row in rows:
            p('| ' + ' | '.join(str(v) for v in row) + ' |')
        p()
    def pp(value):
        return f'{100 * value:.8g}'
    def interval(values):
        return '[' + ', '.join(pp(v) for v in values) + ']'
    p('# ACVM1 mechanism replication — complete fixed developmental study')
    p()
    p('29 September 2026. Independent acceptance passed for 8,197 successful unique tasks and all 8,199 allocation attempts. These comprise four new CPU fits, 8,192 GPU evaluation episodes, one CPU analysis, and two preserved failed fitting attempts. No successful task was recomputed. The designated SSD archive passed whole-file and every-member verification before scientific aggregates were opened.')
    p()
    p('## Result in brief')
    p()
    p('The fixed experiment does not establish a clear active-feedback mechanism advantage. Active success was 23.5026%, compared with no_update 22.9818%, committed_feedback 23.3073%, static 22.4609%, ordinary 24.3490% and early replanning 26.5625%. The primary active-minus-no_update estimate is +0.5208 percentage points (descriptive 95% interval [-0.5859, +1.6276]); active-minus-committed_feedback is +0.1953 points ([-0.5208, +0.9766]). Both intervals include zero, as do their multiplicity-adjusted nominal intervals and conservative bounds. The latter contrast changes sign across the fixed pairs.')
    p()
    p('All seven descriptive 95% intervals include zero. Ordinary prediction and early replanning have higher observed success than active, but the corresponding paired intervals also include zero: this is not evidence establishing their general superiority. The two primary point estimates are well below the declared +5-point practical effect; their nominal bootstrap upper endpoints are also below +5 points, whereas the conservative Hoeffding intervals remain wide. This pattern does not demonstrate a practically meaningful mechanism benefit, prove equivalence or prove that the true effect is zero. No favorable seed, source subset, checkpoint or outcome was selected.')
    p()
    p('## Scope and statistical unit')
    p()
    p('The frozen ordered set contains 512 source-disjoint developmental references. Each source has five learned policies across three fixed joint/ordinary model pairs, plus one early-replanning episode: 16 actual episodes/source. Early replanning is reused only algebraically in comparisons. The old ACV0 32-source outcomes are excluded. The 64 fitting sources and 16 reporting-only validation sources retain their roles. This is an outcome-informed developmental study, not untouched confirmation, a safety guarantee, model promotion or a novelty verdict.')
    p()
    p('Source variation is the inferential unit. The three fixed training-seed pairs are reported individually and averaged within each source; they are not 1,536 independent sources or a sample supporting population inference over all possible training seeds. H75, 150 physical actions, one five-action prefix/ten-action continuation opportunity, fixed baseline tail, maximum 4×4 tree, 128 integrated responses/prefix, all precisions/ties and the physical interface remained frozen.')
    p()
    p('The original active controller retains its direct-baseline commitment guard; committed_feedback releases the suffix commitment even when static selected the baseline prefix. These unchanged guard semantics mean the four-policy interaction is an operational controller comparison, not a perfectly isolated causal estimate of information gathering. Decision.values retains its historical active-score meaning and is not relabelled as the committed prefix criterion. Full saved decision/guard metadata accompanies the result.')
    p()
    p('## All six policies and all three fixed pairs')
    p()
    table(['Policy', 'Pair 0 successes /512', 'Pair 1 successes /512', 'Pair 2 successes /512', 'Fixed-pair mean success %'],
          [[arm] + item['successes_by_pair'] + [pp(item['fixed_pair_average_success_rate'])]
           for arm, item in summary['arms'].items() if arm != 'early-replan'])
    early = summary['arms']['early-replan']
    p(f"Early replanning: {early['successes_total']}/512 = {pp(early['success_rate'])}%. Exactly 512 early-replan episodes were executed.")
    p()
    p('## Seven frozen contrasts')
    p()
    p('Effects and interval endpoints are percentage points. The first two contrasts are primary. All intervals below are copied from the sealed analysis. The 10,000 bootstrap resamples use whole sources and fixed seed 94431. The descriptive 95% and nominal Bonferroni 99.285714% bootstrap intervals are not finite-sample guarantees. The family-seven Hoeffding bounds are conservative and require independent bounded source observations; the observed finite-cohort means themselves are descriptive.')
    p()
    table(['Contrast', 'Effect pp', 'Pair 0 pp', 'Pair 1 pp', 'Pair 2 pp', 'Descriptive 95%', 'Nominal Bonferroni', 'Simultaneous Hoeffding 95%'],
          [[name, pp(item['effect'])] + [pp(v) for v in item['per_seed_means']] +
           [interval(item['descriptive95']), interval(item['nominal_bonferroni99_285714']), interval(item['simultaneous_hoeffding95'])]
           for name in contrast_names for item in [report['estimator']['contrasts'][name]]])
    p(f"Additional Hoeffding-positive certificate: **{report['hoeffding_positive_additional_certificate']}**. This stringent additional certificate is not a required scientific-success criterion. Its absence is not a scientific-failure verdict. The declared five-percentage-point practical effect must be interpreted alongside all uncertainty evidence. No threshold, multiplicity correction, stopping rule or estimator was changed after outcomes became available.")
    p()
    p('## All 512 source results')
    p()
    p('Each policy cell lists binary outcomes for pairs 0/1/2, in that order. The early column is one actual source outcome. Effects average the three fixed pair differences within each source. Full source-by-pair effects remain in REPORT.json; ALL-SOURCE-RESULTS.json contains the complete source table and ALL-EPISODES.json contains all 8,192 identities, choices, steps, successes and seals.')
    p()
    contrasts = contrast_names
    table(['Source'] + report['arms'] + ['early-replan'] + contrasts,
          [[reference] + ['/'.join(str(report['successes'][i][pair][arm]) for pair in range(3)) for arm in range(5)] +
           [report['early_successes'][i]] + [pp(report['estimator']['contrasts'][name]['source_effects'][i]) for name in contrasts]
           for i, reference in enumerate(report['ordered_sources'])])
    p('## Decisions, guards and endpoints')
    p()
    p('ALL-DECISIONS.json preserves every episode’s complete saved branch metadata, including the decision/guard records available in the frozen evidence. The verified archive additionally preserves every action, state, feature, image and endpoint array. Final analysis independently reconstructed exact initial-tree and same-action prefix coupling from saved arrays for all 8,192 episodes. Later trajectories were allowed to diverge after policy choices diverged. No unexecuted counterfactual outcome was inferred.')
    p()
    decision_rows = []
    for arm in report['arms'] + ['early-replan']:
        items = [v for v in report['evidence'] if v['identity'][2] == arm]
        decision_rows.append([arm, len(items), json.dumps(dict(collections.Counter(str(v['prefix']) for v in items)), sort_keys=True),
                              json.dumps(dict(collections.Counter(str(v['suffix']) for v in items)), sort_keys=True),
                              sum(v['steps'] for v in items), min(v['steps'] for v in items), max(v['steps'] for v in items)])
    table(['Policy', 'Episodes', 'Prefix counts', 'Suffix counts', 'Physical actions', 'Min actions', 'Max actions'], decision_rows)
    p('## Six-model provenance')
    p()
    table(['Pair/model', 'Seed', 'Reused', 'Checkpoint SHA256'],
          [[name, value['seed'], value['reused'], value['sha256']] for name, value in freeze['models'].items()])
    table(['New fit', 'Seed', 'Updates', 'Parameters', 'Final fit loss', 'Final validation loss', 'Fit seconds'],
          [[name, value['seed'], value['updates'], value.get('parameters'), value.get('final_fit_loss'),
            value.get('final_validation_loss'), value.get('seconds')] for name, value in fits.items()])
    p('Original pair 94011/94012 was loaded from authenticated final checkpoints without refitting. New pairs 94411/94412 and 94421/94422 used exactly 192 updates each. Full traces are preserved. Preprocessing used fitting sources only; validation remained reporting-only. Six checkpoint identities and preprocessing were frozen before evaluation access. No checkpoint, seed or ensemble selection occurred. The earlier saved-data mechanism findings, including worse conditional prediction metrics, remain unchanged.')
    p()
    p('## Complete costs and measurement scopes')
    p()
    p(f"GPU allocation: {accounting['gpu_seconds']:,} seconds = {accounting['gpu_seconds']/3600:.6f} hours, within 2,457,600 seconds. CPU-stage allocation-wall: {accounting['cpu_stage_seconds']:,} seconds, within the explicitly approved 36,008-second cumulative cap. Failed allocations 304589 and 304591 consumed 0 and 8 CPU-stage seconds and are included. Original R2 successful fit 304593 consumed 11 seconds and was retained without repetition. ACCOUNTING.json and FINAL-SCHEDULER.json preserve every attempt and its exact allocation supplier.")
    p()
    table(['Policy/stage', 'Tasks', 'Allocation s', 'Worker wall s', 'Worker CPU s', 'Max process RSS B', 'Saved worker bytes'],
          [[name, value['tasks'], value['allocation_seconds'], f"{value['worker_wall_seconds']:.6f}", f"{value['process_cpu_seconds']:.6f}",
            value['max_process_rss_bytes'], value['output_bytes']] for name, value in summary['resources'].items()])
    table(['Policy/stage', 'Max Torch allocated B', 'Max Torch reserved B', 'Image encodings', 'Fingerprinting s'],
          [[name, value['max_torch_allocated_bytes'], value['max_torch_reserved_bytes'], value['image_encodings'], f"{value['fingerprinting_seconds']:.6f}"]
           for name, value in summary['resources'].items()])
    count_names = sorted({key for value in summary['resources'].values() for key in value['counts']})
    table(['Policy/stage'] + count_names,
          [[name] + [value['counts'].get(key, 0) for key in count_names] for name, value in summary['resources'].items()])
    p('All evaluation workers were independently associated with their exact Slurm allocation, gpu09/gpu09.cluster, one visible NVIDIA RTX 6000 Ada Generation and their original per-job limits. Process RSS is a worker high-water mark, not whole-node RAM. Torch allocator peaks do not measure whole-device VRAM. Worker wall/CPU measurements end before writing the final technical receipt and seal; they are not complete allocation elapsed time. Fingerprinting is included in worker timings and must not be added again. Physical actions, rollout calls, sequences and latent transitions have different units. Queue and dispatch overhead are excluded from allocation charges. Controller process CPU/RSS and archive process CPU were not recorded by this frozen finalizer and are not imputed.')
    p()
    p('## Authentication and preservation')
    p()
    p(f"Scientific manifest `{accepted['package']}`; original worker approval `{accepted['approval']}`; R3 manifest `{accepted['recovery_manifest']}`; R3 approval `{accepted['recovery_approval']}`. Model freeze `{accepted['model_freeze_sha256']}`; first16 gate `{accepted['technical_gate_sha256']}`. The first complete source block passed before source2. All original STOPs and finite recovery authorities remain preserved.")
    p()
    archive = preservation['archive']
    p(f"Verified archive: **{archive['bytes']:,} bytes / {archive['members']:,} regular members**, SHA256 `{archive['sha256']}`. Location: `{preservation['ssd']}/final.tar`. Whole-file and every-member verification passed. Input member bytes: {preservation['input_member_bytes']:,}. Request SHA256 `{preservation['request_sha256']}`; verification receipt SHA256 `{preservation['verification_sha256']}`. Archive wall {preservation['archive_wall_seconds']:.6f}s; first transfer plus verification {preservation['transfer_and_verification_wall_seconds']:.6f}s.")
    p()
    table(['Archive root', 'Member bytes'], sorted(preservation['root_member_bytes'].items()))
    p(f"Complete evaluated-worker bytes: {preservation['evaluation_worker_bytes']:,}; all other archived member bytes: {preservation['other_member_bytes']:,}. All worker, group, live, controller and archive caps passed. An inclusive bound counting the live roots, remote archive, all new-study SSD files and a further 1 GB allowance for preservation metadata/publication is {preservation['inclusive_bytes_upper_bound']:,} bytes, below the 80 GB cap.")
    p()
    p('One new-study archive covers nine roots: original scientific source, R1/R2/R3 sources, original/R1/R2/R3 controls and the full run. Historical studies were not rearchived or retransferred. Scientific aggregates were first opened after designated-SSD verification. REPORT.json is byte-identical to the sealed analysis; this publication performs presentation arithmetic only and does not rerun the estimator, fitting, simulation or model inference. Historical decisions and E12 drafts remain unchanged. AV1 remains unlaunched. No automatic follow-up research or promotion is authorized.')
    p()
    with (HERE / 'RESULTS-20260929.md').open('x', encoding='utf8', newline='\n') as stream:
        stream.write('\n'.join(lines))
    with (HERE / 'PUBLICATION-CHECK.json').open('x', encoding='utf8', newline='\n') as stream:
        json.dump(dict(passed=True, source_count=512, episodes=8192, successful_tasks=8197, attempts=8199,
                       fixed_contrasts=7, fixed_seed_pairs=3, source_is_unit=True, analysis_rerun=False,
                       report_sha256=summary['report_sha256']), stream, sort_keys=True, indent=2)
        stream.write('\n')
    print('Complete fixed report formatted; all publication identity checks passed.')


if __name__ == '__main__':
    main()
