"""One exclusive CPU artificial reference test using the existing runtime."""
import base64,json
from .common import ROOT,DOC,RUN,OLD_RUN,identity,write_new
from wm_diag0_native_v3.transport import ssh

PROGRAM=r'''
import base64,hashlib,json,os,pathlib,resource,subprocess,sys
data=json.load(sys.stdin);r=pathlib.Path(TEST_ROOT);r.mkdir(exist_ok=False)
for n,b in data['files'].items():
 p=r/n;p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(b)
 if hashlib.sha256(raw).hexdigest()!=data['identities'][n]['sha256']:raise ValueError('artificial source identity')
 with p.open('xb') as f:f.write(raw)
 p.chmod(0o444)
env={k:v for k,v in os.environ.items() if not k.startswith(('APPTAINERENV_','SINGULARITYENV_'))}
for k,v in {'PYTHONPATH':str(r)+':'+OLD_SOURCE+':'+DINO_SOURCE,'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','CUDA_VISIBLE_DEVICES':'',
 'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4','HOME':'/tmp','XFORMERS_DISABLED':'1'}.items():env['APPTAINERENV_'+k]=v
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
cmd=['apptainer','exec','--containall','--cleanenv','--no-home','--bind',str(r)+':'+str(r)+':ro','--bind',OLD_SOURCE+':'+OLD_SOURCE+':ro',
 '--bind',DINO_SOURCE+':'+DINO_SOURCE+':ro','--bind',VENV+':'+VENV+':ro',SIF,VENV+'/bin/python','-B','-m','wm_diag0_rc1_v1.tests','reference']
p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=60)
if len(p.stdout)+len(p.stderr)>100000:raise ValueError('bounded artificial stdout')
print(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'research_checkpoints_or_data_loaded':False,'new_allocation':False,'source':data['identities']}))
'''

def main():
    if (DOC/'ARTIFICIAL-REFERENCE-001.json').exists() or (DOC/'ARTIFICIAL-REFERENCE-001.started.json').exists():raise FileExistsError('exclusive artificial attempt')
    c=json.loads((ROOT/'docs/world-model-diagnostic-a2-campaign-v4-20261015/campaign/CONTRACT.json').read_text())
    names=('__init__.py','common.py','pointwise.py','models.py','reference.py','tests.py')
    files={'wm_diag0_rc1_v1/'+n:(ROOT/'wm_diag0_rc1_v1'/n).read_bytes() for n in names}
    payload={'files':{n:base64.b64encode(b).decode() for n,b in files.items()},
      'identities':{n:{'bytes':len(b),'sha256':__import__('hashlib').sha256(b).hexdigest()} for n,b in files.items()}}
    values={'TEST_ROOT':RUN+'-artificial-ONE','OLD_SOURCE':OLD_RUN+'/source','DINO_SOURCE':c['dino_source'],'VENV':c['venv'],'SIF':c['sif']}
    write_new(DOC/'ARTIFICIAL-REFERENCE-001.started.json',{'source':payload['identities'],'research_calls':0})
    z=ssh('\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+PROGRAM,json.dumps(payload).encode())
    write_new(DOC/'ARTIFICIAL-REFERENCE-001.json',z);print(json.dumps(z,indent=2))
    if z['returncode']:raise RuntimeError('artificial test failed; preserve no blind retry')

if __name__=='__main__':main()
