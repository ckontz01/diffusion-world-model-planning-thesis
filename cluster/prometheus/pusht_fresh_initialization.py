"""Opt-in instantaneous PushT initialization, not historical-state recovery.

Importing this module neither registers an environment nor patches native code.
The native constructor/setup, geometry, collision handlers and step are reused.
"""
from copy import deepcopy
import numpy as np

CONTRACT = 'pusht-instantaneous-fresh-v1'
ENV_ID = 'thesis/PushTFresh-v0'
OPTION = 'instantaneous_record'


def vector(value, size, name):
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f'{name} must be a finite length-{size} vector')
    return result.copy()


def validate_record(record):
    allowed = {'state', 'goal_state', 'proprio', 'block_velocity',
               'block_angular_velocity', 'agent_angular_velocity', 'agent_angle',
               'agent_force', 'block_force', 'agent_torque', 'block_torque'}
    if not isinstance(record, dict) or set(record) - allowed:
        raise ValueError('unknown initialization field; inventory it explicitly')
    out = {k: vector(record[k], 7, k) for k in ('state', 'goal_state')}
    for k in ('state', 'goal_state'):
        if not 0 <= out[k][4] < 2 * np.pi:
            raise ValueError('angles must use the dataset observation convention [0,2pi)')
    if 'proprio' in record:
        p = vector(record['proprio'], 4, 'proprio')
        if not np.array_equal(p, out['state'][[0, 1, 5, 6]]):
            raise ValueError('recorded state and proprio disagree')
    for k in ('block_velocity', 'agent_force', 'block_force'):
        out[k] = vector(record.get(k, [0, 0]), 2, k)
    for k in ('block_angular_velocity', 'agent_angular_velocity', 'agent_torque', 'block_torque'):
        value = np.asarray(record.get(k, 0), dtype=np.float64)
        if value.shape != () or not np.isfinite(value):
            raise ValueError(f'{k} must be a finite scalar')
        out[k] = float(value)
    if 'agent_angle' in record:
        value = np.asarray(record['agent_angle'], dtype=np.float64)
        if value.shape != () or not np.isfinite(value):
            raise ValueError('agent_angle must be finite scalar')
        out['agent_angle'] = float(value)
    return out


def signed_velocity_space(space):
    """Metadata-only copy: change only signed velocity lower bounds to -512.

    Kept separate from initialization. No clipping, dtype or value conversion.
    SAGE's already-correct declaration is an idempotent no-op in value terms.
    """
    from gymnasium import spaces
    result = deepcopy(space)
    for key, size, indices in [('proprio', 4, [2, 3]), ('state', 7, [5, 6])]:
        old = result[key]
        if old.shape != (size,) or old.dtype != np.float64:
            raise ValueError('unsupported native observation declaration')
        low = old.low.copy()
        if not np.isin(low[indices], [0, -512]).all():
            raise ValueError('unexpected native velocity bounds')
        low[indices] = -512
        result.spaces[key] = spaces.Box(low=low, high=old.high.copy(), dtype=old.dtype)
    return result


def fresh_type(native):
    """Subclass factory: the legacy reset and setter remain available unchanged."""
    class FreshPushT(native):
        def __init__(self, *, correct_velocity_space=False, **kwargs):
            super().__init__(**kwargs)
            # Capture constructor/init_value geometry, never a sampled reset value.
            self._fresh_template = deepcopy(self.variation_space.value)
            self._fresh_pending = None
            if correct_velocity_space:
                self.observation_space = signed_velocity_space(self.observation_space)

        def queue_instantaneous_record(self, record):
            """Queue for the next normal wrapped/vector reset (one-shot)."""
            validate_record(record)
            self._fresh_pending = deepcopy(record)

        def reset(self, *, seed=None, options=None):
            options = {} if options is None else options
            record = options.get(OPTION, self._fresh_pending)
            if record is None:
                return super().reset(seed=seed, options=options)
            if set(options) - {OPTION}:
                raise ValueError('fresh reset forbids un-inventoried native reset options')
            spec = validate_record(record)  # reject before mutating existing physics
            self._fresh_pending = None
            import gymnasium as gym
            gym.Env.reset(self, seed=seed)
            # Native RNG API, but no sampling is used to construct fresh physics.
            self.rng = np.random.default_rng(seed)
            self.variation_space.set_value(deepcopy(self._fresh_template))
            self.latest_action = None
            self.coverage_arr = []

            def construct(state, dynamics):
                # Native construction allocates a NEW Space, bodies and handlers.
                # No private physics field is read, cleared, copied or guessed.
                native._setup(self)
                if self.block_cog is not None:
                    self.block.center_of_gravity = self.block_cog
                if self.damping is not None:
                    self.space.damping = self.damping
                self.agent.angle = dynamics.get('agent_angle', float(self._fresh_template['agent']['angle']))
                self.agent.position = state[:2].tolist()
                self.agent.velocity = state[5:7].tolist()
                self.block.angle = float(state[4])
                self.block.position = state[2:4].tolist()
                self.block.velocity = tuple(dynamics.get('block_velocity', [0, 0]))
                for name in ('agent', 'block'):
                    body = getattr(self, name)
                    body.angular_velocity = dynamics.get(name + '_angular_velocity', 0)
                    body.force = tuple(dynamics.get(name + '_force', [0, 0]))
                    body.torque = dynamics.get(name + '_torque', 0)
                    # Supported spatial-index update: does not integrate or solve.
                    self.space.reindex_shapes_for_body(body)
                self.goal_pose = spec['goal_state'][2:5].copy()
                self.goal_state = spec['goal_state'].copy()

            # Render the supplied goal on disposable fresh physics, never by
            # moving the start bodies and carrying their contacts back and forth.
            construct(spec['goal_state'], {})
            goal_image = self.render().copy()
            construct(spec['state'], spec)
            self._goal = goal_image
            state = self._get_obs()
            observation = {'state': state, 'proprio': state[[0, 1, 5, 6]].copy()}
            return observation, self._get_info()

    FreshPushT.__name__ = 'InstantaneousPushT'
    return FreshPushT


def make_env(**kwargs):
    from stable_worldmodel.envs.pusht.env import PushT
    return fresh_type(PushT)(**kwargs)


def register():
    import gymnasium as gym
    if ENV_ID in gym.registry:
        if gym.registry[ENV_ID].entry_point != 'pusht_fresh_initialization:make_env':
            raise RuntimeError('fresh environment ID already belongs to another implementation')
    else:
        gym.register(ENV_ID, entry_point='pusht_fresh_initialization:make_env')
    return ENV_ID


def reset_world(world, records, *, seed=None):
    """New interface, deliberately separate from legacy dataset evaluation.

    Preserve normal wrappers/pool bookkeeping and let them supply fresh rendered
    observations. Never overwrite their pixels/state with a dataset image.
    Call world.set_policy() with a fresh/reset policy before a new episode.
    """
    pool = world.envs
    envs = pool.envs if hasattr(pool, 'envs') else pool.unwrapped.envs
    if len(records) != len(envs):
        raise ValueError('one explicit record per batch slot required')
    for record in records:
        validate_record(record)
    for env, record in zip(envs, records):
        env.unwrapped.queue_instantaneous_record(record)
    world.reset(seed=seed)
    return world.infos
