from __future__ import annotations

from pathlib import Path

import pytest
from acid_alternative.io_utils import sha256_file
from acid_alternative.verify_c1_authorization import verify


def write(path: Path, value: bytes) -> Path:
    path.write_bytes(value)
    return path


def test_authorization_binds_every_confirmation_input(tmp_path: Path):
    source = write(tmp_path / "source", b"source")
    analysis = write(tmp_path / "analysis", b"analysis")
    orchestration = write(tmp_path / "orchestration", b"orchestration")
    manifest = write(tmp_path / "eval", b"eval")
    checkpoint = write(tmp_path / "world", b"world")
    identification = write(tmp_path / "i1", b"identification")
    identification_summary = write(tmp_path / "i1-summary", b"summary")
    scorer = write(tmp_path / "scorer", b"scorer")
    state = write(tmp_path / "state.tsv", b"state")
    evidence = {
        name: {
            "path": str(write(tmp_path / f"{name}.json", name.encode())),
            "sha256": "",
            "kind": kind,
        }
        for name, (kind, _role_field, _role_value) in {
            "closed_loop": (
                "matched_five_arm_closed_loop_analysis",
                "role",
                "development",
            ),
            "validation": (
                "heldout_correct_action_identification_analysis",
                "analysis_role",
                "D1",
            ),
            "mechanism": (
                "three_task_same_candidate_mechanism_analysis",
                "analysis_role",
                "D1",
            ),
            "sensitivity": (
                "three_task_cem_weight_sigma_sensitivity_analysis",
                "analysis_role",
                "D1",
            ),
        }.items()
    }
    for record in evidence.values():
        record["sha256"] = sha256_file(Path(record["path"]))
    authorization = {
        "status": "authorized",
        "kind": "acid_alternative_c1_authorization_v1",
        "confirmation_outcomes_unseen": True,
        "authorized_by": "test",
        "decision_note": "freeze primary configuration",
        "task_suite": ["pusht", "reacher", "cube"],
        "source_manifest_sha256": sha256_file(source),
        "analysis_manifest_sha256": sha256_file(analysis),
        "orchestration_manifest_sha256": sha256_file(orchestration),
        "development_submission_state": str(state),
        "development_submission_state_sha256": sha256_file(state),
        "development_evidence": evidence,
        "primary_configuration": {
            "lambda_weight": 0.07,
            "goal_offset": 25,
            "horizon": 5,
            "receding_horizon": 5,
            "action_block": 5,
            "cem_samples": 300,
            "cem_steps": 30,
            "cem_topk": 30,
        },
        "tasks": {
            task: {
                "eval_manifest_sha256": sha256_file(manifest),
                "world_model_checkpoint_sha256": sha256_file(checkpoint),
                "identification_manifest_sha256": sha256_file(identification),
                "identification_summary_sha256": sha256_file(
                    identification_summary
                ),
                "scorer_checkpoint_sha256": {
                    variant: {
                        str(seed): sha256_file(scorer) for seed in (6101, 6102, 6103)
                    }
                    for variant in (
                        "acid",
                        "reachability",
                        "reachability_shuffled",
                        "diffusion",
                        "diffusion_shuffled",
                        "diffusion_action_ablated",
                        "forward",
                        "forward_shuffled",
                    )
                },
            }
            for task in ("pusht", "reacher", "cube")
        },
    }
    result = verify(
        authorization,
        task="pusht",
        arm="diffusion",
        seed=6101,
        source_manifest=source,
        analysis_manifest=analysis,
        orchestration_manifest=orchestration,
        eval_manifest=manifest,
        world_model_checkpoint=checkpoint,
        identification_manifest=identification,
        identification_summary=identification_summary,
        scorer_checkpoint=scorer,
    )
    assert result["status"] == "pass"
    identification_summary.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="identification_summary_sha256 mismatch"):
        verify(
            authorization,
            task="pusht",
            arm="diffusion",
            seed=6101,
            source_manifest=source,
            analysis_manifest=analysis,
            orchestration_manifest=orchestration,
            eval_manifest=manifest,
            world_model_checkpoint=checkpoint,
            identification_manifest=identification,
            identification_summary=identification_summary,
            scorer_checkpoint=scorer,
        )
    identification_summary.write_bytes(b"summary")
    scorer.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="authorized scorer hash differs"):
        verify(
            authorization,
            task="pusht",
            arm="diffusion",
            seed=6101,
            source_manifest=source,
            analysis_manifest=analysis,
            orchestration_manifest=orchestration,
            eval_manifest=manifest,
            world_model_checkpoint=checkpoint,
            identification_manifest=identification,
            identification_summary=identification_summary,
            scorer_checkpoint=scorer,
        )
