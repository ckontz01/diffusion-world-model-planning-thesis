"""Read-only presentation of the sealed analysis; no new fit/rollout/bootstrap."""
import collections,hashlib,json,statistics,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(n):return json.loads((HERE/n).read_text())
def write(n,v):
    raw=v if isinstance(v,str) else json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n'
    with (HERE/n).open('x',encoding='utf8',newline='\n') as f:f.write(raw)
r=read('REPORT.json');campaign=read('CAMPAIGN-ACCOUNTING.json');pres=read('PRESERVATION.json');fit=read('FIT-RECORDS.json')
assert pres['scientific_aggregate_first_opened_after_verified_backup'] and campaign['successful_unique_tasks']==339
arms=r['controls'];refs=r['source_ids'];y=r['binary_outcomes_by_source'];assert len(refs)==len(y)==32 and len(arms)==8
assert len(set(refs))==32 and all(len(v)==8 and set(v)<={0,1} for v in y)
for i,arm in enumerate(arms):assert sum(v[i] for v in y)/32==r['success_mean'][arm]
alltech=dict(r['all_worker_resources'],analysis=read('ANALYSIS-TECHNICAL.json'));assert len(alltech)==339
alloc={v['spec']['key']:v for v in campaign['allocations'] if v['job']!='304189'}
assert len(alloc)==339 and campaign['gpu_seconds']==19365 and campaign['cpu_stage_seconds']==52
req=json.loads((Path(pres['ssd'])/'REQUEST.json').read_text())
def resource_group(keys):
    ts=[alltech[k] for k in keys];counts=collections.Counter()
    for t in ts:
        for v in t.get('search_and_decision_counts',[]):counts.update(v)
    return {'tasks':len(keys),'allocation_seconds':sum(alloc[k]['seconds'] for k in keys),
        'worker_cpu_seconds':sum(t['process_cpu_seconds'] for t in ts),'worker_wall_through_payload_seconds':sum(t['worker_wall_seconds_through_payload'] for t in ts),
        'max_worker_rss_bytes':max(t['peak_process_rss_bytes'] for t in ts),
        'max_torch_allocated_bytes':max(t.get('peak_torch_allocated_bytes',0) for t in ts),
        'max_torch_reserved_bytes':max(t.get('peak_torch_reserved_bytes',0) for t in ts),
        'image_encodings':sum(t.get('image_encodings',0) for t in ts),
        'fingerprinting_seconds':sum(t.get('fingerprinting_seconds',0) for t in ts),'counts':dict(counts),
        'output_bytes':sum(info['bytes'] for n,info in req['members'].items() if any(n.startswith('run/'+k+'/') for k in keys))}
resources={arm:resource_group([k for k,t in alltech.items() if t['spec'].get('control')==arm]) for arm in arms}
resources['collection']=resource_group([k for k,t in alltech.items() if t['spec']['stage']=='collection'])
resources['cpu_stages']=resource_group([k for k,t in alltech.items() if not t['spec']['gpu']])
resources['all_successful_workers']=resource_group(list(alltech))
decisions={};diagnostics={};support={}
for arm in arms:
    rows=[v for v in r['chosen_branches_and_endpoints'] if v['control']==arm];assert len(rows)==32
    decisions[arm]={'prefix_counts':dict(collections.Counter(str(v['prefix']) for v in rows)),
        'suffix_counts':dict(collections.Counter(str(v['suffix']) for v in rows)),
        'prefix_terminations':sum(v['terminal_prefix'] for v in rows),'suffix_terminations':sum(v['terminal_suffix'] for v in rows),
        'steps_sum':sum(v['steps'] for v in rows),'steps_min':min(v['steps'] for v in rows),'steps_max':max(v['steps'] for v in rows)}
    ds=[v for v in r['observed_prefix_predictive_diagnostics'] if v['control']==arm]
    diagnostics[arm]={}
    for key in ('terminal_ce','conditional_response_nll_per_coordinate','bce','brier'):
        vals=[v[key] for v in ds if v[key] is not None];diagnostics[arm][key]={'n':len(vals),'mean':statistics.mean(vals) if vals else None}
for arm,effects in r['supporting_active_minus'].items():
    assert effects==[row[arms.index('active')]-row[arms.index(arm)] for row in y]
    support[arm]={'mean':sum(effects)/32,'gains':effects.count(1),'losses':effects.count(-1),'ties':effects.count(0),'source_effects':effects}
for name,v in r['primary_comparisons'].items():
    arm=name.replace('active-minus-','');assert v['source_effects']==[row[arms.index('active')]-row[arms.index(arm)] for row in y]
fits={key:fit['run/'+key+'/FIT.json'] for key in ('fit-joint','fit-ordinary')}
assert all(v['updates']==192 for v in fits.values())
summary={'resources':resources,'decisions':decisions,'diagnostics':diagnostics,'supporting_comparisons':support,
    'source_is_unit':True,'bootstrap_rerun':False,'model_or_physics_invoked':False,
    'report_sha256':hashlib.sha256((HERE/'REPORT.json').read_bytes()).hexdigest(),'archive_input_member_bytes':sum(v['bytes'] for v in req['members'].values())}
write('SUMMARY.json',summary)
write('ALL-CHOICES-AND-ENDPOINTS.json',r['chosen_branches_and_endpoints'])
write('ALL-PREDICTIVE-DIAGNOSTICS.json',r['observed_prefix_predictive_diagnostics'])
lines=[]
def p(s=''):lines.append(s)
def table(headers,rows):
    p('| '+' | '.join(headers)+' |');p('|'+'|'.join('---' for _ in headers)+'|')
    for row in rows:p('| '+' | '.join(str(v) for v in row)+' |')
    p()
def pct(v):return f'{100*v:.9g}'
def interval(v):return '['+', '.join(pct(x) for x in v)+']'
p('# ACV0 bounded developmental pilot — complete and preserved')
p();p('24 September 2026. All 339 unique scientific tasks completed; 340 allocated attempts include the historical failed job 304189 and its one authorized replacement. Full acceptance and designated-SSD whole/member verification passed before any scientific aggregate was opened. No successful scientific work was repeated to repair controllers or preservation.')
p();p('## Result and limits');p()
p('Active feedback verification has the highest observed native-success count, 10/32. Its paired gain is 5/32 over the ordinary same-information predictor, 4/32 over Bayesian last-layer feedback, and 3/32 over ordinary early replanning. This is an outcome-informed, 32-source developmental pilot—not untouched confirmation, a safety guarantee, a novelty finding or established general superiority. The early-replanning interval includes zero; the wider Bayesian interval touches zero. No model promotion or follow-up study is authorized.')
p();p('## Fixed scope');p()
p('Unchanged roles: 64 fitting, 16 reporting-only validation, 32 final-development sources. PushT, H75, 150 physical-action maximum; one initial five-action prefix plus ten-action continuation opportunity followed by fixed vanilla-CEM tail from absolute action 15. Maximum 4×4 tree; 128 response samples per prefix; original baseline retained; N300/K30/J30; NumPy float64 search, BF16 Le-WM inference, float32 delivered actions. Two models trained for exactly 192 updates each, with fitting-only preprocessing and final-update selection. Ordinary early replanning remains the unrestricted fresh-search control with its full workload. No reserved payloads or prior-study results are pooled.')
p();p('## All eight arms');p()
table(['Arm','Successes /32','Native success %'],[[arm,sum(v[i] for v in y),pct(r['success_mean'][arm])] for i,arm in enumerate(arms)])
p('## Frozen primary paired comparisons');p()
p('Differences and interval endpoints below are percentage points. Reference/source—not branch, episode, seed or row—is the statistical unit. Frozen bootstrap: 10,000 whole-source resamples, seed 94301. Published intervals are copied from the sealed analysis, not recomputed. The nominal 95% and nominal Bonferroni 98.333% percentile summaries are not finite-sample simultaneous-coverage proofs. The unusual 28.203125 pp endpoint is retained from NumPy quantile interpolation, not silently snapped to a source-count grid.');p()
table(['Active minus','Difference pp','Gains','Losses','Ties','Nominal 95%','Nominal 98.333%'],[[name.replace('active-minus-',''),pct(v['mean']),v['gains'],v['losses'],v['ties'],interval(v['nominal95']),interval(v['nominal_bonferroni98_333'])] for name,v in r['primary_comparisons'].items()])
p('## Declared supporting comparisons');p()
table(['Active minus','Difference pp','Gains','Losses','Ties'],[[arm,pct(v['mean']),v['gains'],v['losses'],v['ties']] for arm,v in support.items()])
p('The mechanism-specific evidence is modest: active exceeds no_update only on source 847 and passive only on source 1326, with all other source outcomes tied in each comparison. These two one-source gains do not establish that adaptive feedback or active prefix selection reliably improves success. No new uncertainty analysis was added for these supporting contrasts.');p()
p('## All 32 source-level outcomes and primary paired effects');p()
p('Binary success 0/1; differences −1/0/+1. Source order is the frozen analysis order. The complete matrix also defines every supporting source effect without selecting favorable sources.');p()
table(['Source']+arms+['A−ordinary','A−Bayes','A−early'],[[ref]+row+[row[arms.index('active')]-row[arms.index(arm)] for arm in ('ordinary','bayesian','early-replan')] for ref,row in zip(refs,y)])
p('## Choices and termination');p()
table(['Arm','Prefix counts (zero-based; None=no tree choice)','Suffix counts','Prefix terminal','Suffix terminal','Physical steps','Min/max'],[[arm,json.dumps(v['prefix_counts'],sort_keys=True),json.dumps(v['suffix_counts'],sort_keys=True),v['prefix_terminations'],v['suffix_terminations'],v['steps_sum'],str(v['steps_min'])+'/'+str(v['steps_max'])] for arm,v in decisions.items()])
p('All 256 per-source/control choices, steps and native endpoints are in ALL-CHOICES-AND-ENDPOINTS.json and byte-identical REPORT.json. Early termination is preserved, not padded or resampled.');p()
p('## Prediction diagnostics (descriptive, selected branches only)');p()
table(['Arm','Terminal CE mean(n)','Response NLL/coordinate mean(n)','Outcome BCE mean(n)','Brier mean(n)'],[[arm]+['n/a(0)' if v[key]['mean'] is None else f"{v[key]['mean']:.8g}({v[key]['n']})" for key in ('terminal_ce','conditional_response_nll_per_coordinate','bce','brier')] for arm,v in diagnostics.items()])
p('Terminal/response diagnostics are from the joint model on each actually chosen prefix. Outcome predictions use ordinary/Bayesian predictions for those respective arms, otherwise the joint model. These are not common-distribution causal comparisons: different controllers may choose different branches. Missing early-terminated response diagnostics remain missing. Model fit and information gain do not replace native success. Bayesian is a last-layer approximation, not a full ALPaCA reproduction.');p()
p('## Fitting records');p()
table(['Model','Updates','Seed','Parameters','Final fit loss','Final validation loss','Recorded fit seconds'],[[key,v['updates'],v['seed'],v['parameters'],v['final_fit_loss'],v['final_validation_loss'],v['seconds']] for key,v in fits.items()])
p('The 64-fit/16-validation traces and preprocessing are preserved in FIT-RECORDS.json. Validation is reporting-only; no favorable epoch selection or additional fitting occurred. Losses between the joint and ordinary objectives are not a comparable success metric.');p()
p('## Resource accounting');p()
p('Total 19365 GPU-allocation seconds = 5.379167 GPU-allocation hours, including 23 seconds for FAILED 304189. All 336 successful GPU workers reported exactly NVIDIA RTX6000 Ada Generation on gpu09 (worker gpu09.cluster), one visible GPU; the site partition label a6000 is not the device name. The failed job lacked a measured exact device string and is not retroactively claimed to have one. Three CPU stages used 52 allocation-wall seconds, no GPU. Caps 220800/21600 seconds were unchanged. There were zero automatic retries and zero R2–R6 replacements.');p()
table(['Group','Tasks','Allocation s','Worker CPU s','Worker wall through payload s','Max RSS B','Output bytes'],[[k,v['tasks'],v['allocation_seconds'],f"{v['worker_cpu_seconds']:.6f}",f"{v['worker_wall_through_payload_seconds']:.6f}",v['max_worker_rss_bytes'],v['output_bytes']] for k,v in resources.items()])
keys=sorted({key for v in resources.values() for key in v['counts']})
table(['Group']+keys,[[k]+[v['counts'].get(key,0) for key in keys] for k,v in resources.items() if k!='cpu_stages'])
table(['Group','Image encodings','Fingerprinting s','Max Torch allocated B','Max Torch reserved B'],[[k,v['image_encodings'],f"{v['fingerprinting_seconds']:.6f}",v['max_torch_allocated_bytes'],v['max_torch_reserved_bytes']] for k,v in resources.items()])
p('Work/counter scopes: physical_steps are actual simulated actions; rollout_calls, sequences, latent_transitions and CEM solves are distinct workload counters, not interchangeable forward passes. outcome_queries are learned-outcome score queries, not extra physical endpoints. Encodings include the recorded goal/observation work. Worker wall and process CPU stop after payload/check work and before writing TECHNICAL/seal/final storage validation; they are not full Slurm elapsed time. Fingerprinting is included within worker timings, so do not add it again. Worker RSS is a process high-water mark, not whole-node RAM or a sum of peaks. Torch counters are allocator scopes, not total GPU memory. CPU process seconds can exceed elapsed wall on multithreaded workers. No throughput equivalence or speedup claim is inferred across devices.');p()
p('FINAL-SCHEDULER.json preserves raw top-level and step TotalCPU/MaxRSS fields separately; reported process CPU comes from worker measurements rather than treating top-level 00:00:00 as actual CPU use. Controller CPU/RSS was not measured after exit and is unavailable; controller/transport event times and archive CPU/wall are retained separately, not charged as GPU allocations. Failed 304189 process CPU is not imputed from its 23-second allocation.');p()
p('## Authentication and preservation');p()
p(f"Original scientific manifest: `{pres['source_manifest']}`. Worker approval: `{pres['worker_approval']}`. R5 acceptance manifest:`{pres['r5_manifest']}`; R6 archive-only manifest:`{pres['r6_manifest']}`. Original input/role/grid/backend identities remain in the sealed source and MODEL-FREEZE.json; both 192-update model seals predate final-source evaluation.")
p();freeze=read('MODEL-FREEZE.json')
table(['Model/file','SHA256'],[[key+'/SEAL.json',v['seal']] for key,v in freeze['models'].items()]+[[key+'/'+n,info['sha256']] for key,v in freeze['models'].items() for n,info in v['files'].items() if n in ('joint.npz','ordinary.npz','bayesian.npz','PREPROCESSING.json')])
p(f"Final archive: 814663680 bytes, 3308 members, SHA256 `{pres['archive_sha256']}`. Archive input member bytes:{summary['archive_input_member_bytes']}. Designated native SSD: `{pres['ssd']}/final.tar`. Whole hash and every member verified; request SHA `{pres['request_sha256']}`; backup receipt SHA `{pres['backup_receipt_sha256']}`. Archive wall{pres['archive_wall_seconds']:.6f}s/CPU{pres['archive_cpu_seconds']:.6f}s; transfer+verification{pres['transfer_wall_seconds']:.6f}s. No historical archive was recreated or transferred. All 13 original/recovery roots, failed-v2 provenance, original STOPs, 339 outputs/models and authorities are retained.")
p();p('R4 completed science then stopped at a live-queue finalization check. The triggering queue stdout was not preserved; later reconciliation proved no live or unknown allocation. R5 metadata-only acceptance authenticated all outputs unchanged. Its archive attempt stopped before file creation on a nested-root label mismatch; R6 corrected only inventory paths, preserving that failure. Exactly one final archive was created and its first SSD transfer passed. No scientific rerun or reanalysis was used. Full finite recovery contracts, tests, remote commits and small-package backups remain in adjacent finalization-r5 and preservation-r6 records.');p()
p('## Deliverables and boundary');p()
p('REPORT.json is byte-identical to the sealed cluster analysis. SUMMARY.json is presentation arithmetic from that completed report, without new fitting, simulation, bootstrap or comparator selection. CAMPAIGN-ACCOUNTING.json contains all 340 attempts; R5-COMPLETE.json contains 339 successful suppliers; full scientific effect/choice/diagnostic rows are retained. This publication changes no scientific output. Continue to preserve historical decisions and E12 drafts. AV1 is unlaunched. No next experiment or model promotion is automatically authorized.');p()
write('RESULTS-20260924.md','\n'.join(lines))
print(json.dumps({'resources':resources,'supporting':support,'decisions':decisions,'diagnostics':diagnostics,'report_sha256':summary['report_sha256']},indent=2))
