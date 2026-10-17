"""Diagnosed local missing-import repair; failed V1/source/charge retained."""
import ast,inspect,json,tempfile,time
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from . import binding as failed
from .parallel_binding import parallel_authenticate
from wm_diag0_rc1_final_v2.inventory_v3 import plan
from wm_diag0_rc1_final_v2.root_binding_v1 import authenticate,compare

def main():
    receipt=ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/LOCAL-FINALWHOLEBIND001.json'
    z=json.loads(receipt.read_text())
    if z['status']!='CHILD_NONZERO' or "NameError: name 'Path' is not defined" not in z['stdout'] or (DOC/'BINDING001.started.json').exists():raise ValueError('exact saved local-only failure phase')
    text=Path(failed.__file__).read_text()
    changes=[('import ast,hashlib,inspect,json,sys','import ast,hashlib,inspect,json,sys\nfrom pathlib import Path'),
      ('from .common import ROOT,DOC,identity,write_new','from .common import ROOT,DOC,identity,write_new\nfrom .parallel_binding import parallel_authenticate'),
      ('deadline=time.monotonic()+140','deadline=time.monotonic()+90'),
      ('proof=authenticate(planned,paths,auth,deadline)',"proof,all_observed,metadata_commitment=parallel_authenticate(planned,paths,auth,deadline)\nobserved.update(all_observed)"),
      ("'precompute_roots':proof,'storage':storage","'precompute_roots':proof,'metadata_tokens_commitment':metadata_commitment,'storage':storage"),
      ('import os,stat,sys,json,time,hashlib,resource,subprocess\\nfrom pathlib import Path,PurePosixPath\\n','import os,stat,sys,json,time,hashlib,resource,subprocess\\nfrom concurrent.futures import ThreadPoolExecutor\\nfrom pathlib import Path,PurePosixPath\\n'),
      ('roots.accumulator,roots.add,roots.finish,roots.authenticate,recovery.closed_indices,','roots.accumulator,roots.add,roots.finish,roots.authenticate,parallel_authenticate,recovery.closed_indices,'),
      ("call('BINDING001',program(),args,seconds=165)","call('BINDING002',program(),args,seconds=108)")]
    for old,new in changes:
        if text.count(old)!=1:raise ValueError('exact smallest repair/parallel algorithm preimage '+old[:60])
        text=text.replace(old,new)
    target=Path(__file__).with_name('binding_v2.py');ast.parse(text,feature_version=(3,6))
    with target.open('xb') as f:f.write(text.encode())
    # The predecessor measured124.781s for serial partial-runtime binding. The
    # NEW four-reader implementation is independently checked against the exact
    # serial root commitment, with stable stat tokens and no hash/copy omission.
    with tempfile.TemporaryDirectory(prefix='wm-new-parallel-root-') as tmp:
        root=Path(tmp);(root/'old').mkdir()
        for i in range(16):(root/'old'/('failure-'+str(i))).write_bytes(bytes([i])*1031)
        p=plan(root,['old'],{},{});paths={'study/old':str(root/'old')};end=time.monotonic()+10
        a=authenticate(p,paths,'a'*64,end);b,seen,meta=parallel_authenticate(p,paths,'a'*64,end);compare(a,b)
        if len(seen)!=16 or not meta['bytes']:raise AssertionError('every logical file bound')
    from . import binding_v2 as fixed
    if fixed.Path is not Path:raise AssertionError('actual main import fixed')
    ast.parse(fixed.program(),feature_version=(3,6))
    write_new(DOC/'BINDING-REPAIR-001.json',{'status':'LOCAL_NAMEERROR_DIAGNOSED_NEW_V2_PARALLEL_BINDING_FIXTURE_PASSED',
        'failed_source':identity(failed.__file__),'failed_LOCAL':identity(receipt),'new_source':identity(target),'parallel_source':identity(ROOT/'wm_diag0_rc1_close_v1/parallel_binding.py'),
        'no_WSL_or_cluster_query_by_failed_operation':True,'old_failed_charge_seconds_retained':180,
        'prospective_remaining_binding_seconds':{'new_full_binding_with_four_readers':120,'later_exact_stage_and_dispatch':45},
        'same_component_remaining_seconds':165,'no_component_transfer_refund_or_regrant':True,
        'full_binding_deadline_is_a_hard_stop_not_performance_guarantee':True,'scientific_payloads_read':False})
    print(json.dumps({'status':'NEW_V2_LOCAL_AND_PARALLEL_FIXTURES_PASSED','old_failure_preserved':True}))

if __name__=='__main__':main()
