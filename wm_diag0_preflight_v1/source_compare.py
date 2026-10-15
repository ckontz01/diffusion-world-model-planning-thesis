"""Read-only comparison of declared A2 native source against existing runtime."""
import ast
import difflib
import hashlib
import json
from wm_diag0_preflight_v1.common import DOC,ROOT,SITE,write_new
from wm_diag0_preflight_v1.transport import ssh

def main():
    names=['stable_worldmodel/envs/pusht/env.py','stable_worldmodel/envs/pusht/expert_policy.py',
           'stable_worldmodel/envs/dmcontrol/reacher.py','stable_worldmodel/envs/dmcontrol/dmcontrol.py',
           'stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py','stable_worldmodel/envs/utils.py',
           'stable_worldmodel/spaces.py','stable_worldmodel/policy.py']
    code='SITE='+repr(SITE)+'\nNAMES='+repr(names)+'\n'+'''
import pathlib,json
rows={}
for name in NAMES:
 raw=(pathlib.Path(SITE)/name).read_bytes()
 if len(raw)>200000: raise ValueError('source read bound')
 rows[name]=raw.decode('utf8')
print(json.dumps(rows))
'''
    live=ssh(code); inv=json.loads((DOC/'CLUSTER-INVENTORY-002.json').read_text())['source_members']; rows={}
    base=ROOT/'docs/world-model-diagnostic-a2-20261004/source-audit/point-lewm/stable-worldmodel'
    for name,source in live.items():
        raw=source.encode()
        if hashlib.sha256(raw).hexdigest()!=inv[name]['sha256']: raise ValueError('live source changed since preflight')
        declared=(base/name).read_text(encoding='utf8')
        difference=''.join(difflib.unified_diff(declared.splitlines(True),source.splitlines(True),fromfile='declared/'+name,tofile='live/'+name))
        rows[name]={'declared_sha256':hashlib.sha256((base/name).read_bytes()).hexdigest(),
                    'live_sha256':inv[name]['sha256'],'ast_equal':ast.dump(ast.parse(declared))==ast.dump(ast.parse(source)),
                    'diff':difference,'live_source':source}
    write_new(DOC/'NATIVE-SOURCE-COMPARISON-001.json',rows)
    for n,r in rows.items():
        print(n,'AST_EQUAL',r['ast_equal']); print(r['diff'])

if __name__=='__main__': main()
