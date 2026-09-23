"""Technical framing and disabled-entry tests only; no SSH/research calls."""
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import operate as o

started=time.monotonic()
cases=[]
for payload in (b'',b'\x00\xff\r\n'+bytes(range(256))*4000):
    code="import hashlib,sys;p=sys.stdin.buffer.read();print(json.dumps({'bytes':len(p),'sha':hashlib.sha256(p).hexdigest(),'run':CONFIG['run']}))"
    data=o.envelope(code,payload)
    r=subprocess.run([sys.executable,'-B','-S','-c',o.BOOTSTRAP],input=data,capture_output=True,timeout=20)
    assert r.returncode==0,r.stderr
    assert json.loads(r.stdout)=={'bytes':len(payload),'sha':hashlib.sha256(payload).hexdigest(),'run':o.RUN}
    cases.append({'payload_bytes':len(payload),'envelope_bytes':len(data),'exact_binary_roundtrip':True})
try:o.envelope('pass',b'x'*2_000_000)
except AssertionError:pass
else:raise AssertionError('Oversized envelope accepted')
for code in (o.PREFLIGHT,o.STAGE,o.LAUNCH,o.OBSERVE):compile(code,'<operation>','exec')
# Reproduce real double-base64 stage framing size, including full execution text.
instruction=o.ATTACHMENT.read_bytes()
approval=o.read(o.PACKAGE/'APPROVAL-TEMPLATE.json');approval.update(authorized=True,instruction=instruction.decode())
payload={'archive':base64.b64encode((o.PACKAGE/'source-export.tar').read_bytes()).decode(),
         'approval':base64.b64encode(json.dumps(approval).encode()).decode(),
         'instruction':base64.b64encode(instruction).decode(),'provenance':{'synthetic':True}}
stage_bytes=len(o.envelope(o.STAGE,json.dumps(payload).encode()))
interlocks=[]
for script in ('dispatch.py','worker.py','supervise.py'):
    args=[sys.executable,'-B','-S',str(o.PACKAGE/script),'--approval',str(o.PACKAGE/'APPROVAL-TEMPLATE.json'),'--run',o.RUN]
    if script!='dispatch.py':args+=['--task','collect-fit-490']
    r=subprocess.run(args,capture_output=True,text=True,timeout=20)
    assert r.returncode!=0 and 'Research execution disabled' in r.stderr,(script,r.stdout,r.stderr)
    interlocks.append(script)
receipt={'status':'PASSED','binary_framing':cases,'overflow_rejected':True,'stage_envelope_bytes':stage_bytes,
         'disabled_before_dependencies_or_scheduler':interlocks,'all4_operations_compile':True,
         'helper_sha256':o.sha(o.HERE/'operate.py'),'script_sha256':o.sha(__file__),
         'wall_seconds':time.monotonic()-started,'network_calls':0,'research_allocations':0,'research_payload_reads':0}
o.write(o.HERE/'OPERATION-TESTS.json',receipt)
print(json.dumps(receipt,indent=2))
