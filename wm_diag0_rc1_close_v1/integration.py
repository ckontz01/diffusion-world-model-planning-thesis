"""New actual Linux integration: pure controller import, owned children, archive."""
import ast,base64,json
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .transport_v2 import call

def source_members():
    result={}
    for package in ('wm_diag0_rc1_close_v1','wm_diag0_rc1_final_v1','wm_diag0_rc1_final_v2'):
        for p in (ROOT/package).glob('*.py'):result[p.relative_to(ROOT).as_posix()]=p.read_bytes()
    for name in ('__init__.py','common.py'):
        p=ROOT/'wm_diag0_rc1_completion_v1'/name;result[p.relative_to(ROOT).as_posix()]=p.read_bytes()
    if sum(map(len,result.values()))>2000000:raise ValueError('bounded new final source snapshot')
    return result

CODE=r'''
import base64,hashlib,json,os,resource,sys,time
from pathlib import Path
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]));resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592));resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_FSIZE,(1000000,1000000))
data=json.load(sys.stdin);ops=Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015-rc1-preservation-v2')
source=ops/'review-source-001'
source.mkdir(parents=True,exist_ok=False)
for name,encoded in data['members'].items():
 p=source/name;p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(encoded)
 if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=data['identities'][name]:raise ValueError('reviewed source frame')
 with p.open('xb') as f:f.write(raw)
 p.chmod(0o444)
for p in sorted(source.rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
source.chmod(0o555)
sys.path[:0]=[str(source),'/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/campaign-v4-rc1-grid-recovery-r1/source']
from wm_diag0_rc1_close_v1 import driver,workflow,archive_operation as archive,analysis_closure as closure
from wm_diag0_rc1_close_v1.parallel_binding import parallel_authenticate
from wm_diag0_rc1_final_v2.inventory_v3 import plan
from wm_diag0_rc1_final_v2.archive_v2 import canonical
from wm_diag0_rc1_final_v2.archive_verify_v2 import verify,strict_json
from wm_diag0_rc1_final_v1.cpu_process_v2 import run_child
from wm_diag0_rc1_final_v2.evidence_auth_v1 import USAGE
if 'numpy' in sys.modules:raise AssertionError('native controller unexpectedly imported scientific NumPy runtime')
root=ops/'tests/final-runtime-001';root.mkdir(parents=True,exist_ok=False)
study=root/'study';old=study/'old';old.mkdir(parents=True);(old/'STOP.json').write_bytes(b'old retained STOP')
runtime=root/'runtime';runtime.mkdir();(runtime/'opaque').write_bytes(b'NOT JSON\x00opaque runtime')
def ident(p):
 raw=Path(p).read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def write(p,value):
 with p.open('xb') as f:f.write(canonical(value))
priorpaths={'study/old':str(old),'runtime':str(runtime)}
prior,_,_=parallel_authenticate(plan(study,['old'],{'runtime':runtime},{}),priorpaths,'f'*64,time.monotonic()+20)
final=study/'campaign-v4-rc1-final-v2';task=final/'tasks/analysis-0'
for n in ('controls','logs','output','tmp'):(task/n).mkdir(parents=True,exist_ok=False)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');children=[]
for role in ('analysis','independent_acceptance'):
 end=time.monotonic()+8
 children.append(run_child(['python3','-B','-c',"print('NEW TINY OWNED FIXTURE; NOT SCIENTIFIC ANALYSIS')"],env,task/'logs'/(role+'.log'),[],40000000,100000,end,end+5))
# Deliberately NONJSON opaque output; test controls are explicitly synthetic.
(task/'output/RESULTS.json').write_bytes(b'NOT SCIENTIFIC JSON\x00opaque fixture')
(task/'output/ACCEPTANCE.json').write_bytes(b'opaque acceptance fixture')
write(task/'output/MEMBERS.json',{n:ident(task/'output'/n) for n in ('RESULTS.json','ACCEPTANCE.json')});seal=ident(task/'output/MEMBERS.json')
contract={'bytes':1,'sha256':'b'*64};validator=ident(source/'wm_diag0_rc1_close_v1/analysis_validate.py')
c={'gpu_stages_authorized':False,'rc1_final':{'analysis_authorized':True,'historical_usage_receipt':{'identity':USAGE}},'staged_members':{closure.VALIDATOR:validator}}
accepted={'accepted':True,'phase':'analysis','output_seal':seal,'source_roots':120,'retained_fits':6,'active_heads':4,'diagnostic_parents':128,'scientific_values_emitted_to_controls':False}
proof=dict(closure.COUNTS,status='COMPLETE_ANALYSIS_INDEPENDENTLY_RECONSTRUCTED_PENDING_ARCHIVE_AND_FINAL_SSD',contract_sha256=contract['sha256'],analysis_output_seal=seal,validator_source=validator,
 historical_evidence_reauthentication={'status':'ALL59_HISTORICAL_ORIGINAL_EVIDENCE_IDENTITIES_REAUTHENTICATED','authenticated_files':59,'opaque_bytes_hashed':2826430,'receipt':USAGE},
 scientific_values_emitted=False,research_model_simulator_fit_source_generation_calls=0,parent_publication_authorized=False,final_gate_ready=False)
write(task/'controls/ACCEPTED.json',accepted);write(task/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json',proof)
closed=closure.close_after_owned_children(c,contract,task,ident(task/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json'),time.monotonic()+10)
write(root/'ANALYSIS-CLOSED.json',closed);closed_id=ident(root/'ANALYSIS-CLOSED.json')
end=time.monotonic()+8
children.append(run_child(['python3','-B','-c',"print('NEW TINY OWNED ARCHIVE ROLE FIXTURE')"],env,root/'archive-role.log',[],40000000,100000,end,end+5))
paths=dict(priorpaths,**{'study/campaign-v4-rc1-final-v2':str(final)})
def fresh():return plan(study,['old',final.name],{'runtime':runtime},{})
binding={'root_paths':paths,'final_contract_sha256':contract['sha256']}
args=(c,contract,task,closed,fresh(),binding,'f'*64,prior,root/'once.tar',root/'portable.json',root/'READBACK.json',fresh,2954852312)
result=archive.preserve_closed_inventory(*args,deadline=time.monotonic()+25)
portable=strict_json((root/'portable.json').read_bytes())
checked=verify(root/'once.tar',portable,binding,time.monotonic()+15,check_sources=False,expected_whole=result['whole'],expected_manifest=result['manifest'])
if checked['logical_members']!=len(fresh()['members']) or ident(root/'ANALYSIS-CLOSED.json')!=closed_id:raise AssertionError('complete dynamic closure/archive/readback')
try:archive.preserve_closed_inventory(*args,deadline=time.monotonic()+5)
except FileExistsError:pass
else:raise AssertionError('once-only archive refusal absent')
bad=dict(proof,allocation_attempts=138)
try:closure.check_proof(c,contract,accepted,bad)
except ValueError:pass
else:raise AssertionError('obsolete138 proof accepted')
try:driver.allocation_gate(c,{'job_id':'synthetic-not-allocation'},time.monotonic()+5)
except PermissionError:pass
else:raise AssertionError('unallocated native process promoted to CPU authority')
z={'status':'ACTUAL_LINUX_NEW_RECOVERY_FINAL_IMPORT_OWNED_CHILDREN_CLOSED139_ONCE_ARCHIVE_ORIGINAL_READBACK_PASSED',
 'source_identities':data['identities'],'fixture_root':str(root),'source_root':str(source),'real_harmless_owned_children':len(children),
 'tiny_archive':ident(root/'once.tar'),'scientific_payloads_read':False,'actual_research_analysis_or_allocation':False,
 'production_full_dispatch_gate_substituted':False,'actual_allocation_gate_refused_unallocated_process':True,
 'no_Numpy_in_native_controller':True,'fixture_controls_are_synthetic_not_actual_acceptance':True,
 'scheduler_calls':0,'new_GPU_CPU_research_allocations':0,'final_gate_ready':False}
write(root/'RESULT.json',z);print(json.dumps(z,separators=(',',':')))
'''

def main():
    members=source_members();ids={n:{'bytes':len(b),'sha256':__import__('hashlib').sha256(b).hexdigest()} for n,b in members.items()}
    ast.parse(CODE,feature_version=(3,6))
    result=call('LINUX-FINAL001'.replace('-',''),CODE,{'members':{n:base64.b64encode(b).decode() for n,b in members.items()},'identities':ids},seconds=150)
    print(json.dumps({'status':result['status'],'actual_analysis':False,'new_research_allocations':0}))
if __name__=='__main__':main()
