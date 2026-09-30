from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def resolve_policy_checkpoint(policy: str, stablewm_home: Path) -> Path:
    """Mirror stable-worldmodel checkpoint resolution for lineage assertions."""

    run_path = Path(policy)
    if not run_path.exists():
        run_path = stablewm_home / policy
    if run_path.is_dir():
        candidates = sorted(
            run_path.glob("*_object.ckpt"),
            key=lambda path: path.stat().st_ctime,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError(f"no object checkpoint in {run_path}")
        return candidates[0].resolve()
    candidate = Path(f"{run_path}_object.ckpt")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate.resolve()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    if temporary.exists():
        raise FileExistsError(temporary)
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)
