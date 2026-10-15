"""Freeze finite preflight input identities; hashes only, no model imports."""
import hashlib
import json
from wm_diag0_preflight_v1.common import *

A2=ROOT/'docs/world-model-diagnostic-a2-20261004'
ENC=ROOT/'docs/world-model-diagnostic-a2-cluster-native-v1-20261015'

def blobs():
    out={}
    for name in ('__init__.py','common.py','worker.py','supervisor.py'):
        out['wm_diag0_preflight_v1/'+name]=(ROOT/'wm_diag0_preflight_v1'/name).read_bytes()
    prep=json.loads((ENC/'PREPARE-001.json').read_text())
    for row in prep['encoder_source']['members']:
        p=ROOT/row['path']; verify(p,{k:row[k] for k in ('bytes','sha256')})
        out['encoder/'+row['upstream_path']]=p.read_bytes()
    for name in ('__init__.py','vit.py','proprio.py'):
        p=A2/'source-audit/point-lewm/third_party/dino_wm/models'/name
        out['dino/models/'+name]=p.read_bytes()
    lewm=json.loads((DOC/'LEWM-SOURCE-001.json').read_text())
    for name,row in lewm.items():
        b=row['source'].encode()
        if hashlib.sha256(b).hexdigest()!=row['sha256'] or len(b)!=row['bytes']: raise ValueError('Le-WM source record')
        out['lewm/'+name]=b
    artifacts=json.loads((A2/'ARTIFACT-RECEIPTS.json').read_text())
    for row in artifacts:
        p=A2/'artifacts'/(row['name']+'.pth'); verify(p,{k:row[k] for k in ('bytes','sha256')})
        out['artifacts/'+p.name]=p.read_bytes()
    for task in ('pusht','reacher'):
        for name in ('hydra.yaml','swm_h5_norm_stats.json'):
            out['configs/'+task+'/'+name]=(A2/'source-audit'/task/'dino-wm'/name).read_bytes()
    plan=A2/'ROOT-PLAN.json'
    if identity(plan)['sha256']!='e648465420311a69a3df237b9f199ecd070e1c1241481376888ffbffe593630f': raise ValueError('root plan changed')
    out['ROOT-PLAN.json']=plan.read_bytes()
    for name in out: relative(name)
    return out

def main():
    items=blobs()
    inv=json.loads((DOC/'CLUSTER-INVENTORY-002.json').read_text())
    if inv['new_run_already_exists']: raise FileExistsError('run already exists')
    for task,wanted in [('pusht','c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659'),('reacher','6b03b0e39f00a601b83dc94765e4b022c48127ced762543bddb1398ce52c310d')]:
        if inv['lewm'][task]['sha256']!=wanted or inv['lewm'][task]['unresolved_stack_globals']: raise ValueError('Le-WM identity/globals')
    members={n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in items.items()}
    source_bytes=sum(r['bytes'] for n,r in members.items() if not n.startswith('artifacts/'))
    if source_bytes>2_000_000 or sum(r['bytes'] for r in members.values())>270_000_000: raise ValueError('stage reservation')
    c={'study':'WM-DIAG0-A2','stage':'CPU_PREFLIGHT_V1','run':RUN,'sif':SIF,'sif_sha256':SIF_HASH,
       'venv':VENV,'site_packages':SITE,'staged_members':members,'runtime_source':inv['source_members'],'lewm':inv['lewm'],
       'runtime_packages':['torch','torchvision','numpy','einops','transformers','timm','stable-worldmodel','stable-pretraining','safetensors'],
       'runtime_binary_closure':'SIF authenticated in full; existing venv source inventory plus installed-version metadata bound. Complete additional native simulator/binary/asset closure is a later gate, not claimed here.',
       'commands':'Original DINO and Le-WM objects: torch.load CPU weights_only=False. Encoder: pinned local vit_small plus weights_only=True strict tensor state. No forward, simulator, labels or fit.',
       'attempts':1,'allocation_seconds':1200,'work_seconds':1140,'cpus':4,'memory_bytes':8589934592,
       'output_bytes':1000000,'logs_bytes':100000,'tmp_bytes':20000000,
       'gpu_jobs':0,'cpu_full_future_after_reserving_this':12600,'cpu_aggregate_cap':13800,
       'gpu_full_future_seconds':468000,'live_bytes_reserved':12342309744,'live_cap':13000000000,
       'archive_cap':14000000000,'inclusive_reserved':43374852312,'inclusive_cap':44000000000,
       'no_retry':True,'no_environment_changes':True,'functional_parity_tested':False,'campaign_ready':False}
    reservation(1200)
    write_new(DOC/'CONTRACT.json',c)
    print(json.dumps({'contract':identity(DOC/'CONTRACT.json'),'source_bytes':source_bytes,'staged_bytes':sum(r['bytes'] for r in members.values()),'members':len(members)}))

if __name__=='__main__': main()
