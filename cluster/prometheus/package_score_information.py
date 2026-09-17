"""Build SI1 source closure and disabled approval; never submit or fit."""
import argparse
import hashlib
import json
from pathlib import Path
import score_information as s

FILES = ['cluster/prometheus/'+name+'.py' for name in (
    'candidate_value_contract','candidate_value_learning','candidate_value_data',
    'candidate_value_models','breadth_precision_contract','breadth_precision_data',
    'score_information','prepare_score_information','test_score_information','package_score_information')]
FILES += ['cluster/prometheus/run_score_information.sh',
    'analysis/cvl1-objective-capacity-20260915-v1/study.py']
FILES += [s.DOC+'/'+name for name in ('PROTOCOL.md','RESOURCE-PLAN.md','LINEAGE.json','FOLDS.json')]


def build(output):
    assert s.ct.sha(s.ROOT/s.DOC/'LINEAGE.json')==s.LINEAGE_SHA
    assert s.ct.json_read(s.ROOT/s.DOC/'FOLDS.json')['held_out']==s.folds()
    out=Path(output);out.mkdir(parents=True,exist_ok=False);lines=[];total=0
    for name in sorted(FILES):
        data=(s.ROOT/name).read_bytes()
        if name.endswith(('.py','.sh','.md')):data=data.replace(b'\r\n',b'\n')
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
        total+=len(data);lines.append(hashlib.sha256(data).hexdigest()+'  '+name+'\n')
    assert total<20000000
    manifest=''.join(lines).encode();(out/'SI1-SOURCE-MANIFEST.sha256').write_bytes(manifest)
    approval=dict(study=s.VERSION,execution_authorized=False,source_sha256=hashlib.sha256(manifest).hexdigest(),
                  lineage_sha256=s.LINEAGE_SHA,fits=24,caps=s.CAPS)
    (out/'APPROVAL-TEMPLATE.json').write_text(json.dumps(approval,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(source_sha256=approval['source_sha256'],files=len(FILES),bytes=total,execution_authorized=False)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);build(p.parse_args().output)
