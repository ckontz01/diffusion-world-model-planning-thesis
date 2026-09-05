#!/usr/bin/env python3
"""Localize exposed E19 repeat artifacts and replay fixed banks, never episodes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

import gdp_cem_e19_l1_tools as audit
import gdp_cem_e19_d2_specs as d2
import gdp_cem_e19_discrepancy_specs as spec
import gdp_cem_e19_specs as e19
from trace_gdp_cem_e19_discrepancy import canonical_sha256, sha256_file, value_record


PARENT = Path(d2.PARENT_SNAPSHOT)
RAW = Path(d2.PARENT_RUN_ROOT)
ROOT = Path("/lustreFS/data/superworld/ckontzias/thesis")
ALLOWED_RAW = {"results.json", "cell-status.json", "trace.json", "comparison-bank.pt"}


def verify_inventory(directory: Path, allowed: set[str]) -> dict[str, str]:
    entries = {}
    for line in (directory / "sha256.txt").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        if name not in allowed or name in entries:
            raise RuntimeError(f"non-allowlisted checksum entry: {name}")
        if sha256_file(directory / name) != digest:
            raise RuntimeError(f"checksum mismatch: {directory / name}")
        entries[name] = digest
    if set(entries) != allowed:
        raise RuntimeError("incomplete inventory")
    return entries


def dump_sealed(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(audit.json_safe(payload), stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    path.chmod(0o444)


def bank_path(sentinel, repeat):
    return RAW / "sentinels" / f"s{sentinel.sentinel_id}" / f"r{repeat}" / "comparison-bank.pt"


def read_bank(sentinel, repeat):
    bank = torch.load(bank_path(sentinel, repeat), map_location="cpu", weights_only=False)
    content = {key: value for key, value in bank.items() if key != "content_sha256"}
    if canonical_sha256(content) != bank["content_sha256"]:
        raise RuntimeError("historical bank content hash failed")
    for key in ("sentinel_id", "benchmark", "method", "seed", "horizon"):
        if bank[key] != getattr(sentinel, key):
            raise RuntimeError(f"bank identity mismatch: {key}")
    return bank


def bank_comparison(a, b):
    fields = []
    def visit(x, y, path):
        rx, ry = audit.json_safe(value_record(x)), audit.json_safe(value_record(y))
        if isinstance(rx, dict) and rx.get("kind") in {"torch", "numpy"}:
            if rx == ry:
                row = {"exact": True, "record": rx}
            elif (torch.is_tensor(x) and torch.is_tensor(y)) or (
                    isinstance(x, np.ndarray) and isinstance(y, np.ndarray)
                    and x.dtype.kind not in "OSU" and y.dtype.kind not in "OSU"):
                row = audit.tensor_delta(x, y)
            else:
                row = {"exact": False, "left": rx, "right": ry}
            fields.append({"path": path, **row})
        elif isinstance(x, dict) and isinstance(y, dict):
            for key in sorted(x.keys() | y.keys()):
                visit(x.get(key), y.get(key), f"{path}.{key}" if path else key)
        elif rx != ry:
            fields.append({"path": path, "exact": False, "left": rx, "right": ry})
    visit({k: v for k, v in a.items() if k != "content_sha256"},
          {k: v for k, v in b.items() if k != "content_sha256"}, "")
    return {"all_field_comparisons": fields,
            "differing_paths": [row["path"] for row in fields if not row["exact"]],
            "opaque_paths_left": audit.opaque_paths(value_record(a)),
            "opaque_paths_right": audit.opaque_paths(value_record(b)),
            "all_fields_except_render_time_exact": all(row["exact"] or row["path"] == "info.render_time" for row in fields)}


def localize(output):
    from analyze_gdp_cem_e19_discrepancy import e19_result_path
    if sha256_file(PARENT / "SOURCE-MANIFEST.sha256") != d2.PARENT_SOURCE_MANIFEST_SHA256:
        raise RuntimeError("parent source manifest differs")
    if sha256_file(PARENT / spec.PROTOCOL_FILENAME) != d2.PARENT_PROTOCOL_SHA256:
        raise RuntimeError("parent protocol differs")
    inventories = {}
    for sentinel in spec.SENTINELS:
        for repeat in (0, 1):
            directory = bank_path(sentinel, repeat).parent
            inventories[f"s{sentinel.sentinel_id}/r{repeat}"] = verify_inventory(directory, ALLOWED_RAW)
    rows = []
    for sentinel in spec.SENTINELS:
        sid = sentinel.sentinel_id
        traces, results = [], []
        for repeat in (0, 1):
            directory = bank_path(sentinel, repeat).parent
            trace = json.loads((directory / "trace.json").read_text())
            if (canonical_sha256(trace["events"]) != trace["event_stream_sha256"]
                    or trace["diagnostic_source_manifest_sha256"] != d2.PARENT_SOURCE_MANIFEST_SHA256
                    or trace["diagnostic_protocol_sha256"] != d2.PARENT_PROTOCOL_SHA256
                    or trace["repeat"] != repeat
                    or trace["sentinel"]["sentinel_id"] != sid):
                raise RuntimeError("trace identity/content failed")
            traces.append(trace)
            results.append(json.loads((directory / "results.json").read_text()))
        old_path = e19_result_path(Path(spec.E19_RUN_ROOT), sentinel)
        if sha256_file(old_path) != sentinel.e19_result_sha256:
            raise RuntimeError("prespecified E19 baseline result hash failed")
        original_result = json.loads(old_path.read_text())
        banks = [read_bank(sentinel, r) for r in (0, 1)]
        row = {"sentinel_id": sid, "benchmark": sentinel.benchmark, "method": sentinel.method,
               "horizon": sentinel.horizon, "seed": sentinel.seed,
               "trace": audit.trace_comparison(*traces), "bank": bank_comparison(*banks),
               "repeat_outcomes": audit.outcome_comparison(*results),
               "repeat0_vs_original_e19": audit.outcome_comparison(original_result, results[0]),
               "repeat1_vs_original_e19": audit.outcome_comparison(original_result, results[1])}
        rows.append(row)
        print(json.dumps({"localized_sentinel": sid, "bank_differing_paths": row["bank"]["differing_paths"],
                          "first_non_time_trace_difference": row["trace"]["first_non_render_time_differences"][:1],
                          "episode_flips": row["repeat_outcomes"]["changed_episode_count"]}), flush=True)
        del traces, banks
    report = {"kind": "e19_l1_exposed_artifact_localization", "inventories": inventories, "sentinels": rows,
              "new_episode_count": 0, "parent_decisions_modified": False, "protected_data_read": False}
    dump_sealed(output / "LOCALIZATION.json", report)


def official_fit(sentinel):
    if sentinel.benchmark == "pusht":
        from sage.eval import pusht as module
    else:
        from sage.eval import cube as module
    return (module.GaussianCEM if sentinel.method in {"base_cem", "lewm_generator"}
            else module.PriorInitializedCEM)._fit


def fit_replay(sentinel, repeat, bank, device):
    candidates, costs = bank["candidates"].to(device), bank["costs"].to(device)
    clamp = sentinel.benchmark == "cube" or sentinel.method in {"base_cem", "lewm_generator"}
    before = torch.cuda.get_rng_state().clone()
    mean, std, values, indices = audit.observe_fit(official_fit(sentinel), candidates, costs)
    if sentinel.benchmark == "pusht" and clamp:
        std = std.clamp_min(1e-6)
    trace = json.loads((bank_path(sentinel, repeat).parent / "trace.json").read_text())
    event = next(row for row in trace["events"] if row["kind"] == "cem_fit" and row["plan_index"] == 0 and row["round_index"] == 0)
    recorded = bank["elite_indices"].to(device)
    reconstructed_mean, reconstructed_std = audit.selected_distribution(candidates, recorded, clamp=clamp)
    result = {"sentinel_id": sentinel.sentinel_id, "repeat": repeat,
              "exact_original_topk_calls_captured": 1,
              "recorded_vs_actual_elites": audit.elite_rows(recorded, indices),
              "recorded_elites_reconstruct_replay_mean": torch.equal(mean, reconstructed_mean),
              "recorded_elites_reconstruct_replay_std": torch.equal(std, reconstructed_std),
              "recorded_elites_reconstruct_historical_mean": value_record(reconstructed_mean) == event["mean"],
              "recorded_elites_reconstruct_historical_std": value_record(reconstructed_std) == event["effective_std"],
              "replay_matches_historical_mean": value_record(mean) == event["mean"],
              "replay_matches_historical_std": value_record(std) == event["effective_std"],
              "replay_matches_historical_elite_costs": value_record(values) == event["elite_costs"],
              "boundary": audit.boundary_rows(costs),
              "global_cuda_rng_unchanged": torch.equal(before, torch.cuda.get_rng_state())}
    return result


def replay(output):
    import compare_gdp_cem_e19_discrepancy as comparison
    if not torch.cuda.is_available() or not torch.__version__.startswith("2.5.1"):
        raise RuntimeError("requires pinned CUDA PyTorch 2.5.1 environment")
    device = torch.device("cuda:0")
    if torch.cuda.get_device_name() != "NVIDIA RTX 6000 Ada Generation":
        raise RuntimeError("GPU differs from E19 diagnostic")
    comparison_dir = RAW / "comparison"
    verify_inventory(comparison_dir, {"COMPARISON-AUDIT.json"})
    previous = json.loads((comparison_dir / "COMPARISON-AUDIT.json").read_text())
    models = {}
    model_records = {}
    for task in ("pusht", "cube"):
        object_path = ROOT / "data/stablewm" / comparison.OBJECT_FILES[task]
        if sha256_file(object_path) != e19.TASKS[task]["e18_object_sha256"]:
            raise RuntimeError("exact compatibility checkpoint differs")
        models[task] = comparison.load_compat(object_path).to(device).to(torch.bfloat16)
        model_records[task] = comparison.state_record(models[task])

    fits, fixed_costs = [], []
    for sentinel in spec.SENTINELS:
        for repeat in (0, 1):
            bank = read_bank(sentinel, repeat)
            if "candidates" not in bank:
                fixed_costs.append({"sentinel_id": sentinel.sentinel_id, "repeat": repeat,
                                    "status": "not_applicable_prior_top_has_no_historical_cost_tensor"})
                continue
            fits.append(fit_replay(sentinel, repeat, bank, device))
            model = models[sentinel.benchmark]
            costs = [comparison.score_fixed_bank(task=sentinel.benchmark, model=model, info=bank["info"],
                     candidates=bank["candidates"], goal_latent=bank["actual_local_goal"].to(device), device=device).cpu()
                     for _ in range(2)]
            fixed_costs.append({"sentinel_id": sentinel.sentinel_id, "repeat": repeat,
                                "two_replays": audit.tensor_delta(*costs),
                                "replay_vs_historical": audit.tensor_delta(bank["costs"].float(), costs[0])})
            print(json.dumps({"replayed_fixed_bank": sentinel.sentinel_id, "repeat": repeat,
                              "costs_exact": fixed_costs[-1]["replay_vs_historical"]["exact"]}), flush=True)

    transport = []
    for sentinel in spec.SENTINELS[:2]:
        bank = read_bank(sentinel, 0)
        manifest_path = PARENT / "official-sage/data/manifests/pusht" / f"seed{sentinel.seed}" / f"h{sentinel.horizon}.json"
        manifest = json.loads(manifest_path.read_text())
        images = comparison.load_manifest_images(manifest=manifest, horizon=sentinel.horizon,
            hdf5_path=ROOT / "data/stablewm/pusht_expert_train.h5",
            lance_path=Path(spec.E19_RUN_ROOT) / "preparation/pusht_expert_train.lance")
        h5_start, h5_goal, jpeg_start, jpeg_goal = images
        jpeg_info = comparison.replace_first_plan_images(bank["info"], jpeg_start, jpeg_goal)
        lossless_info = comparison.replace_first_plan_images(bank["info"], h5_start, h5_goal)
        jpeg_h, jpeg_g, jpeg_cost = comparison.score_pusht_variant(model=models["pusht"], info=jpeg_info, candidates=bank["candidates"], device=device)
        lossless_h, lossless_g, lossless_cost = comparison.score_pusht_variant(model=models["pusht"], info=lossless_info, candidates=bank["candidates"], device=device)
        old = next(row for row in previous["pusht_transport_comparisons"] if row["sentinel_id"] == sentinel.sentinel_id)
        checks = {"jpeg_cost_matches_bank": torch.equal(jpeg_cost.cpu(), bank["costs"].float()),
                  "jpeg_cost_matches_prior_comparison": value_record(jpeg_cost) == old["jpeg_costs"],
                  "lossless_cost_matches_prior_comparison": value_record(lossless_cost) == old["lossless_costs"],
                  "jpeg_history_matches_prior_comparison": value_record(jpeg_h) == old["jpeg_history_latents"],
                  "lossless_history_matches_prior_comparison": value_record(lossless_h) == old["lossless_history_latents"]}
        candidates = bank["candidates"].to(device)
        j_mean, j_std, _, j_elites = audit.observe_fit(official_fit(sentinel), candidates, jpeg_cost)
        l_mean, l_std, _, l_elites = audit.observe_fit(official_fit(sentinel), candidates, lossless_cost)
        if sentinel.method == "base_cem":
            j_std, l_std = j_std.clamp_min(1e-6), l_std.clamp_min(1e-6)
        per_environment = []
        for i, (elite, j_boundary, l_boundary) in enumerate(zip(audit.elite_rows(j_elites, l_elites), audit.boundary_rows(jpeg_cost), audit.boundary_rows(lossless_cost))):
            per_environment.append({**elite, "manifest_record": manifest["records"][i],
                                    "jpeg_boundary": j_boundary, "lossless_boundary": l_boundary,
                                    "fitted_mean_delta": audit.tensor_delta(j_mean[i:i+1], l_mean[i:i+1]),
                                    "fitted_std_delta": audit.tensor_delta(j_std[i:i+1], l_std[i:i+1])})
        transport.append({"sentinel_id": sentinel.sentinel_id, "method": sentinel.method,
                          "reconstruction_checks": checks, "comparison_valid": all(checks.values()),
                          "per_environment": per_environment,
                          "candidate_bank_unchanged": True,
                          "history_latent_delta": audit.tensor_delta(jpeg_h, lossless_h),
                          "goal_latent_delta": audit.tensor_delta(jpeg_g, lossless_g),
                          "cost_delta": audit.tensor_delta(jpeg_cost, lossless_cost),
                          "fitted_mean_delta": audit.tensor_delta(j_mean, l_mean),
                          "fitted_std_delta": audit.tensor_delta(j_std, l_std),
                          "interpretation": "Encoding sensitivity only; author representation and success effect unknown."})
        print(json.dumps({"transport_localized": sentinel.sentinel_id, "comparison_valid": all(checks.values())}), flush=True)
    states_unchanged = {task: model_records[task] == comparison.state_record(model) for task, model in models.items()}
    dump_sealed(output / "FIXED-BANK-REPLAY.json", {"kind": "e19_l1_fixed_bank_replay", "torch": torch.__version__,
                 "gpu": torch.cuda.get_device_name(), "fit_replays": fits, "fixed_cost_replays": fixed_costs,
                 "transport": transport, "checkpoint_states_unchanged": states_unchanged,
                 "new_episode_count": 0, "new_candidate_sampling": False,
                 "no_full_grid_authorization": True, "protected_data_read": False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / "experiments/gdp-cem-e19-l1") or args.output.exists():
        raise ValueError("requires a fresh E19-L1 output namespace")
    torch.set_num_threads(8)
    with torch.inference_mode():
        localize(args.output)
        replay(args.output)
    inventory = args.output / "sha256.txt"
    with inventory.open("x") as stream:
        for path in sorted(args.output.glob("*.json")):
            stream.write(f"{sha256_file(path)}  {path.name}\n")
    inventory.chmod(0o444)
    print("E19-L1 complete; no episode executed", flush=True)


if __name__ == "__main__":
    main()
