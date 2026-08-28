from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

import audit_gdp_cem_e19_release as audit
import gdp_cem_e19_specs as spec


def test_pinned_upstream_has_exact_classified_line_ending_defect() -> None:
    root = Path(
        os.environ.get("E19_SAGE_ROOT", "/home/chris/upstreams/sage-official")
    )
    if not root.is_dir():
        return
    result = audit.audit_manifest_line_endings(root)
    assert result["passed"]
    assert result["manifest_count"] == 36
    assert result["checkout_byte_match_count"] == 0
    assert result["crlf_compatibility_match_count"] == 36
    assert result["semantic_match_count"] == 36

    process = subprocess.run(
        [sys.executable, "scripts/audit_release.py"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    classification = audit.classify_upstream_audit(process)
    assert not classification["pristine_audit_passed"]
    assert classification["classified_packaging_defect_only"]
    assert classification["expected_byte_mismatch_count"] == (
        spec.EXPECTED_RELEASE_BYTE_MISMATCHES
    )


def test_semantic_hash_is_order_sensitive() -> None:
    payload = {
        "records": [
            {
                "episode_id": 1,
                "start_frame": 2,
                "goal_frame": 27,
                "goal_offset_steps": 25,
                "record_id": "a",
                "split": "test",
            },
            {
                "episode_id": 3,
                "start_frame": 4,
                "goal_frame": 29,
                "goal_offset_steps": 25,
                "record_id": "b",
                "split": "test",
            },
        ]
    }
    forward = audit.semantic_manifest_hash(payload)
    payload["records"].reverse()
    assert audit.semantic_manifest_hash(payload) != forward
