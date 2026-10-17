"""Complete fixed-results handoff, accessible only after actual final SSD gate."""
import json,statistics
from pathlib import Path
from .common import DOC,identity

def main():
    gate=json.loads((DOC/'FINAL-SSD-VERIFIED.json').read_text())
    release=json.loads((DOC/'RESULTS-RELEASED.json').read_text())
    ssd=Path(gate['archive']).parent
    if gate['status']!='COMPLETE_STUDY_INDEPENDENT_ACCEPTANCE_AND_FINAL_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_GATE_PASSED':raise PermissionError('actual final gate required')
    if identity(DOC/'FINAL-SSD-VERIFIED.json')!=identity(ssd/'FINAL-SSD-VERIFIED.json') or release['final_gate']!=identity(DOC/'FINAL-SSD-VERIFIED.json'):raise PermissionError('matching native SSD/release chain')
    for name in ('RESULTS','ACCEPTANCE'):
        if identity(DOC/(name+'.json'))!=release[name]:raise ValueError('sealed complete payload changed')
    r=json.loads((DOC/'RESULTS.json').read_text());a=json.loads((DOC/'ACCEPTANCE.json').read_text())
    if a['status']!='ALL120_SOURCES_6_RETAINED_FITS_4_ACTIVE_HEADS_128_PARENTS_INDEPENDENTLY_ACCEPTED' or len(a['parent_output_seals'])!=128:raise ValueError('complete independent acceptance')
    if len(r['settings'])!=4 or any(x['n_independent_parents']!=32 for x in r['settings'].values()):raise ValueError('all four complete fixed settings')
    lines=['WM-DIAG0-A2 RC1 — COMPLETE RESULTS FOR PRO REVIEW',
        '', 'STATUS: Complete analysis independently reconstructed from original accepted inputs; final uncompressed archive independently verified against originals and read back whole/every-member on designated THESIS_SSD.',
        'The RESULTS.json historical status says pending SSD because those exact sealed bytes were created before preservation. FINAL-SSD-VERIFIED.json supplies the subsequent completed gate; archived scientific bytes were not rewritten.',
        '', 'DESIGN AND INTERPRETATION',
        'Four task/backbone settings; 32 diagnostic source parents per task, shared across the paired backbones, hence 64 source parents per backbone. All 120 source roots, six retained fits, four active heads and 128 task/backbone parent evaluations accepted. Those 128 evaluations are not 128 independent source parents. The 124 ordinary GPU runs plus four technical evaluations supply the 128 evaluations.',
        'P0: predicted consequences / original S0 score. P1: predicted consequences / fixed S1 coordinate-readout score. O0: actually realized prefix consequences encoded by the same backbone / S0. O1: realized encoded consequences / S1.',
        'Each parent uses the same frozen candidate action bank across cells. Two evaluation draws are averaged within parent, not treated as extra independent observations. Candidates and paired backbone evaluations also do not increase independent source-parent n. The exact native-return reference is distinct from bank-selected P0.',
        'S1 is a fixed float64 ridge coordinate readout (alpha=1), not a tuned router or predictor repair. The realized row supplies true prefix consequences, not evaluation-tail success labels.',
        'Intervals: descriptive 95% percentile parent-paired bootstrap, 10,000 resamples, seed 20261004. No multiplicity-controlled or causal decomposition claim. No cross-backbone significance test is made.',
        '', 'ALL FOUR SETTINGS — SUCCESS FRACTIONS AND CELL INTERVALS']
    for key,p in r['settings'].items():
        lines.append('\n'+key+'; independent parents='+str(p['n_independent_parents']))
        for cell,value in p['cells'].items():
            ci=p['cell_ci95'][cell];lines.append('  {}: {:.6f} [{:.6f}, {:.6f}]'.format(cell,value,*ci))
        lines.append('  Exact native-return reference: {:.6f}; initial successes: {}'.format(p['native_reference'],p['initial_success_count']))
        lines.append('  Optimistic tested-bank hindsight mean: {:.6f}; split-draw hindsight mean: {:.6f}'.format(statistics.mean(p['hindsight_optimistic_parent']),statistics.mean(p['split_draw_hindsight_parent'])))
        for name,x in p['contrasts'].items():
            lines.append('  {}: {:.6f} [{:.6f}, {:.6f}]; gains/losses/ties={}/{}/{}'.format(name,x['mean'],*x['ci95_percentile'],x['gains'],x['losses'],x['ties']))
    lines+=['','POOLED WITHIN BACKBONE — DESCRIPTIVE ONLY (64 parents each)']
    for key,p in r['pooled_by_backbone'].items():
        lines.append('\n'+key+'; cells='+json.dumps(p['cells'],sort_keys=True)+'; native reference='+str(p['native_reference']))
        for name,x in p['contrasts'].items():lines.append('  {}: {:.6f} [{:.6f}, {:.6f}]'.format(name,x['mean'],*x['ci95_percentile']))
    lines+=['','HELD-OUT REALIZED READOUT QUALITY — NO REFITTING OR THRESHOLD SELECTION',json.dumps(r['head_quality'],sort_keys=True,indent=2),
        '', 'COMPLETE DIAGNOSTIC AND PROVENANCE FILES',
        'RESULTS.json contains every parent effect, gains/losses/ties, selected indices, candidate counts and means, native reference, initial successes, termination reasons for every branch, local task distances, feature-prediction diagnostics, head lineage and failure-inclusive accounting. These are all released, not a favorable subset.',
        'Prediction MSE is within-backbone only: latent units are not comparable across backbones. Hindsight is optimistic tested-bank opportunity, not deployable performance or global solvability.',
        'The original failed grid parent is retained, not silently dropped. Recovery reused every successful run and replaced only the diagnosed failed run; its missing completed usage seal is charged conservatively at full approved parent maxima, not presented as retrospective instrumentation.',
        '', 'ALL FIXED LIMITATIONS']
    lines+=['- '+x for x in r['limitations']]
    lines+=['', 'VERIFICATION', 'Final CPU job: '+gate['terminal_CPU_job'],
        'Final contract: '+gate['contract']['sha256'], 'Finalizer source commit: '+gate['source_commit'],
        'Archive: '+gate['archive'], 'Archive bytes: '+str(gate['whole']['bytes']), 'Archive SHA256: '+gate['whole']['sha256'],
        'Independent acceptance: ACCEPTANCE.json; complete results: RESULTS.json; terminal provenance: TERMINALCPU001.json; final native readback: FINAL-SSD-VERIFIED.json.',
        '', 'REVIEW REQUEST',
        'Review whether the complete four-cell evidence supports a limited diagnostic conclusion about the fixed tested banks, the prediction/score interaction and the disclosed readout/representation limitations. Challenge unsupported causal or architectural interpretations. This is not authorization for a new experiment or science change.']
    path=DOC/'PRO-RESULTS-HANDOFF.txt'
    with path.open('xb') as out:out.write(('\n'.join(lines)+'\n').encode('utf8'))
    print(json.dumps({'status':'COMPLETE_FIXED_RESULTS_HANDOFF_WRITTEN_AFTER_FINAL_SSD','report':identity(path)}))

if __name__=='__main__':main()
