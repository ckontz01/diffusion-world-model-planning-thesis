"""Continuation shares native-v3's single finite preparation charge."""
from pathlib import Path
from wm_diag0_native_v3.common import ROOT,REMOTE,identity,write_new,canonical

DOCREL='docs/world-model-diagnostic-a2-campaign-v4-20261015'
DOC=ROOT/DOCREL
SOURCE_RUN=REMOTE+'/experiments/wm-diag0-a2-20261015/native-v3-import-r1'
RUN=REMOTE+'/experiments/wm-diag0-a2-20261015/campaign-v4'
SETTINGS=(('pusht','lewm'),('pusht','dinowm_noprop'),('reacher','lewm'),('reacher','dinowm_noprop'))

def setting(key):
    if not 0<=key<4:raise ValueError('one of four settings')
    return SETTINGS[key]
