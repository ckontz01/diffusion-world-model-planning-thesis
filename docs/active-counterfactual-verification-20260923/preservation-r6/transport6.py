"""Finite R6 transport, reusing the previously tested8MB SSH envelope."""
import argparse,base64,sys
from pathlib import Path
import archive6 as a
r=a.load5()
import transport5 as t
HERE=a.REPO/'docs/active-counterfactual-verification-publication-20260923/preservation-r6'
REL='docs/active-counterfactual-verification-20260923/preservation-r6'
def config():return {'binding':a.binding(),'rel':REL,'transport':a.read(a.ROOT/'SOURCE-TRANSPORT.json'),'approval_sha256':a.sha(HERE/'EXECUTION-APPROVAL.json')}
STAGE=r'''
from pathlib import Path,PurePosixPath
import base64,io,hashlib,tarfile,sys,time
b=CONFIG['binding'];source=Path(b['source']);control=Path(b['control'])
assert not source.exists() and not control.exists(),'Exclusive R6 namespace; no repeat'
assert not (Path(b['r5_control']).parent.parent/'experiments/active-counterfactual-verification-pilot-v1/run-c2c6fcbe8c41fed2/final-preservation').exists(),'Existing preservation; reconcile first'
package=json.loads(sys.stdin.buffer.read(8000000));raw=base64.b64decode(package['archive'],validate=True);approval=base64.b64decode(package['approval'],validate=True)
assert hashlib.sha256(approval).hexdigest()==CONFIG['approval_sha256']
trans=CONFIG['transport'];assert len(raw)==trans['bytes'] and hashlib.sha256(raw).hexdigest()==trans['sha256']
members={}
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tar:
 for m in tar:
  n=PurePosixPath(m.name);assert m.isfile() and len(n.parts)==1 and not n.is_absolute() and m.name not in members
  data=tar.extractfile(m).read();assert {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}==trans['members'][m.name]
  members[m.name]=data
assert set(members)==set(trans['members'])
assert hashlib.sha256(members['SOURCE-MANIFEST.json']).hexdigest()==b['manifest']
manifest=json.loads(members['SOURCE-MANIFEST.json']);assert set(members)==set(manifest['files'])|{'SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json'}
for n,h in manifest['files'].items():assert hashlib.sha256(members[n]).hexdigest()==h
assert json.loads(members['APPROVAL-TEMPLATE.json'])['authorized'] is False
source.mkdir();control.mkdir();root=source/CONFIG['rel'];root.mkdir(parents=True)
for n,data in members.items():
 with (root/n).open('xb') as f:f.write(data)
sys.path.insert(0,str(root));import archive6 as a
with (control/'EXECUTION-APPROVAL.json').open('xb') as f:f.write(approval)
a.write(control/'SMALL-PACKAGE-DELIVERY.json',package['delivery'])
ctx=a.Context(control/'EXECUTION-APPROVAL.json');combined=a.guard(ctx)
from controller_runtime import verify
pins=verify()
items=a.inventory_from_roots(a.roots(ctx),ctx.run/'final-preservation',ctx.old.baseline['inventory'])
result={'unix':time.time(),'manifest':b['manifest'],'approval_sha256':ctx.approval_sha,'members':len(members),
 'all_original_root_members_accounted':True,'inventory_files':len(items),'root_labels':[n for n,p in a.roots(ctx)],
 'runtime':pins,'scientific_payloads_decoded':0,'new_jobs':0,'archive_exists':False}
a.write(control/'TRANSPORT-VERIFIED.json',result);print(json.dumps(result))
'''
ARCHIVE=r'''
from pathlib import Path
import sys
b=CONFIG['binding'];control=Path(b['control']);sys.path.insert(0,str(Path(b['source'])/CONFIG['rel']))
import archive6 as a
ctx=a.Context(control/'EXECUTION-APPROVAL.json');assert a.read(control/'TRANSPORT-VERIFIED.json')['approval_sha256']==ctx.approval_sha
from controller_runtime import verify
verify();print(json.dumps(a.archive(ctx)))
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['stage','archive']);args=p.parse_args()
    # Original R5 local() also verifies pinned old closure and the designatedSSD.
    t.local();t.HERE=HERE;t.configuration=config
    if args.mode=='stage':
        a.write(HERE/'LOCAL-PREFLIGHT.json',{'old_r5_and_ssd_verified':True,'r6_manifest':a.binding()['manifest']})
        delivery=a.read(HERE/'DELIVERY.json');assert delivery['status']=='VERIFIED' and delivery['remote_head_verified']
        trans=a.read(a.ROOT/'SOURCE-TRANSPORT.json');t.verify_archive(a.ROOT/'source-export.tar',trans)
        payload={'archive':base64.b64encode((a.ROOT/'source-export.tar').read_bytes()).decode(),
            'approval':base64.b64encode((HERE/'EXECUTION-APPROVAL.json').read_bytes()).decode(),'delivery':delivery}
        t.once('SOURCE-TRANSPORT',STAGE,a.canonical(payload))
    else:
        assert a.read(HERE/'SOURCE-TRANSPORT.json')['returncode']==0
        t.once('ARCHIVE',ARCHIVE)
if __name__=='__main__':main()
