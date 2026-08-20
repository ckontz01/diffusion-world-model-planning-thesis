import numpy as np
from acid_alternative_diagnostics.execute_candidate_pools import (
    ReplayPolicy,
    execute_batch,
    success_from_trace,
    task_distance,
)


def test_replay_policy_consumes_fixed_plan_in_order():
    policy = ReplayPolicy()
    actions = np.arange(12, dtype=np.float32).reshape(2, 3, 2)
    policy.set_actions(actions)
    assert np.array_equal(policy.get_action({}), actions[:, 0])
    assert np.array_equal(policy.get_action({}), actions[:, 1])
    assert policy.cursor == 2


def test_task_distance_wraps_angle_and_matches_success_geometry():
    state = np.zeros((1, 7), dtype=np.float32)
    goal = np.zeros((1, 7), dtype=np.float32)
    state[0, 4] = 2.0 * np.pi - 0.1
    goal[0, 4] = 0.1
    assert np.allclose(task_distance(state, goal), 0.2, atol=1.0e-6)
    assert success_from_trace(state, goal).item()


def test_success_uses_joint_agent_and_object_position_error():
    state = np.zeros((1, 7), dtype=np.float32)
    goal = np.zeros((1, 7), dtype=np.float32)
    state[0, :4] = 10.0
    assert not success_from_trace(state, goal).item()


def test_execute_batch_allows_tasks_without_push_t_state_diagnostics(monkeypatch):
    import acid_alternative_diagnostics.execute_candidate_pools as module

    policy = ReplayPolicy()

    class FakeEnvs:
        class Unwrapped:
            _autoreset_envs = np.zeros(1)

        unwrapped = Unwrapped()

    class FakeWorld:
        def __init__(self):
            self.infos = {
                "pixels": np.zeros((1, 1, 2, 2, 3), dtype=np.uint8),
                "goal": np.zeros((1, 1, 2, 2, 3), dtype=np.uint8),
            }
            self.terminateds = np.array([False])
            self.num_envs = 1
            self.envs = FakeEnvs()

        def step(self):
            policy.get_action(self.infos)

    world = FakeWorld()
    monkeypatch.setattr(
        module,
        "prepare_dataset_reset",
        lambda **kwargs: {"goal": world.infos["goal"]},
    )
    result = execute_batch(
        world=world,
        policy=policy,
        dataset=object(),
        episodes=[0],
        starts=[0],
        goal_offset=25,
        callables=[],
        raw_actions=np.zeros((1, 2, 1), dtype=np.float32),
    )
    assert "state_trace" not in result
    assert "goal_state" not in result
    assert result["pixel_trace"].shape[0] == 3
