"""Prepare using authenticated completed LGP1 evidence, never research inference."""
import hashlib,json,statistics,subprocess,tarfile
from pathlib import Path
import lgprb1_contract as c

REPO=Path(__file__).resolve().parents[2]
BACKUP=Path('D:/THESIS-BACKUPS/local-goal-proposals-20260918/run-b54a55b16bcb83a5')

def main():
    from lgp1_preserve import check_ssd
    check_ssd();doc=REPO/c.DOC;doc.mkdir(exist_ok=True)
    request=c.read(BACKUP/'BACKUP-REQUEST.json');verified=c.read(BACKUP/'BACKUP-VERIFIED.json')
    c.require(verified['sha256']==request['sha256']=='24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd','Accepted archive')
    with tarfile.open(BACKUP/'final.tar','r:') as tar:
        def get(name):
            data=tar.extractfile(name).read()
            c.require(hashlib.sha256(data).hexdigest()==request['members'][name]['sha256'],'Archived bytes '+name)
            return data
        manifest=get('source/LGP1-SOURCE-MANIFEST.sha256')
        c.require(hashlib.sha256(manifest).hexdigest()==c.OLD_SOURCE_SHA,'Actual executed source')
        original={line.split('  ',1)[1]:line.split('  ',1)[0] for line in manifest.decode().splitlines()}
        runtime=get('source/cluster/prometheus/lgp1_runtime.py')
        with (doc/'LEGACY-RUNTIME.py.txt').open('xb') as f:f.write(runtime)
        auth=json.loads(get('new-control/FINAL-AUTHENTICATION-20260919.json'))
        report=json.loads(get('run/analysis/REPORT.json'))
        refs=json.loads(get('source/'+c.old.DOC+'/DATA-ROLES.json'))['development_reference_indices']
        frozen=report['model_freeze']
        models={name:dict(model_sha256=digest,seal=frozen['seals'][name],root=(c.OLD_FITS/name).as_posix()) for name,digest in frozen['models'].items()}
        scientific=['local_goal_models.py','local_goal_proposals.py','lgp1_tensor.py','lgp1_endpoint.py',
                    'e18_fresh_driver.py','pusht_fresh_initialization.py','independent_pusht_runtime.py','lgp1_train.py','lgp1_worker.py']
        code={}
        for name in scientific:
            path='cluster/prometheus/'+name;data=(REPO/path).read_bytes().replace(b'\r\n',b'\n')
            c.require(hashlib.sha256(data).hexdigest()==original[path],'Unchanged scientific component '+name)
            code[path]=original[path]
        workers=[dict(name=w['name'],root=w['root'],seal=w['seal'],task=w['metadata']['task'],job=w['job'])
                 for w in auth['workers'] if w['metadata']['task']['kind']=='evaluation']
        rows=report['rows'];stages=[s for r in rows for s in r['stages']]
        c.require(len(rows)==384 and len(workers)==192 and all(len(s['rounds'])==30 for s in stages),'Executed 30-round grid')
        inventory=dict(stage_keys=sorted(set().union(*(set(s) for s in stages))),
            round_keys=sorted(set().union(*(set(v) for s in stages for v in s['rounds']))),
            saved_raw_proposal_banks=False,saved_proposal_bank_hashes=False,saved_context_hashes=True,
            saved_elite_indices=True,saved_complete_population_cost_vectors=False,
            endpoint_evidence=True,claim='Context hashes and summaries cannot establish historical raw-bank equality or shorter-budget success.')
        reuse=dict(historical_record='f42c189b2e18968303dee5a733cf670d2301a657',source=c.OLD_SOURCE.as_posix(),source_sha256=c.OLD_SOURCE_SHA,
            input_sha256=c.INPUT_SHA,source_files=original,unchanged_scientific_components=code,
            legacy_runtime_sha256=hashlib.sha256(runtime).hexdigest(),models=models,main_workers=workers,
            canonical_approval_sha256=auth['canonical_approval_sha256'],freeze_sha256=c.FREEZE_SHA,
            aggregate_seal_sha256=auth['aggregate_seal_sha256'],aggregate_sha256=request['members']['run/analysis/REPORT.json']['sha256'],
            backup_sha256=verified['sha256'],backup_members=1733,reused_main_episodes=384,reused_populations=30,
            references=refs,diagnostic_inventory=inventory)
        c.write(doc/'REUSE.json',reuse);c.write(doc/'GRID.json',c.grid(refs))
        allocations={w['metadata']['task']['name']:w['allocation_seconds'] for w in auth['workers'] if w['metadata']['task']['kind']=='evaluation'}
        predictions=[]
        for family in c.old.FAMILIES:
            for seed in c.old.SEEDS:
                for ref in refs:
                    rr=[r for r in rows if (r['family'],r['seed'],r['reference'])==(family,seed,ref)]
                    ss=[s for r in rr for s in r['stages']]
                    alloc=allocations[f'evaluation-{family}-{seed}-{ref}']
                    fixed=max(0,alloc-sum(s['seconds'] for s in ss))
                    variable=statistics.mean(s['refinement_total_seconds'] for s in ss)
                    other=statistics.mean(s['seconds']-s['refinement_total_seconds'] for s in ss)
                    for n in (1,5):
                        predictions.append(dict(family=family,seed=seed,reference=ref,populations=n,
                            historical_allocation_seconds=alloc,historical_stages=len(ss),
                            setup_delivery_and_other_seconds=fixed,
                            full_budget_model_seconds=fixed+30*(other+variable*n/30),
                            no_refinement_speedup_seconds=fixed+30*(other+variable)))
        cost=dict(model='Retain measured allocation-minus-planning overhead; allow all 30 stages per two-horizon job; scale only refinement component. Scenario, not promise.',
            historical_main_allocation_seconds=sum(allocations.values()),historical_main_stages=len(stages),
            historical_planning_seconds=sum(s['seconds'] for s in stages),
            full_budget_model_seconds=sum(p['full_budget_model_seconds'] for p in predictions),
            no_speedup_model_seconds=sum(p['no_refinement_speedup_seconds'] for p in predictions),
            scenario_with_twofold_slowdown_and_technical_reservation_seconds=2*sum(p['no_refinement_speedup_seconds'] for p in predictions)+1200,
            proposed_gpu_allocation_cap=70320,proposed_cpu_allocation_cap=7200,
            new_jobs=387,new_gpu_jobs=386,new_main_episodes=768,technical_full_episodes=0,
            technical_first_decisions=16,per_main_job_seconds=180,per_technical_job_seconds=600,
            predictions=predictions,diagnostic_inventory=inventory,
            new_worker_bytes=2_000_000_000,new_source_control_log_bytes=100_000_000,total_remote_including_history_bytes=8_000_000_000,
            prior_observed_remote_bytes=3466064528,old_archive_bytes=1734420480,
            old_main_worker_bytes=232714292,old_analysis_bytes=228389686,
            storage_model='New raw round logs roughly 6/30 of two new budget grids versus the 30-round history, plus 768 compact endpoint files; conservative new-worker ceiling 2GB, plus duplicate final archive and old ~3.47GB.')
        c.write(doc/'MEASURED-COST.json',cost)
    # Exact checkpoint/file byte reads only; no tensor load or reserved payload.
    paths={(c.OLD_SOURCE/p).as_posix():h for p,h in code.items()}
    paths.update({v['root']+'/model.pt':v['model_sha256'] for v in models.values()})
    paths[(c.OLD_SOURCE/'LGP1-SOURCE-MANIFEST.sha256').as_posix()]=c.OLD_SOURCE_SHA
    paths[(c.OLD_RUN/'PRE-EVALUATION-FREEZE.json').as_posix()]=c.FREEZE_SHA
    remote="import json,hashlib,pathlib\nexpected="+repr(paths)+"\nfor n,h in expected.items():\n p=pathlib.Path(n);a=hashlib.sha256()\n with p.open('rb') as f:\n  for b in iter(lambda:f.read(1048576),b''):a.update(b)\n assert a.hexdigest()==h,n\nprint(json.dumps(dict(verified_files=len(expected),hashes=expected,research_inference_calls=0,simulator_calls=0,optimizer_steps=0)))"
    r=subprocess.run(['wsl','-d','Thesis-Ubuntu','-u','chris','--','ssh','-o','BatchMode=yes','prometheus','/usr/bin/python3.9','-B','-'],input=remote,text=True,capture_output=True)
    c.require(r.returncode==0,r.stderr);c.write(doc/'REMOTE-BYTE-COMPATIBILITY.json',json.loads(r.stdout))
    print(json.dumps({k:v for k,v in cost.items() if k not in ('predictions','diagnostic_inventory')}))

if __name__=='__main__':main()
