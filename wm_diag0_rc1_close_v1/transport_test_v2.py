"""NEW actual native CLI/framing test, then derive distinct fixed binding V3."""
import ast,json,subprocess,sys
from pathlib import Path
from .common import DOC,identity,write_new
from .transport_v2 import frame,BOOTSTRAP
from . import binding_v2

def main():
    # Longer than Windows command-line ceiling, sent ONLY on stdin; JSON must
    # survive the exact buffer/text transition used by the production bootstrap.
    code="import json,sys\ndata=json.load(sys.stdin)\nprint(json.dumps({'value':data['value'],'program':'ran'}))\n"+'#'+'x'*50000+'\n'
    p=subprocess.run([sys.executable,'-B','-c',BOOTSTRAP],input=frame(code,{'value':'tiny ordinary fixture'}),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
    if p.returncode or json.loads(p.stdout)!= {'value':'tiny ordinary fixture','program':'ran'}:raise AssertionError('actual native framed CLI failed '+repr(p.stderr))
    bad=bytearray(frame(code,{}));bad[bad.index(10)+10]^=1
    q=subprocess.run([sys.executable,'-B','-c',BOOTSTRAP],input=bytes(bad),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
    if not q.returncode:raise AssertionError('changed program frame accepted')
    text=Path(binding_v2.__file__).read_text()
    edits=[('from .transport import call','from .transport_v2 import call'),
       ("value=layout();write_new(DOC/'LAYOUT-001.json',value)","value=layout()\n    if json.loads((DOC/'LAYOUT-001.json').read_text())!=value:raise ValueError('retained exact layout authority')"),
       ('deadline=time.monotonic()+90','deadline=time.monotonic()+270'),
       ("call('BINDING002',program(),args,seconds=108)","call('BINDING003',program(),args,seconds=295)")]
    for before,after in edits:
        if text.count(before)!=1:raise ValueError('exact failed V2 derivation preimage')
        text=text.replace(before,after)
    ast.parse(text,feature_version=(3,6));target=Path(__file__).with_name('binding_v3.py')
    with target.open('xb') as f:f.write(text.encode())
    write_new(DOC/'TRANSPORT-STDIN-TEST-002.json',{'status':'ACTUAL_NATIVE_LONG_PROGRAM_SHORT_ARGV_AND_JSON_FRAMING_PASSED',
        'program_bytes':len(code),'actual_argv_chars':len(BOOTSTRAP),'changed_frame_rejected':True,'sources':{'transport':identity(Path(__file__).with_name('transport_v2.py')),'test':identity(__file__),'binding':identity(target)},
        'WSL_SSH_calls':0,'configured_transport_or_security_changes':False,'scientific_payloads_read':False})
    print(json.dumps({'status':'ACTUAL_NATIVE_FRAMING_PASSED','research_calls':0}))
if __name__=='__main__':main()
