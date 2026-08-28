#!/usr/bin/env python3
"""Create the disclosed PushT Lance transport and seal E19 inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import gdp_cem_e19_specs as spec


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sage-root", type=Path, required=True)
    parser.add_argument("--pusht-hdf5", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    output = args.output_root.resolve()
    if output.exists():
        raise FileExistsError(output)
    checkpoint_root = args.checkpoint_root.resolve()
    for entry in spec.CHECKPOINTS.values():
        path = checkpoint_root / entry["filename"]
        if path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"official SAGE checkpoint mismatch: {path}")
    if sha256_file(args.pusht_hdf5) != spec.TASKS["pusht"]["dataset_sha256"]:
        raise RuntimeError("PushT source HDF5 hash mismatch")

    output.mkdir(parents=True)
    lance_path = output / "pusht_expert_train.lance"
    from stable_worldmodel.data import convert

    convert(
        str(args.pusht_hdf5),
        str(lance_path),
        dest_format="lance",
        progress=True,
        mode="error",
        jpeg_quality=95,
    )
    if not lance_path.is_dir():
        raise RuntimeError("PushT Lance conversion did not create a directory")

    lance_files = sorted(path for path in lance_path.rglob("*") if path.is_file())
    with (output / "lance-sha256.txt").open("x", encoding="utf-8") as stream:
        for path in lance_files:
            stream.write(f"{sha256_file(path)}  {path.relative_to(output)}\n")
    checkpoint_rows = []
    for key, entry in spec.CHECKPOINTS.items():
        path = checkpoint_root / entry["filename"]
        checkpoint_rows.append(
            {
                "key": key,
                "filename": entry["filename"],
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = {
        "kind": "gdp_cem_e19_official_sage_input_preparation",
        "status": "passed",
        "sage_git_commit": spec.SAGE_GIT_COMMIT,
        "sage_hf_repo": spec.SAGE_HF_REPO,
        "sage_hf_revision": spec.SAGE_HF_REVISION,
        "checkpoints": checkpoint_rows,
        "pusht_hdf5": {
            "path": str(args.pusht_hdf5),
            "bytes": args.pusht_hdf5.stat().st_size,
            "sha256": sha256_file(args.pusht_hdf5),
        },
        "pusht_lance": {
            "path": str(lance_path),
            "file_count": len(lance_files),
            "bytes": sum(path.stat().st_size for path in lance_files),
            "tree_manifest_sha256": sha256_file(output / "lance-sha256.txt"),
            "conversion": (
                "pinned official stable_worldmodel.data.convert; "
                "LanceWriter; mode=error; jpeg_quality=95"
            ),
        },
        "runtime": {"python": sys.version, "python_executable": sys.executable},
        "scientific_sage_modification": False,
        "performance_metric_read": False,
        "d5_read": False,
    }
    (output / "PREPARATION.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output / "sha256.txt").open("x", encoding="utf-8") as stream:
        for path in (output / "PREPARATION.json", output / "lance-sha256.txt"):
            stream.write(f"{sha256_file(path)}  {path.name}\n")
        for row in checkpoint_rows:
            path = checkpoint_root / row["filename"]
            stream.write(f"{row['sha256']}  {path}\n")
    os.sync()


if __name__ == "__main__":
    main()
