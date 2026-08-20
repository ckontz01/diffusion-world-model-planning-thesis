from acid_alternative.verify_prepared_task import optional_exact


def test_optional_legacy_metadata_accepts_absence_but_rejects_conflict():
    assert optional_exact({}, "kind", "episode_partition")
    assert optional_exact(
        {"kind": "episode_partition"}, "kind", "episode_partition"
    )
    assert not optional_exact(
        {"kind": "different_schema"}, "kind", "episode_partition"
    )
