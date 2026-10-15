"""One bounded encoding-only fault isolation; no predictor/physics/scoring."""
import json,sys
from pathlib import Path
import numpy as np
import torch
from wm_diag0_campaign_v4.models import Adapter
from wm_diag0_native_v3.store import authenticate,load_array
from wm_diag0_native_v3.runtime import verify_imports
from .common import identity,write_new

@torch.inference_mode()
def main():
    root=Path(sys.argv[1]); cp=root/'source/PROBE-CONTRACT.json'; c=json.loads(cp.read_text())
    if identity(cp)['sha256']!=sys.argv[2]:raise ValueError('exact probe contract')
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0) not in c['allowed_gpu_names']:raise ValueError('exact single GPU')
    for name,row in c['prior_members'].items():
        if identity(Path(c['prior_source'])/name)!=row:raise ValueError('frozen model/config/source')
    source_acceptance=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(source_acceptance)!=c['source_acceptance']:raise ValueError('original accepted sources')
    accepted=json.loads(source_acceptance.read_text())
    directory=Path(c['source_runs']['pusht'])/'tasks/pusht-000/output'
    authenticate(directory,accepted['source_seals']['pusht-000'],12_000_000)
    history=load_array(directory/'selector/history.npy',(1,224,224,3),['|u1'])
    failed=Path(c['recovery']['old_run'])/'tasks/technical-1/output'
    for name,row in c['recovery']['partial'].items():
        if identity(failed/name)!=row:raise ValueError('preserved failed partial')
    actions=load_array(failed/'actions.npy',(16,25,2),['<f4'])
    adapter=Adapter('pusht','dinowm_noprop',root/'source',c)
    verify_imports(c,root/'source')
    x=adapter.pixels(history)[None]
    z=torch.from_numpy(adapter.normalized(actions)).to(adapter.device)
    wm=adapter.model
    def difference(a,b):
        a,b=a.float(),b.float();delta=(a-b).abs();limit=2**-8+(2**-6)*b.abs()
        return {'shape':list(a.shape),'exact':torch.equal(a,b),'within_original_tolerance':bool(torch.all(delta<=limit)),
                'max_absolute_difference':float(delta.max()),'mismatched_elements':int((delta>limit).sum()),'elements':a.numel()}
    with adapter.autocast():
        single=wm.encode_obs({'visual':x,'proprio':torch.zeros(1,1,1,device=adapter.device)})
        batch=wm.encode_obs({'visual':x.expand(16,-1,-1,-1,-1),'proprio':torch.zeros(16,1,1,device=adapter.device)})
        grouped=wm.encode_act(z)
        separate=torch.cat([wm.encode_act(z[:,i:i+1]) for i in range(5)],dim=1)
    report={'status':'ENCODING_ONLY_DIAGNOSIS_COMPLETE','source_encoding_batch1_vs16':difference(single['visual'].expand_as(batch['visual']),batch['visual']),
            'action_encoding_sequence5_vs_five_sequence1':difference(grouped,separate),
            'source_proprio_batch1_vs16':difference(single['proprio'].expand_as(batch['proprio']),batch['proprio']),
            'actual_usage':{'visual_encoder_calls':2,'encoded_frames':17,'action_encoder_calls':6,'proprio_encoder_calls':2,
                            'predictor_calls':0,'cost_calls':0,'physics_resets':0,'controller_actions':0},
            'GPU':torch.cuda.get_device_name(0),'torch':torch.__version__,'rtol':2**-6,'atol':2**-8,
            'tolerances_changed':False,'model_or_science_changed':False,'scientific_outputs_read_or_generated':False,
            'contract_sha256':sys.argv[2]}
    if adapter.predictor_calls or adapter.cost_api_calls:raise ValueError('encoding-only authority')
    verify_imports(c,root/'source')
    write_new(root/'tasks/encoding-only/output/DIAGNOSIS.json',report)
    print(json.dumps(report))

if __name__=='__main__':main()
