"""Model-free comparison of common-runtime and released SAGE preparation."""
import argparse,ast,hashlib,json,types
from copy import deepcopy
from pathlib import Path
import numpy as np
import torch
import stable_worldmodel as swm
from torchvision import tv_tensors
from independent_pusht_runtime import SAGE


def main(out):
 import sys
 sys.path.append(str(SAGE))
 from sage.eval import pusht as p
 source=SAGE/'stable_worldmodel/policy.py'
 tree=ast.parse(source.read_text())
 base=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BasePolicy')
 method=next(n for n in base.body if isinstance(n,ast.FunctionDef) and n.name=='_prepare_info')
 namespace={'np':np,'torch':torch,'tv_tensors':tv_tensors}
 exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
 official=namespace['_prepare_info'];rng=np.random.default_rng(202609063)
 rows=[]
 for batch in (1,3,50):
  for history in (1,3):
   policy=swm.policy.BasePolicy()
   policy.process={'action':p.ArrayNormalizer(np.array([-.007,.008],np.float32),np.array([.2,.21],np.float32))}
   policy.transform={'pixels':p.image_transform(224,torch.bfloat16),'goal':p.image_transform(224,torch.bfloat16)}
   data={'pixels':rng.integers(0,256,(batch,history,64,64,3),dtype=np.uint8),
         'goal':rng.integers(0,256,(batch,history,64,64,3),dtype=np.uint8),
         'action':rng.normal(size=(batch,history,2)).astype(np.float32),
         'state':rng.normal(size=(batch,history,7)),
         '_env_id':np.arange(batch),'_plan_call':np.zeros(batch,np.int64)}
   a=policy._prepare_info(deepcopy(data));b=official(policy,deepcopy(data))
   assert a.keys()==b.keys()
   for k in a:
    assert torch.is_tensor(a[k]) and torch.is_tensor(b[k])
    assert a[k].dtype==b[k].dtype and a[k].shape==b[k].shape and torch.equal(a[k],b[k]),k
   rows.append({'batch':batch,'history':history,'all_prepared_fields_bit_identical':True})
 result={'all_passed':True,'rows':rows,'model_calls':0,'final_data_read':False,
          'official_policy_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'scope':'synthetic raw inputs, actual released transforms/normalizer; common vs vendor BasePolicy preparation only',
          'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 path=Path(out)
 with path.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();main(a.out)
