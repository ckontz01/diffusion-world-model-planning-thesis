"""Fresh factory/replay and absolute-budget control, exercised with fake worlds.

Real native environment binding is deliberately NOT supplied in this package.
"""
from dataclasses import dataclass
import numpy as np
from .core import array_id, frozen


@dataclass(frozen=True)
class SourceHistory:
    parent: str
    construction_id: str
    replay_actions: np.ndarray
    observation_ids: tuple
    elapsed: int


def run_branch(factory, source, candidate, tail, budget, draw_id, *, domain):
    if domain != 'artificial':
        raise PermissionError('Native physics/research collection disabled')
    if budget != 50 or not 0 <= source.elapsed <= budget:
        raise ValueError('Original absolute budget must be 50')
    # Historical replay is physically charged, but is not a fresh grant of
    # control budget. It can precede the diagnostic's elapsed=0 origin.
    if len(source.observation_ids) != len(source.replay_actions)+1:
        raise ValueError('Complete replay provenance')
    world = factory(source.construction_id, draw_id)
    actions, observations, endpoints = [], [], []
    terminal = False
    try:
        obs, success, terminal, truncated = world.reset()
        if array_id(obs) != source.observation_ids[0]:
            raise ValueError('Fresh root authentication failed')
        if terminal or truncated or success:
            if len(source.replay_actions):
                raise ValueError('Source replay crosses an initial terminal')
        for j, action in enumerate(source.replay_actions):
            if terminal or truncated or success:
                raise ValueError('Source history includes post-terminal physics')
            obs, success, terminal, truncated = world.step(action)
            if array_id(obs) != source.observation_ids[j+1]:
                raise ValueError('Full history replay mismatch')
        observations.append(frozen(obs))
        endpoints.append(bool(success))
        terminal_flags, truncation_flags = [bool(terminal)], [bool(truncated)]
        elapsed, prefix_steps = source.elapsed, 0
        chunk = candidate.actions
        for action in chunk:
            if terminal or truncated or success or elapsed == budget:
                break
            obs, success, terminal, truncated = world.step(action)
            actions.append(frozen(action)); observations.append(frozen(obs)); endpoints.append(bool(success))
            terminal_flags.append(bool(terminal)); truncation_flags.append(bool(truncated))
            elapsed += 1; prefix_steps += 1
        prefix_id = array_id(np.stack(observations))
        tail_actions = []
        # The policy object is branch-owned and receives ACTUAL observations.
        while not (terminal or truncated or success) and elapsed < budget:
            action = tail(obs, elapsed, budget-elapsed, draw_id)
            obs, success, terminal, truncated = world.step(action)
            actions.append(frozen(action)); tail_actions.append(frozen(action))
            observations.append(frozen(obs)); endpoints.append(bool(success)); elapsed += 1
            terminal_flags.append(bool(terminal)); truncation_flags.append(bool(truncated))
        shape = chunk.shape[1:]
        a = np.stack(actions) if actions else np.empty((0,*shape), dtype=chunk.dtype)
        ta = np.stack(tail_actions) if tail_actions else np.empty((0,*shape),dtype=chunk.dtype)
        reason = 'success' if success else 'truncated' if truncated else 'terminal_failure' if terminal else 'budget_failure'
        return {'parent': source.parent, 'construction': source.construction_id,
                'candidate_id': candidate.identity, 'draw_id': draw_id,
                'replay_id': array_id(source.replay_actions), 'prefix_id': prefix_id,
                'tail_id': array_id(ta), 'actions': frozen(a), 'observations': frozen(np.stack(observations)),
                'endpoint_flags': tuple(endpoints), 'terminal_flags': tuple(terminal_flags),
                'truncation_flags': tuple(truncation_flags), 'replay_steps': len(source.replay_actions), 'source_elapsed': source.elapsed,
                'elapsed': elapsed, 'prefix_steps': prefix_steps, 'success': bool(success),
                'reason': reason, 'domain': domain}
    finally:
        world.close()
