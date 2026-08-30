"""Frozen identities for the E19-D2 analyzer-only reanalysis."""

from __future__ import annotations


PROTOCOL_FILENAME = (
    "ACID-ALTERNATIVE-E19-D2-METHOD-AWARE-DISCREPANCY-REANALYSIS-"
    "PROTOCOL-2026-08-30.md"
)
PARENT_SNAPSHOT = (
    "/lustreFS/data/superworld/ckontzias/thesis/snapshots/"
    "gdp-cem-e19-discrepancy-e347bc087381ecf0"
)
PARENT_SOURCE_MANIFEST_SHA256 = (
    "e347bc087381ecf0902581e8225165dbd64c887eba661b74b064c09d4e13d7fa"
)
PARENT_PROTOCOL_SHA256 = (
    "e420dca314038141caa30cadf0fe67ba649e53803d393e85a52c5a87a321f319"
)
PARENT_RUN_ROOT = (
    "/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/"
    "discrepancy-diagnostic-run-20260829-e347bc08"
)
E19_RUN_ROOT = (
    "/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/"
    "native-reproduction-run-20260828-9f549988"
)
LEGACY_ANALYZER_SHA256 = (
    "3ddecca36b538509a7664dd5bfdaa12fd6ae007e788a909c4a01f0a11811c710"
)
PARENT_SPECS_SHA256 = (
    "0fc796ef859d56cea7c7e8c0c59ec040709794a974dfc51d8e34b5a98f1ff888"
)
PARENT_TRACER_SHA256 = (
    "d7868498b3dcd77efbf7e7d57f55f2f6a8b1097070b3c90632163205b7a83589"
)
HISTORY_CONDITIONED_METHODS = frozenset(
    {
        "far_goal_prior_cem",
        "lewm_generator",
        "generator_prior_top",
        "sage",
    }
)
HISTORY_FREE_METHODS = frozenset({"base_cem"})
EXPECTED_SENTINELS = 5
EXPECTED_REPEATS = 2
EXPECTED_RUNS = EXPECTED_SENTINELS * EXPECTED_REPEATS
EXPECTED_EPISODES = 500
