#!/usr/bin/env python3
"""Adapt the frozen E6 evaluator to the three E6D all-gate controls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import acid_alt_d2_models as d2
import acid_alt_e6d_allgate as e6d


PROTOCOL_SHA256 = "808f16435775c04b36862637efa200bc4eb47797089ac3f913be962035ed9fd4"
E6_SUMMARY_SHA256 = "84ae66457c70f5a8c386d682dab5a77bfd807f3fdf0c52de0ea7b3264ebbc0cc"


def validate_authorization(
    path: Path, *, protocol: Path, source_manifest: Path
) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "authorized_for_exposed_d2_diagnostic_only"
        or value.get("kind") != "acid_alt_e6d_d2_authorization"
        or value.get("analysis_role") != "post_e6_exposed_d2_allgate_diagnostic"
        or value.get("protocol_sha256") != PROTOCOL_SHA256
        or d2.sha256_file(protocol) != PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != d2.sha256_file(source_manifest)
        or value.get("e6_summary_sha256") != E6_SUMMARY_SHA256
        or value.get("arms") != list(e6d.ARMS)
        or value.get("scorer_seed") != 6101
        or value.get("planner_seed") != 8301
        or value.get("confirmation_claim_allowed") is not False
        or value.get("d3_access_allowed") is not False
        or value.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E6D authorization is invalid")
    evidence = Path(value["e6_summary"])
    if not evidence.is_file() or d2.sha256_file(evidence) != E6_SUMMARY_SHA256:
        raise RuntimeError("E6D prior E6 evidence differs")
    return value


def main() -> None:
    e6d.install()
    import evaluate_acid_alt_e6_d2 as base

    base.PROTOCOL_SHA256 = PROTOCOL_SHA256
    base.validate_authorization = validate_authorization
    base.main()


if __name__ == "__main__":
    main()
