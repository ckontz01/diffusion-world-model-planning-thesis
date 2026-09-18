"""Read pinned sources and evaluate only artificial StandardScaler arrays."""
import argparse,base64,hashlib,json,os,subprocess
from pathlib import Path
import lgp1_contract as c

REMOTE=r'''
import hashlib,inspect,json,pathlib
import numpy as np
import sklearn
from sklearn.preprocessing import StandardScaler
root=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis')
site=root/'envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages'
paths=[pathlib.Path(inspect.getsourcefile(StandardScaler)),
 root/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage/stable_worldmodel/wm/lewm/lewm.py',
 site/'stable_worldmodel/envs/pusht/env.py',site/'stable_worldmodel/world.py',
 site/'gymnasium/wrappers/common.py',next(site.glob('scikit_learn-*.dist-info/RECORD'))]
sources={str(p):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),text=p.read_bytes().decode()) for p in paths}
x=(np.arange(2100,dtype=np.float32).reshape(-1,2)-1037)/np.float32(37)
mean=np.array([.123456789,-.987654321],np.float64);scale=np.array([.21234567890,.3876543210],np.float64)
s=StandardScaler();s.mean_=mean;s.scale_=scale;s.n_features_in_=2
inverse=s.inverse_transform(x.copy());forward=s.transform(x.copy())
print(json.dumps(dict(sklearn_version=sklearn.__version__,numpy_version=np.__version__,sources=sources,
 methods={n:inspect.getsource(getattr(StandardScaler,n)) for n in ('transform','inverse_transform')},
 fixture=dict(x=x.tolist(),mean=mean.tolist(),scale=scale.tolist(),inverse=inverse.tolist(),forward=forward.tolist()),
 research_calls=0,simulator_calls=0,gpu_calls=0)))
'''

def main(output):
    prefix=['wsl','-d','Thesis-Ubuntu','-u','chris','--'] if os.name=='nt' else []
    command=prefix+['ssh','prometheus','apptainer','exec','--cleanenv','--bind',str(c.ROOT)+':'+str(c.ROOT)+':ro',
        str(c.ROOT/'containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'),
        'env','CUDA_VISIBLE_DEVICES=','PYTHONDONTWRITEBYTECODE=1','OPENBLAS_NUM_THREADS=1',
        str(c.ROOT/'envs/hi-lewm-artifact-py311-cu121-swm006/bin/python'),'-B','-']
    result=subprocess.run(command,input=REMOTE,text=True,capture_output=True)
    c.require(result.returncode==0,result.stderr)
    value=json.loads(result.stdout);repo=Path(__file__).resolve().parents[2]
    lock=c.read(repo/c.DOC/'INPUTS.json')
    record=None
    for name,item in value['sources'].items():
        c.require(hashlib.sha256(item['text'].encode()).hexdigest()==item['sha256'],'Fetched source bytes')
        if name in lock['files']:c.require(item['sha256']==lock['files'][name],'Existing pinned source/RECORD identity')
        if name.endswith('/RECORD'):record=item['text']
    data_path=next(n for n in value['sources'] if n.endswith('/preprocessing/_data.py'))
    line=next(line for line in record.splitlines() if line.startswith('sklearn/preprocessing/_data.py,'))
    encoded=line.split(',')[1].split('=',1)[1]
    c.require(base64.urlsafe_b64decode(encoded+'='*((-len(encoded))%4)).hex()==value['sources'][data_path]['sha256'],'Installed scaler source versus accepted package RECORD')
    value['authenticated_against_reviewed_input_lock']=c.sha(repo/c.DOC/'INPUTS.json')
    c.write(output,value)
    print(json.dumps(dict(version=value['sklearn_version'],source=data_path,sha256=value['sources'][data_path]['sha256'],synthetic_only=True)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
