"""Map legacy top-level ``module`` pickle names to pinned SAGE classes."""

from stable_worldmodel.wm.lewm.module import *  # noqa: F403
from stable_worldmodel.wm.lewm.module import Predictor

# The historical checkpoint used ``module.ARPredictor``.  The pinned official
# SAGE release contains the same class under its current name, ``Predictor``.
ARPredictor = Predictor
