#!/usr/bin/env python3
"""Run the frozen E14 Gate-B analyzer with NumPy-safe JSON serialization."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def json_dumps(value: Any, *args: Any, **kwargs: Any) -> str:
    kwargs.setdefault("default", json_default)
    return json.dumps(value, *args, **kwargs)


class JsonProxy:
    loads = staticmethod(json.loads)
    dumps = staticmethod(json_dumps)


def atomic_json(path: Path, value: Any) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(
                value,
                stream,
                indent=2,
                sort_keys=True,
                default=json_default,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def load_frozen_analyzer(path: Path) -> ModuleType:
    expected = os.environ.get("E14_ORIGINAL_ANALYZER_SHA256")
    if not expected or sha256_file(path) != expected:
        raise RuntimeError("frozen E14 Gate-B analyzer hash differs")
    module_spec = importlib.util.spec_from_file_location(
        "_e14_frozen_gate_b_analyzer", path
    )
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("could not load frozen E14 Gate-B analyzer")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    module.atomic_json = atomic_json
    module.json = JsonProxy
    return module


def main() -> None:
    original = os.environ.get("E14_ORIGINAL_ANALYZER")
    if not original:
        raise RuntimeError("E14_ORIGINAL_ANALYZER is required")
    module = load_frozen_analyzer(Path(original))
    module.main()


if __name__ == "__main__":
    main()
