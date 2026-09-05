#!/usr/bin/env python3
"""Host Slurm orchestration: only predeclared continuation, no model decisions.

Submits one registered stage and its afterok analysis. An afterok continuation
job invokes this again; it reads only the already-produced verified decision.
It does not poll, tune methods, inspect individual partial outcomes or retry
failed jobs. Failures leave the dependent analysis blocked for diagnosis.
"""
import argparse,hashlib,json,os,shlex,subprocess
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def submit(argv):
    result=subprocess.check_output(['sbatch','--parsable']+argv,universal_newlines=True,stdin=subprocess.DEVNULL).strip()
    job=result.split(';')[0]
    if not job.isdigit():raise RuntimeError('unexpected sbatch response')
    return job

def main(root,stage,dependency=None,dry=False):
    root=Path(root);cfg=json.loads((root/'CONFIG.json').read_text());source=Path(cfg['source_directory'])
    if sha(source/'SOURCE-MANIFEST.sha256')!=cfg['source_manifest_sha256']:raise RuntimeError('source manifest differs')
    if stage:
        summary=json.loads((root/('analysis-%d'%(stage-1))/'SUMMARY.json').read_text())
        check=json.loads((root/('analysis-%d'%(stage-1))/'INDEPENDENT-VERIFICATION.json').read_text())
        if not check['all_passed'] or check['summary_sha256']!=sha(root/('analysis-%d'%(stage-1))/'SUMMARY.json'):raise RuntimeError('unverified previous look')
        if summary['stop']:
            terminal={'decision':summary['decision'],'n':summary['n'],'analysis_stage':stage-1,
                      'summary_sha256':check['summary_sha256'],'complete':True}
            target=root/'TERMINAL.json'
            with target.open('x') as f:json.dump(terminal,f,indent=2);f.write('\n')
            print(json.dumps(terminal));return
    if stage>=len(cfg['looks']):raise RuntimeError('continuation beyond registered maximum')
    record=root/('SUBMISSION-%d.json'%stage)
    if record.exists():raise RuntimeError('stage already submitted; no duplicate execution')
    registry=json.loads((root/'REGISTRY.json').read_text());count=len(registry['stages'][stage])
    runner=source/'run_independent_pusht.sh';logs=root/'logs';logs.mkdir(exist_ok=True)
    evalcmd='USE_GPU=1 bash {} {} {} --study {} --stage {}'.format(shlex.quote(str(runner)),shlex.quote(str(root)),shlex.quote(str(source/'independent_pusht_worker.py')),shlex.quote(str(root)),stage)
    array=['--job-name=ind-pusht-s%d'%stage,'--partition=a6000','--qos=normal-a6000','--account=superworld',
       '--cpus-per-task=4','--mem=24G','--gres=gpu:1','--time=02:00:00','--array=0-%d%%4'%(count-1),
       '--output='+str(logs/'eval-%A_%a.out'),'--error='+str(logs/'eval-%A_%a.err'),'--wrap='+evalcmd]
    if dependency:array.insert(0,'--dependency=afterok:'+dependency)
    analysis='set -e; bash {} {} {} --study {} --stage {}; bash {} {} {} --study {} --stage {}'.format(
      shlex.quote(str(runner)),shlex.quote(str(root)),shlex.quote(str(source/'analyze_independent_pusht.py')),shlex.quote(str(root)),stage,
      shlex.quote(str(runner)),shlex.quote(str(root)),shlex.quote(str(source/'verify_independent_pusht_analysis.py')),shlex.quote(str(root)),stage)
    if dry:
        print(json.dumps({'dry_run':True,'array':array,'analysis_command':analysis,'stage':stage,'tasks':count},indent=2));return
    arrayid=submit(array)
    journal={'stage':stage,'array_job':arrayid,'source_manifest_sha256':cfg['source_manifest_sha256'],'phase':'array_submitted'}
    record.write_text(json.dumps(journal,indent=2)+'\n')
    analysisid=submit(['--dependency=afterok:'+arrayid,'--job-name=ind-analyze-s%d'%stage,
      '--partition=defq','--qos=normal','--account=superworld','--cpus-per-task=4','--mem=16G','--time=00:40:00',
      '--output='+str(logs/'analysis-%j.out'),'--error='+str(logs/'analysis-%j.err'),'--wrap='+analysis])
    journal.update(analysis_job=analysisid,phase='analysis_submitted')
    record.write_text(json.dumps(journal,indent=2)+'\n')
    nextcmd='/usr/bin/python3 {} --study {} --stage {}'.format(shlex.quote(str(source/'submit_independent_pusht.py')),shlex.quote(str(root)),stage+1)
    nextid=submit(['--dependency=afterok:'+analysisid,'--job-name=ind-next-s%d'%stage,
      '--partition=defq','--qos=normal','--account=superworld','--cpus-per-task=1','--mem=1G','--time=00:05:00',
      '--output='+str(logs/'controller-%j.out'),'--error='+str(logs/'controller-%j.err'),'--wrap='+nextcmd])
    result={'stage':stage,'cumulative_n':cfg['looks'][stage],'task_count':count,
       'array_job':arrayid,'analysis_job':analysisid,'continuation_job':nextid,
       'dependency':dependency,'source_manifest_sha256':cfg['source_manifest_sha256']}
    with record.open('w') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--stage',type=int,required=True)
    p.add_argument('--dependency');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    main(a.study,a.stage,a.dependency,a.dry_run)
