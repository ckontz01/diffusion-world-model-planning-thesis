"""Frozen Le-WM benchmark identities for the matched three-task study."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

TaskName = Literal["pusht", "reacher", "cube"]


@dataclass(frozen=True)
class TaskSpec:
    task: TaskName
    eval_config_name: str
    dataset_name: str
    dataset_relative_path: str
    world_model_policy: str
    checkpoint_relative_path: str
    artifact_slug: str
    reachability_target: str
    i1_source_partition: str
    published_lewm_b0: float
    published_acid: float

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)


TASKS: dict[TaskName, TaskSpec] = {
    "pusht": TaskSpec(
        task="pusht",
        eval_config_name="pusht",
        dataset_name="pusht_expert_train",
        dataset_relative_path="pusht_expert_train.h5",
        world_model_policy="pusht/lewm_hf_22b330c",
        checkpoint_relative_path="pusht/lewm_hf_22b330c_object.ckpt",
        artifact_slug="lewm-hf-22b330c",
        reachability_target="pusht_task_state",
        i1_source_partition="P4",
        published_lewm_b0=0.96,
        published_acid=1.00,
    ),
    "reacher": TaskSpec(
        task="reacher",
        eval_config_name="reacher",
        dataset_name="dmc/reacher_random",
        dataset_relative_path="reacher.h5",
        world_model_policy="reacher/lewm",
        checkpoint_relative_path="reacher/lewm_object.ckpt",
        artifact_slug="lewm",
        reachability_target="temporal",
        i1_source_partition="P4",
        published_lewm_b0=0.76,
        published_acid=0.88,
    ),
    "cube": TaskSpec(
        task="cube",
        eval_config_name="cube",
        dataset_name="ogbench/cube_single_expert",
        dataset_relative_path="cube_single_expert.h5",
        world_model_policy="cube/lewm_hf_b0747c5",
        checkpoint_relative_path="cube/lewm_hf_b0747c5_object.ckpt",
        artifact_slug="lewm-hf-b0747c5",
        reachability_target="temporal",
        i1_source_partition="P4",
        published_lewm_b0=0.70,
        published_acid=0.74,
    ),
}


def get_task_spec(task: str) -> TaskSpec:
    try:
        return TASKS[task]  # type: ignore[index]
    except KeyError as error:
        raise ValueError(f"unknown benchmark task: {task!r}") from error
