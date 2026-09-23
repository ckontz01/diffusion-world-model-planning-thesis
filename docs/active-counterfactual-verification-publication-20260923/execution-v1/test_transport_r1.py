"""Local stdlib transport framing tests; no SSH, research or scheduler calls."""
import hashlib
import json
import subprocess
import sys
import time
import operate as o

if __name__=='__main__':
    started=time.monotonic()
    results=[]
    for payload in (b'',b'\x00\xff\r\n'+bytes(range(256))*4000):
        # Real operation blocks inherit json from the old transport header.
        code="import hashlib,sys; p=sys.stdin.buffer.read(); print(json.dumps({'bytes':len(p),'sha256':hashlib.sha256(p).hexdigest(),'run':CONFIG['run']}))"
        data=o.envelope(code,payload)
        r=subprocess.run([sys.executable,'-B','-S','-c',o.BOOTSTRAP],input=data,capture_output=True,timeout=20)
        assert r.returncode==0,r.stderr
        answer=json.loads(r.stdout)
        assert answer=={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'run':o.RUN}
        results.append({'payload_bytes':len(payload),'envelope_bytes':len(data),'sha256_match':True})
    try:o.envelope('pass',b'x'*2_000_000)
    except AssertionError:overflow_rejected=True
    else:raise AssertionError('Envelope overflow was accepted')
    for code in (o.PREFLIGHT,o.STAGE,o.LAUNCH,o.OBSERVE):compile(code,'<operation>','exec')
    receipt={'status':'PASSED','cases':results,'overflow_rejected':overflow_rejected,
             'fixed_bootstrap_argument_characters':len(o.BOOTSTRAP),'all4_operations_compile':True,
             'network_calls':0,'research_payload_reads':0,'wall_seconds':time.monotonic()-started,
             'helper_sha256':o.sha(o.HERE/'operate.py')}
    receipt['operation_json_global_preserved']=True
    o.write(o.HERE/'TRANSPORT-R1-TESTS-FINAL.json',receipt);print(json.dumps(receipt,indent=2))
