"""Mechanical provenance-preserving adapters; never edit the executed closure."""
import r1 as r
import difflib

def generate(name,out,changes):
    original=(r.science_root/name).read_text(encoding='utf8')
    text=original
    for before,after in changes:
        r.require(text.count(before)==1,'Unique reviewed adaptation: '+before)
        text=text.replace(before,after)
    with (r.ROOT/out).open('xb') as f:f.write(text.encode())
    return ''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='runtime-v2/'+name,tofile='control-r1/'+out))

if __name__=='__main__':
    patch=generate('worker.py','worker_r1.py',[
        ('import common as c','import r1 as r\nimport common as c'),
        ("auth=c.Authorization(a.approval,a.run);spec=next(j for j in c.grid() if j['key']==a.task)","ctx=r.Context(os.environ['ACVM_R1_APPROVAL']);c.require(a.approval==str(ctx.worker_approval) and a.run==str(ctx.run),'Recovery worker invocation');auth=ctx.auth;spec=next(j for j in c.grid() if j['key']==a.task)"),
        ("claim=auth.run/'submissions'/(spec['key']+'.json')","claim=auth.run/'submissions-r1'/(spec['key']+'.json')"),
        ("job=os.environ['SLURM_JOB_ID'],hard_seconds=spec['seconds']","recovery_approval=ctx.approval_sha,job=os.environ['SLURM_JOB_ID'],hard_seconds=spec['seconds']")])
    patch+=generate('dispatch.py','campaign_r1.py',[
        ('import common as c','import r1 as r\nimport common as c'),
        ("c.write(auth.run/'submissions'/(spec['key']+'.json')","c.write(auth.run/'submissions-r1'/(spec['key']+'.json')"),
        ("if __name__=='__main__':main()","if __name__=='__main__':raise SystemExit('Use controller.py with separate recovery authority')")])
    patch+=generate('acceptance.py','acceptance_r1.py',[
        ('import common as c','import r1 as r\nimport common as c'),
        ("log=run/'logs'/(spec['key']+suffix)","log=r.slurm_log(run,spec['key'],suffix)"),
        ("'reused','submissions','logs'","'reused','submissions','submissions-r1','logs'")])
    patch+=generate('preserve.py','preserve_r1.py',[
        ('import common as c','import r1 as r\nimport common as c'),
        ("roots=dict(source=c.REPO,control=control,run=auth.run)","ctx=r.Context(control/'EXECUTION-APPROVAL.json');r.baseline(ctx);roots=dict(science_source=c.REPO,recovery_source=r.ROOT,original_control=ctx.old_control,recovery_control=control,run=auth.run)"),
        ("if __name__=='__main__':main()","if __name__=='__main__':raise SystemExit('Use preserve_entry.py with separate recovery authority')")])
    with (r.ROOT/'SOURCE-DIFF.patch').open('xb') as f:f.write(patch.encode())
    print('Four mechanical adapters created; historical sources unchanged')
