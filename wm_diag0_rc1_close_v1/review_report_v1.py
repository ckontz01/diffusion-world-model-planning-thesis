"""Post-SSD parent arithmetic/coverage review, without changing sealed results."""
import json,math,statistics
from .common import DOC,identity,write_new

WEIGHTS={'O0-P0':(-1,0,1,0),'P1-P0':(-1,1,0,0),'O1-O0':(0,0,-1,1),'interaction':(1,-1,-1,1)}
CELLS=('P0','P1','O0','O1')
def close(a,b):
    if type(a) not in (int,float) or type(b) not in (int,float) or not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>1e-12:raise ValueError('complete report arithmetic')

def group(p,n):
    if p['n_independent_parents']!=n or len(p['parent_ids'])!=n or len(set(p['parent_ids']))!=n or len(p['source_cells'])!=n:raise ValueError('independent parent coverage')
    for row in p['source_cells']:
        if len(row)!=4 or any(type(x) not in (int,float) or not 0<=x<=1 for x in row):raise ValueError('four bounded cells per parent')
    for index,name in enumerate(CELLS):
        close(p['cells'][name],statistics.mean(row[index] for row in p['source_cells']))
        ci=p['cell_ci95'][name]
        if len(ci)!=2 or not 0<=ci[0]<=ci[1]<=1:raise ValueError('bounded fixed cell intervals')
    for name,weights in WEIGHTS.items():
        c=p['contrasts'][name];effects=[sum(a*b for a,b in zip(row,weights)) for row in p['source_cells']]
        if effects!=c['parent_effects']:raise ValueError('all exact paired parent effects')
        close(c['mean'],statistics.mean(effects))
        if (c['gains'],c['losses'],c['ties'])!=(sum(x>0 for x in effects),sum(x<0 for x in effects),sum(x==0 for x in effects)):raise ValueError('every gain/loss/tie reported')
        ci=c['ci95_percentile']
        if len(ci)!=2 or not all(type(x) in (int,float) and math.isfinite(x) for x in ci) or ci[0]>ci[1]:raise ValueError('finite ordered fixed contrast interval')
    if any(len(p[k])!=n for k in ('native_parent','candidate_counts','candidate_mean_success','hindsight_optimistic_parent','split_draw_hindsight_parent','selected_indices')):raise ValueError('native/bank/hindsight rows complete')
    close(p['native_reference'],statistics.mean(p['native_parent']))

def main():
    release=json.loads((DOC/'RESULTS-RELEASED.json').read_text())
    if identity(DOC/'RESULTS.json')!=release['RESULTS'] or identity(DOC/'FINAL-SSD-VERIFIED.json')!=release['final_gate']:raise PermissionError('actual final SSD/result identity gate')
    result=json.loads((DOC/'RESULTS.json').read_text());acceptance=json.loads((DOC/'ACCEPTANCE.json').read_text())
    expected={task+'|'+backbone for task in ('pusht','reacher') for backbone in ('lewm','dinowm_noprop')}
    if set(result['settings'])!=expected or set(result['head_quality'])!=expected or set(result['termination_reasons'])!=expected:raise ValueError('all four settings, quality and branch reasons')
    for name,p in result['settings'].items():
        group(p,32)
        if set(result['termination_reasons'][name])!=set(p['parent_ids']):raise ValueError('termination reason every source parent')
        q=result['head_quality'][name];width=6 if name.startswith('pusht|') else 2
        if set(q)!= {'coordinate_mae','coordinate_rmse'} or any(len(q[k])!=width or any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in q[k]) for k in q):raise ValueError('all held-out readout coordinate errors disclosed')
    for task in ('pusht','reacher'):
        if result['settings'][task+'|lewm']['parent_ids']!=result['settings'][task+'|dinowm_noprop']['parent_ids']:raise ValueError('paired backbones must not inflate source-parent n')
    for p in result['pooled_by_backbone'].values():group(p,64)
    if len(result['local_task_distances'])!=128 or len(result['feature_prediction_diagnostics'])!=128 or len(acceptance['parent_output_seals'])!=128:raise ValueError('all parent diagnostic and accepted-seal coverage')
    if len(result['head_lineage'])!=6 or sum(x['active'] is True for x in result['head_lineage'])!=4:raise ValueError('six retained/four active heads')
    report=(DOC/'PRO-RESULTS-HANDOFF.txt').read_text(encoding='utf8')
    if report.count('gains/losses/ties=')!=16 or any('- '+x not in report for x in result['limitations']) or 'not an external scientific replication or peer review' not in report:raise ValueError('complete unfiltered report and accurate validation scope')
    proof={'status':'POST_SSD_COMPLETE_REPORT_PARENT_ARITHMETIC_COVERAGE_AND_LIMITATIONS_REVIEW_PASSED',
        'results':identity(DOC/'RESULTS.json'),'acceptance':identity(DOC/'ACCEPTANCE.json'),'report':identity(DOC/'PRO-RESULTS-HANDOFF.txt'),
        'final_gate':identity(DOC/'FINAL-SSD-VERIFIED.json'),'all_four_settings_and_16_fixed_contrasts_checked':True,
        'source_parent_n_not_inflated_by_backbones_candidates_or_draws':True,'all_128_parent_diagnostics_and_6_retained_4_active_heads_present':True,
        'sealed_scientific_bytes_modified':False,'new_estimator_fit_model_simulator_or_experiment':False,'all_limitations_disclosed':True}
    write_new(DOC/'REPORT-REVIEW-001.json',proof);print(json.dumps(proof))

if __name__=='__main__':main()
