"""Bind direct human-adopted instructions and immutable completed publication."""
import json,subprocess
from pathlib import Path
from .common import ROOT,DOC,OLD,identity,write_new

def main():
    a=json.loads((DOC/'AUTHORITY.json').read_text());p=Path(a['human_adopted_instruction_file']);raw=p.read_bytes()
    write_new(DOC/'HUMAN-ADOPTED-INSTRUCTIONS.txt',raw)
    anchors={}
    for name in ('PRO-RESULTS-HANDOFF.txt','RESULTS.json','ACCEPTANCE.json','FINAL-SSD-VERIFIED.json','FINAL-CONTRACT-002.json'):
        source=OLD/name;relative=source.relative_to(ROOT).as_posix()
        published=subprocess.check_output(['git','show',a['completed_publication']+':'+relative],cwd=ROOT,timeout=10)
        if published!=source.read_bytes():raise ValueError('completed published input changed: '+name)
        anchors[name]=identity(source)
    gate=json.loads((OLD/'FINAL-SSD-VERIFIED.json').read_text())
    if identity(Path(gate['archive']).parent/'FINAL-SSD-VERIFIED.json')!=anchors['FINAL-SSD-VERIFIED.json']:raise ValueError('matching completed designated SSD gate')
    write_new(DOC/'ACTIVATION.json',{'status':'NEW_SAVED_DATA_DISCOVERY_SCOPE_ACTIVATED_COMPLETED_STUDY_UNCHANGED','instructions':identity(DOC/'HUMAN-ADOPTED-INSTRUCTIONS.txt'),
        'authority':identity(DOC/'AUTHORITY.json'),'completed_publication':a['completed_publication'],'completed_anchors':anchors,'old_monitors_resumed':False,'new_derived_results_computed':False})
    import numpy as np
    print(json.dumps({'status':'ACTIVATED','compatible_existing_native_numpy':np.__version__,'anchors':len(anchors)}))

if __name__=='__main__':main()
