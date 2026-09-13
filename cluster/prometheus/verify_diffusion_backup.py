"""Rehash every indexed completed shard, including previously verified shards.

Unlike the incremental copier, this never trusts index membership as evidence
that bytes still match. It does not parse episode or RESULT outcome payloads.
No copies, deletions, network access, or repairs are performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

from diffusion_bottleneck import (
    LOCK_SHA, IntegrityError, checked_child, read_json, require,
    require_sha, sha256, write_report,
)
from diffusion_bottleneck_traces import expected_tasks, sealed_stage

STUDY = "/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5"


def recheck_task(local: Path, key: str, record: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    require(key == f'stage-0/task-{expected["task"]:04d}', "Unexpected backup key")
    require(record["path"] == key, "Index path mismatch")
    task_root = checked_child(local, key)
    require_sha(task_root / "DONE.json", record["done_sha256"])
    done = read_json(task_root / "DONE.json")
    require(done["task"] == expected, "Wrong indexed task metadata")
    require(done["result_sha256"] == record["result_sha256"], "DONE/index disagreement")
    results = task_root / "results"
    require_sha(results / "RESULT.json", record["result_sha256"])
    names = set()
    bytes_verified = 0
    for line in (results / "sha256.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        require(len(parts) == 2, "Malformed checksum line")
        digest, name = parts
        require(bool(re.fullmatch(r"RESULT\.json|episode-[0-9]{5}-h(?:75|150)\.(?:json|npz)", name)), "Unexpected sealed filename")
        require(name not in names, "Duplicate sealed filename")
        names.add(name)
        path = checked_child(results, name)
        require(not (results / name).is_symlink(), "Symlinked payload")
        require_sha(path, digest)
        bytes_verified += path.stat().st_size
    expected_names = {"RESULT.json"} | {
        f'episode-{i:05d}-h{h}.{ext}'
        for i in range(expected["begin"], expected["end"])
        for h in (75, 150) for ext in ("json", "npz")
    }
    require(names == expected_names, "Incomplete or extra payload inventory")
    return {"files_rehashed": len(names) + 1, "payload_bytes_rehashed": bytes_verified,
            "done_sha256": record["done_sha256"], "result_sha256": record["result_sha256"]}


def recheck(local: Path, source_study: Path | None = None) -> dict[str, Any]:
    index_path = local / "COMPLETED-SHARD-BACKUP.json"
    index = read_json(index_path)
    require(index.get("study") == STUDY, "Unexpected study identity")
    shards = index["shards"]
    require(isinstance(shards, dict), "Invalid shard index")
    tasks = {f'stage-0/task-{t["task"]:04d}': t for t in expected_tasks()}
    require(set(shards) <= set(tasks), "Index contains unknown or unevaluated-stage entries")
    source_records = {}
    if source_study is not None:
        source_files, _ = sealed_stage(source_study)
        for path, task in source_files:
            key = f'stage-0/task-{task["task"]:04d}'
            done = path.parent.parent / "DONE.json"
            source_records[key] = (sha256(done), sha256(path), sha256(path.parent / "sha256.txt"))
    passed, errors = {}, {}
    for key, record in sorted(shards.items()):
        try:
            info = recheck_task(local, key, record, tasks[key])
            if source_study is not None:
                triple = (info["done_sha256"], info["result_sha256"],
                          sha256(local / key / "results" / "sha256.txt"))
                require(triple == source_records[key], "Canonical-source identity mismatch")
            passed[key] = info
        except (OSError, ValueError, KeyError) as exc:
            errors[key] = {"type": type(exc).__name__, "message": str(exc)}
    missing = sorted(set(tasks) - set(shards))
    complete = not missing and not errors and len(passed) == 450
    return {
        "scope": "Byte-level revalidation of all indexed stage-0 shards; no outcomes interpreted",
        "index_sha256": sha256(index_path), "indexed_shards": len(shards),
        "expected_shards": 450, "rehashed_shards": len(passed),
        "missing_shards": missing, "errors": errors,
        "payload_bytes_rehashed": sum(v["payload_bytes_rehashed"] for v in passed.values()),
        "complete_local_shard_copy": complete,
        "canonical_source_compared": source_study is not None,
        "complete_source_matched_backup": complete and source_study is not None,
        "reference_collection_backup_verified": False,
        "note": "The 6,000 reference trajectories and archived analyses require separate inventory checks. Local consistency alone is not canonical-source certification.",
        "no_input_files_changed": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-study", type=Path, required=True)
    parser.add_argument("--source-study", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        roots = (args.local_study,) + ((args.source_study,) if args.source_study is not None else ())
        for root in roots:
            require(root.resolve() not in args.out.resolve().parents, "Output inside source/backup tree")
        report = recheck(args.local_study, args.source_study)
        write_report(args.out, report, roots)
        print(json.dumps({"rehashed": report["rehashed_shards"], "errors": len(report["errors"]),
                          "complete": report["complete_local_shard_copy"]}))
        return 2 if report["errors"] else (0 if report["complete_local_shard_copy"] else 3)
    except (OSError, ValueError, KeyError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
