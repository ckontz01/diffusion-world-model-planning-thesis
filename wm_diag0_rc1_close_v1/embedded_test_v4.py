"""Exercise embedded runtime functions, not only AST, before real binding V4."""
import ast,json,tempfile,time
from pathlib import Path
from .common import DOC,ROOT,identity,write_new
from . import binding_v3

def main():
    old=Path(binding_v3.__file__);text=old.read_text()
    edits=[('import os,stat,sys,json,time,hashlib,resource,subprocess\\n','import os,stat,sys,json,time,hashlib,resource,subprocess,math\\n'),
       ("call('BINDING003',program(),args,seconds=295)","call('BINDING004',program(),args,seconds=295)")]
    for a,b in edits:
        if text.count(a)!=1:raise ValueError('exact embedded missing-math repair')
        text=text.replace(a,b)
    target=old.with_name('binding_v4.py');ast.parse(text,feature_version=(3,6))
    with target.open('xb') as f:f.write(text.encode())
    from . import binding_v4 as fixed
    code=fixed.program();prefix=code.split('os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))')[0]
    scope={};exec(compile(prefix,'<actual-reviewed-embedded-prefix>','exec'),scope)
    c=json.loads((ROOT/'docs/world-model-diagnostic-rc1-recovery-r1-20261016/GRID-CONTRACT.json').read_text())
    oldids={str(i):str(400000+i) for i in range(67)};oldids['66']='317411';newids={str(i):str(500000+i) for i in range(66,124)}
    wants=scope['expected_starts'](c,oldids,newids)
    lines=[]
    for k,(raw,state,exitcode,n) in scope['OLD_ALLOCATED'].items():lines.append('|'.join([k,raw,state,exitcode,str(n),'4','gpu09']))
    for logical,want in wants.items():
        record={k:v for k,v in want.items() if k!='path'};record.update(PID=123,start_ticks='456',node='gpu09',time=1.0)
        scope['check_started'](record,want)
        lines.append('|'.join([logical,want['job_id'],'FAILED' if logical=='317180_66' else 'COMPLETED','125:0' if logical=='317180_66' else '0:0','79' if logical=='317180_66' else '1','4','gpu09']))
    for logical in scope['OLD_UNALLOCATED']|{'317180_[67-123%1]'}:lines.append('|'.join([logical,'399999','CANCELLED by 1201','0:0','0','4','None assigned']))
    answer=scope['terminal_ledger'](c,'\n'.join(lines),oldids,newids)
    if answer['allocated_attempts']!=139:raise AssertionError('embedded exact full ledger')
    with tempfile.TemporaryDirectory(prefix='wm-embedded-final-') as tmp:
        root=Path(tmp);(root/'old').mkdir();(root/'old/failure').write_bytes(b'NOT JSON\x00opaque')
        p=scope['plan'](root,['old'],{},{});paths={'study/old':str(root/'old')}
        a=scope['authenticate'](p,paths,'a'*64,time.monotonic()+5)
        b,observed,tokens=scope['parallel_authenticate'](p,paths,'a'*64,time.monotonic()+5)
        if a!=b or len(observed)!=1:raise AssertionError('actual embedded parallel and serial binding')
    write_new(DOC/'EMBEDDED-TEST-004.json',{'status':'ACTUAL_EMBEDDED_FUNCTION_NAMESPACE_139_LEDGER_128_STARTS_OPAQUE_ROOTS_PASSED',
        'source':identity(target),'test_source':identity(__file__),'old_failed_source':identity(old),
        'scientific_payload_reads':False,'WSL_SSH_scheduler_calls':0})
    print(json.dumps({'status':'EMBEDDED_RUNTIME_TEST_PASSED','research_calls':0}))
if __name__=='__main__':main()
