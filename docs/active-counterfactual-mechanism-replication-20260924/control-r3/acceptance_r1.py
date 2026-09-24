"""Independent byte/technical acceptance; no efficacy-based continuation."""
import r1 as recovery
import common as c
import scheduler as s
import time
from prefix_coupling import check_technical

def worker(run,spec,row,package,approval):
    s.allocation(spec,row)
    root=run/spec['key']; c.verify_seal(root,spec)
    t=c.read(root/'TECHNICAL.json')
    c.require(t['passed'] is True and t['spec']==spec and t['package']==package and t['approval']==approval,'Worker contract binding')
    c.require(t['job']==row['job'] and t['hard_seconds']==spec['seconds'] and t['work_seconds']==spec['work_seconds'],'Worker identity/time')
    c.require(c.bytes_in(root)<=spec['byte_cap'],'Complete worker seal footprint')
    for suffix in ('.slurm.out','.slurm.err','.out','.err'):
        log=recovery.slurm_log(run,spec['key'],suffix)
        c.require(log.is_file() and log.stat().st_size<=4096,'Bounded complete worker/container/Slurm logs')
    c.require(t['peak_process_rss_bytes']<=spec['ram_gib']*(1<<30),'RSS envelope')
    if spec['gpu']:
        c.require((root/'evidence.npz').is_file() and (root/'EVIDENCE.json').is_file(),'Saved action/endpoint evidence required')
        s.association(c.read(root/'HARDWARE.json'),row)
        c.require(t['models_unchanged'] and t['checks']['passed'] and t['checks']['reference']==spec['reference'],'Independent endpoint/model checks')
        c.require(t['checks']['role']=='mechanism_evaluation' and t['episode_identity']==[spec['reference'],spec['pair'],spec['control']],'New-role episode identity')
        c.require(t['prefix_coupling']['reference']==spec['reference'] and t['prefix_coupling']['prefix_steps']==min(5,t['checks']['actions']),'Recorded prefix/source association')
        check_technical([t['prefix_coupling']])
    else:
        if spec['stage']=='fitting':
            f=c.read(root/'FIT.json'); c.require(f['seed']==spec['seed'] and f['updates']==192 and len(f['trace'])==192,'Exact fitted seed/update trace')
        else:
            c.require(t['verified_episodes']==8192 and t['source_count']==512 and t['old32_included'] is False and (root/'REPORT.json').is_file(),'Independent full-grid analysis')
            c.require(t['prefix_coupling_checked_episodes']==8192,'Independent saved-array prefix coupling for full grid')
    return dict(key=spec['key'],job=row['job'],seal=c.sha(root/'SEAL.json'),unix=time.time())

def gate(run,jobs):
    first=[j for j in jobs if j['stage']=='evaluation'][:16]
    c.require(len(first)==16 and len({j['reference'] for j in first})==1,'Included full source block')
    trees=set(); initials=set(); seals={}; prefixes=[]
    for j in first:
        c.verify_seal(run/j['key'],j); t=c.read(run/j['key']/'TECHNICAL.json')
        c.require(t['passed'] and t['models_unchanged'] and t['checks']['passed'],'Technical-only tranche')
        initials.add(t['initial_goal_digest'])
        c.require(t['prefix_coupling']['reference']==j['reference'],'Tranche prefix/source association')
        prefixes.append(t['prefix_coupling'])
        if j['control']!='early-replan': trees.add(t['tree_digest'])
        seals[j['key']]=c.sha(run/j['key']/'SEAL.json')
    c.require(len(trees)==len(initials)==1,'Exact initial tree/actions/features across15 learned cells')
    coupling=check_technical(prefixes)
    c.write(run/'TECHNICAL-TRANCHE-PASSED.json',dict(unix=time.time(),seals=seals,scientific_selection=False,prefix_coupling=coupling))
def check_gate(run):
    g=c.read(run/'TECHNICAL-TRANCHE-PASSED.json')
    expected={j['key'] for j in c.grid() if j['stage']=='evaluation' and j['reference']==c.roles()['mechanism_evaluation'][0]}
    c.require(set(g['seals'])==expected and len(expected)==16 and g['scientific_selection'] is False,'Exact included16 gate')
    for k,h in g['seals'].items(): c.require(c.sha(run/k/'SEAL.json')==h,'Tranche seal unchanged')
    actual=check_technical([c.read(run/k/'TECHNICAL.json')['prefix_coupling'] for k in sorted(expected)])
    c.require(g['prefix_coupling']==actual,'Tranche prefix-coupling receipt')
    return g

def ledger(control,jobs,require_complete=True):
    rows=c.lines(control/'CAMPAIGN.jsonl'); claimed={}; submitted={}; terminal={}; accepted={}
    for e in rows:
        kind=e['event']; key=e.get('key')
        target={'claim':claimed,'submitted':submitted,'terminal':terminal,'accepted':accepted}.get(kind)
        if target is not None:
            c.require(key not in target,'Duplicate '+kind+' logical task'); target[key]=e
    c.require(set(submitted)<=set(claimed) and set(terminal)<=set(submitted) and set(accepted)<=set(terminal),'Ledger state order')
    ids=[e['job'] for e in submitted.values()]; c.require(len(ids)==len(set(ids)),'Unique allocation suppliers')
    for k,e in terminal.items(): c.require(e['row']['job']==submitted[k]['job'],'Terminal identity association')
    if require_complete: c.require(set(accepted)=={j['key'] for j in jobs}==set(claimed),'Complete fixed grid / no extra attempt')
    return dict(claimed=claimed,submitted=submitted,terminal=terminal,accepted=accepted,
                gpu_seconds=sum(e['row']['seconds'] for k,e in terminal.items() if claimed[k]['spec']['gpu']),
                cpu_seconds=sum(e['row']['seconds'] for k,e in terminal.items() if not claimed[k]['spec']['gpu']))

def full(auth,control,rows,resolution=None):
    jobs=c.grid(); state=ledger(control,jobs,False)
    allowed={j['key'] for j in jobs}|{'reused','submissions','submissions-r1','submissions-r2','submissions-r3','recovery-history','logs','ALL-MODELS-FROZEN.json','TECHNICAL-TRANCHE-PASSED.json'}
    c.require({p.name for p in auth.run.iterdir()}<=allowed,'Unrecognized run artifact/extra task')
    expected={j['key'] for j in jobs}; c.require(set(state['claimed'])==set(state['terminal'])==expected,'All claimed tasks terminal, no ambiguity')
    raw={r['job']:r for r in rows}; c.require(len(rows)==len(raw)==len(jobs) and set(raw)=={e['job'] for e in state['submitted'].values()},'Independent exact allocation set')
    faults={p.relative_to(control).as_posix():c.sha(p) for p in c.files(control) if p.name.startswith('STOP') or p.name.startswith('FAILURE')}
    missing=sorted(expected-set(state['accepted']))
    if faults or missing:
        c.require(resolution is not None,'Explicit dated control-fault resolution required')
        r=c.read(resolution)
        c.require(r['schema']=='ACVM1-control-resolution' and r['package']==auth.approval['package_sha256'] and r['faults']==faults
                  and r['missing_acceptance']==missing and r['instruction'].startswith('RESOLVE ACVM1 CONTROL ') and r['new_jobs']==0,'Exact resolution binding; no implicit recovery')
    receipts=[]
    for j in jobs:
        row=raw[state['submitted'][j['key']]['job']]
        c.require(row==state['terminal'][j['key']]['row'],'Independent scheduler/accounting equality')
        receipts.append(worker(auth.run,j,row,auth.approval['package_sha256'],auth.approval_sha))
    from models import check_freeze
    f=check_freeze(auth.run,auth.approval['package_sha256']); g=check_gate(auth.run)
    evals=[j for j in jobs if j['gpu']]
    c.require(f['unix']<min(state['claimed'][j['key']]['unix'] for j in evals),'Models frozen before evaluation')
    c.require(g['unix']<state['claimed'][evals[16]['key']]['unix'],'Source2 after included16 gate')
    return dict(unix=time.time(),package=auth.approval['package_sha256'],approval=auth.approval_sha,run=str(auth.run),tasks=8197,episodes=8192,sources=512,attempts=len(raw),gpu_seconds=state['gpu_seconds'],
                cpu_seconds=state['cpu_seconds'],receipts=receipts,control_faults=faults,resolution_sha256=c.sha(resolution) if resolution else None)
