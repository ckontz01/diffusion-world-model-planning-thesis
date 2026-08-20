from __future__ import annotations

import csv
from pathlib import Path

from acid_alternative.create_eval_manifests import find_legacy_pairs


def test_missing_legacy_root_is_recorded_but_not_fatal(tmp_path: Path):
    missing = tmp_path / "historical-results-not-present"

    pairs, sources = find_legacy_pairs([missing], maximum_h5_bytes=1024)

    assert pairs == set()
    assert sources == [
        {
            "path": str(missing),
            "status": "missing_optional_root",
            "pairs_found": 0,
        }
    ]


def test_other_task_path_tokens_are_not_treated_as_contamination(tmp_path: Path):
    legacy_root = tmp_path / "reacher-parent"
    pusht = legacy_root / "pusht-history" / "episodes.tsv"
    cube = legacy_root / "cube-history" / "episodes.tsv"
    for path, episode in ((pusht, 11), (cube, 22)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=("episode_id", "start_step"), delimiter="\t"
            )
            writer.writeheader()
            writer.writerow({"episode_id": episode, "start_step": 3})

    pairs, sources = find_legacy_pairs(
        [legacy_root],
        maximum_h5_bytes=1024,
        excluded_path_tokens=("cube", "reacher"),
    )

    assert pairs == {(11, 3)}
    assert any(
        source.get("status") == "excluded_other_task_paths"
        and source["files_skipped"] == 1
        for source in sources
    )
