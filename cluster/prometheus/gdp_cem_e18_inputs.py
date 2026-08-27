"""Strict E18 loaders for the intentionally failed E17 adapter artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

import gdp_cem_e17_specs as e17
import gdp_cem_e18_specs as spec
from gdp_cem_e15_data import sha256_file
from gdp_cem_e17_models import TransitionStateAdapter


def checksum_records(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        result[name.lstrip("*")] = digest
    return result


def verify_e17_audit(audit_path: Path, task_first_path: Path) -> dict[str, Any]:
    if (
        not audit_path.is_file()
        or not task_first_path.is_file()
        or sha256_file(audit_path) != spec.E17_AUDIT_SHA256
        or sha256_file(task_first_path) != spec.E17_TASK_FIRST_SHA256
    ):
        raise RuntimeError("E18 E17 audit artifacts differ")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        audit.get("status") != "ok"
        or audit.get("kind")
        != "gdp_cem_e17_transition_state_adapter_preflight_audit"
        or audit.get("decision") != "stop_transition_adapter_preflight_failed"
        or audit.get("both_tasks_passed") is not False
        or audit.get("planner_evaluation_authorized") is not False
        or audit.get("separate_protocol_draft_authorized") is not False
        or audit.get("full_horizon_diffusion_authorized") is not False
        or audit.get("task_results", {}).get("pusht", {}).get("passed") is not True
        or audit.get("task_results", {}).get("cube", {}).get("passed") is not False
        or audit.get("protocol_sha256") != spec.E17_PROTOCOL_SHA256
        or audit.get("source_manifest_sha256") != spec.E17_SOURCE_MANIFEST_SHA256
        or int(audit.get("task_first_rows", -1)) != 8
        or audit.get("task_first_tsv_sha256") != spec.E17_TASK_FIRST_SHA256
        or audit.get("d5_read") is not False
        or audit.get("claim_allowed") is not False
    ):
        raise RuntimeError("E18 did not preserve the E17 failure record")
    return audit


def load_e17_adapter(
    directory: Path,
    *,
    task: str,
    device: torch.device,
) -> tuple[TransitionStateAdapter, dict[str, Any]]:
    if task not in spec.TASKS:
        raise ValueError("invalid E18 adapter task")
    files = {
        name: directory / name
        for name in ("final.pt", "training.jsonl", "summary.json", "sha256.txt")
    }
    if not all(path.is_file() for path in files.values()):
        raise FileNotFoundError(f"incomplete E17 adapter directory: {directory}")
    expected_checksums = {
        "final.pt": sha256_file(files["final.pt"]),
        "training.jsonl": sha256_file(files["training.jsonl"]),
        "summary.json": sha256_file(files["summary.json"]),
    }
    if checksum_records(files["sha256.txt"]) != expected_checksums:
        raise RuntimeError("E17 adapter checksum file differs")
    if (
        expected_checksums["summary.json"] != spec.E17_SUMMARY_SHA256[task]
        or expected_checksums["final.pt"] != spec.E17_CHECKPOINT_SHA256[task]
    ):
        raise RuntimeError("E17 adapter frozen identity differs")
    summary = json.loads(files["summary.json"].read_text(encoding="utf-8"))
    task_spec = spec.TASK_SPEC[task]
    expected_architecture = {
        "latent_dim": spec.LATENT_DIM,
        "state_dim": int(task_spec["state_dim"]),
        "action_dim": int(task_spec["primitive_action_dim"]),
        "input_dim": e17.input_dim(
            state_dim=int(task_spec["state_dim"]),
            action_dim=int(task_spec["primitive_action_dim"]),
        ),
        "width": e17.MODEL_WIDTH,
        "residual_blocks": e17.MODEL_RESIDUAL_BLOCKS,
    }
    gate = summary.get("adapter_gate", {})
    if (
        summary.get("status") != "ok"
        or summary.get("kind")
        != "gdp_cem_e17_transition_state_adapter_preflight"
        or summary.get("task") != task
        or int(summary.get("seed", -1)) != e17.MODEL_SEED
        or summary.get("architecture") != expected_architecture
        or int(summary.get("final_step", -1)) != e17.TRAIN_STEPS
        or summary.get("checkpoint_sha256") != expected_checksums["final.pt"]
        or summary.get("training_trace_sha256")
        != expected_checksums["training.jsonl"]
        or summary.get("protocol_sha256") != spec.E17_PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != spec.E17_SOURCE_MANIFEST_SHA256
        or summary.get("final_checkpoint_written_before_validation_open") is not True
        or int(summary.get("validation_payload_rows_read_before_checkpoint", -1))
        != 0
        or summary.get("validation_checkpoint_selection") is not False
        or gate.get("passed") is not spec.E17_GATE_PASSED[task]
        or summary.get("d5_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("E17 adapter summary differs")
    payload = torch.load(files["final.pt"], map_location="cpu", weights_only=False)
    if (
        payload.get("kind") != "gdp_cem_e17_final_transition_state_adapter"
        or payload.get("task") != task
        or int(payload.get("seed", -1)) != e17.MODEL_SEED
        or payload.get("architecture") != expected_architecture
        or int(payload.get("final_step", -1)) != e17.TRAIN_STEPS
        or int(payload.get("validation_payload_rows_read_before_checkpoint", -1))
        != 0
        or payload.get("protocol_sha256") != spec.E17_PROTOCOL_SHA256
        or payload.get("source_manifest_sha256") != spec.E17_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E17 adapter checkpoint differs")
    model = TransitionStateAdapter(
        state_dim=int(task_spec["state_dim"]),
        action_dim=int(task_spec["primitive_action_dim"]),
    )
    model.load_state_dict(payload["ema_state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != int(summary.get("parameter_count", -1)):
        raise RuntimeError("E17 adapter parameter count differs")
    record = {
        "summary": str(files["summary.json"]),
        "summary_sha256": expected_checksums["summary.json"],
        "checkpoint": str(files["final.pt"]),
        "checkpoint_sha256": expected_checksums["final.pt"],
        "parameter_count": parameter_count,
        "e17_gate_passed": gate["passed"],
        "e17_failure_preserved": True,
        "e17_used_as_authorization": False,
    }
    return model, record


__all__ = ["checksum_records", "load_e17_adapter", "verify_e17_audit"]
