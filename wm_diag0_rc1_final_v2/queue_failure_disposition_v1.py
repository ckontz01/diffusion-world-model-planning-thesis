"""Local-only disposition of retained observation errors; no scheduler retry.

Authenticates original saved bytes and frozen guard source. It does not recover
discarded sacct/squeue data, infer research state, weaken the guard or alter any
published source, job/controller, environment or security setting.
"""
import ast,base64,hashlib,json
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,identity,write_new
from wm_diag0_rc1_completion_v1.compact import program
from wm_diag0_rc1_grid_v1.scheduler import SOURCE

FAILURE={'bytes':1302,'sha256':'4511f3c450e9a5b90622e71cdb59eceab3ac1829692d17ee91c41c399a994adb'}
PROGRAM='6a6caa4c0eae6149bde0b45726a9ee5f7a7b0137590c648dda43047fe7f40023'


def retained(stream):
    raw=base64.b64decode(stream['retained_prefix_base64'],validate=True)
    if stream['truncated'] is not False or len(raw)!=stream['bytes'] or hashlib.sha256(raw).hexdigest()!=stream['sha256']:
        raise ValueError('complete exact saved diagnostic bytes, no reconstructed missing output')
    return raw


def main():
    target=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/OBSERVATION-GUARD-DISPOSITION-012.json'
    if target.exists():raise FileExistsError('preserve exclusive completed disposition')
    failure_path=DOC/'OBSERVE-R012.failure.json'
    if identity(failure_path)!=FAILURE:raise ValueError('exact retained new failure identity')
    z=json.loads(failure_path.read_text());local=json.loads((DOC/'LOCAL-RESUMEOBS012.json').read_text())
    if z['dispatch']!='317180' or z['program_sha256']!=PROGRAM or type(z['transport_returncode']) is not int or z['transport_returncode']!=1:
        raise ValueError('same exact scheduled observation/transport response')
    if z['failure_kind']!='NONZERO_TRANSPORT_OR_REMOTE_NO_CAUSE_ASSUMED' or z['research_failure_inferred'] is not False or z['research_jobs_or_controllers_changed'] is not False:
        raise ValueError('never relabel observation error as research failure')
    if local['component']!='monitoring' or local['status']!='CHILD_NONZERO' or local['charged_seconds']!=30 or local['returncode']!=125:
        raise ValueError('original full-reservation local failure chain')
    message=retained(z['captured']['stderr']).decode('utf8',errors='strict')
    if retained(z['captured']['stdout'])!=b'':raise ValueError('no saved research snapshot to interpret')
    exact='RuntimeError: queue unavailable/ambiguous; not proof of terminal allocations: slurm_load_jobs error: Invalid job id specified'
    if exact not in message or 'in exact_snapshot' not in message:raise ValueError('only exact retained queue guard rejection diagnosed')
    frozen=program()
    if hashlib.sha256(frozen.encode()).hexdigest()!=PROGRAM:raise ValueError('published observer program unchanged')
    for required in ("p.returncode!=1",'p.stdout.strip()',"{x[0] for x in rows}!=set(required_logical)","any(x[2].split()[0] not in terminal for x in rows)"):
        if required not in SOURCE:raise ValueError('original complete terminal-history guard retained')
    for folder in (DOC,ROOT/'docs/world-model-diagnostic-rc1-monitor-v2-20261016'):
        published=json.loads((folder/'SSD-VERIFIED-001.json').read_text())
        for n,want in published['working_source_members'].items():
            if identity(ROOT/n)!=want:raise ValueError('frozen published dependency/source/evidence unchanged')
    evidence={'R012failure':FAILURE,'R012local':identity(DOC/'LOCAL-RESUMEOBS012.json'),
              'R012started':identity(DOC/'OBSERVE-R012.started.json')}
    for label in ('010','011'):
        p=DOC/('LOCAL-HUMANOBS'+label+'.json');row=json.loads(p.read_text())
        if row['status']!='FAILED' or row['charged_seconds']!=30 or row['returncode']!=125 or row['stdout']!='' or row['error']!="TimeoutError('owned operation work deadline; not proof of cluster failure')":
            raise ValueError('preserve prior outer timeouts without inferring their cause')
        if (DOC/('OBSERVE-R'+label+'.json')).exists() or (DOC/('OBSERVE-R'+label+'.failure.json')).exists():
            raise ValueError('new later evidence needs separate reconciliation, never overwrite history')
        evidence['R'+label+'local']=identity(p);evidence['R'+label+'started']=identity(DOC/('OBSERVE-R'+label+'.started.json'))
    ast.parse(Path(__file__).read_text(),feature_version=(3,6));ast.parse(frozen,feature_version=(3,6))
    result={'status':'SAVED_QUEUE_INVALID_ID_STRICT_GUARD_REJECTION_AUTHENTICATED_NOT_RESEARCH_STATE',
        'source':identity(__file__),'evidence':evidence,'unchanged_observer_program_sha256':PROGRAM,
        'retained_stderr_encoding':'utf8','retained_stderr_bytes':len(message.encode()),
        'retained_stderr_sha256':z['captured']['stderr']['sha256'],
        'diagnosed_scope':'R012 remote exact_snapshot raised on queue Invalid job ID; its complete-terminal fallback guard did not pass',
        'discarded_inner_sacct_rows_squeue_stdout_and_returncode_recovered':False,
        'which_inner_guard_condition_failed_known':False,
        'R010_R011_timeout_causes_retrospectively_inferred':False,
        'current_cluster_health':'UNVERIFIED','current_completed_or_live_run_count_known':False,
        'last_successful_observation':'R009 is historical only, not current proof',
        'research_failure_or_all_finished_or_cancellation_inferred':False,
        'research_jobs_or_controllers_changed':False,'published_observer_or_guard_changed':False,
        'automatic_retry':False,'same_observation_labels_reusable':False,
        'next_scheduled_observation':'ONE new exclusive R013 or later after current exact lineage/path/source checks; never R010/R011/R012 again',
        'additional_WSL_SSH_scheduler_cluster_SSD_or_research_queries':0,
        'scientific_payloads_or_quality_or_outcomes_read':False,'final_gate_ready':False}
    write_new(target,result,limit=12000)
    print(json.dumps({'status':result['status'],'discarded_scheduler_data_recovered':False,
                      'current_cluster_health':'UNVERIFIED','additional_cluster_queries':0}))


if __name__=='__main__':main()
