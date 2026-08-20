#!/usr/bin/env python3
"""Synthetic invariants for the GDP-CEM 25-step cache join."""

from __future__ import annotations

import numpy as np

from build_goal_conditioned_action_sequence_cache import assemble_sequences


def main() -> None:
    lengths = (31, 28)
    episodes = np.concatenate(
        [np.full(length - 5, index, dtype=np.int64) for index, length in enumerate(lengths)]
    )
    steps = np.concatenate(
        [np.arange(length - 5, dtype=np.int64) for length in lengths]
    )
    offsets = np.asarray((0, lengths[0]), dtype=np.int64)
    source = np.concatenate(
        [offset + np.arange(length - 5) for offset, length in zip(offsets, lengths)]
    ).astype(np.int64)
    target = source + 5
    roles = np.concatenate(
        [
            np.full(lengths[0] - 5, 0, dtype=np.uint8),
            np.full(lengths[1] - 5, 1, dtype=np.uint8),
        ]
    )
    primitive = np.arange(len(source) * 10, dtype=np.float32).reshape(len(source), 10)
    result = assemble_sequences(
        source_index=source,
        target_index=target,
        episode=episodes,
        step=steps,
        role=roles,
        action=primitive,
    )
    if len(result["source_index"]) != (lengths[0] - 25) + (lengths[1] - 25):
        raise RuntimeError("GDP-CEM synthetic sequence count differs")
    if not np.all(result["goal_index"] - result["source_index"] == 25):
        raise RuntimeError("GDP-CEM synthetic goal offset differs")
    first = result["action"][0]
    expected = np.stack([primitive[offset] for offset in (0, 5, 10, 15, 20)])
    if not np.array_equal(first, expected):
        raise RuntimeError("GDP-CEM action-block join differs")
    boundary = lengths[0] - 25
    if result["episode_idx"][boundary] != 1 or result["step_idx"][boundary] != 0:
        raise RuntimeError("GDP-CEM synthetic episode boundary differs")

    broken = steps.copy()
    broken[3] += 1
    try:
        assemble_sequences(
            source_index=source,
            target_index=target,
            episode=episodes,
            step=broken,
            role=roles,
            action=primitive,
        )
    except RuntimeError:
        pass
    else:
        raise RuntimeError("GDP-CEM accepted noncontiguous transition steps")
    print("GDP-CEM sequence-cache tests: ok")


if __name__ == "__main__":
    main()

