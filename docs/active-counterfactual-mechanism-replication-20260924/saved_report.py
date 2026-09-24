"""One exclusive, CPU-only analysis of authenticated, already-preserved data.

Reads only ACV0's published report, selected final/validation evidence and the
two typed small predictors. No training data, reference payload, Le-WM, torch,
physics, cluster or fitting invocation. Old statistics are not recalculated.
"""
import base
import io, json, tarfile, time
import numpy as np
from model import JointModel, OrdinaryModel, Preprocessing
from policy import Selector, context, features
from tree import Ledger, identity, tie_argmax
from committed_feedback import CommittedFeedbackSelector, MODE
from decomposition import restore_tree, prefix_values

ARCHIVE = 'bd0f53b85c3de36376bc68a084d4fbc7cb5b0958943534a890d0ee9b2d70342b'
REQUEST = '1628cc4d732734729818077238c47b8099c7041503262d8ff7d5796fc6abaea4'
GATE = '180b319779520d4164e4e4b6d20ea5dede2879a8bd5fd504440cbcb8f085e994'
REPORT = '28fe9fa78fd6b6e4dad4059abb15092ad78d5f502d2c2470974cf594412bfacf'

class Saved:
    def __init__(self):
        assert base.digest((base.SSD/'REQUEST.json').read_bytes()) == REQUEST
        assert base.digest((base.SSD/'BACKUP-VERIFIED.json').read_bytes()) == GATE
        self.req = base.read(base.SSD/'REQUEST.json'); gate = base.read(base.SSD/'BACKUP-VERIFIED.json')
        assert gate['status']=='VERIFIED' and gate['archive']==self.req['sha256']==ARCHIVE
        assert (base.SSD/'final.tar').stat().st_size == self.req['bytes'] == 814663680
        self.tar = tarfile.open(base.SSD/'final.tar','r:'); self.reads = {}
    def raw(self, name):
        # Explicit research-artifact allowlist; no general archive extraction.
        assert name.startswith(('run/evaluate-', 'run/collect-validation-', 'run/fit-joint/joint.npz',
                                'run/fit-ordinary/ordinary.npz'))
        b = self.tar.extractfile(name).read(); expected = self.req['members'][name]
        assert expected == {'bytes':len(b),'sha256':base.digest(b)}
        self.reads[name] = expected
        return b
    def evidence(self, key):
        prefix = 'run/'+key+'/'
        m = json.loads(self.raw(prefix+'EVIDENCE.json'))
        # Only low-dimensional arrays needed for this audit; no image decoding.
        with np.load(io.BytesIO(self.raw(prefix+'evidence.npz')),allow_pickle=False) as z:
            a = {k:z[k] for k in z.files if k.startswith('tree/') or k=='goal_latent' or
                 k.endswith(('/initial_latent','/latent','/state','/flags','/action','/dynamics','/pixel_hash'))}
        return a,m

def models(saved):
    with np.load(io.BytesIO(saved.raw('run/fit-joint/joint.npz')),allow_pickle=False) as z:
        m=json.loads(str(z['metadata'])); assert m['kind']=='ACV0-artificial-or-reviewed-fit-only'
        pre=Preprocessing(*(z[k].copy() for k in ('xmean','xstd','amean','astd','rmean','rstd')),m['fit_ids'])
        j=JointModel(m['xdim'],m['adim'],m['rdim'],m['seed'],m['width'],pre)
        for i,p in enumerate(j.params): p[:]=z[f'p{i}']; p.setflags(write=False)
    with np.load(io.BytesIO(saved.raw('run/fit-ordinary/ordinary.npz')),allow_pickle=False) as z:
        m=json.loads(str(z['metadata'])); assert m['kind']=='ACV0-ordinary'
        o=OrdinaryModel(j.xdim,j.adim,j.rdim,m['seed'],j.pre)
        assert tuple(m['dims'])==o.net.dims
        for i,p in enumerate(o.params): p[:]=z[f'p{i}']; p.setflags(write=False)
    return j,o

def choice(tree, p, s):
    if p is None: return dict(prefix=None,suffix=None)
    n=tree.nodes[p]
    return dict(prefix=p,suffix=s,prefix_sha256=identity(n.prefix),
                suffix_sha256=None if s is None else identity(n.suffixes[s]),
                prefix_actions=n.prefix.tolist(),suffix_actions=None if s is None else n.suffixes[s].tolist())

def mean(values): return float(np.mean(values))

def main():
    out=base.HERE/'SAVED-DATA-MECHANISM.json'
    if out.exists(): raise FileExistsError('One saved-data report already exists')
    started=time.monotonic(); cpu=time.process_time()
    assert base.digest((base.PUB/'REPORT.json').read_bytes())==REPORT
    report=base.read(base.PUB/'REPORT.json'); roles=base.read(base.OLD/'DATA-ROLES-PROPOSED.json')['proposed_roles']
    assert report['source_ids']==roles['final_development'] and len(set(report['source_ids']))==32
    old={(x['reference'],x['control']):x for x in report['chosen_branches_and_endpoints']}
    saved=Saved(); joint,ordinary=models(saved); select=CommittedFeedbackSelector(joint,ordinary)
    assert set(map(str,joint.pre.fit_ids))==set(map(str,roles['fit']))
    final=[]; validation=[]; decomposition=[]; replay=0
    for ref in report['source_ids']:
        records={}; canonical=None; prefix_traces={}
        for mode in report['controls']:
            historic=old[ref,mode]; row=dict(historic)
            if mode in ('vanilla','early-replan'):
                # Existing actual endpoint only; these policies do not choose from this tree.
                records[mode]=row; continue
            a,m=saved.evidence(f'evaluate-{ref}-{mode}')
            assert m['reference']==ref and m['role']=='final_development' and m['control']==mode
            b=m['branches'][0]; tree=restore_tree(a)
            if canonical is None: canonical={k:v for k,v in a.items() if k.startswith('tree/')}
            for k,v in canonical.items(): np.testing.assert_array_equal(v,a[k])
            for k in ('prefix','suffix','steps'): assert b[k]==historic[k]
            assert int(b['success'])==historic['native_success']==int(a['b0/flags'][:,0].any())
            row.update(choice(tree,b['prefix'],b['suffix']))
            h=context([a['b0/initial_latent']],[],a['goal_latent'],0)
            if mode!='bayesian':
                led=Ledger(); d=select.select(tree,h,led,mode)
                assert d.prefix==b['prefix']
                suffix=None if b['steps']<=5 else select.after(d,tree,h,a['b0/latent'][4],led)
                assert suffix==b['suffix']; replay+=1
                np.testing.assert_allclose(d.values,b['decision']['values'],rtol=1e-11,atol=1e-12)
            prefix_traces[mode]={k:a['b0/'+k][:5] for k in ('state','latent','flags','action','dynamics','pixel_hash')}
            if mode=='active':
                values=prefix_values(joint,tree,h)
                decomposition.append(dict(role='final_development',reference=ref,prefixes=values))
                row['prior_committed_suffix_for_actual_prefix']=values[b['prefix']]['committed_suffix']
                row['response_changed_suffix']=b['suffix'] is not None and b['suffix']!=values[b['prefix']]['committed_suffix']
            records[mode]=row
        active,nu=records['active'],records['no_update']
        assert active['prefix_sha256']==nu['prefix_sha256']
        for k in prefix_traces['active']: np.testing.assert_array_equal(prefix_traces['active'][k],prefix_traces['no_update'][k])
        changed=active['suffix_sha256']!=nu['suffix_sha256']
        assert changed==active['response_changed_suffix']
        final.append(dict(reference=ref,actual=records,active_no_update_same_physical_prefix=True,
                          response_changed_suffix=changed,observed_active_minus_no_update=active['native_success']-nu['native_success']))
    for ref in roles['validation']:
        a,m=saved.evidence(f'collect-validation-{ref}')
        assert m['reference']==ref and m['role']=='validation'
        tree=restore_tree(a); h=context([a['b0/initial_latent']],[],a['goal_latent'],0)
        vals=prefix_values(joint,tree,h)
        decomposition.append(dict(role='validation',reference=ref,prefixes=vals))
        by_prefix={p:[(i,b) for i,b in enumerate(m['branches']) if b['prefix']==p] for p in range(len(tree.nodes))}
        metrics=[]; node_records=[]; choices={}
        for p,bs in by_prefix.items():
            i,first=bs[0]; terminal=first['suffix'] is None
            assert [b['suffix'] for _,b in bs]==([None] if terminal else list(range(len(tree.nodes[p].suffixes))))
            for bi,b in bs:
                assert bool(b['success'])==bool(a[f'b{bi}/flags'][:,0].any())
                for field in ('state','latent','flags','action','dynamics','pixel_hash'):
                    np.testing.assert_array_equal(a[f'b{bi}/{field}'][:5],a[f'b{i}/{field}'][:5])
            if terminal:
                node_records.append(dict(prefix=p,terminal=True,success=int(first['success']),suffix_outcomes=[])); continue
            node=tree.nodes[p]; x,aa=features(h,node); residual=(a[f'b{i}/latent'][4]-node.predicted_prefix)[None]
            prior=joint.forward(x,aa)[0]['q'][0]; posterior=joint.forward(x,aa,residual)[0]['q'][0]
            oq=ordinary.forward(x,aa,residual)[0][0]; y=np.array([int(b['success']) for _,b in bs])
            scores={}
            for label,q in (('joint_prior',prior),('joint_conditional',posterior),('ordinary_conditional',oq)):
                clipped=np.clip(q,1e-12,1-1e-12)
                scores[label]={'bce':mean(-y*np.log(clipped)-(1-y)*np.log1p(-clipped)), 'brier':mean((q-y)**2)}
            metrics.append(scores)
            node_records.append(dict(prefix=p,terminal=False,suffix_outcomes=y.tolist(),joint_prior=prior.tolist(),
                                     joint_conditional=posterior.tolist(),ordinary_conditional=oq.tolist(),scores=scores))
        for mode in ('static',MODE,'no_update','active','ordinary'):
            led=Ledger(); d=select.select(tree,h,led,mode); bi,b=by_prefix[d.prefix][0]
            s=None if b['suffix'] is None else select.after(d,tree,h,a[f'b{bi}/latent'][4],led)
            matched=next(t for _,t in by_prefix[d.prefix] if t['suffix']==s)
            choices[mode]=dict(prefix=d.prefix,suffix=s,success=int(matched['success']),
                               prefix_sha256=identity(tree.nodes[d.prefix].prefix))
        source_scores={label:{metric:mean([x[label][metric] for x in metrics]) for metric in ('bce','brier')}
                       for label in ('joint_prior','joint_conditional','ordinary_conditional')} if metrics else None
        validation.append(dict(reference=ref,role='validation_report_only',prefixes=node_records,
                               descriptive_saved_bank_choices=choices,source_mean_scores=source_scores))
    changed=[r for r in final if r['response_changed_suffix']]
    summary=dict(final_sources=32,validation_sources=16,unchanged_deployed_decisions_replayed=replay,
                 active_no_update_identical_prefixes=32,response_changed_suffixes=len(changed),
                 changed_source_ids=[r['reference'] for r in changed],
                 changed_pair_outcomes={f'{ya}{yn}':sum(r['actual']['active']['native_success']==ya and r['actual']['no_update']['native_success']==yn for r in changed) for ya,yn in ((0,0),(0,1),(1,0),(1,1))},
                 validation_saved_bank_successes={mode:sum(r['descriptive_saved_bank_choices'][mode]['success'] for r in validation) for mode in ('static',MODE,'no_update','active','ordinary')},
                 validation_same_candidate_scores={label:{metric:mean([r['source_mean_scores'][label][metric] for r in validation if r['source_mean_scores'] is not None]) for metric in ('bce','brier')} for label in ('joint_prior','joint_conditional','ordinary_conditional')})
    result=dict(status='CPU-only post-hoc saved-data description; no new research execution',summary=summary,
                final_development=final,validation=validation,predicted_prefix_decomposition=decomposition,
                interpretation=['All final endpoints are previously executed actual outcomes, not newly imputed branches.',
                                'New control has NO assigned outcomes on the old32 final sources.',
                                'Validation bank replay is descriptive selection among completely saved executed branches, not a new final cohort.',
                                'Anticipated feedback increment is model predicted, not a realized causal information benefit.',
                                'Finite-integration correction may be signed; the same-draw max-minus-fixed term is nonnegative.',
                                'No training records or protected payloads were opened; preprocessing and models were not fitted.'],
                authentication=dict(original_report_sha256=REPORT,archive_sha256=ARCHIVE,request_sha256=REQUEST,
                                    prior_verified_receipt_sha256=GATE,selected_members=saved.reads,original_code=base.PINS),
                resources=dict(wall_seconds=time.monotonic()-started,process_cpu_seconds=time.process_time()-cpu,
                               threads=4,lewm_forwards=0,physics_steps=0,fits=0,reference_payload_reads=0,gpu_jobs=0))
    saved.tar.close(); base.authenticate_code()
    assert base.digest((base.PUB/'REPORT.json').read_bytes())==REPORT
    base.write(out,result)
    print(json.dumps({'summary':summary,'resources':result['resources']},indent=2))

if __name__=='__main__': main()
