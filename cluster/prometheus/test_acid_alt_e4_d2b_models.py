from __future__ import annotations

import csv
import json

import torch
from torch import nn

import acid_alt_e4_d2b_models as d2b
import analyze_acid_alt_e4_d2b as analysis
from acid_alt_e4_models import ConditionalActionDenoiser


class FakeWorldModel(nn.Module):
    def __init__(self, latent_dim: int = 4) -> None:
        super().__init__()
        self.anchor = nn.Parameter(torch.zeros(()), requires_grad=False)
        self.latent_dim = latent_dim

    def encode(self, value):
        pixels = value["pixels"]
        if pixels.ndim == 2:
            pixels = pixels[:, None, :]
        return {"emb": pixels[..., : self.latent_dim] + self.anchor}

    def rollout(self, work, candidates):
        batch, count, horizon, _ = candidates.shape
        base = torch.zeros(
            batch,
            count,
            horizon + 1,
            self.latent_dim,
            device=candidates.device,
            dtype=candidates.dtype,
        )
        base[:, :, 1:, : candidates.shape[-1]] = candidates.cumsum(dim=2)
        work["predicted_emb"] = base
        return work

    def criterion(self, work):
        return work["predicted_emb"][:, :, -1].square().mean(dim=-1)


def _inputs():
    generator = torch.Generator().manual_seed(17)
    candidates = torch.randn(2, 7, 5, 2, generator=generator)
    info = {"goal": torch.zeros(2, 1, 4)}
    return info, candidates


def test_frozen_arm_grid_and_weights() -> None:
    assert len(d2b.ARMS) == 18
    assert len(set(d2b.ARMS)) == len(d2b.ARMS)
    assert d2b.arm_lambda("acid_l002") == 0.02
    assert d2b.arm_lambda("acid") == 0.07
    assert d2b.arm_lambda("acid_l014") == 0.14
    assert d2b.arm_lambda("cider_tail_l002") == 0.02
    assert d2b.arm_lambda("cider_tail") == 0.07
    assert d2b.arm_lambda("cider_tail_l014") == 0.14
    assert d2b.expected_artifact_family("cider_shuffled") == "e4_shuffled"


def test_shuffled_reliability_is_exact_b0() -> None:
    info, candidates = _inputs()
    b0 = d2b.E4D2BCostModel(
        FakeWorldModel(),
        arm="b0",
        task="pusht",
        planner_seed=8401,
    )
    shuffled_scorer = ConditionalActionDenoiser(
        latent_dim=4,
        action_dim=2,
        width=16,
        depth=1,
        noise_embedding_dim=8,
    )
    payload = {
        "seed": 7101,
        "model_config": {"latent_dim": 4, "action_dim": 2},
    }
    calibration = {
        "quantiles": {
            str(sigma): {"cider_q95": 0.0, "cider_q99": 1.0}
            for sigma in (0.5, 1.0, 2.0, 4.0)
        }
    }
    shuffled = d2b.E4D2BCostModel(
        FakeWorldModel(),
        arm="cider_shuffled",
        task="pusht",
        planner_seed=8401,
        scorer=shuffled_scorer,
        payload=payload,
        calibration=calibration,
    )
    b0_cost = b0.get_cost(info, candidates)
    shuffled_cost = shuffled.get_cost(info, candidates)
    assert torch.equal(b0_cost, shuffled_cost)
    assert shuffled.diagnostic_history[0]["reliability"] == 0
    assert not any(shuffled.diagnostic_history[0]["active_weight"])


def test_b0_rejects_hidden_scorer() -> None:
    scorer = ConditionalActionDenoiser(
        latent_dim=4,
        action_dim=2,
        width=16,
        depth=1,
        noise_embedding_dim=8,
    )
    try:
        d2b.E4D2BCostModel(
            FakeWorldModel(),
            arm="b0",
            task="pusht",
            planner_seed=8401,
            scorer=scorer,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("B0 accepted a hidden scorer")


def test_analyzer_pairing_and_bootstrap_shapes() -> None:
    assert analysis.expected_model_seed("b0") is None
    assert analysis.expected_model_seed("acid") == 6101
    assert analysis.expected_model_seed("cider_tail") == 7101
    left = torch.tensor(([1, 0, 1, 0, 1] * 10), dtype=torch.int8).numpy()
    right = torch.tensor(([0, 0, 1, 1, 1] * 10), dtype=torch.int8).numpy()
    discordance = analysis.paired_discordance(left, right)
    assert discordance == {
        "left_success_right_failure": 10,
        "left_failure_right_success": 10,
        "both_success": 20,
        "both_failure": 10,
        "discordant_total": 20,
    }
    indices = analysis.bootstrap_indices()
    summary = analysis.summarize(
        {task: left.astype(float) for task in analysis.TASKS}, indices
    )
    assert summary["equal_task"]["estimate"] == 0.6
    assert summary["bootstrap_repetitions"] == 100_000


def test_analyzer_accepts_evaluator_schema(tmp_path) -> None:
    episodes = tmp_path / "episodes.tsv"
    with episodes.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "eval_index",
                "episode_id",
                "start_step",
                "planner_seed",
                "arm",
                "success",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for index in range(50):
            writer.writerow(
                {
                    "eval_index": index,
                    "episode_id": index + 100,
                    "start_step": index,
                    "planner_seed": 8401,
                    "arm": "cider_tail",
                    "success": int(index % 2 == 0),
                }
            )
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "status": "ok",
                "kind": "acid_alt_e4_d2b_closed_loop_evaluation",
                "analysis_role": (
                    "post-E3 exposed D2 exploratory closed-loop development"
                ),
                "task": "pusht",
                "arm": "cider_tail",
                "model_seed": 7101,
                "planner_seed": 8401,
                "episode_count": 50,
                "success_count": 25,
                "parent_protocol_sha256": "parent",
                "d2b_freeze_sha256": "freeze",
                "source_manifest_sha256": "source",
                "d2a_summary_sha256": "d2a",
                "d2a_authorization_sha256": "authorization",
                "confirmation_claim_allowed": False,
                "publication_claim_allowed": False,
                "alternative_to_acid_claim_allowed": False,
                "protected_c1_i1_read": False,
                "episodes_tsv": str(episodes),
                "episodes_tsv_sha256": analysis.sha256_file(episodes),
                "eval_manifest_sha256": "manifest",
                "dataset_sha256": "dataset",
                "world_model_checkpoint_sha256": "world-model",
                "elapsed_seconds": 2.0,
                "cem_cost_calls": 30,
                "runtime": {
                    "gpu": "synthetic",
                    "peak_cuda_memory_allocated_bytes": 1024,
                },
            }
        ),
        encoding="utf-8",
    )
    record = analysis.load_run(
        ("pusht", "cider_tail", summary),
        parent_protocol_sha256="parent",
        d2b_freeze_sha256="freeze",
        source_manifest_sha256="source",
        d2a_summary_sha256="d2a",
        authorization_sha256="authorization",
    )
    assert int(record["success"].sum()) == 25
    assert record["model_seed"] == 7101
