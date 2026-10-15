from pathlib import Path
from wm_diag0_native_v3.common import ROOT,identity,write_new,canonical
DOCREL='docs/world-model-diagnostic-rc1-v1-20261016'
DOC=ROOT/DOCREL
BASE='/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015'
RUN=BASE+'/campaign-v4-rc1-v1'
OLD_RUN=BASE+'/campaign-v4'
V3_RUN=BASE+'/campaign-v4-numerical-v3'
V3_REPORT={'bytes':15815,'sha256':'196bd63be202ac7cecbac1f21f7e4689e64c47748fb98be1222914c2dab8240f'}
COMMON=[20,26,32,38,44]
CONTEXT=[20,23,26,29,32,35,38,44]
EXPECTED_GATE_USAGE=dict(visual_encoder_calls=88,encoded_frames=88,proprio_encoder_calls=88,
 action_encoder_calls=5,predictor_calls=5,cost_reforecast_API_operations=1,terminal_score_reductions=1,
 predictor_bundle_loads=2,restricted_encoder_loads=2,CEM_calls=0,physics_resets=0,controller_actions=0)
REPRESENTATION='RC1_pointwise_B1_T1_original_BF16_F32_v1'
