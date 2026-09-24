"""Metadata reconciliation and production bindings. NO payload/model/runtime loading."""
import common as c
from pathlib import Path
import sys
import time
import subprocess
import argparse

def main():
    if sys.argv[1:]==['--forecast-only']:
        forecast();return
    sys.path.append(str(c.PROPOSAL))
    from prepare_proposal import reconcile,query
    if sys.argv[1:]==['--reconcile-live']:
        saved=c.read(c.ROOT/'RECONCILIATION.json');audit,ac=reconcile();records,reader=query(ac)
        old=c.read(c.PROPOSAL/'ELIGIBILITY.json')
        c.require(audit['metadata_pins']==saved['metadata_pins'] and reader==saved['reader_sha256'],'Changed role/source reader')
        for n,h in saved['role_ledger_inventory'].items():c.require(c.sha(c.REPO/n)==h,'Intervening role ledger conflict')
        c.require({str(i):records[str(i)] for i in old['selected_references']}==old['records'],'Source metadata conflict')
        saved.update(status='LIVE_METADATA_RECONCILED',live_conflicts=0,unix=time.time(),pending_receipt=c.sha(c.ROOT/'RECONCILIATION.json'))
        c.write(c.ROOT/'RECONCILIATION-LIVE.json',saved);print('Exact512 live metadata reauthenticated; zero payload reads');return
    old=c.read(c.PROPOSAL/'ELIGIBILITY.json')
    parser=argparse.ArgumentParser();parser.add_argument('--offline-draft',action='store_true');args=parser.parse_args()
    audit,ac=reconcile()
    if args.offline_draft:records,reader=old['records'],old['identity_reader_sha256']
    else:records,reader=query(ac)
    for key in ('metadata_pins','eligible_before_selection','acv0','rb2','prior_union','exclusion_roles'):
        c.require(audit[key]==old[key],'Intervening role conflict: '+key)
    c.require({str(i):records[str(i)] for i in old['selected_references']}==old['records'],'Exact512 identity/order unchanged')
    # Record the full local role-ledger inventory so newly introduced assignments cannot be hidden.
    names=subprocess.run(['git','ls-files','docs'],cwd=c.REPO,capture_output=True,text=True,check=True).stdout.splitlines()
    role_names=[n for n in names if any(k in Path(n).name for k in ('DATA-ROLES','FOLDS','ALLOCATION','ELIGIBILITY'))]
    expected={
      'docs/active-counterfactual-verification-20260923/DATA-ROLES-PROPOSED.json',
      'docs/action-verification-testbed-20260922/DATA-ROLES-PROPOSED.json',
      'docs/candidate-value-score-information-20260918/FOLDS.json',
      'docs/candidate-value-learning-20260914/PROPOSED-ALLOCATION.json',
      'docs/candidate-value-breadth-precision-20260915/DATA-ROLES.json',
      'docs/active-counterfactual-mechanism-replication-20260924/ELIGIBILITY.json',
      'docs/local-goal-proposals-20260918/DATA-ROLES.json',
      'docs/local-goal-source-replication-20260920/DATA-ROLES.json'}
    c.require(set(role_names)==expected,'New role ledger requires reconciliation, never source substitution')
    c.write(c.ROOT/'RECONCILIATION.json',dict(status='PENDING_SSD_AND_CONFIGURED_WSL' if args.offline_draft else 'LIVE_METADATA_RECONCILED',unix=time.time(),reviewed_preparation='70e359258d0763a29be40831998696e2ca7a9d0d',
            metadata_pins=audit['metadata_pins'],role_ledger_inventory={n:c.sha(c.REPO/n) for n in role_names},
            reader_sha256=reader,registry_sha256=old['registry_sha256'],selected_order=c.digest(old['selected_references']),
            records=c.digest(old['records']),payload_reads=0,assigned_now=False,local_conflicts=0,live_conflicts=None if args.offline_draft else 0,
            limitation='Repository ledger inventory plus authenticated original registry. Must recheck at future launch for intervening assignments.'))
    rm={k:ac['proposed_roles'][k] for k in ('fit','validation')};rm['mechanism_evaluation']=old['selected_references']
    c.write(c.ROOT/'ROLES.json',dict(roles=rm,old32_excluded=ac['proposed_roles']['final_development'],registry=old['registry_sha256'],status='proposed; execution disabled'))
    b=c.read(c.OLD/'INPUT-BINDINGS.json')
    b['references']={k:dict(v,file=str(Path(b['registry_path']).parent).replace('\\','/')+'/'+v['file']) for k,v in old['records'].items()}
    b['roles_sha256']=c.sha(c.ROOT/'ROLES.json');b['research_payload_reads_in_preparation']=0
    c.write(c.ROOT/'INPUT-BINDINGS.json',b)
    c.write(c.ROOT/'CONTROLLER-RUNTIME.json',c.read(c.OLD/'CONTROLLER-RUNTIME.json'))
    pub=c.REPO/'docs/active-counterfactual-verification-publication-20260923/completion-r6'
    fit=c.read(pub/'FIT-RECORDS.json');remote=c.RESEARCH+'/experiments/active-counterfactual-verification-pilot-v1/run-c2c6fcbe8c41fed2'
    files={}
    for name,source in [('joint.npz','fit-joint/joint.npz'),('ordinary.npz','fit-ordinary/ordinary.npz'),
                        ('fit-dataset.npz','fit-joint/fit-dataset.npz'),('validation-dataset.npz','fit-joint/validation-dataset.npz'),
                        ('PREPROCESSING.json','fit-joint/PREPROCESSING.json'),('ORIGINAL-JOINT-FIT.json','fit-joint/FIT.json'),('ORIGINAL-ORDINARY-FIT.json','fit-ordinary/FIT.json')]:
        folder,member=source.split('/')
        info=fit['run/'+folder+'/SEAL.json']['files'][member]
        files[name]=dict(path=remote+'/'+source,**info)
    c.write(c.ROOT/'MODEL-REUSE.json',dict(files=files,original_commit='5d8666754ad8aa0507730f86cf3ee6caa32c105a',
                original_archive_sha256='bd0f53b85c3de36376bc68a084d4fbc7cb5b0958943534a890d0ee9b2d70342b',
                original_seal_objects_canonical_digest={k:c.digest(v) for k,v in fit.items() if k.endswith('/SEAL.json')},reuse_without_refit=True,
                saved_data_only=True,validation_reporting_only=True))
    c.write(c.ROOT/'REPORTING-CONTRACT.json',dict(primary=['active-minus-no_update','active-minus-committed_feedback'],
            contrasts=7,multiplicity='unchanged family7; nominal Bonferroni bootstrap plus simultaneous Hoeffding bounds',
            hoeffding_positive='Stringent additional certificate, NOT a necessary scientific success criterion. Its absence is not a scientific-failure verdict.',
            bootstrap='Nominal intervals, not finite-sample guarantees.',effect_size=.05,
            interpretation='Interpret fixed five-point practical effect with full uncertainty; never change threshold post-outcome.',
            seed_variation='Three fixed pairs reported separately; not independent source observations or a population of training seeds.',
            source_unit=512,early_replan_runs_per_source=1,old32_pooling=False,promotion=False,automatic_expansion=False,
            saved_analysis_preserved='Including worse conditional prediction metrics; no model/target response to findings.'))
    forecast()
    print(c.json.dumps(dict(local_metadata_checked=512,live_metadata_checked=not args.offline_draft,payload_reads=0,fit_jobs=4,execution_enabled=False)))

def forecast():
    pub=c.REPO/'docs/active-counterfactual-verification-publication-20260923/completion-r6'
    accounting=c.read(pub/'CAMPAIGN-ACCOUNTING.json')['allocations'];table=[]
    for arm in c.CONTROLS:
        oldarm='static' if arm=='committed_feedback' else arm
        rows=[r for r in accounting if r.get('spec',{}).get('control')==oldarm and r['state']=='COMPLETED']
        c.require(len(rows)==32,'Historical32 per arm')
        total=sum(r['seconds'] for r in rows);n=512 if arm=='early-replan' else 1536
        table.append(dict(arm=arm,historical_allocations=None if arm=='committed_feedback' else 32,
                          measured_seconds=None if arm=='committed_feedback' else total,
                          scenario_seconds_per_episode=total/32,scenario_basis='UNMEASURED; explicitly assumed static-mean proxy' if arm=='committed_feedback' else 'ACV0 actual allocation mean',
                          new_episodes=n,scenario_gpu_seconds=n*total/32))
    predicted=sum(r['scenario_gpu_seconds'] for r in table)
    c.write(c.ROOT/'COST-FORECAST.json',dict(accounting_sha256=c.sha(pub/'CAMPAIGN-ACCOUNTING.json'),table=table,
            scenarios=[dict(slowdown=x,gpu_hours=x*predicted/3600) for x in (1,2,3)],full_gpu_ceiling_hours=2457600/3600,
            cpu_stage_ceiling_hours=10,new_fit_jobs=4,new_fit_cost_unmeasured=True,new_analysis_cost_unmeasured=True,
            historical_cpu_jobs=[dict(key=r['spec']['key'],seconds=r['seconds']) for r in accounting if r.get('spec') and not r['spec']['gpu']],
            caveats='Scenarios are assumptions, not future throughput evidence. Queue, host verification, transfer and preservation time excluded. No rebatching, shorter timeouts, concurrency increase or best-seed selection.'))
    from storage import footprint
    c.write(c.ROOT/'FOOTPRINT.json',footprint(c.grid()))
if __name__=='__main__':main()
