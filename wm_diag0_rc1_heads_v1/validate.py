"""Independent original ridge equations plus RC1 route and exact module counts."""
import json,sys
from pathlib import Path
from .common import identity,write_new,USAGE

def accept(directory,seal,c,setting):
    if setting not in (1,3):raise ValueError('DINO heads only')
    from wm_diag0_campaign_v4.accept_readout import accept as equations
    from wm_diag0.core import FeatureContract
    from .route import check
    d=dict(json.loads((Path(directory)/'READOUT.json').read_text())['contract'])
    d['feature_shape']=tuple(d['feature_shape']);d['positions']=tuple(d['positions'])
    check(c,setting,FeatureContract(**d))
    result=equations(directory,seal,c,setting)
    result.update(RC1_pointwise_route_independently_bound=True,original_heads_preserved=True,validation_used_for_tuning=False)
    return result

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];setting=int(sys.argv[3]);cp=root/'source/HEADS-CONTRACT.json'
    if identity(cp)['sha256']!=expected:raise ValueError('frozen head contract')
    c=json.loads(cp.read_text());task=root/'tasks'/('readout-'+str(setting));w=json.loads((task/'controls/WORKER-SUCCESS.json').read_text())
    if w['phase']!='RC1_readout' or w['setting']!=setting or w['actual_usage']!=USAGE or w['predictor_bundle_loads']!=1 or w['restricted_encoder_loads']!=1:
        raise ValueError('actual task/module/frame identity')
    result=accept(task/'output',w['output_seal'],c,setting)
    result.update(phase='RC1_readout',setting=setting,actual_usage=w['actual_usage'],fit_frames=256,validation_frames=96,
        quality_or_predictions_emitted=False,contract_sha256=expected)
    write_new(task/'controls/ACCEPTED.json',result)
    print(json.dumps({'status':'RC1_HEAD_INDEPENDENTLY_ACCEPTED','setting':setting,'output_seal':w['output_seal']}))

if __name__=='__main__':main()
