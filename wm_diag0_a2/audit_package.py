"""Preparation metadata closure; no imports of downloaded source or models."""
import hashlib
import json
from pathlib import Path
import subprocess
from .design import DOC, ROOT, root_plan, counts, storage

BASE = '0386998aab0994a724bf46b331939e99854bf3e9'
INSTRUCTION = Path('C:/Users/Chris/.codex/attachments/dcec997c-6f7d-410a-9a12-3a35d28cc0b1/Pasted text.txt')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def dependencies(commit):
    names = git('ls-tree','-r','--name-only',commit,'--','wm_diag0','docs/world-model-diagnostic-20261004').decode().splitlines()
    prefix = 'docs/world-model-diagnostic-20261004/'
    return [n for n in names if n.startswith('wm_diag0/') or
            (n.startswith(prefix) and ('/' not in n[len(prefix):] or '/test-receipts/' in n))]

def digest(raw): return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def main():
    if json.loads((DOC/'ROOT-PLAN.json').read_text()) != root_plan(): raise ValueError('Root plan')
    if json.loads((DOC/'RESOURCE-PLAN.json').read_text()) != {'counts':counts(),'storage':storage()}: raise ValueError('Resource plan')
    rows = {}
    for name in dependencies(BASE):
        raw = git('show',BASE+':'+name)
        # Git-normalized comparison does not alter the existing checkout.
        if git('hash-object','--path='+name,name).strip() != git('rev-parse',BASE+':'+name).strip():
            raise ValueError('Inherited source changed: '+name)
        rows[name]=digest(raw)
    sources=json.loads((DOC/'SOURCE-AUDIT-RECEIPTS.json').read_text())
    sources+=json.loads((DOC/'ENCODER-PIN.json').read_text())['source_receipts']
    for row in sources:
        raw=(ROOT/row['path']).read_bytes()
        if digest(raw)!={'bytes':row['bytes'],'sha256':row['sha256']}: raise ValueError('Source authentication')
    record={'study':'WM-DIAG0-A2-v1','status':'PREPARATION_ONLY','original_git_commit':BASE,
            'request_path':str(INSTRUCTION),'request':digest(INSTRUCTION.read_bytes()),
            'inherited_immutable_dependencies':rows,'source_receipts_authenticated':len(sources),
            'models_loaded':False,'native_sources_generated':0,'research_authority':False}
    with (DOC/'INPUT-AND-INHERITANCE.json').open('x',encoding='utf8') as f: json.dump(record,f,indent=2)
    print(json.dumps({'original_git_commit':BASE,'dependencies_authenticated':len(rows),
                      'source_receipts_authenticated':len(sources),'request':record['request']}))

if __name__=='__main__':main()
