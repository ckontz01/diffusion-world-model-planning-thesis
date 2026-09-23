"""Pinned production bridge; no torch/physics import or research open at import."""
import common as c
import hashlib
import importlib.util
import sys
import types
import numpy as np
from policy import Observation


def array_hash(value):
    a = np.ascontiguousarray(value)
    return hashlib.sha256(str((a.shape, a.dtype.str)).encode() + a.tobytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return m


def load_backend(auth):
    c.require(type(auth) is c.Authorization, 'Execution capability required before model imports')
    auth.runtime()
    checkpoint = auth.checkpoint()  # hash before deserializing trusted pinned pickle
    import torch
    import stable_worldmodel as swm
    sources = auth.inputs['model_sources']
    cls = load_module('acv_official_lewm', sources['lewm']).LeWM
    mod = load_module('acv_official_module', sources['module'])
    alias = types.ModuleType('jepa'); alias.JEPA = cls
    mod.ARPredictor = mod.Predictor
    sys.modules['jepa'] = alias; sys.modules['module'] = mod
    # Exact inspected AutoCostModel path (no directory search/network fallback).
    c.require(checkpoint.endswith('_object.ckpt'), 'Pinned object filename')
    c.require(not c.Path(checkpoint[:-len('_object.ckpt')]).is_dir(), 'No AutoCostModel directory search')
    model = swm.policy.AutoCostModel(checkpoint[:-len('_object.ckpt')])
    c.require(type(model) is cls, 'Wrong loaded LeWM class')
    torch.manual_seed(94041); torch.cuda.manual_seed_all(94041)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False; torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    model = model.to('cuda').to(torch.bfloat16).eval().requires_grad_(False)
    backend = LeWMBridge(model, torch, 'cuda')
    backend.frozen_hash = backend.fingerprint()
    return backend


class LeWMBridge:
    """Dependency-injected tensor bridge also exercised with artificial loaders.

    NumPy float64 search/cost; BF16 frozen model and normalized model actions.
    Image operation order is the pinned helper: float, /255 iff max>2,
    bilinear resize align_corners=False, ImageNet normalize, then BF16.
    """
    def __init__(self, model, torch_api, device):
        self.model, self.torch, self.device = model, torch_api, device
        self.current = None; self.pixels_current = None; self.encodings = 0
        self.fingerprint_seconds = 0.0

    def fingerprint(self):
        import time
        started = time.monotonic(); h = hashlib.sha256()
        for name, t in sorted(self.model.state_dict().items()):
            h.update(name.encode()); h.update(str((tuple(t.shape), t.dtype)).encode())
            h.update(t.detach().cpu().contiguous().reshape(-1).view(self.torch.uint8).numpy().tobytes())
        self.fingerprint_seconds += time.monotonic()-started
        return h.hexdigest()

    def pixels(self, image):
        t = self.torch
        a = np.asarray(image)
        c.require(a.dtype == np.uint8 and a.shape == (224, 224, 3), 'Native uint8 image contract')
        x = t.as_tensor(a, device=self.device).permute(2, 0, 1)[None, None].float()
        if x.max() > 2.0: x = x / 255.0
        x = t.nn.functional.interpolate(x.reshape(1, 3, 224, 224), size=(224, 224), mode='bilinear', align_corners=False).reshape(1, 1, 3, 224, 224)
        mean = t.as_tensor([.485, .456, .406], device=self.device, dtype=x.dtype).reshape(1, 1, 3, 1, 1)
        std = t.as_tensor([.229, .224, .225], device=self.device, dtype=x.dtype).reshape(1, 1, 3, 1, 1)
        return ((x - mean) / std).to(t.bfloat16)

    def encode(self, image, *, current=False):
        with self.torch.no_grad():
            pixels = self.pixels(image)
            z = self.model.encode({'pixels': pixels})['emb'].detach().float().cpu().numpy()[0, 0].copy()
        c.require(z.shape == (192,) and np.isfinite(z).all(), 'D192 encoding')
        self.encodings += 1
        if current: self.current, self.pixels_current = z.copy(), pixels
        return z

    def rollout(self, current, normalized):
        t = self.torch
        np.testing.assert_array_equal(current, self.current)
        c.require(normalized.ndim == 3 and normalized.shape[1:] == (3, 10), 'Three action blocks')
        n = len(normalized)
        with t.no_grad():
            emb = t.as_tensor(current, device=self.device, dtype=t.bfloat16).reshape(1, 1, 1, 192).expand(1, n, 1, 192)
            pixels = self.pixels_current[:, None].expand(1, n, 1, 3, 224, 224)
            actions = t.as_tensor(normalized[None], device=self.device, dtype=t.bfloat16)
            out = self.model.rollout({'pixels': pixels, 'emb': emb}, actions)['predicted_emb']
            result = out.detach().float().cpu().numpy()[0].copy()
        c.require(result.shape == (n, 4, 192) and np.isfinite(result).all(), 'Current+three predicted states')
        np.testing.assert_array_equal(result[:, 0], np.broadcast_to(current, (n, 192)))
        return result


def delivered(action):
    a = np.asarray(action)
    c.require(a.shape == (2,) and np.isfinite(a).all() and (abs(a) <= 1).all(), 'Primitive physical Box action')
    return a.astype(np.float32)  # stored float64 proposal remains unchanged


def dynamics(env):
    values = []
    for name in ('agent', 'block'):
        body = getattr(env, name)
        values.extend([*body.position, *body.velocity, body.angle, body.angular_velocity,
                       *body.force, body.torque])
    values.extend([env.space.damping, env.dt, env.control_hz, env.k_p, env.k_v,
                   env.action_scale, float(env.n_contact_points)])
    a = np.asarray(values, dtype=np.float64)
    c.require(a.shape == (25,) and np.isfinite(a).all(), 'Public physical dynamics inventory')
    return a


class NativeEpisode:
    """Owns one NEW World, explicit action API; no optimizer/branch outcome API."""
    def __init__(self, world, backend, record, seed, reset_fn):
        self.world, self.backend, self.record = world, backend, record
        self.clock = 0; self.closed = False; self.done = False; self.records = []; self.prefix_images = []
        try:
            reset_fn(world, [record], seed=int(seed))
            self.native = world.envs.envs[0].unwrapped
            c.require(world.num_envs == 1, 'Single fresh world slot')
            np.testing.assert_allclose(self.native._get_obs(), record['state'], rtol=0, atol=1e-10)
            np.testing.assert_array_equal(self.native.goal_state, record['goal_state'])
            self.goal_image = np.asarray(world.infos['goal'])[0, -1].copy()
            self.initial_image = np.asarray(world.infos['pixels'])[0, -1].copy()
            self.goal = backend.encode(self.goal_image)
            self.first = self.snapshot(False, False, None)
            self.obs = Observation(self.first['latent'].copy(), 0, False, False, False)
        except BaseException:
            world.close(); self.closed = True; raise

    def snapshot(self, terminated, truncated, action):
        info = self.world.infos
        image = np.asarray(info['pixels'])[0, -1].copy()
        np.testing.assert_array_equal(info['goal'][0, -1], self.goal_image)
        state = np.asarray(info['state'])[0, -1].copy()
        np.testing.assert_array_equal(state, self.native._get_obs())
        proprio = np.asarray(info['proprio'])[0, -1].copy()
        z = self.backend.encode(image, current=True)
        if 0 < self.clock <= 5: self.prefix_images.append(image)
        return {'state': state, 'proprio': proprio, 'latent': z, 'dynamics': dynamics(self.native),
                'pixel_hash': np.frombuffer(bytes.fromhex(array_hash(image)), dtype=np.uint8).copy(),
                'flags': np.array([terminated, truncated], bool),
                'action': np.zeros(2, np.float32) if action is None else action.copy()}

    def initial(self):
        c.require(self.clock == 0 and not self.closed, 'Fresh initial observation only')
        return self.obs

    def step(self, action):
        c.require(not self.done and not self.closed and self.clock < 150, 'Post-terminal/over-budget work')
        a = delivered(action)
        _, _, terms, truncs, info = self.world.envs.step(a[None])
        self.world.infos = info; self.clock += 1
        c.require(int(np.asarray(info['step_idx'])[0, -1]) == self.clock, 'Native/action clock mismatch')
        actual = np.asarray(info['action'])[0, -1].copy()
        c.require(actual.dtype == np.float32, 'Native delivered dtype changed')
        np.testing.assert_array_equal(actual, a)
        terminated, truncated = bool(terms[0]), bool(truncs[0])
        c.require(not truncated, 'Unexpected native truncation before TimeLimit300')
        item = self.snapshot(terminated, truncated, actual); self.records.append(item)
        self.done = terminated or truncated
        self.obs = Observation(item['latent'].copy(), self.clock, terminated, terminated, truncated)
        return self.obs

    def close(self):
        if not self.closed: self.world.close(); self.closed = True


def source_factory(auth, index, role, backend):
    c.require(type(auth) is c.Authorization, 'Execution capability required before reference open')
    ref = auth.reference(index, role)
    # Only exact allowlisted initial and H75 target; no other outcome read.
    with np.load(ref['file'], allow_pickle=False) as z:
        initial = z['initial_request'].copy(); goal = z['states'][75].copy()
    record = {'state': initial, 'goal_state': goal}
    import stable_worldmodel as swm
    sys.path.insert(0, str(c.REPO / 'cluster/prometheus'))
    from pusht_fresh_initialization import register, reset_world
    def factory():
        world = swm.World(register(), num_envs=1, image_shape=(224, 224), max_episode_steps=300,
                          correct_velocity_space=True, history_size=1, frame_skip=1, verbose=0)
        return NativeEpisode(world, backend, record, ref['environment_seed'], reset_world)
    return factory, ref, record
