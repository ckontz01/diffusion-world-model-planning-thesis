#!/usr/bin/env python3
"""Run the frozen v2 trainer for the authorized v3 seeds 6102 and 6103.

The base trainer is hash-checked and adapted in memory.  This keeps the
training algorithm byte-auditable: the only executable substitutions are the
seed guard and two provenance labels; the protocol hash is rebound before
``main`` is called.
"""

from __future__ import annotations

import hashlib
import sys
import types
from pathlib import Path


EXPECTED_BASE_TRAINER_SHA256 = (
    "871ebc12c4af778031155f78b060e017c7060775d3f2e32bb49dc986925a52ad"
)
EXPECTED_PROTOCOL_SHA256 = (
    "c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_base_source(argv: list[str]) -> tuple[Path, list[str]]:
    flag = "--base-trainer-source"
    if argv.count(flag) != 1:
        raise SystemExit(f"exactly one {flag} is required")
    index = argv.index(flag)
    if index + 1 >= len(argv):
        raise SystemExit(f"{flag} requires a path")
    path = Path(argv[index + 1])
    filtered = argv[:index] + argv[index + 2 :]
    return path, filtered


def load_adapted_trainer(path: Path) -> types.ModuleType:
    if not path.is_file():
        raise FileNotFoundError(path)
    if sha256_file(path) != EXPECTED_BASE_TRAINER_SHA256:
        raise RuntimeError("base residual-diffusion trainer hash mismatch")
    source = path.read_text(encoding="utf-8")
    replacements = (
        (
            '    if args.seed != 6101:\n'
            '        raise RuntimeError("this frozen pilot permits only seed 6101")',
            '    if args.seed not in (6102, 6103):\n'
            '        raise RuntimeError("the frozen v3 expansion permits only seeds 6102 and 6103")',
        ),
        (
            '"kind": "residual_diffusion_x0_pilot_training"',
            '"kind": "residual_diffusion_x0_multiseed_d2_training"',
        ),
        (
            '"analysis_role": "P1-only post-v1 architectural development"',
            '"analysis_role": "P1-only frozen v3 multi-seed expansion"',
        ),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise RuntimeError(f"base trainer adaptation anchor changed: {old!r}")
        source = source.replace(old, new)
    module = types.ModuleType("frozen_v3_residual_diffusion_trainer")
    module.__file__ = str(path)
    module.__package__ = None
    exec(compile(source, str(path), "exec"), module.__dict__)
    module.EXPECTED_PROTOCOL_SHA256 = EXPECTED_PROTOCOL_SHA256
    return module


def main() -> None:
    base_path, filtered = extract_base_source(sys.argv[1:])
    module = load_adapted_trainer(base_path)
    original = sys.argv
    try:
        sys.argv = [original[0], *filtered]
        module.main()
    finally:
        sys.argv = original


if __name__ == "__main__":
    main()
