"""Decoder-corrected reduction plus unchanged supplementary checks, 32 references.

Two cohorts are reported explicitly. No model or simulator imports/execution.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import verify_diffusion_branch as decoder
import verify_diffusion_branch_supplement as semantic
from diffusion_bottleneck import require,require_sha,sha256,write_report,checked_child
from diffusion_extension_control import REFS

def verify_source(root,expected):
    require_sha(root/'SOURCE-MANIFEST.sha256',expected)
    for line in (root/'SOURCE-MANIFEST.sha256').read_text().splitlines():
        digest,name=line.split(maxsplit=1);require_sha(checked_child(root,name),digest)

def effects(rows,refs):
    records=[]
    for ref in refs:
        r=[x for x in rows if x['reference']==ref and x['available']]
        result={'reference':ref,'available_anchors':len(r),'contrasts':{}}
        for cond in ('state','latent','joint','greedy64'):
            by_h=[]
            for h in (75,150):
                points=[x for x in r if x['horizon']==h]
                if not points:continue
                b=[x['selected']['baseline']['first_chunk' if cond=='greedy64' else 'committed_two_chunk'] for x in points]
                q=[x['greedy64_first_chunk'] if cond=='greedy64' else x['selected'][cond]['committed_two_chunk'] for x in points]
                by_h.append({'horizon':h,'anchors':len(points),
                    'margin_improvement':float(np.mean([u['closest_margin']-v['closest_margin'] for u,v in zip(b,q)])),
                    'success_difference_pp':100*float(np.mean([int(v['success'])-int(u['success']) for u,v in zip(b,q)]))})
            result['contrasts'][cond]={'per_horizon':by_h,
                'margin_improvement':float(np.mean([x['margin_improvement'] for x in by_h])) if len(by_h)==2 else None,
                'success_difference_pp':float(np.mean([x['success_difference_pp'] for x in by_h])) if len(by_h)==2 else None}
        records.append(result)
    summary={}
    for cond in ('state','latent','joint','greedy64'):
        summary[cond]={}
        for metric in ('margin_improvement','success_difference_pp'):
            values=np.asarray([r['contrasts'][cond][metric] for r in records if r['contrasts'][cond][metric] is not None])
            require(len(values)>0,'No reference-level effects')
            rng=np.random.default_rng(20260914)
            samples=values[rng.integers(0,len(values),size=(10000,len(values)))].mean(axis=1)
            summary[cond][metric]={'n_references':len(values),'mean':float(values.mean()),'median':float(np.median(values)),
                'min':float(values.min()),'max':float(values.max()),'positive':int((values>0).sum()),
                'negative':int((values<0).sum()),'zero':int((values==0).sum()),
                'exploratory_reference_bootstrap_95':np.quantile(samples,[.025,.975]).tolist()}
    return {'reference_count':len(refs),'reference_effects':records,'summary':summary,
        'estimand':'Within-reference equal mean of H75/H150, each using available fixed anchors; both horizons required; repeat0 only. Positive favors intervention. Greedy uses matched first-chunk endpoints only.',
        'uncertainty':'Post-result development reference-resampling intervals, not confirmation; unavailable anchor counts retained; repeated processes are not independent samples.'}

def analyze(root,study,src,manifest_sha,pilot_src,pilot_root,canonical,pilot_aggregate,dispatch,out):
    verify_source(src,manifest_sha);verify_source(pilot_src,semantic.LAUNCH_SHA)
    require_sha(canonical,semantic.CANONICAL_SHA);cert=json.loads(canonical.read_text())
    require_sha(pilot_aggregate,semantic.AGGREGATE_SHA);old=json.loads(pilot_aggregate.read_text())
    require(str(study.resolve())==cert['canonical_study'],'Wrong canonical study')
    control=json.loads(dispatch.read_text())
    require(control['all_56_completed'] is True and len(set(control['job_ids']))==56,'Incomplete dispatch')
    require(control['allocation_seconds']<=7200 and control['bytes']<=1_000_000_000,'Cost/storage violation')
    reports={};seals={}
    for ref in REFS:
        for rep in (0,1):
            path=root/f'ref-{ref}-repeat-{rep}';r,s=decoder.seal(path)
            require((r['reference'],r['repeat'])==(ref,rep),'Run identity')
            if ref in REFS[:4]:
                require(path.resolve()==(pilot_root/path.name).resolve(),'Pilot not reused in place')
                require(s==old['seals'][str(pilot_root/path.name)],'Pilot bytes changed')
            reports[ref,rep]=r;seals[str(path)]=s
    # Reuse the accepted decoder arithmetic and repeat-array checks unchanged.
    decoder.REFS=REFS
    aggregate=decoder.analyze(root)
    aggregate['runs']=64;aggregate['scope']='32 fixed exposed development references; four reused and28 new; no efficacy claim'
    aggregate.pop('linear_32_reference_two_repeat_runner_seconds')
    write_report(out/'DECODER-AGGREGATE.json',aggregate,(root,study,src,pilot_src))
    counts=[];all_steps=all_branches=0;history_hashes={}
    for ref in REFS:
        task=f'stage-0/task-{ref//64:04d}';result=study/task/'results/RESULT.json'
        require_sha(result,cert['shards'][task]['result_sha256']);historical=json.loads(result.read_text())
        rows=[x for x in historical['rows'] if x['reference_index']==ref]
        require(len(rows)==2 and {x['horizon'] for x in rows}=={75,150},'Historical grid')
        history={x['horizon']:x for x in rows};traces={}
        for h,row in history.items():
            require(row['failure'] is None,'Historical failure')
            path=checked_child(result.parent,row['trajectory_file']);require_sha(path,row['trajectory_sha256'])
            with np.load(path,allow_pickle=False) as data:traces[h]={k:data[k].copy() for k in ('states','actions','goal_state')}
            require(len(traces[h]['actions'])==row['delivered'] and len(traces[h]['states'])==row['delivered']+1,'Historical length')
        history_hashes[str(ref)]=sha256(result)
        runner=(pilot_src/'cluster/prometheus/diffusion_bottleneck_branch.py') if ref in REFS[:4] else (src/'cluster/prometheus/diffusion_bottleneck_extension_runner.py')
        for rep in (0,1):
            report=reports[ref,rep];semantic.provenance(report,sha256(runner),historical['model_state_sha256'])
            semantic.coverage(report['anchors'],history);steps=branches=available=0
            with np.load(root/f'ref-{ref}-repeat-{rep}/BANKS.npz',allow_pickle=False) as bank:
                for row in report['anchors']:
                    h,t=row['horizon'],row['anchor'];prefix=f'h{h}/t{t}/'
                    if not row['available']:
                        require(not any(k.startswith(prefix) for k in bank.files),'Unavailable evidence');continue
                    def v(k):return bank[prefix+k]
                    trace=traces[h]
                    nb,ns=semantic.check_anchor(v,row,trace['states'],trace['actions'],trace['goal_state'])
                    branches+=nb;steps+=ns;available+=1
                for h in (75,150):
                    anchors=[x['anchor'] for x in report['anchors'] if x['horizon']==h and x['available']]
                    steps+=max(anchors)+1 if anchors else 0
            semantic.counters(report,branches,steps);all_steps+=steps;all_branches+=branches
            counts.append({'reference':ref,'repeat':rep,'available_anchors':available,'branches':branches,'steps':steps})
    require(all_steps==aggregate['primitive_steps_including_prefixes'] and all_branches==aggregate['physical_branch_rollouts'],'Accounting')
    final={'all_combined_checks_passed':True,'runs':64,'new_runs':56,'reused_runs':8,'counts':counts,
        'combined32':effects(aggregate['anchors'],REFS),'additional28':effects(aggregate['anchors'],REFS[4:]),
        'pilot4':effects(aggregate['anchors'],REFS[:4]),'aggregate_sha256':sha256(out/'DECODER-AGGREGATE.json'),
        'extension_manifest_sha256':manifest_sha,'pilot_manifest_sha256':semantic.LAUNCH_SHA,
        'canonical_sha256':semantic.CANONICAL_SHA,'model_state_sha256':semantic.MODEL_SHA,
        'historical_result_sha256':history_hashes,'seals':seals,'dispatch':control,
        'new_runner_wall_seconds':sum(r['wall_seconds'] for (ref,rep),r in reports.items() if ref in REFS[4:]),
        'protected_payload_reads':0,'unevaluated_reference_payload_reads':0,'training_runs':0,
        'historical_decision_changed':False,'neural_or_hidden_physics_independently_regenerated':False,
        'program_sha256':sha256(Path(__file__))}
    write_report(out/'COMBINED-REPORT.json',final,(root,study,src,pilot_src))
    with (out/'sha256.txt').open('x') as f:
        for name in ('DECODER-AGGREGATE.json','COMBINED-REPORT.json'):f.write(sha256(out/name)+'  '+str(out/name)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','study','src','pilot-src','pilot-root','canonical','pilot-aggregate','dispatch','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest-sha',required=True);a=p.parse_args()
    a.out.mkdir(exist_ok=True);analyze(a.root,a.study,a.src,a.manifest_sha,a.pilot_src,a.pilot_root,a.canonical,a.pilot_aggregate,a.dispatch,a.out)
