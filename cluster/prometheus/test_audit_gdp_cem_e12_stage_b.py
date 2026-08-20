#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import gdp_cem_e12_specs as spec
from audit_gdp_cem_e12_stage_b import METHODS, build_audit, sha256_file


class StageBAuditTest(unittest.TestCase):
    def write_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        protocol_source = Path(__file__).with_name(
            "ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md"
        )
        protocol = root / protocol_source.name
        protocol.write_bytes(protocol_source.read_bytes())
        self.assertEqual(sha256_file(protocol), spec.PROTOCOL_SHA256)
        source_manifest = root / "TRAINING-SOURCE-MANIFEST.sha256"
        source_manifest.write_text("fixture  fixture\n", encoding="utf-8")
        source_sha = hashlib.sha256(source_manifest.read_bytes()).hexdigest()
        results = root / "results"
        for task in spec.TASKS:
            for seed in spec.SEEDS:
                for method, (directory, kind, goal_mode) in METHODS.items():
                    output = results / task / f"seed-{seed}" / directory
                    output.mkdir(parents=True)
                    checkpoint = output / "best.pt"
                    trace = output / "training.jsonl"
                    checkpoint.write_bytes(f"{task}-{seed}-{method}-checkpoint".encode())
                    trace.write_text('{"step": 1}\n', encoding="utf-8")
                    summary = {
                        "status": "ok",
                        "kind": kind,
                        "task": task,
                        "seed": seed,
                        "checkpoint": str(checkpoint.resolve()),
                        "checkpoint_sha256": sha256_file(checkpoint),
                        "training_trace": str(trace.resolve()),
                        "training_trace_sha256": sha256_file(trace),
                        "parameter_count": 123,
                        "elapsed_seconds": 1.0,
                        "validity": {"passed": True, "finite": True},
                        "protocol_sha256": spec.PROTOCOL_SHA256,
                        "source_manifest_sha256": source_sha,
                        "protected_p4_c1_i1_read": False,
                        "d3_read": False,
                        "d4_read": False,
                        "runtime": {"slurm_job_id": "fixture"},
                    }
                    if goal_mode is not None:
                        summary.update(
                            {
                                "goal_mode": goal_mode,
                                "best_epoch": 1,
                                "initial_validation": {"mean_mse": 1.0},
                                "best_validation": {"mean_mse": 0.5},
                            }
                        )
                    else:
                        summary.update(
                            {
                                "reconstruction_not_official": True,
                                "best_step": 10,
                                "initial_validation_epsilon_mse": 1.0,
                                "best_validation_epsilon_mse": 0.5,
                            }
                        )
                    (output / "summary.json").write_text(
                        json.dumps(summary), encoding="utf-8"
                    )
        return results, protocol, source_manifest

    def test_all_valid_authorizes_only_stage_c(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            results, protocol, source_manifest = self.write_fixture(Path(temporary))
            audit = build_audit(results, protocol, source_manifest)
            self.assertEqual(audit["status"], "passed")
            self.assertTrue(audit["stage_b_passed"])
            self.assertTrue(audit["stage_c_authorized"])
            self.assertFalse(audit["stage_d_authorized"])
            self.assertEqual(audit["invalid_artifact_count"], 0)

    def test_invalid_head_blocks_stage_c_and_d(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            results, protocol, source_manifest = self.write_fixture(Path(temporary))
            summary_path = (
                results / "reacher" / "seed-6101" / "prism-head-h25" / "summary.json"
            )
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["status"] = "invalid"
            summary["validity"] = {
                "passed": False,
                "finite": True,
                "validation_mse_drop_at_least_15_percent": False,
            }
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            audit = build_audit(results, protocol, source_manifest)
            self.assertEqual(audit["status"], "blocked")
            self.assertFalse(audit["stage_b_passed"])
            self.assertFalse(audit["stage_c_authorized"])
            self.assertFalse(audit["stage_d_authorized"])
            self.assertEqual(audit["invalid_artifact_count"], 1)
            self.assertEqual(audit["failed_artifacts"][0]["task"], "reacher")

    def test_status_validity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            results, protocol, source_manifest = self.write_fixture(Path(temporary))
            summary_path = (
                results / "reacher" / "seed-6101" / "prism-head-h25" / "summary.json"
            )
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["validity"]["passed"] = False
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "status_matches_validity"):
                build_audit(results, protocol, source_manifest)


if __name__ == "__main__":
    unittest.main()
