"""Reaggregate the exported run table independently from the primary reducer."""
import argparse,csv,gzip,json,math
from pathlib import Path
from statistics import mean,stdev
import numpy as np
from scipy.stats import t
from independent_pusht_collect import sha

def verify(study,stage):
    study=Path(study);root=study/f'analysis-{stage}'
    for line in (root/'sha256.txt').read_text().splitlines():
        h,name=line.split(maxsplit=1);assert Path(name).name==name and sha(root/name)==h
    report=json.loads((root/'SUMMARY.json').read_text());cfg=json.loads((study/'CONFIG.json').read_text())
    with gzip.open(root/'ALL-EPISODES.tsv.gz','rt') as f: rows=list(csv.DictReader(f,delimiter='\t'))
    n=cfg['looks'][stage];arms=cfg['arms'];seeds=cfg['training_seed_blocks']
    assert len(rows)==n*2*len(seeds)*len(arms)
    grid={}
    for r in rows:
        key=(int(r['reference_index']),int(r['horizon']),int(r['train_seed']),r['arm'])
        assert key not in grid;grid[key]=int(r['success']);assert grid[key] in (0,1)
    expected={(i,h,s,a) for i in range(n) for h in (75,150) for s in seeds for a in arms}
    assert set(grid)==expected
    for a in arms:
        allvals=[grid[i,h,s,a] for i in range(n) for h in (75,150) for s in seeds]
        assert abs(mean(allvals)-report['arm_success'][a])<1e-12
    alpha=cfg['alpha_by_look'][stage];crit=t.ppf(1-alpha,n-1)
    past={} if stage==0 else json.loads((study/f'analysis-{stage-1}/SUMMARY.json').read_text())['ever_rejected']
    ever={};futility=False
    for control,r in report['primary'].items():
        differences=[mean([grid[i,h,s,'vad_continuation']-grid[i,h,s,control] for h in (75,150) for s in seeds]) for i in range(n)]
        delta=mean(differences);se=stdev(differences)/math.sqrt(n);lower=delta-crit*se
        assert abs(delta-r['difference'])<1e-12 and abs(se-r['se'])<1e-12
        assert abs(lower-r['lower_bound_this_look'])<1e-12
        assert bool(lower>0)==r['reject_this_look']
        upper=delta+t.ppf(.999,n-1)*se
        assert abs(upper-r['futility_upper_bound'])<1e-12
        futility=futility or upper<0
        ever[control]=bool(past.get(control,False) or lower>0)
    assert report['ever_rejected']==ever and report['all_three_established']==all(ever.values())
    assert report['futility']==bool(futility)
    assert report['stop']==(all(ever.values()) or futility or stage==len(cfg['looks'])-1)
    result={'all_passed':True,'n':n,'logical_runs':len(rows),'source':'independent csv/statistics reaggregation',
            'summary_sha256':sha(root/'SUMMARY.json'),'input_lock_sha256':sha(study/'INPUT-LOCK.json'),
            'decision':report['decision'],'stop':report['stop']}
    target=root/'INDEPENDENT-VERIFICATION.json';assert not target.exists()
    target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--stage',type=int,required=True)
    a=p.parse_args();verify(a.study,a.stage)
