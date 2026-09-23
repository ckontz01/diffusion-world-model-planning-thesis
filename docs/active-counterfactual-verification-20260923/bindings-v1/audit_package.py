"""Read-only completed-package audit; no research input or scheduler access."""
import common as c
import ast
import subprocess
import sys


def main():
    for p in c.ROOT.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    syntax = "$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile('"+str(c.ROOT/'backup_package.ps1')+"',[ref]$t,[ref]$e)|Out-Null;if($e.Count){throw ($e|Out-String)}"
    subprocess.run(['powershell.exe','-NoProfile','-Command',syntax],check=True,capture_output=True,timeout=30)
    subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','bash','-n'],
                   input=(c.ROOT/'run_worker.sh').read_bytes(),check=True,capture_output=True,timeout=30)
    manifest=c.read(c.ROOT/'SOURCE-MANIFEST.json')
    for name,h in manifest['files'].items():c.require(c.sha(c.REPO/name)==h,'Source closure: '+name)
    a=c.read(c.ROOT/'APPROVAL-TEMPLATE.json');c.require(a['authorized'] is False,'Disabled template')
    c.require(a['package_sha256']==c.sha(c.ROOT/'SOURCE-MANIFEST.json'),'Frozen package SHA')
    for script in ('dispatch.py','worker.py','supervise.py','preserve.py'):
        args=[sys.executable,str(c.ROOT/script)]
        if script=='preserve.py':args+=['archive']
        args+=['--approval',str(c.ROOT/'APPROVAL-TEMPLATE.json'),'--run',a['run']]
        if script in ('worker.py','supervise.py'):args+=['--task','collect-fit-490']
        run=subprocess.run(args,capture_output=True,text=True,timeout=20)
        c.require(run.returncode!=0 and 'Research execution disabled' in run.stderr, 'Real CLI must refuse before data/scheduler: '+script)
    # The exact accepted files must remain unchanged, including results/receipts.
    names=subprocess.check_output(['git','ls-tree','-r','--name-only','1c66038901fe39640add38aa796a816c06ccd1ae','docs/active-counterfactual-verification-20260923'],cwd=c.REPO,text=True).splitlines()
    for name in names:
        before=subprocess.check_output(['git','show','1c66038901fe39640add38aa796a816c06ccd1ae:'+name],cwd=c.REPO)
        c.require(__import__('hashlib').sha256(before).hexdigest()==c.sha(c.REPO/name),'Accepted artifact changed: '+name)
    result={'status':'PASSED','source_members':len(manifest['files']),'accepted_files_unchanged':len(names),
            'python_powershell_bash_syntax_passed':True,
            'all4_cli_interlocks_refused':True,'approval_authorized':False,'research_payload_reads':0,'gpu_allocations':0,
            'package_sha256':a['package_sha256'],'complete_grid':len(c.grid())}
    c.write(c.ROOT/'PACKAGE-AUDIT.json',result);print(c.json.dumps(result,indent=2))


if __name__=='__main__':main()
