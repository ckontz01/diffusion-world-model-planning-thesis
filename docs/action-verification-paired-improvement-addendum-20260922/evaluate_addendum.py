"""One replay of fixed artificial AV0 fixtures; new control, exclusive outputs."""
import hashlib
import json
from pathlib import Path
import subprocess
from paired_improvement import AV0, PairedImprovement, THRESHOLDS
from controls import TablePredictor, LearnThenTest, Simultaneous, point, metrics
from suite import rows, predict

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
ACCEPTED='ca0a05d5ec1c9ab66d723529ac227c98de5b73e1'


def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()


def original_manifest():
    """All accepted AV0 files: Git-normalized identities plus local raw bytes."""
    relative=AV0.relative_to(REPO).as_posix()
    listing=subprocess.check_output(['git','ls-tree','-r',ACCEPTED,'--',relative],cwd=REPO,text=True)
    entries=[]
    for line in listing.splitlines():
        header,path=line.split('\t',1);blob=header.split()[2]
        actual=subprocess.check_output(['git','hash-object','--path='+path,path],cwd=REPO,text=True).strip()
        if actual!=blob:raise RuntimeError('Accepted AV0 changed: '+path)
        p=REPO/path
        entries.append(dict(path=path,accepted_git_blob=blob,bytes=p.stat().st_size,
                            sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    if len(entries)!=25:raise RuntimeError('Unexpected accepted AV0 inventory')
    return entries


def reconstruct_accepted_table(fit):
    """Restore the original sufficient statistics, not a new fitted model choice.

    AV0 did not serialize counts/predictions. Replay the unchanged integer
    sufficient statistics and use its unmodified TablePredictor.predict method.
    No training constructor, optimizer, new capacity, regularizer or fit split.
    """
    model=TablePredictor.__new__(TablePredictor)
    model.fit_ids=frozenset(r['id'] for r in fit)
    model.counts={}
    for context in range(16):
        members=[r for r in fit if r['context']==context]
        if members:
            for slot in range(8):
                model.counts[context,slot]=(len(members),sum(r['outcomes'][slot] for r in members))
    return model


def summarize(source_rows, choices):
    result=metrics(source_rows,choices)
    result.update(gains=sum(r['outcomes'][a]>r['outcomes'][0] for r,a in zip(source_rows,choices)),
                  losses=sum(r['outcomes'][a]<r['outcomes'][0] for r,a in zip(source_rows,choices)),
                  overrides=sum(a!=0 for a in choices),
                  baseline_success=sum(r['outcomes'][0] for r in source_rows)/len(source_rows))
    assert result['sampled_outcome_difference']==(result['gains']-result['losses'])/len(source_rows)
    return result


def compare_dict(actual,expected):
    for key,value in actual.items():
        if key in expected and value!=expected[key]:raise AssertionError('AV0 replay mismatch: '+key)


def main():
    if (ROOT/'RESULTS.json').exists():raise RuntimeError('Results already exist; no overwrite')
    before=original_manifest()
    config=json.loads((AV0/'CONTRACT.json').read_text())
    assert config['seeds']==[92201,92202,92203]
    assert tuple(config['ltt_thresholds'])==THRESHOLDS
    original=json.loads((AV0/'ARTIFICIAL-RESULTS.json').read_text())
    results=[]
    for old in original['results']:
        case,seed=old['case'],old['seed']
        splits={role:rows(case,seed,role,n) for role,n in config['sources_per_seed_scenario'].items()}
        source_digest=digest(splits)
        assert source_digest==old['source_data_sha256'], 'Original source digest mismatch'
        ids=[r['id'] for rr in splits.values() for r in rr]
        assert len(ids)==len(set(ids))
        model=reconstruct_accepted_table(splits['fit'])
        predictions={role:[predict(model,r,case) for r in rr] for role,rr in splits.items() if role!='fit'}
        calibration=[(p,r['outcomes']) for p,r in zip(predictions['calibration'],splits['calibration'])]
        # Evidence checks only: original code/rules/results are not edited.
        old_ltt=LearnThenTest.calibrate(calibration,THRESHOLDS,config['alpha'],config['delta'])
        assert list(old_ltt.tests)==old['ltt_tests']
        assert list(old_ltt.accepted)==old['ltt_accepted']
        old_sim=Simultaneous.calibrate(calibration,config['alpha'])
        assert old_sim.q==old['simultaneous_q']
        compare_dict(metrics(splits['test'],[point(p) for p in predictions['test']]),old['metrics']['point'])
        control=PairedImprovement.calibrate([(r['id'],p,r['outcomes'])
                                             for r,p in zip(splits['calibration'],predictions['calibration'])])
        selected={role:summarize(splits[role],[control.choose(p) for p in predictions[role]])
                  for role in ('calibration','test')}
        evidence=dict(case=case,seed=seed,source_data_sha256=source_digest,source_digest_matches_av0=True,
                      prediction_sha256=digest(predictions),
                      restored_count_table_sha256=digest(sorted((c,a,n,y) for (c,a),(n,y) in model.counts.items())),
                      original_point_metrics_exact_match=True,original_ltt_tests_exact_match=True,
                      original_simultaneous_q_exact_match=True,
                      accepted_thresholds=control.accepted,chosen_threshold=control.threshold,
                      calibration_tests=control.tests,selected_rule_metrics=selected,
                      comparison_to_accepted_av0={m:old['metrics'][m] for m in
                          ('baseline','point','simultaneous','ltt','pc_complete','pc_logged')},
                      test_choices_sha256=digest([control.choose(p) for p in predictions['test']]))
        results.append(evidence)
    assert len(results)==18
    assert {(r['case'],r['seed']) for r in results}=={
        (c,s) for c in config['scenarios'] for s in config['seeds']}
    after=original_manifest();assert before==after,'AV0 byte preservation failed'
    output=dict(accepted_av0_commit=ACCEPTED,control='established paired-improvement testing control',
                claim='expected paired success improvement; not individual action safety or full HCPI',
                original_files_unchanged=True,original_file_inventory=before,
                contract_sha256=hashlib.sha256((ROOT/'CONTRACT.json').read_bytes()).hexdigest(),
                replay='original deterministic count model restored; no optimizer/new training choice',
                original_split_sizes=config['sources_per_seed_scenario'],results=results)
    with (ROOT/'RESULTS.json').open('x',encoding='utf8') as f:json.dump(output,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(cases=18,matching_source_digests=18,original_files_unchanged=len(before),
                         accepted_cases=sum(bool(r['accepted_thresholds']) for r in results))))


if __name__=='__main__':main()
