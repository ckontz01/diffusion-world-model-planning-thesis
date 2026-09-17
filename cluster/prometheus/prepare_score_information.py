"""Metadata/header-only lineage preparation. No model imports or execution."""
import ast
import json
import struct
import zipfile
from pathlib import Path
import breadth_precision_contract as p
import candidate_value_contract as ct

VERSION = 'candidate-value-score-information-20260918'
BP_SHA = '70e3838c83561b8b24ea2f2c2f6875c2674d7c9b391e682c1023ba3641238975'
BP = p.ROOT / 'experiments/candidate-value-breadth-precision-20260915/run-70e3838c83561b8b'


def headers(path):
    result = {}
    with zipfile.ZipFile(path) as z:
        for name in ('x', 'immediate', 'continuation'):
            with z.open(name+'.npy') as f:
                assert f.read(6) == b'\x93NUMPY'
                major, minor = f.read(2)
                assert major in (1, 2, 3)
                n = struct.unpack('<H' if major == 1 else '<I', f.read(2 if major == 1 else 4))[0]
                h = ast.literal_eval(f.read(n).decode('utf8' if major == 3 else 'latin1'))
                assert h['shape'] == ((64,619) if name == 'x' else (64,))
                assert h['descr'] == '<f4' and not h['fortran_order']
                result[name] = h
    return result


def prepare(target):
    source = p.ROOT / ('snapshots/candidate-value-breadth-precision-20260915-'+BP_SHA[:16])
    assert ct.sha(source/'SOURCE-MANIFEST.sha256') == BP_SHA
    members = dict((n,h) for h,n in (x.split('  ',1) for x in (source/'SOURCE-MANIFEST.sha256').read_text().splitlines()))
    sources = {}
    for rel in ('cluster/prometheus/candidate_value_hook.py', 'cluster/prometheus/candidate_value_learning.py',
                'cluster/prometheus/breadth_precision_data.py'):
        assert ct.sha(source/rel) == members[rel]
        sources[rel] = members[rel]
    old_request = p.OLD_RUN/'BACKUP-REQUEST-train.json'
    assert ct.sha(old_request) == p.TRAIN_REQUEST_SHA
    old_seals = ct.json_read(old_request)['seals']
    stage = BP/'CLUSTER-STAGE-train.json'; stages = ct.json_read(stage)
    assert stages['source_sha256'] == BP_SHA and len(stages['seals']) == 384
    # Bind this accepted stage through the sealed terminal archive's manifest.
    assert ct.sha(BP/'BACKUP-REQUEST-cluster-final.json') == 'a1166ab7eab3d563388bb4065ed941f71621d9b6a03c57550896d9708bca74de'
    req = ct.json_read(BP/'BACKUP-REQUEST-cluster-final.json')
    assert ct.sha(BP/'terminal/sha256.txt') == req['seals']['terminal']
    terminal = dict((n,h) for h,n in (x.split('  ',1) for x in (BP/'terminal/sha256.txt').read_text().splitlines()))
    assert ct.sha(stage) == terminal['CLUSTER-STAGE-train.json']
    a = p.allocation(); roots = []; count = 0
    for role, refs in (('original_train',a['original_train']),('extra_train',a['extra_train'])):
        for i,ref in enumerate(refs):
            for offset,h in enumerate((75,150)):
                index=2*i+offset
                d=(p.OLD_RUN/('train-%d'%index) if role=='original_train' else BP/('breadth-%d'%index))
                digest=(old_seals if role=='original_train' else stages['seals'])[d.name]
                assert ct.sha(d/'sha256.txt')==digest
                seal=dict((n,v) for v,n in (x.split('  ',1) for x in (d/'sha256.txt').read_text().splitlines()))
                assert ct.sha(d/'REPORT.json')==seal['REPORT.json']
                report=ct.json_read(d/'REPORT.json')
                assert (report['reference'],report['horizon'])==(ref,h)
                banks={}
                for bank in report['banks']:
                    if bank['available']:
                        name='bank-%d.npz'%bank['anchor']
                        assert ct.sha(d/name)==seal[name]
                        headers(d/name); banks[name]=seal[name];count+=1
                roots.append(dict(path=str(d),reference=ref,horizon=h,role=role,seal_sha256=digest,
                                  report_sha256=seal['REPORT.json'],banks=banks))
    assert len(roots)==384 and count==1426
    result=dict(version=VERSION,accepted_bp1_commit='05973d5932e21c13b86cd95307dc055bba646255',
        bp_source_sha256=BP_SHA,old_source_sha256=p.OLD_SOURCE_SHA,old_train_request_sha256=p.TRAIN_REQUEST_SHA,
        bp_stage_sha256=ct.sha(stage),bp_final_request_sha256=ct.sha(BP/'BACKUP-REQUEST-cluster-final.json'),
        sources=sources,roots=roots,references=192,available_banks=count,feature_dimension=619,
        saved_score_shape=[64],saved_dtype='<f4',score_omission_original_design=True,
        numeric_payloads_decoded=False,outcome_analysis_performed=False,model_or_simulator_called=False)
    ct.json_write(target,result)
    print(json.dumps(dict(target=str(target),sha256=ct.sha(target),roots=len(roots),banks=count)))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    prepare(Path(parser.parse_args().output))
