"""Conservatively retain historical invalidated/cancelled parent assignments."""
from dtv_success_cost import metadata as m

def main():
    m.REMOTE=r'''
import base64,hashlib,json,pathlib,time
R=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis');files=[];total=0
for directory in ('manifests/acid-alternative-v1/pusht-invalidated-job-296413-unfiltered-task-paths','manifests/quarantine/acid-alt-preparation-20260814/reacher-eval-v1-cancelled-job-296512'):
 for p in sorted((R/directory).glob('*.tsv')):
  b=p.read_bytes();total+=len(b)
  if total>1000000:raise RuntimeError('finite metadata ceiling')
  files.append(dict(path=str(p.relative_to(R)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode()))
print(json.dumps(dict(files=files,total_bytes=total,observed_unix=time.time(),payload_reads=0,inference=False,physics=False)))
'''
    m.DOC=m.DOC/'invalidated';m.main()

if __name__=='__main__':main()
