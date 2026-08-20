#!/usr/bin/env python3
"""Print shell-safe fields from the frozen task registry."""

from __future__ import annotations

import argparse
import json
import shlex

from acid_alternative.task_registry import TASKS, get_task_spec


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=tuple(TASKS))
    parser.add_argument("--format", choices=("shell", "json"), default="shell")
    args = parser.parse_args()
    payload = get_task_spec(args.task).to_dict()
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        shell_key = key.upper()
        shell_value = str(value)
        print(f"{shell_key}={shlex.quote(shell_value)}")


if __name__ == "__main__":
    main()
