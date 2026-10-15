"""Separate final45.89698539988s metadata reserve, within original14400 cap."""
import ctypes,json,os,subprocess,sys,time
from pathlib import Path
from wm_diag0_rc1_v1.common import ROOT,identity,write_new
DOC=ROOT/'docs/world-model-diagnostic-rc1-ops-reserve-v1-20261016'

def command_check(command):
    if len(command)<4 or Path(command[0]).resolve()!=Path(sys.executable).resolve() or command[1:3]!=['-B','-m'] or command[3] not in ('wm_diag0_rc1_technical_v1.operations','wm_diag0_rc1_grid_v1.operations'):
        raise ValueError('only reviewed exact-dispatch metadata/staging modules; not model execution')

def main():
    label=sys.argv[1];limit=int(sys.argv[2]);act=json.loads((DOC/'ACTIVATION.json').read_text())
    if not label.isalnum() or not 1<=limit<=30:raise ValueError('exclusive finite metadata operation')
    old=ROOT/'docs/world-model-diagnostic-rc1-v1-20261016/PREPARATION-ACTIVATION.json'
    if identity(old)!=act['previous_activation_identity']:raise ValueError('original nonrefundable funding unchanged')
    total=sum(json.loads(p.read_text())['elapsed_seconds'] for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json'))
    if total+limit>act['new_measured_seconds_ceiling']:raise ValueError('last unreserved metadata preparation exhausted; no further grant')
    begin=DOC/('LOCAL-'+label+'.started.json');out=DOC/('LOCAL-'+label+'.json')
    if begin.exists() or out.exists():raise FileExistsError('no repeated or ambiguous operation')
    command_check(sys.argv[3:])
    from wm_diag0.windows_limits import limits
    kernel,handle,usage=limits();write_new(begin,{'command':sys.argv[3:],'timeout_seconds':limit,'funding':'ACTIVATION.json'})
    env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
    began=time.monotonic();r={'returncode':125,'status':'FAILED','component':'last_unreserved_metadata_reserve'}
    try:
        p=subprocess.run(sys.argv[3:],cwd=ROOT,env=env,timeout=limit,capture_output=True,text=True,encoding='utf8',errors='replace')
        r.update(status='FINISHED',returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except Exception as exc:r['error']=repr(exc)
    finally:
        kernel.QueryInformationJobObject(handle,9,ctypes.byref(usage),ctypes.sizeof(usage),None)
        r.update(elapsed_seconds=time.monotonic()-began,peak_job_memory_bytes=usage.peak_job,affinity_mask=usage.basic.affinity)
        write_new(out,r);print(json.dumps(r,indent=2))
    return r['returncode']

if __name__=='__main__':sys.exit(main())
