"""Reconcile a pre-existing Git/SSD line-ending difference without editing history."""
import common as c
import hashlib
import subprocess
import sys


def main():
    manifest=c.read(c.ROOT/'SOURCE-MANIFEST.json')
    for name,h in manifest['files'].items():c.require(c.sha(c.REPO/name)==h,'Frozen source changed: '+name)
    approval=c.read(c.ROOT/'APPROVAL-TEMPLATE.json')
    c.require(approval['authorized'] is False and approval['package_sha256']==c.sha(c.ROOT/'SOURCE-MANIFEST.json'),'Disabled package identity')
    for script in ('dispatch.py','worker.py','supervise.py','preserve.py'):
        args=[sys.executable,str(c.ROOT/script)]
        if script=='preserve.py':args+=['archive']
        args+=['--approval',str(c.ROOT/'APPROVAL-TEMPLATE.json'),'--run',approval['run']]
        if script in ('worker.py','supervise.py'):args+=['--task','collect-fit-490']
        result=subprocess.run(args,capture_output=True,text=True,timeout=20)
        c.require(result.returncode!=0 and 'Research execution disabled' in result.stderr,'CLI refusal: '+script)
    base='1c66038901fe39640add38aa796a816c06ccd1ae'
    receipt=c.read(c.BASE/'DELIVERY.json')
    before_receipt=subprocess.check_output(['git','show',base+':'+(c.BASE/'DELIVERY.json').relative_to(c.REPO).as_posix()],cwd=c.REPO)
    c.require(hashlib.sha256(before_receipt).hexdigest()==c.sha(c.BASE/'DELIVERY.json'),'Accepted backup receipt unchanged')
    saved={v['path'].replace('\\','/'):v for v in receipt['members']}
    for name,value in saved.items():
        p=c.BASE/name
        c.require(c.sha(p)==value['sha256'] and p.stat().st_size==value['bytes'],'Original accepted local/SSD identity: '+name)
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',base,'docs/active-counterfactual-verification-20260923'],cwd=c.REPO,text=True).splitlines()
    differences=[]
    for name in names:
        before=subprocess.check_output(['git','show',base+':'+name],cwd=c.REPO)
        current=(c.REPO/name).read_bytes()
        if before!=current:
            relative=(c.REPO/name).relative_to(c.BASE).as_posix()
            c.require(relative=='prototype-reproduction/TABLE.md','Unexpected historical mismatch: '+name)
            c.require(current.replace(b'\r\n',b'\n')==before,'Not only CRLF/LF')
            c.require(hashlib.sha256(current).hexdigest()==saved[relative]['sha256'],'Must match pre-existing accepted SSD receipt')
            differences.append({'path':relative,'git_sha256':hashlib.sha256(before).hexdigest(),
                                'preserved_local_and_prior_ssd_sha256':saved[relative]['sha256'],
                                'kind':'Pre-existing CRLF checkout / LF Git blob; no byte was changed'})
    c.require(len(differences)==1,'Exact reconciled historical difference')
    audit={'status':'PASSED_WITH_DOCUMENTED_PREEXISTING_EOL_DIFFERENCE','source_members':len(manifest['files']),
           'source_closure_unchanged':True,'all4_cli_interlocks_refused':True,'approval_authorized':False,
           'accepted_local_files_matching_prior_ssd_receipt':len(saved),'accepted_receipt_git_bytes_match':True,
           'accepted_git_files_checked':len(names),'git_byte_matches':len(names)-len(differences),
           'differences':differences,'research_payload_reads':0,'gpu_allocations':0,'complete_grid':len(c.grid()),
           'package_sha256':approval['package_sha256'],'audit_script_sha256':c.sha(__file__),
           'prior_failed_audit_retained_in':'ATTEMPTS.jsonl',
           'syntax_checks':'Python/PowerShell/Bash passed in audit-frozen-v1 before its historical TABLE.md assertion'}
    c.write(c.ROOT/'PACKAGE-AUDIT.json',audit);print(c.json.dumps(audit,indent=2))


if __name__=='__main__':main()
