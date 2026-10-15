"""One finite preparation envelope; never activate another on retry."""
import ctypes,json,os,subprocess,sys,time
from .common import ROOT,DOC,write_new

def main():
    label,component,seconds=sys.argv[1],sys.argv[2],int(sys.argv[3])
    if not label.isalnum() or not 1<=seconds<=180:raise ValueError('exclusive finite operation')
    a=json.loads((DOC/'PREPARATION-ACTIVATION.json').read_text())
    caps=a['component_ceiling_seconds'];rows=[json.loads(p.read_text()) for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    if component not in caps:raise ValueError('bounded component')
    if sum(r['elapsed_seconds'] for r in rows)+seconds>750:raise ValueError('total preparation exhausted')
    if sum(r['elapsed_seconds'] for r in rows if r['component']==component)+seconds>caps[component]:raise ValueError('component exhausted; no silent reserve transfer')
    old=ROOT/'docs/world-model-diagnostic-a2-native-v3-20261015'
    measured=sum(json.loads(p.read_text())['elapsed_seconds'] for p in old.glob('LOCAL-*.json') if not p.name.endswith('.started.json'))
    if abs(measured-a['old_continuation_measured_seconds_at_activation'])>1e-6:raise ValueError('old runner used after activation; reconcile funding')
    pth=DOC/('LOCAL-'+label+'.json');start=DOC/('LOCAL-'+label+'.started.json')
    if start.exists() or pth.exists():raise FileExistsError('no repeated/ambiguous operation')
    from wm_diag0.windows_limits import limits
    kernel,handle,usage=limits()
    write_new(start,{'command':sys.argv[4:],'timeout_seconds':seconds,'component':component})
    env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
    began=time.monotonic();r={'returncode':125,'component':component,'status':'FAILED'}
    try:
        p=subprocess.run(sys.argv[4:],cwd=ROOT,env=env,timeout=seconds,capture_output=True,text=True,encoding='utf8',errors='replace')
        r.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,status='FINISHED')
    except Exception as exc:r['error']=repr(exc)
    finally:
        kernel.QueryInformationJobObject(handle,9,ctypes.byref(usage),ctypes.sizeof(usage),None)
        r.update(elapsed_seconds=time.monotonic()-began,peak_job_memory_bytes=usage.peak_job,affinity_mask=usage.basic.affinity)
        write_new(pth,r);print(json.dumps(r,indent=2))
    return r['returncode']

if __name__=='__main__':sys.exit(main())
