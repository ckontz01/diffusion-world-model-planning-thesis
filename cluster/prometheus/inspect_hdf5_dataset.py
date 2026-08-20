#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import h5py
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    datasets: dict[str, dict] = {}
    with h5py.File(args.dataset, "r") as handle:
        def visitor(name: str, obj) -> None:
            if isinstance(obj, h5py.Dataset):
                datasets[name] = {
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                    "chunks": list(obj.chunks) if obj.chunks is not None else None,
                    "compression": obj.compression,
                    "compression_opts": obj.compression_opts,
                    "storage_bytes": int(obj.id.get_storage_size()),
                }

        handle.visititems(visitor)

        by_basename = {Path(name).name: name for name in datasets}
        episode_name = next(
            (by_basename[name] for name in ("episode_idx", "ep_idx") if name in by_basename),
            None,
        )
        step_name = by_basename.get("step_idx")
        episode_summary = None
        if episode_name is not None:
            episode_ids = np.asarray(handle[episode_name][:]).reshape(-1)
            unique_ids, counts = np.unique(episode_ids, return_counts=True)
            episode_summary = {
                "episode_dataset": episode_name,
                "step_dataset": step_name,
                "num_rows": int(episode_ids.size),
                "num_episodes": int(unique_ids.size),
                "episode_id_min": int(unique_ids.min()),
                "episode_id_max": int(unique_ids.max()),
                "rows_per_episode": {
                    "min": int(counts.min()),
                    "max": int(counts.max()),
                    "mean": float(counts.mean()),
                    "median": float(np.median(counts)),
                    "p05": float(np.percentile(counts, 5)),
                    "p95": float(np.percentile(counts, 95)),
                },
            }
            if step_name is not None:
                step_idx = np.asarray(handle[step_name][:]).reshape(-1)
                episode_summary["step_index"] = {
                    "min": int(step_idx.min()),
                    "max": int(step_idx.max()),
                    "nan_count": int(np.count_nonzero(~np.isfinite(step_idx))),
                }

    result = {
        "status": "ok",
        "dataset": str(args.dataset.resolve()),
        "file_bytes": args.dataset.stat().st_size,
        "episode_summary": episode_summary,
        "datasets": datasets,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

