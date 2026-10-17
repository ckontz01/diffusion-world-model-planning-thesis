"""Preserve raw published bytes without changing the user's Git configuration."""
from .common import ROOT,DOC,write_new
from .build import derive
def main():
    p='wm_diag0_rc1_close_v1/'
    helper='''
def reviewed_additions():
    review=json.loads((DOC/'REVIEW-001.json').read_text());result={}
    for name,want in review['new_members'].items():
        path=EVIDENCE[name[len('final_evidence/'):]] if name.startswith('final_evidence/') else ROOT/name
        raw=path.read_bytes()
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=want:raise ValueError('frozen reviewed source changed '+name)
        result[name]=raw
    return result
'''
    pub=derive(p+'publication.py',p+'publication_v2.py',[
        ("['git',*args]","['git','-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol',*args]"),
        ('def main():',helper+'\ndef main():'),('raw=additions()[name]','raw=reviewed_additions()[name]')])
    stage=derive(p+'stage.py',p+'stage_v2.py',[
        ('from .freeze import additions','from .publication_v2 import reviewed_additions'),
        ('new=additions()','new=reviewed_additions()'),
        ("    volume();cpath=DOC/'FINAL-CONTRACT.json'","    volume();cpath=DOC/'FINAL-CONTRACT.json'\n    if identity(__file__)!=pub['members']['wm_diag0_rc1_close_v1/stage_v2.py']:raise ValueError('published actual staging caller source')")])
    write_new(DOC/'NATIVE-PUBLICATION-ADAPTER-002.json',{'status':'RAW_SOURCE_BYTE_PRESERVING_COMMAND_LOCAL_GIT_ADAPTER','publication':pub,'stage':stage,
        'persistent_Git_or_environment_config_changes':False,'frozen_CPU_source_or_contract_changed':False,
        'source_only_operations_added_after_CPU_freeze_are_not_silently_inserted_into_CPU_closure':True})
    print('Native publication/staging adapters ready')
if __name__=='__main__':main()
