"""Read only dependency source text, never instantiate a native environment."""
from dtv_success_cost import metadata as m

def main():
    m.REMOTE=r'''
import base64,hashlib,json,pathlib,time
R=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis')
p=R/'envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages/ogbench/manipspace/envs/env.py'
b=p.read_bytes()
print(json.dumps(dict(files=[dict(path=str(p.relative_to(R)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode())],total_bytes=len(b),observed_unix=time.time(),payload_reads=0,inference=False,physics=False)))
'''
    m.DOC=m.DOC/'native-base';m.main()
if __name__=='__main__':main()
