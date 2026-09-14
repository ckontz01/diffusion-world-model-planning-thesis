"""Metadata/source-only launch capsule builder. Does NOT grant launch approval.

Run on Prometheus before launch review. No reference NPZ or outcome is opened.
The collection registry is authenticated, then projected to selected identity
fields; no nonselected record/payload is exported or used for allocation.
"""
import argparse
import json
from pathlib import Path
import candidate_value_contract as ct


def identity_projection(path,ids):
    """Decode only selected identity fields, not registry outcome/descriptive values.

    The registry's raw bytes are authenticated separately. Lexically skip values
    outside this allowlist; do not materialize its nonselected outcome records.
    """
    raw=Path(path).read_text();decoder=json.JSONDecoder();wanted=set(ids)
    def ws(i):
        while raw[i].isspace():i+=1
        return i
    def end(i):
        i=ws(i)
        if raw[i]=='"':
            j=i+1
            while True:
                if raw[j]=='\\':j+=2;continue
                if raw[j]=='"':return j+1
                j+=1
        if raw[i] in '{[':
            closing='}' if raw[i]=='{' else ']';j=ws(i+1)
            while raw[j]!=closing:
                if raw[j] in ',:':j=ws(j+1)
                else:j=ws(end(j))
            return j+1
        j=i
        while raw[j] not in ',]} \r\n\t':j+=1
        return j
    def members(i):
        ct.require(raw[i]=='{','Registry object');i=ws(i+1)
        while raw[i]!='}':
            key,j=decoder.raw_decode(raw,i);j=ws(j)
            ct.require(raw[j]==':','Registry key');start=ws(j+1);stop=end(start)
            yield key,start,stop
            i=ws(stop)
            if raw[i]==',':i=ws(i+1)
    arrays=[(i,j) for key,i,j in members(ws(0)) if key=='records']
    ct.require(len(arrays)==1,'Registry records');i=ws(arrays[0][0]+1);position=0;result={}
    allowed={'index','file','sha256','environment_seed','namespace','attempt'}
    while raw[i]!=']':
        stop=end(i)
        if position in wanted:
            result[position]={key:json.loads(raw[a:b]) for key,a,b in members(i) if key in allowed}
            ct.require(set(result[position])==allowed and result[position]['index']==position,'Identity-only registry projection')
        position+=1;i=ws(stop)
        if raw[i]==',':i=ws(i+1)
    ct.require(set(result)==wanted,'Missing selected identity')
    return result


def freeze(source,out):
    source=Path(source);source_sha=ct.sha(source/'SOURCE-MANIFEST.sha256')
    ct.verify_source(source,source_sha)
    base=ct.ROOT/'experiments/independent-pusht/final-20260906-4a608e5'
    lock=base/'INPUT-LOCK.json'
    ct.require(ct.sha(lock)=='90ac1fd4e8e5fbaa3941ab9a5b7ed127bc20cb96018bed5d143b7dec2cbf64cb','Historical input lock')
    registry=base/'collection/COLLECTION.json';expected=ct.json_read(lock)['collection_sha256']
    ct.require(ct.sha(registry)==expected,'Collection registry identity')
    metadata=identity_projection(registry,sum(ct.allocation().values(),[]));records={}
    for ref in sum(ct.allocation().values(),[]):
        r=metadata[ref]
        ct.require(r['index']==ref and r['file']=='reference-%05d.npz'%ref,'Registered source identity')
        records[str(ref)]=dict(file=str(base/'collection'/r['file']),sha256=r['sha256'],
            environment_seed=r['environment_seed'],source_key=r['namespace']+':'+str(r['attempt']))
    pins=ct.json_read(source/'cluster/prometheus/INDEPENDENT-PINNED-INPUTS.json')
    env=ct.ROOT/'envs/hi-lewm-artifact-py311-cu121-swm006'
    image=ct.ROOT/'containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'
    runtime_files={str(image):ct.sha(image)}
    for r in pins['checkpoints']:
        if (r['family'],r['training_seed'])==('vad',7201):
            ct.require(ct.sha(r['path'])==r['sha256'],'Proposer bytes')
            runtime_files[r['path']]=r['sha256']
            for name in ('summary.json','training.jsonl','sha256.txt'):
                p=Path(r['path']).with_name(name);runtime_files[str(p)]=ct.sha(p)
    for p,key in ((ct.ROOT/'data/stablewm/pusht/lewm_hf_22b330c_object.ckpt','lewm_sha256'),
                  (ct.ROOT/'experiments/gdp-cem-e17/development-run-20260827-9fb5a8c2/models/pusht/final.pt','adapter_sha256')):
        ct.require(ct.sha(p)==pins[key],'Frozen checkpoint bytes');runtime_files[str(p)]=pins[key]
        if key=='adapter_sha256':
            for name in ('summary.json','training.jsonl','sha256.txt'):
                q=p.with_name(name);runtime_files[str(q)]=ct.sha(q)
    roots={str(env):ct.tree_hash(env)}
    code_root=ct.ROOT/'src/hi-lewm'
    code_roots={str(code_root):ct.tree_hash(code_root,code_only=True)}
    obj=dict(version=ct.VERSION,source_sha256=source_sha,protocol_sha256=ct.sha(source/ct.DOC),
             runtime_tree_algorithm='regular-bytes-and-symlink-text-v2',
             records=records,runtime_files=runtime_files,runtime_roots=roots,runtime_code_roots=code_roots,
             collection_registry_sha256=expected,reference_payloads_opened=0,
             excluded_reference_payloads_opened=0,researcher_approved=False)
    ct.json_write(out,obj)
    ct.capsule(source,out,source_sha)
    print('Capsule SHA256: '+ct.sha(out)+'; no launch authorization created')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();freeze(a.source,a.out)
