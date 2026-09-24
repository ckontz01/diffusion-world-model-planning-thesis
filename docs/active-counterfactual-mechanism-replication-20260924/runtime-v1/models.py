"""Explicit seed wrapper around the accepted trainer; metadata-only freeze."""
import common as c
from pathlib import Path
import shutil
import time
PAIRS=((94011,94012),(94411,94412),(94421,94422))

def reuse(auth):
    root=auth.run/'reused'; root.mkdir(exist_ok=False)
    spec=c.read(c.ROOT/'MODEL-REUSE.json')
    for name,i in spec['files'].items():
        src=Path(i['path']); c.require(src.stat().st_size==i['bytes'] and c.sha(src)==i['sha256'],'Reused input '+name)
        with src.open('rb') as r,(root/name).open('xb') as w: shutil.copyfileobj(r,w)
        c.require(c.sha(root/name)==i['sha256'],'Reused copy '+name)
    c.seal(root,{'reuse_only':True,'binding':c.sha(c.ROOT/'MODEL-REUSE.json')})

def fit_explicit(spec,fit,validation,pre,out,role_map):
    import numpy as np
    from model import JointModel,OrdinaryModel
    from fitting import train192
    c.require(spec['pair'] in (1,2) and spec['seed']==PAIRS[spec['pair']][spec['kind']=='ordinary'],'Declared initialization seed')
    c.require(spec['updates']==192,'Fixed192')
    cls=JointModel if spec['kind']=='joint' else OrdinaryModel
    model=cls(996,212,192,seed=spec['seed'],preprocessing=pre)
    progress=[]
    try: result=train192(model,fit,validation,role_map,progress)
    except BaseException:
        with (out/'PARTIAL-WEIGHTS.npz').open('xb') as f: np.savez(f,**{f'p{i}':v for i,v in enumerate(model.params)})
        c.write(out/'PARTIAL-FIT.json',dict(seed=spec['seed'],trace=progress,accepted=False,resume=False)); raise
    if spec['kind']=='joint': model.save(out/'joint.npz')
    else:
        meta={'kind':'ACV0-ordinary','preprocessing':'joint.npz','dims':model.net.dims,'seed':spec['seed']}
        with (out/'ordinary.npz').open('xb') as f: np.savez(f,metadata=np.array(c.json.dumps(meta)),**{f'p{i}':v for i,v in enumerate(model.params)})
    c.write(out/'FIT.json',result)
    c.write(out/'PREPROCESSING.json',pre_record(model.pre))
    return result

def pre_record(pre):
    from bridge import array_hash
    return dict(fit_ids=list(pre.fit_ids),statistics_sha256={k:array_hash(getattr(pre,k)) for k in ('xmean','xstd','amean','astd','rmean','rstd')})

def fitting(auth,spec,out):
    import numpy as np
    from model import JointModel
    c.verify_seal(auth.run/'reused')
    joint=JointModel.load(auth.run/'reused/joint.npz')
    data={}
    for role in ('fit','validation'):
        with np.load(auth.run/'reused'/(role+'-dataset.npz'),allow_pickle=False) as z: data[role]={k:z[k] for k in z.files}
    result=fit_explicit(spec,data['fit'],data['validation'],joint.pre,out,c.roles())
    original=c.read(auth.run/'reused/PREPROCESSING.json')
    c.require(c.read(out/'PREPROCESSING.json')=={k:original[k] for k in ('fit_ids','statistics_sha256')},'Identical fit-only preprocessing')
    return result

def freeze(run,package):
    run=Path(run); c.verify_seal(run/'reused')
    for name,info in c.read(c.ROOT/'MODEL-REUSE.json')['files'].items():
        p=run/'reused'/name
        c.require(p.stat().st_size==info['bytes'] and c.sha(p)==info['sha256'],'Original saved input/checkpoint binding')
    for kind,seed in zip(('JOINT','ORDINARY'),PAIRS[0]):
        original=c.read(run/'reused'/('ORIGINAL-'+kind+'-FIT.json'))
        c.require(original['seed']==seed and original['updates']==192,'Original final192 checkpoint association; no refit')
    models={}
    for pair,seeds in enumerate(PAIRS):
        for kind,seed in zip(('joint','ordinary'),seeds):
            root=run/('reused' if pair==0 else f'fit-pair{pair}-{kind}')
            c.verify_seal(root)
            if pair:
                fit=c.read(root/'FIT.json'); c.require(fit['seed']==seed and fit['updates']==192 and len(fit['trace'])==192,'Final192 seed association')
                c.require(c.read(root/'PREPROCESSING.json')['statistics_sha256']==c.read(run/'reused/PREPROCESSING.json')['statistics_sha256'],'Same preprocessing')
            p=root/(kind+'.npz')
            models[f'{pair}-{kind}']=dict(path=p.relative_to(run).as_posix(),seed=seed,sha256=c.sha(p),bytes=p.stat().st_size,
                                         seal=c.sha(root/'SEAL.json'),reused=pair==0)
    c.write(run/'ALL-MODELS-FROZEN.json',dict(package=package,unix=time.time(),models=models,
            preprocessing=c.sha(run/'reused/PREPROCESSING.json'),selection=False))

def check_freeze(run,package):
    run=Path(run); f=c.read(run/'ALL-MODELS-FROZEN.json')
    c.require(f['package']==package and f['selection'] is False and len(f['models'])==6,'Six model freeze')
    c.require(c.sha(run/'reused/PREPROCESSING.json')==f['preprocessing'],'Frozen preprocessing')
    bindings=c.read(c.ROOT/'MODEL-REUSE.json')['files']
    for pair,seeds in enumerate(PAIRS):
        for kind,seed in zip(('joint','ordinary'),seeds):
            i=f['models'][f'{pair}-{kind}']; p=run/i['path']
            c.require(i['seed']==seed and i['reused']==(pair==0) and c.sha(p)==i['sha256'] and c.sha(p.parent/'SEAL.json')==i['seal'],'Frozen model bytes/seed')
            if pair==0:c.require(i['sha256']==bindings[kind+'.npz']['sha256'],'Original checkpoint, never a refitted substitute')
    return f

def load_pair(auth,pair):
    from model import JointModel,OrdinaryModel
    f=check_freeze(auth.run,auth.approval['package_sha256'])
    j=JointModel.load(auth.run/f['models'][f'{pair}-joint']['path'])
    o=OrdinaryModel.load(auth.run/f['models'][f'{pair}-ordinary']['path'],j)
    c.require((j.seed,o.seed)==PAIRS[pair],'Loaded seed metadata')
    return j,o
