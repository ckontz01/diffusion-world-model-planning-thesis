"""CPU-only original-artifact loading and inference-state inventory. NO forwards.

Ordinary cluster route explicitly authorized by the human after the VM waiver.
Hashes identify inputs; they do not certify arbitrary pickle code as harmless.
"""
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
from wm_diag0_preflight_v1.common import identity, verify, write_new

def tensor_slots(module, is_tensor):
    """Include persistent/nonpersistent buffers and plain/nested tensor attributes."""
    rows=[]
    def visit(name,value,depth=0):
        if is_tensor(value): rows.append((name,'unregistered',value)); return
        if depth>=4: return
        if type(value) is dict:
            for k,v in value.items():
                if type(k) is str: visit(name+'.'+k,v,depth+1)
        elif type(value) in (list,tuple):
            for i,v in enumerate(value): visit(name+'.'+str(i),v,depth+1)
    for name,t in module._parameters.items():
        if t is not None: rows.append((name,'parameter',t))
    for name,t in module._buffers.items():
        if t is not None: rows.append((name,'nonpersistent_buffer' if name in module._non_persistent_buffers_set else 'persistent_buffer',t))
    for name,v in vars(module).items():
        if name not in ('_parameters','_buffers','_modules'): visit(name,v)
    if len(rows)>2000: raise ValueError('tensor attribute bound')
    return rows

def validate_dino_structure(bundle):
    from models.vit import ViTPredictor, Attention
    from models.proprio import ProprioceptiveEmbedding
    import torch
    if type(bundle) is not dict: raise ValueError('DINO bundle must be mapping')
    p,a,r=(bundle[k] for k in ('predictor','action_encoder','proprio_encoder'))
    if type(p) is not ViTPredictor or type(a) is not ProprioceptiveEmbedding or type(r) is not ProprioceptiveEmbedding:
        raise ValueError('DINO explicit class binding')
    if list(p.pos_embedding.shape)!=[1,588,404] or p.pool!='mean' or len(p.transformer.layers)!=6:
        raise ValueError('DINO 3-history/196-patch/404-channel predictor architecture')
    if (a.in_chans,a.emb_dim,a.num_frames,a.tubelet_size)!=(10,10,1,1): raise ValueError('action architecture')
    if (r.in_chans,r.emb_dim,r.num_frames,r.tubelet_size)!=(1,10,1,1): raise ValueError('noprop architecture')
    expected=torch.arange(588).div(196,rounding_mode='floor')
    expected=(expected[:,None]>=expected[None,:]).to(torch.float32)[None,None]
    masks=[]
    for name,m in p.named_modules():
        if type(m) is Attention:
            if m.heads!=16 or not hasattr(m,'bias') or m.bias.dtype!=torch.float32 or not torch.equal(m.bias,expected):
                raise ValueError('missing/changed unregistered causal mask: '+name)
            if 'bias' in m._parameters or 'bias' in m._buffers: raise ValueError('mask registration differs from released implementation')
            masks.append(name+'.bias')
    if len(masks)!=6: raise ValueError('exactly six complete causal masks required')
    return masks

def inventory(model):
    import torch
    if not isinstance(model,torch.nn.Module): raise ValueError('module required')
    modules={}; tensors={}; alias={}; storage={}
    for prefix,m in model.named_modules(remove_duplicate=False):
        flags={'class':type(m).__module__+'.'+type(m).__name__,'training':m.training}
        for name in ('in_chans','emb_dim','num_frames','tubelet_size','num_heads','heads','scale','pool','p','dim','history_size','num_hist','num_pred','in_features','out_features','eps'):
            value=vars(m).get(name)
            if type(value) in (str,int,float,bool): flags[name]=value
        modules[prefix]=flags
        for name,kind,t in tensor_slots(m,torch.is_tensor):
            key=(prefix+'.' if prefix else '')+name
            if key in tensors: raise ValueError('tensor key collision')
            if t.device.type!='cpu' or t.layout!=torch.strided: raise ValueError('CPU dense state required')
            if t.is_floating_point() and not bool(torch.isfinite(t).all()): raise ValueError('nonfinite model state')
            raw=t.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
            tensors[key]={'kind':kind,'shape':list(t.shape),'dtype':str(t.dtype),'stride':list(t.stride()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            alias.setdefault(id(t),[]).append(key)
            storage.setdefault((t.untyped_storage().data_ptr(),t.storage_offset(),tuple(t.shape),tuple(t.stride())),[]).append(key)
    if len(tensors)>2000: raise ValueError('model inventory bound')
    return {'modules':modules,'tensors':tensors,'same_object_aliases':[v for v in alias.values() if len(v)>1],
            'same_storage_views':[v for v in storage.values() if len(v)>1],
            'state_dict_alone_used':False,'forwards':0}

def main():
    started=time.monotonic()
    contract_path=Path(sys.argv[1]); expected_hash=sys.argv[2]; output=Path(sys.argv[3])
    if identity(contract_path)['sha256']!=expected_hash: raise ValueError('contract identity')
    c=json.loads(contract_path.read_text()); root=contract_path.parent
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE,(980000,resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
    def emit(name,row):
        raw=json.dumps(row,sort_keys=True,indent=2).encode()
        current=sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        if len(raw)>900000 or current+len(raw)>950000: raise ValueError('aggregate preflight output bound')
        write_new(output/name,row)
    dispatch=json.loads((root.parent/'controls/DISPATCH.json').read_text())
    if os.environ.get('SLURM_JOB_ID')!=dispatch['job_id'] or dispatch['contract_sha256']!=expected_hash:
        raise ValueError('exact dispatch ID and contract required')
    if os.environ.get('CUDA_VISIBLE_DEVICES') not in ('',None): raise ValueError('CPU-only task')
    for rel,row in c['staged_members'].items(): verify(root/rel,row)
    for name,row in c['runtime_source'].items(): verify(Path(c['site_packages'])/name,row)
    for name,row in c['lewm'].items(): verify(row['path'],{k:row[k] for k in ('bytes','sha256')})
    # Only authenticated explicit source roots; no torch.hub/Hydra constructors.
    sys.path[:0]=[str(root/'lewm'),str(root/'dino'),str(root/'encoder')]
    import torch
    torch.set_num_threads(4); torch.set_num_interop_threads(1)
    if torch.cuda.is_initialized(): raise ValueError('unexpected CUDA initialization')
    runtime={'python':sys.version,'torch':torch.__version__,'versions':{name:importlib.metadata.version(name) for name in c['runtime_packages']},
             'forwards':0,'physics_steps':0,'source_roots_generated':0}
    emit('runtime.json',runtime)
    for task in ('pusht','reacher'):
        # Real artifact executable-object deserialization, confined to this
        # ordinary CPU Slurm allocation. No inference is called.
        bundle=torch.load(root/('artifacts/'+task+'.pth'),map_location='cpu',weights_only=False)
        masks=validate_dino_structure(bundle)
        row={'artifact':c['staged_members']['artifacts/'+task+'.pth'],'required_masks':masks,
             'payload_keys':sorted(bundle),'objects':{k:inventory(bundle[k]) for k in ('predictor','action_encoder','proprio_encoder')},'forwards':0}
        emit('dino-'+task+'.json',row)
        del row,bundle; gc.collect()
    # Official tensor-only encoder: explicit pinned local constructor, strict load.
    from dinov2.models.vision_transformer import vit_small
    encoder=vit_small(img_size=518,patch_size=14,init_values=1.0,ffn_layer='mlp',block_chunks=0,
                      num_register_tokens=0,interpolate_antialias=False,interpolate_offset=0.1)
    state=torch.load(root/'artifacts/dinov2_vits14.pth',map_location='cpu',weights_only=True)
    encoder.load_state_dict(state,strict=True)
    if encoder.embed_dim!=384 or encoder.patch_size!=14: raise ValueError('encoder definition')
    row=inventory(encoder); row['strict_original_state_load']=True; row['training_time_checkout_verified']=False
    emit('encoder.json',row)
    del encoder,state,row; gc.collect()
    from jepa import JEPA
    for task in ('pusht','reacher'):
        model=torch.load(c['lewm'][task]['path'],map_location='cpu',weights_only=False)
        if type(model) is not JEPA: raise ValueError('Le-WM original class identity')
        emit('lewm-'+task+'.json',inventory(model))
        del model; gc.collect()
    if torch.cuda.is_initialized(): raise ValueError('unexpected CUDA initialization')
    emit('SUCCESS.json',{'status':'AUTHENTICATED_CPU_LOADING_COMPLETE','job_id':dispatch['job_id'],
               'elapsed_seconds':time.monotonic()-started,'forwards':0,'physics_steps':0,'fitting':False,
               'full_campaign_ready':False,'functional_equivalence_tested':False})

if __name__=='__main__': main()
