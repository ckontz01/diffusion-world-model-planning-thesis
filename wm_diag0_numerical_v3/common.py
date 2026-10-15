from wm_diag0_campaign_v4.common import ROOT, RUN as OLD_RUN, identity, write_new

DOCREL = 'docs/world-model-diagnostic-a2-numerical-validation-v3-20261016'
DOC = ROOT / DOCREL
RUN = OLD_RUN + '-numerical-v3'
OLD_CONTRACT = 'f08e53e73035171340fe2438e3061685a3be6d1f18a8b132540717bd447a60dc'
AMENDMENT = 'c04894f4244fd80249473eef2a399ec215435f8ad78a7871ea9faf7164203029'
COMMON = [20, 26, 32, 38, 44]
CONTEXT = [20, 23, 26, 29, 32, 35, 38, 44]
EXPECTED_USAGE = dict(visual_encoder_calls=34, encoded_frames=78,
    proprio_encoder_calls=37, action_encoder_calls=7, predictor_calls=15,
    cost_reforecast_API_operations=3, terminal_score_reductions=3,
    physics_resets=0, controller_actions=0, CEM_calls=0,
    predictor_bundle_loads=2, restricted_encoder_loads=2)
