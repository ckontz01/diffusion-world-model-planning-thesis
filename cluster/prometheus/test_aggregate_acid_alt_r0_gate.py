import json
from pathlib import Path

import pytest
from aggregate_acid_alt_r0_gate import main


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def write_episodes(path: Path, successes: list[int]) -> None:
    rows = ["eval_index\tepisode_id\tstart_step\tplanner_seed\tarm\tsuccess"]
    rows.extend(
        f"{index}\t{100 + index}\t0\t42\tb0\t{success}"
        for index, success in enumerate(successes)
    )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def invoke(monkeypatch, tmp_path: Path, acid_rate: float, accuracy: float) -> Path:
    shared = {
        "status": "ok",
        "episode_count": 2,
        "planner_seed": 42,
        "eval_manifest_sha256": "m",
        "dataset_sha256": "d",
        "world_model_checkpoint_sha256": "w",
    }
    b0_ep = tmp_path / "b0.tsv"
    write_episodes(b0_ep, [1, 0])
    b0 = tmp_path / "b0.json"
    write_json(
        b0,
        {
            **shared,
            "arm": "b0",
            "success_rate_fraction": 0.5,
            "episode_tsv": str(b0_ep),
        },
    )
    arguments = [
        "gate",
        "--b0-summary",
        str(b0),
        "--minimum-b0-rate",
        "0.4",
        "--expected-episodes",
        "2",
    ]
    successes = [1, int(acid_rate >= 1.0)]
    for offset, seed in enumerate((6101, 6102, 6103)):
        episode_path = tmp_path / f"acid-{seed}.tsv"
        write_episodes(episode_path, successes)
        summary = tmp_path / f"acid-{seed}.json"
        write_json(
            summary,
            {
                **shared,
                "arm": "acid",
                "success_rate_fraction": sum(successes) / 2,
                "episode_tsv": str(episode_path),
                "scorer_training_seed": seed,
            },
        )
        training = tmp_path / f"train-{seed}.json"
        write_json(
            training,
            {
                "status": "ok",
                "model": "acid",
                "condition": "true",
                "seed": seed,
                "best_validation_loss": 0.1 + offset,
                "final_validation": {"correct_action_pairwise_accuracy": accuracy},
            },
        )
        arguments.extend(["--acid-summary", str(summary)])
        arguments.extend(["--acid-training-summary", str(training)])
    output = tmp_path / "gate.json"
    arguments.extend(["--output", str(output)])
    monkeypatch.setattr("sys.argv", arguments)
    main()
    return output


def test_gate_passes_matched_inputs(monkeypatch, tmp_path):
    output = invoke(monkeypatch, tmp_path, acid_rate=1.0, accuracy=0.75)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "pass"
    assert all(result["gates"].values())


def test_gate_fails_below_chance_action_recovery(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="4"):
        invoke(monkeypatch, tmp_path, acid_rate=1.0, accuracy=0.5)
    result = json.loads((tmp_path / "gate.json").read_text(encoding="utf-8"))
    assert result["status"] == "fail"
    assert not result["gates"]["acid_correct_action_recovery"]
