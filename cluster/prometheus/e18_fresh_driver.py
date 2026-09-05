"""Fail-closed episode driver; independent streams, no dataset evaluator.

The caller owns frozen model/scaler construction. There is no dataset loader,
success reducer, action clipping, physics repair or legacy fallback here.
"""
from copy import deepcopy
import numpy as np
from pusht_fresh_initialization import ENV_ID, reset_world, validate_record


def computational_info(info):
    """Only fields consumed by unchanged E18: fresh images and raw current state."""
    result = {}
    for key in ('pixels', 'goal', 'state'):
        if key not in info:
            raise RuntimeError(f'missing current initialized input: {key}')
        value = np.asarray(info[key])
        if not np.isfinite(value).all():
            raise RuntimeError(f'non-finite current input: {key}')
        result[key] = value.copy()
    return result


class FreshEpisode:
    """One World slot and one new solver/policy per episode.

    The budget counts delivered primitive actions, never reset/render calls.
    Completed slots remain unstepped. The same World may be explicitly reset
    only after completion; policy_factory must construct a fresh solver too.
    """
    def __init__(self, world, policy_factory, *, observe=None):
        if world.num_envs != 1:
            raise ValueError('independent episode driver requires one environment')
        self.world = world
        self.factory = policy_factory
        self.observe = observe or (lambda event, **data: None)
        self.status = 'new'
        self.steps = 0
        self._previous_policy = None
        self._previous_solver = None

    def start(self, record, *, horizon, budget, seed):
        if self.status not in ('new', 'done'):
            raise RuntimeError('cannot replace unfinished/failed episode')
        if horizon not in (75, 150) or not 0 < budget <= 2 * horizon:
            raise ValueError('invalid explicit horizon or budget')
        spec = validate_record(record)
        env = self.world.envs.envs[0].unwrapped
        if (getattr(getattr(env, 'spec', None), 'id', None) != ENV_ID or
                not callable(getattr(env, 'queue_instantaneous_record', None))):
            raise RuntimeError('explicit R3 environment required; no legacy fallback')
        self.status = 'failed'  # any initialization exception is terminal
        policy = self.factory(horizon, seed)
        solver = policy.planner
        if policy is self._previous_policy or solver is self._previous_solver:
            raise RuntimeError('episode must own a new policy and solver')
        if solver.diagnostic_history:
            raise RuntimeError('new solver contains old episode diagnostics')
        self.world.set_policy(policy)
        if policy._stage_index != 0 or len(policy._action_buffer):
            raise RuntimeError('new policy is not at decision zero')
        self.policy = policy
        self._previous_policy, self._previous_solver = policy, solver
        self.steps, self.budget = 0, int(budget)
        self.observe('before_reset', record=deepcopy(spec), policy=policy)
        reset_world(self.world, [record], seed=int(seed))
        if env._fresh_pending is not None:
            raise RuntimeError('explicit record was not consumed')
        # Public body/COG coordinate conversion can round by a few float64 ULPs.
        np.testing.assert_allclose(env._get_obs(), spec['state'], rtol=0, atol=1e-10)
        np.testing.assert_array_equal(self.world.infos['state'][0, -1], env._get_obs())
        np.testing.assert_array_equal(env.goal_state, spec['goal_state'])
        # Own lifecycle flags: native World.reset does not clear these attributes.
        self.world.terminateds = np.zeros(1, dtype=bool)
        self.world.truncateds = np.zeros(1, dtype=bool)
        self.world.rewards = None
        self.goal = np.asarray(self.world.infos['goal']).copy()
        computational_info(self.world.infos)
        self.status = 'running'
        self.observe('initialized', info=deepcopy(self.world.infos), env=env,
                     policy=policy, seed=int(seed))

    def advance(self):
        if self.status != 'running':
            raise RuntimeError('cannot plan/step an uninitialized or completed episode')
        try:
            info = computational_info(self.world.infos)
            np.testing.assert_array_equal(info['goal'], self.goal)
            self.observe('before_action', steps=self.steps, info=deepcopy(info), policy=self.policy)
            action = np.asarray(self.policy.get_action(info))
            if action.shape != (1, 2) or not np.isfinite(action).all() or (np.abs(action) > 1).any():
                raise RuntimeError('invalid decoded primitive action; no clipping/fallback')
            self.observe('action', steps=self.steps, action=action.copy(), policy=self.policy)
            (self.world.states, _reward, self.world.terminateds,
             self.world.truncateds, self.world.infos) = self.world.envs.step(action)
            self.steps += 1
            computational_info(self.world.infos)
            np.testing.assert_array_equal(self.world.infos['action'][0, -1], action[0])
            natural = bool(np.asarray(self.world.terminateds).any())
            truncated = bool(np.asarray(self.world.truncateds).any())
            done = natural or truncated or self.steps == self.budget
            if done:
                self.status = 'done'
            self.observe('after_action', steps=self.steps, done=done,
                         budget_exhausted=self.steps == self.budget,
                         info=deepcopy(self.world.infos))
            return done
        except Exception:
            self.status = 'failed'
            raise


def complete_slots(slots):
    """Deterministic round-robin; terminated slots never receive another action."""
    if not slots or any(s.status != 'running' for s in slots):
        raise RuntimeError('all slots must start explicitly')
    while any(s.status == 'running' for s in slots):
        for slot in slots:
            if slot.status == 'running':
                slot.advance()
    if any(s.status != 'done' for s in slots):
        raise RuntimeError('incomplete slot campaign')
