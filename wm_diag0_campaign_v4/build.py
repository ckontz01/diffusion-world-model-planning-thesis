"""Freeze source-complete native readout/technical/grid/analysis contracts."""
import hashlib,json
from .common import ROOT,DOC,RUN,identity,write_new
from wm_diag0_source_r3.common import RUN as SOURCE_RUN

MODULES=('__init__','common','models','planning','world','diagnostic','readout','accept','accept_readout','worker','validate_task','supervisor','analysis','final_archive','verify_archive')

def additions():
    out={'wm_diag0_campaign_v4/'+m+'.py':(ROOT/'wm_diag0_campaign_v4'/(m+'.py')).read_bytes() for m in MODULES}
    base=ROOT/'docs/world-model-diagnostic-a2-20261004/source-audit/point-lewm/third_party/dino_wm/models'
    for n in ('__init__.py','vit.py','proprio.py','visual_world_model.py'):out['dino/models/'+n]=(base/n).read_bytes()
    return out

def main():
    accepted=json.loads((DOC/'SOURCE-GATE-001.json').read_text());physics=json.loads((DOC/'COMPILED-PHYSICS-BOUND-001.json').read_text());ids=json.loads((DOC/'SOURCE-CONTROL-IDENTITIES-001.json').read_text())
    if accepted['status']!='ALL120_SOURCE_WINDOWS_INDEPENDENTLY_ACCEPTED' or len(accepted['roots'])!=120 or physics['status']!='NATIVE_INTEGRATOR_MULTIPLICITIES_BOUND':raise ValueError('complete independent source/physics gates')
    c=json.loads((ROOT/'docs/world-model-diagnostic-a2-source-r3-20261015/CONTRACT.json').read_text())
    storage=json.loads((DOC/'SOURCE-STORAGE-GATE-001.json').read_text())
    if storage['status']!='ALL_SOURCE_RETAINED_BYTES_WITHIN_RESERVATION':raise ValueError('all failed/live source storage')
    c['source_storage_acceptance']=identity(DOC/'SOURCE-STORAGE-GATE-001.json')
    c['runtime_symlinks']=json.loads((ROOT/'docs/world-model-diagnostic-a2-native-v3-20261015/RUNTIME-INVENTORY-001.json').read_text())['symlinks']
    old=c['staged_members'].copy()
    for n,b in additions().items():
        compile(b,n,'exec',dont_inherit=True)
        row={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        if n.startswith('dino/') and n in c['prior_members'] and row!=c['prior_members'][n]:raise ValueError('original DINO component source identity')
        c['staged_members'][n]=row
    for label in ('CAMPAIGNACCEPTTEST001','CAMPAIGNCONTROLTEST002'):
        p=ROOT/'docs/world-model-diagnostic-a2-native-v3-20261015'/('LOCAL-'+label+'.json')
        if json.loads(p.read_text())['returncode']:raise ValueError('new artificial gate tests')
    c.update(run=RUN,source_generation_authorized=False,gpu_stage_authorized=False,gpu_stages_authorized=True,
             full_campaign_ready=False,conditional_dispatch_ready=True,source_run=SOURCE_RUN,source_runs=accepted['source_runs'],
             source_acceptance=ids['ALL-SOURCES-ACCEPTED.json']['identity'],compiled_physics=physics,
             compiled_physics_identity=ids['COMPILED-PHYSICS-BOUND.json']['identity'],
             dino_source=RUN+'/source/dino',source_supplier=SOURCE_RUN,source_supplier_members=old,
             cpu_charged_before=accepted['cpu_total_with_preflight'],cpu_full_future_reserved=5400,
             gpu_charged_before=0,gpu_full_future_reserved=468000,
             allowed_gpu_names=['NVIDIA RTX 6000 Ada Generation','NVIDIA RTX6000 Ada'],
             allowed_gpu_nodes=['gpu09','gpu09.cluster'],GPU_partition='a6000',GPU_count=1,
             allocation_seconds={'readout':1800,'technical':3600,'grid':3600,'analysis':3600},
             preserve_seconds=60,cpus=4,memory_bytes=8589934592,
             stage_counts={'readout':4,'technical':4,'grid':124,'analysis':1},
             no_requeue=True,max_concurrency=1,automatic_research_replacements=0,
             final_publication_requires_full_independent_acceptance_and_SSD=True,
             preparation_cumulative_seconds=14104.10301460012,preparation_unreserved_seconds=295.89698539988)
    c['remaining_native_gates']=['four native readouts','included first-setting original-object forecast/cost/replay/goal-setting parity','remaining fixed grid','complete independent analysis','final native-Windows SSD whole/member preservation']
    c['included_technical_gate']={'roots':'root000 of each setting; no extra pilot','T':1,'grouping':5,'num_hist':3,'DINO_chunk':100,
       'two_additional_fresh_replays_each':True,'original_reference':'deserialized released objects and pinned original VWorldModel.rollout',
       'cached_native_cost_exact_bits':True,'uncached_DINO_reference_rtol':2**-6,'uncached_DINO_reference_atol':2**-8,'no_tolerance_reselection':True}
    if c['cpu_charged_before']+5400>13800 or 4*1800+128*3600!=468000 or c['live_full_future_bytes']>13000000000:raise ValueError('all-failure-inclusive full future reservations')
    dest=DOC/'campaign';dest.mkdir(exist_ok=True);write_new(dest/'CONTRACT.json',c)
    print(json.dumps({'contract':identity(dest/'CONTRACT.json'),'source_roots_accepted':120,'staged_members':len(c['staged_members']),
        'GPU_future_seconds':468000,'CPU_charged_plus_full_future':c['cpu_charged_before']+5400,'GPU_stages':c['stage_counts'],'independent_real_parity_still_required':True}))

if __name__=='__main__':main()
