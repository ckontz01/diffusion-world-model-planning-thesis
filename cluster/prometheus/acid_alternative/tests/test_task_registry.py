from acid_alternative.task_registry import TASKS, get_task_spec


def test_registry_locks_all_acid_lewm_tasks_and_canonical_dataset_paths():
    assert set(TASKS) == {"pusht", "reacher", "cube"}
    assert {spec.i1_source_partition for spec in TASKS.values()} == {"P4"}
    assert get_task_spec("pusht").dataset_relative_path == "pusht_expert_train.h5"
    assert get_task_spec("reacher").dataset_relative_path == "reacher.h5"
    assert (
        get_task_spec("cube").dataset_relative_path == "cube_single_expert.h5"
    )


def test_registry_locks_published_lewm_and_acid_table_values():
    expected = {
        "pusht": (0.96, 1.00),
        "reacher": (0.76, 0.88),
        "cube": (0.70, 0.74),
    }
    assert {
        task: (spec.published_lewm_b0, spec.published_acid)
        for task, spec in TASKS.items()
    } == expected
