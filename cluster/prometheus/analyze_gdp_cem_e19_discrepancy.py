#!/usr/bin/env python3
"""Seal and classify the frozen E19 discrepancy diagnostic."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import torch

import gdp_cem_e19_discrepancy_specs as spec
from trace_gdp_cem_e19_discrepancy import canonical_sha256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256_file(directory: Path) -> dict[str, str]:
    manifest = directory / "sha256.txt"
    rows: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        relative = relative.lstrip("* ")
        path = directory / relative
        if sha256_file(path) != digest:
            raise RuntimeError(f"checksum mismatch: {path}")
        rows[relative] = digest
    return rows


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def e19_result_path(root: Path, sentinel: spec.Sentinel) -> Path:
    return (
        root
        / "evaluation"
        / sentinel.benchmark
        / sentinel.method
        / f"seed{sentinel.seed}"
        / f"h{sentinel.horizon}"
        / "results.json"
    )


def result_identity(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload["metrics"]
    return {
        "benchmark": payload["benchmark"],
        "method": payload["method"],
        "seed": payload["seed"],
        "horizon": payload["horizon"],
        "schedule": payload["schedule"],
        "num_eval": payload["num_eval"],
        "success_rate": metrics["success_rate"],
        "episode_successes": metrics["episode_successes"],
        "record_ids": payload.get("record_ids"),
        "planner": payload["planner"],
        "environment_budget": payload["environment_budget"],
    }


def trace_gate(trace: dict[str, Any], sentinel: spec.Sentinel, repeat: int) -> dict:
    events = trace["events"]
    plan_ids = [row["plan_index"] for row in events if row["kind"] == "solver_input"]
    unique_plans = sorted(set(plan_ids))
    if plan_ids != unique_plans:
        raise RuntimeError(f"non-monotonic or duplicate solver-input plans: {sentinel}")
    cem = sentinel.method != "generator_prior_top"
    fits = [row for row in events if row["kind"] == "cem_fit"]
    per_plan = {
        plan: [row for row in fits if row["plan_index"] == plan]
        for plan in unique_plans
    }
    checks = {
        "kind": trace.get("kind") == "gdp_cem_e19_discrepancy_trace",
        "sentinel_id": trace.get("sentinel", {}).get("sentinel_id")
        == sentinel.sentinel_id,
        "repeat": trace.get("repeat") == repeat,
        "planner": trace.get("planner") == spec.PLANNER,
        "event_stream": trace.get("event_stream_sha256")
        == canonical_sha256(events),
        "plans_present": bool(unique_plans),
        "fit_count": (
            all(len(rows) == spec.PLANNER["cem_rounds"] for rows in per_plan.values())
            if cem
            else not fits
        ),
        "round_indices": (
            all(
                [row["round_index"] for row in rows]
                == list(range(spec.PLANNER["cem_rounds"]))
                for rows in per_plan.values()
            )
            if cem
            else True
        ),
        "first_round_candidates_and_costs": (
            all(
                "candidates" in rows[0]
                and "costs" in rows[0]
                and all("candidates" not in row and "costs" not in row for row in rows[1:])
                for rows in per_plan.values()
            )
            if cem
            else True
        ),
        "every_fit_has_elite_mean_std": all(
            all(key in row for key in ("elite_indices", "mean", "effective_std"))
            for row in fits
        ),
        "latents_present": any(row["kind"] == "history_latents" for row in events)
        and any(row["kind"] == "final_goal_latents" for row in events)
        and any(
            row["kind"] in {"local_goal", "cube_local_goal_cache"}
            for row in events
        ),
        "observational_only": trace.get("observational_only") is True,
        "source_unmodified": trace.get("official_sage_source_modified") is False,
        "checkpoint_unmodified": trace.get("checkpoint_modified") is False,
        "planner_unmodified": trace.get("planner_parameter_modified") is False,
        "no_protected_read": trace.get("protected_metric_artifact_read") is False,
        "no_e18_comparison": trace.get("e18_vs_sage_comparison_run") is False,
        "no_d5": trace.get("d5_read") is False,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "plan_count": len(unique_plans),
        "fit_count": len(fits),
    }


def cube_cache_gate(traces: list[dict[str, Any]]) -> dict[str, Any]:
    events = []
    scoped_seen: dict[str, str] = {}
    collisions = []
    return_mismatches = []
    hit_mismatches = []
    stage_key_disagreements = []
    for trace_index, trace in enumerate(traces):
        sentinel = trace.get("sentinel", {}).get("sentinel_id", "unknown")
        repeat = trace.get("repeat", "unknown")
        scope = f"s{sentinel}/r{repeat}/t{trace_index}"
        seen: dict[str, str] = {}
        stage_keys: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        trace_events = [
            row for row in trace["events"] if row["kind"] == "cube_local_goal_cache"
        ]
        events.extend(trace_events)
        for event in trace_events:
            keys = [tuple(key) for key in event["stage_keys"]]
            hits = event["cache_hit"]
            before = event["values_before"]
            after = event["values_after"]
            returned = event["returned_by_stage_key"]
            if not (len(keys) == len(hits) == len(returned)):
                raise RuntimeError("Cube cache trace row-count mismatch")
            for key, hit, returned_hash in zip(keys, hits, returned, strict=True):
                text_key = str(key)
                scoped_key = f"{scope}:{text_key}"
                stage = (key[0], key[1])
                if stage in stage_keys and stage_keys[stage] != key:
                    stage_key_disagreements.append(
                        f"{scope}:{stage_keys[stage]}!={key}"
                    )
                else:
                    stage_keys[stage] = key
                expected_hit = text_key in before
                if bool(hit) != expected_hit:
                    hit_mismatches.append(scoped_key)
                value_hash = after.get(text_key)
                if value_hash is None or returned_hash != value_hash:
                    return_mismatches.append(scoped_key)
                if text_key in seen and seen[text_key] != value_hash:
                    collisions.append(scoped_key)
                elif value_hash is not None:
                    seen[text_key] = value_hash
                    scoped_seen[scoped_key] = value_hash
            for text_key, value_hash in after.items():
                scoped_key = f"{scope}:{text_key}"
                if text_key in seen and seen[text_key] != value_hash:
                    collisions.append(scoped_key)
                else:
                    seen[text_key] = value_hash
                    scoped_seen[scoped_key] = value_hash
    checks = {
        "events_present": bool(events),
        "stage_key_arity": all(
            all(len(key) == 4 for key in event["stage_keys"]) for event in events
        ),
        "no_value_drift_or_collision": not collisions,
        "cache_hit_flags_exact": not hit_mismatches,
        "returned_goal_matches_cache": not return_mismatches,
        "expanded_unexpanded_stage_keys_exact": not stage_key_disagreements,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "event_count": len(events),
        "scoped_unique_stage_key_count": len(scoped_seen),
        "collisions": sorted(set(collisions)),
        "hit_mismatches": sorted(set(hit_mismatches)),
        "return_mismatches": sorted(set(return_mismatches)),
        "stage_key_disagreements": sorted(set(stage_key_disagreements)),
    }


def write_author_packet(
    *,
    output: Path,
    audit: dict[str, Any],
    comparison_sha256: str,
    source_snapshot: Path,
    run_root: Path,
) -> list[Path]:
    packet = output / "author-evidence"
    packet.mkdir()
    machine = {
        "kind": "gdp_cem_e19_author_evidence_packet",
        "e19_decision": "stop_native_reproduction_failed",
        "e19_source_manifest_sha256": spec.E19_SOURCE_MANIFEST_SHA256,
        "e19_protocol_sha256": spec.E19_PROTOCOL_SHA256,
        "diagnostic_snapshot": str(source_snapshot),
        "diagnostic_run_root": str(run_root),
        "comparison_audit_sha256": comparison_sha256,
        "diagnostic_decision": audit["decision"],
        "objective_mismatch_classes": audit["objective_mismatch_classes"],
        "sentinels": audit["sentinel_repeatability"],
        "cube_cache": audit["cube_cache"],
        "official_sage_commit": spec.SAGE_GIT_COMMIT,
        "official_sage_tree": spec.SAGE_GIT_TREE,
        "contact_performed": False,
        "protected_metric_artifact_read": False,
        "e18_vs_sage_comparison_run": False,
        "d5_read": False,
    }
    machine_path = packet / "machine-summary.json"
    machine_path.write_text(
        json.dumps(machine, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    readme = packet / "README.md"
    readme.write_text(
        "# Official SAGE E19 reproduction evidence packet\n\n"
        "This packet preserves the failed E19 native-reproduction decision and "
        "the separately frozen discrepancy diagnostic. It does not amend E19, "
        "contact the authors, or include protected evidence.\n\n"
        f"- Official SAGE commit: `{spec.SAGE_GIT_COMMIT}`\n"
        f"- Official SAGE tree: `{spec.SAGE_GIT_TREE}`\n"
        f"- E19 source-manifest SHA-256: `{spec.E19_SOURCE_MANIFEST_SHA256}`\n"
        f"- E19 protocol SHA-256: `{spec.E19_PROTOCOL_SHA256}`\n"
        f"- Diagnostic snapshot: `{source_snapshot}`\n"
        f"- Diagnostic run root: `{run_root}`\n"
        f"- Diagnostic decision: `{audit['decision']}`\n"
        f"- Objective mismatch classes: `{audit['objective_mismatch_classes']}`\n\n"
        "The sealed run contains two exact repeats for each of five prespecified "
        "cells, ordered intermediate hashes, Cube cache keys and values, direct "
        "official-runtime parity, and PushT lossless-versus-JPEG transport "
        "quantification. Verify every adjacent `sha256.txt` before inspection.\n",
        encoding="utf-8",
    )
    return [machine_path, readme]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--e19-run-root", type=Path, default=Path(spec.E19_RUN_ROOT))
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)

    source_manifest_sha256 = sha256_file(args.snapshot / "SOURCE-MANIFEST.sha256")
    diagnostic_protocol_sha256 = sha256_file(
        args.snapshot / spec.PROTOCOL_FILENAME
    )

    repeatability_rows = []
    cube_traces = []
    internal_checks = []
    for sentinel in spec.SENTINELS:
        e19_path = e19_result_path(args.e19_run_root, sentinel)
        if sha256_file(e19_path) != sentinel.e19_result_sha256:
            raise RuntimeError(f"frozen E19 result mismatch: {e19_path}")
        e19_identity = result_identity(load_json(e19_path))
        repeats = []
        for repeat in spec.REPEATS:
            directory = (
                args.run_root
                / "sentinels"
                / f"s{sentinel.sentinel_id}"
                / f"r{repeat}"
            )
            verify_sha256_file(directory)
            result = load_json(directory / "results.json")
            trace = load_json(directory / "trace.json")
            bank = torch.load(
                directory / "comparison-bank.pt", map_location="cpu", weights_only=False
            )
            bank_content = {key: value for key, value in bank.items() if key != "content_sha256"}
            bank_ok = canonical_sha256(bank_content) == bank["content_sha256"]
            gate = trace_gate(trace, sentinel, repeat)
            identity_ok = all(
                (
                    trace.get("diagnostic_source_manifest_sha256")
                    == source_manifest_sha256,
                    trace.get("diagnostic_protocol_sha256")
                    == diagnostic_protocol_sha256,
                    trace.get("e19_source_manifest_sha256")
                    == spec.E19_SOURCE_MANIFEST_SHA256,
                    trace.get("e19_protocol_sha256") == spec.E19_PROTOCOL_SHA256,
                    trace.get("official_sage_commit") == spec.SAGE_GIT_COMMIT,
                    trace.get("official_sage_tree") == spec.SAGE_GIT_TREE,
                )
            )
            internal_checks.extend((bank_ok, gate["passed"], identity_ok))
            repeats.append(
                {
                    "result": result_identity(result),
                    "trace": trace,
                    "bank_sha256": bank["content_sha256"],
                    "trace_gate": gate,
                }
            )
            if sentinel.benchmark == "cube":
                cube_traces.append(trace)
        result_repeat_exact = repeats[0]["result"] == repeats[1]["result"]
        e19_outcome_exact = repeats[0]["result"] == e19_identity and repeats[1]["result"] == e19_identity
        trace_repeat_exact = repeats[0]["trace"]["events"] == repeats[1]["trace"]["events"]
        bank_repeat_exact = repeats[0]["bank_sha256"] == repeats[1]["bank_sha256"]
        passed = all(
            (
                result_repeat_exact,
                e19_outcome_exact,
                trace_repeat_exact,
                bank_repeat_exact,
                repeats[0]["trace_gate"]["passed"],
                repeats[1]["trace_gate"]["passed"],
            )
        )
        repeatability_rows.append(
            {
                "sentinel_id": sentinel.sentinel_id,
                "e19_array_id": sentinel.e19_array_id,
                "benchmark": sentinel.benchmark,
                "method": sentinel.method,
                "seed": sentinel.seed,
                "horizon": sentinel.horizon,
                "result_repeat_exact": result_repeat_exact,
                "e19_outcome_exact": e19_outcome_exact,
                "trace_repeat_exact": trace_repeat_exact,
                "bank_repeat_exact": bank_repeat_exact,
                "repeat_0_event_sha256": repeats[0]["trace"]["event_stream_sha256"],
                "repeat_1_event_sha256": repeats[1]["trace"]["event_stream_sha256"],
                "repeat_0_bank_sha256": repeats[0]["bank_sha256"],
                "repeat_1_bank_sha256": repeats[1]["bank_sha256"],
                "passed": passed,
            }
        )

    cube_cache = cube_cache_gate(cube_traces)
    comparison_dir = args.comparison.parent
    verify_sha256_file(comparison_dir)
    comparison = load_json(args.comparison)
    comparison_sha = sha256_file(args.comparison)
    comparison_identity_valid = all(
        (
            comparison.get("diagnostic_source_manifest_sha256")
            == source_manifest_sha256,
            comparison.get("diagnostic_protocol_sha256")
            == diagnostic_protocol_sha256,
            comparison.get("e19_source_manifest_sha256")
            == spec.E19_SOURCE_MANIFEST_SHA256,
            comparison.get("e19_protocol_sha256") == spec.E19_PROTOCOL_SHA256,
            comparison.get("official_sage_commit") == spec.SAGE_GIT_COMMIT,
            comparison.get("official_sage_tree") == spec.SAGE_GIT_TREE,
        )
    )
    comparison_valid = bool(
        comparison.get("transport_comparisons_valid")
        and comparison.get("runtime_bank_reconstruction_valid")
        and comparison_identity_valid
    )
    no_forbidden_read = all(
        (
            comparison.get("episode_executed") is False,
            comparison.get("official_sage_source_modified") is False,
            comparison.get("checkpoint_modified") is False,
            comparison.get("planner_parameter_modified") is False,
            comparison.get("expected_values_modified") is False,
            comparison.get("tolerance_modified") is False,
            comparison.get("manifest_modified") is False,
            comparison.get("e19_result_modified") is False,
            comparison.get("protected_metric_artifact_read") is False,
            comparison.get("e18_vs_sage_comparison_run") is False,
            comparison.get("d5_read") is False,
        )
    )
    internal_valid = all(internal_checks) and comparison_valid and no_forbidden_read
    mismatch_classes = []
    if not all(row["passed"] for row in repeatability_rows):
        mismatch_classes.append("exact_repeatability")
    if comparison.get("model_state_mismatch") or comparison.get("runtime_mismatch"):
        mismatch_classes.append("compatibility_vs_official_runtime")
    if not cube_cache["passed"]:
        mismatch_classes.append("cube_generated_goal_cache")
    if comparison.get("transport_mismatch"):
        mismatch_classes.append("pusht_jpeg_transport_elite_membership")

    uniquely_correctable = {
        "compatibility_vs_official_runtime",
        "cube_generated_goal_cache",
        "pusht_jpeg_transport_elite_membership",
    }
    e20_authorized = bool(
        internal_valid
        and len(mismatch_classes) == 1
        and mismatch_classes[0] in uniquely_correctable
    )
    if e20_authorized:
        decision = f"authorize_corrected_e20_for_{mismatch_classes[0]}"
    elif internal_valid and not mismatch_classes:
        decision = "prepare_author_evidence_no_objective_technical_mismatch"
    elif internal_valid:
        decision = "prepare_author_evidence_no_unique_e20_correction"
    else:
        decision = "diagnostic_invalid_stop_without_e20"

    audit = {
        "kind": "gdp_cem_e19_official_sage_discrepancy_audit",
        "e19_decision_preserved": "stop_native_reproduction_failed",
        "sentinel_count": len(spec.SENTINELS),
        "repeat_count": len(spec.REPEATS),
        "executed_run_count": len(spec.SENTINELS) * len(spec.REPEATS),
        "executed_episode_count": spec.EXPECTED_TOTAL_EPISODES,
        "sentinel_repeatability": repeatability_rows,
        "cube_cache": cube_cache,
        "comparison_sha256": comparison_sha,
        "comparison_identity_valid": comparison_identity_valid,
        "diagnostic_source_manifest_sha256": source_manifest_sha256,
        "diagnostic_protocol_sha256": diagnostic_protocol_sha256,
        "comparison": comparison,
        "internal_valid": internal_valid,
        "objective_mismatch_classes": mismatch_classes,
        "objective_mismatch_count": len(mismatch_classes),
        "e20_authorized": e20_authorized,
        "decision": decision,
        "expected_values_modified": False,
        "tolerance_modified": False,
        "manifest_modified": False,
        "e19_result_modified": False,
        "protected_metric_artifact_read": False,
        "e18_vs_sage_comparison_run": False,
        "d5_read": False,
    }

    repeatability_path = args.output / "sentinel-repeatability.tsv"
    with repeatability_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(repeatability_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(repeatability_rows)
    cube_path = args.output / "CUBE-CACHE-AUDIT.json"
    cube_path.write_text(
        json.dumps(cube_cache, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    audit_path = args.output / "DISCREPANCY-AUDIT.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    packet_files: list[Path] = []
    if internal_valid and not e20_authorized:
        packet_files = write_author_packet(
            output=args.output,
            audit=audit,
            comparison_sha256=comparison_sha,
            source_snapshot=args.snapshot,
            run_root=args.run_root,
        )

    files = [audit_path, cube_path, repeatability_path, *packet_files]
    with (args.output / "sha256.txt").open("x", encoding="utf-8") as stream:
        for path in sorted(files):
            stream.write(f"{sha256_file(path)}  {path.relative_to(args.output)}\n")
    if not internal_valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
