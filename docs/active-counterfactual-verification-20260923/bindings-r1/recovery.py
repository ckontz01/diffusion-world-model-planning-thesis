"""R1 control-only contract: authenticate one prior failure, never retry."""
import common as c
import os
from pathlib import Path
import subprocess


def prior():
    p = c.read(c.ROOT/'PRIOR-ATTEMPT.json')
    r = p['terminal']
    c.require(p['source_manifest']=='5630b222e8a88d0eaa45408876929724734d1f992afa657131ac770fb0400fa9'
              and p['approval_sha256']=='7ea5f67225ee1bff091e705e7515a4ed8f3589694e6093f1c2e7c607d27a6a88', 'Prior identities')
    c.require(r['job']=='304189' and r['spec']['key']=='collect-fit-490' and r['state']=='FAILED'
              and r['exit_code']=='1:0' and r['seconds']==23 and r['gpu_seconds']==23 and r['cpu_seconds']==0, 'Sole prior charge')
    return p


def approval_binding(manifest):
    contract=c.read(c.ROOT/'RECOVERY-CONTRACT.json')
    c.require(contract['prior_attempt_sha256']==c.sha(c.ROOT/'PRIOR-ATTEMPT.json'), 'Prior receipt binding')
    c.require(contract['instruction_sha256']==c.sha(c.ROOT/'RECOVERY-INSTRUCTION.txt'), 'Instruction binding')
    c.require(contract['new_grid_sha256']==c.digest(c.grid()), 'Amended grid identity')
    name='active-counterfactual-verification-recovery-r1-'+manifest[:16]
    return dict(contract, contract_sha256=c.sha(c.ROOT/'RECOVERY-CONTRACT.json'),
                source=c.RESEARCH+'/snapshots/'+name, control=c.RESEARCH+'/staging/'+name,
                run=c.RUN_PARENT+'/run-'+manifest[:16], source_manifest=manifest)


def prior_paths(p=None):
    p=prior() if p is None else p
    for name,info in p['members'].items():
        label,rel=name.split('/',1)
        root=Path(p['paths'][label]);path=root/rel
        c.require(path.resolve().is_relative_to(root.resolve()) and not path.is_symlink(), 'Prior path')
        yield name,path,info


def authenticate_prior_files(p=None):
    p=prior() if p is None else p
    for label,root in p['paths'].items():
        actual={label+'/'+f.relative_to(root).as_posix() for f in Path(root).rglob('*') if f.is_file()}
        c.require(actual=={n for n in p['members'] if n.startswith(label+'/')}, 'Prior member set')
    for name,path,info in prior_paths(p):
        c.require(path.stat().st_size==info['bytes'] and c.sha(path)==info['sha256'], 'Prior bytes: '+name)
    return p


def validate_scheduler(accounting, queue, p=None):
    p=prior() if p is None else p
    rows=[line.split('|') for line in accounting.splitlines() if 'acv0' in line.lower() or line.split('|')[0]=='304189']
    c.require(rows==[p['scheduler_row']], 'Unexplained or changed prior ACV0 allocation')
    c.require(not any('acv0' in line.lower() or line.startswith('304189|') for line in queue.splitlines()), 'Live ACV0 allocation')


def reconcile():
    p=authenticate_prior_files()
    ident=p['controller_identity'];stat=Path('/proc',str(ident['pid']),'stat')
    if stat.exists():
        fields=stat.read_text().rsplit(')',1)[1].split()
        c.require(fields[19]!=str(ident['start_ticks']) or fields[0]=='Z', 'Prior controller still active')
    fields='JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList,Partition,QOS,Account'
    a=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],'--format='+fields],capture_output=True,text=True,timeout=30)
    q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
    c.require(a.returncode==q.returncode==0,'Prior scheduler reconciliation unavailable')
    validate_scheduler(a.stdout,q.stdout,p)
    return {'authenticated_prior_job':'304189','gpu_seconds':23,'cpu_stage_seconds':0,
            'prior_receipt_sha256':c.sha(c.ROOT/'PRIOR-ATTEMPT.json'),'unexplained_attempts':0,'live_acv0_jobs':0}


def copy_prior(run):
    p=authenticate_prior_files();dest=Path(run)/'provenance-failed-v2';dest.mkdir(exist_ok=False)
    for name,path,info in prior_paths(p):
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(path.read_bytes())
        c.require(c.sha(target)==info['sha256'] and target.stat().st_size==info['bytes'],'Prior copy')
    c.write(dest/'PROVENANCE.json',{'prior_receipt':c.sha(c.ROOT/'PRIOR-ATTEMPT.json'), 'included_in_scientific_data':False,
                                 'originals_unchanged':True,'members':p['members']})


def verify_prior_copy(run):
    p=prior();dest=Path(run)/'provenance-failed-v2'
    c.require(c.read(dest/'PROVENANCE.json')['included_in_scientific_data'] is False,'Provenance only')
    actual={f.relative_to(dest).as_posix() for f in dest.rglob('*') if f.is_file()}
    c.require(actual==set(p['members'])|{'PROVENANCE.json'}, 'Prior provenance member set')
    for name,info in p['members'].items():
        f=dest/name;c.require(f.stat().st_size==info['bytes'] and c.sha(f)==info['sha256'],'Prior provenance hash')


def historical_event():
    return dict(prior()['terminal'],event='historical_terminal',attempt=1,source='failed-bindings-v2',
                scientific_data_accepted=False,prior_receipt_sha256=c.sha(c.ROOT/'PRIOR-ATTEMPT.json'))


def append(path,row):
    with Path(path).open('ab') as f:
        f.write(c.canonical(row)+b'\n');f.flush();os.fsync(f.fileno())


def final_acceptance(run,complete):
    jobs=c.grid();rows=complete['jobs']
    c.require(len(rows)==339 and [r['spec'] for r in rows]==jobs,'339 unique grid tasks')
    c.require(len({r['job'] for r in rows})==339 and '304189' not in {r['job'] for r in rows},'Unique new allocations')
    c.require(complete['new_attempts']==339 and complete['campaign_attempts']==340 and
              complete['authorized_replacement_count']==1 and complete['automatic_retry_count']==0,'Campaign attempt counts')
    c.require(all(r['state']=='COMPLETED' and r['exit_code']=='0:0' and r['attempt']==(2 if r['spec']['key']=='collect-fit-490' else 1)
                  and 0<=r['seconds']<=r['spec']['seconds'] for r in rows),'Successful task attempts')
    gpu=23+sum(r['seconds']*int(r['gpus']) for r in rows if r['spec']['gpu'])
    cpu=sum(r['seconds'] for r in rows if not r['spec']['gpu'])
    c.require(gpu==complete['gpu_seconds'] and cpu==complete['cpu_seconds'] and gpu<=220800 and cpu<=21600,'Combined final charges')
    ledger=[c.json.loads(s) for s in (run/'CAMPAIGN-ATTEMPTS.jsonl').read_text().splitlines()]
    c.require(ledger[0]==historical_event() and sum(r['event']=='historical_terminal' for r in ledger)==1,'Historical attempt charged once')
    submitted=[r for r in ledger if r['event']=='submitted'];terminal=[r for r in ledger if r['event']=='terminal']
    c.require([r['job'] for r in submitted]==[r['job'] for r in rows] and terminal==rows,'All340 allocations reconciled')
    scientific=[c.json.loads(s) for s in (run/'SCIENTIFIC-TASKS.jsonl').read_text().splitlines()]
    c.require([r['key'] for r in scientific]==[j['key'] for j in jobs] and len(scientific)==339,'Unique scientific suppliers')
    for s,r in zip(scientific,rows):
        c.require(s['job']==r['job'] and s['attempt']==r['attempt'] and s['seal_sha256']==c.sha(run/s['key']/'SEAL.json'),'Scientific supplier seal')
    c.require(not any('unresolved' in r['event'] for r in ledger),'Unresolved attempts')
    verify_prior_copy(run)
    return {'successful_unique_tasks':339,'campaign_allocations':340,'prior_failed_allocations':1,
            'gpu_seconds':gpu,'cpu_stage_seconds':cpu,'failed_attempt_in_scientific_denominators':False}
