#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path

import imageio.v2 as imageio


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--expected-episodes", type=int, default=8)
    args = parser.parse_args()

    result = args.output_dir / "hi_pusht_checkpoint_smoke_results.txt"
    episodes = args.output_dir / "hi_pusht_checkpoint_smoke_results_episodes.tsv"
    if not result.is_file() or result.stat().st_size == 0:
        raise SystemExit(f"missing or empty result file: {result}")
    if not episodes.is_file() or episodes.stat().st_size == 0:
        raise SystemExit(f"missing or empty episode manifest: {episodes}")

    result_text = result.read_text(encoding="utf-8")
    for marker in ("==== CONFIG ====", "==== DETERMINISM ====", "==== RESULTS ===="):
        if marker not in result_text:
            raise SystemExit(f"result file lacks marker: {marker}")

    with episodes.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != args.expected_episodes:
        raise SystemExit(
            f"expected {args.expected_episodes} episode rows, found {len(rows)}"
        )
    if [int(row["eval_index"]) for row in rows] != list(range(args.expected_episodes)):
        raise SystemExit("episode eval_index values are not contiguous from zero")

    videos = []
    for row in rows:
        video = Path(row["video_path"])
        if video.parent.resolve() != args.output_dir.resolve():
            raise SystemExit(f"video escapes output directory: {video}")
        if not video.is_file() or video.stat().st_size == 0:
            raise SystemExit(f"missing or empty video: {video}")
        reader = imageio.get_reader(video)
        try:
            frame = reader.get_data(0)
            metadata = reader.get_meta_data()
        finally:
            reader.close()
        if frame.ndim != 3 or frame.shape[2] not in (3, 4):
            raise SystemExit(f"unexpected first-frame shape for {video}: {frame.shape}")
        videos.append(
            {
                "name": video.name,
                "bytes": video.stat().st_size,
                "first_frame_shape": list(frame.shape),
                "fps": metadata.get("fps"),
                "duration": metadata.get("duration"),
            }
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "episode_rows": len(rows),
                "videos": videos,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
