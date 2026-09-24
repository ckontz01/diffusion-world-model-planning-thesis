"""One new corner: committed-value prefix, actual-response feedback suffix.

Original Selector is imported byte-for-byte, never patched. No world/model
loading, fitting, search or reference access at import. Same integration charge
as static is deliberately retained (although not needed to choose its prefix).
"""
import base
from policy import Selector, Decision

MODE = 'committed_feedback'

class CommittedFeedbackSelector(Selector):
    MODES = Selector.MODES + (MODE,)

    def select(self, tree, h, ledger, mode=MODE, seed=94021):
        if mode != MODE:
            return super().select(tree, h, ledger, mode, seed)
        committed = super().select(tree, h, ledger, 'static', seed)
        # Drop ONLY the suffix commitment, including when baseline is best.
        # Inherited after() uses the actual residual and joint predictor.
        return Decision(committed.prefix, None, MODE, committed.values, False)

def evaluate_supplied(factory, rollout, reference, selector, *, settings=None, preserve=None):
    """Future executor adapter, tested with artificial interfaces only.

The caller must supply its separately authorized fresh-world factory/backend.
This does NOT load a backend, open a reference or submit a job. Existing
episodes.evaluate remains untouched; this routes just the new control through
the original build_tree/execute/capture functions and preserves fault evidence.
"""
    import sys, time, numpy as np
    sys.path.insert(0, str(base.OLD/'bindings-r1'))
    from episodes import build_tree, execute, capture, tree_arrays, partial_evidence
    from tree import Ledger
    env = factory(); arrays = {}; started = time.monotonic()
    try:
        ledger = Ledger()
        tree, planner = build_tree(env, rollout, ledger, reference, settings)
        arrays = tree_arrays(tree)
        arrays.update(requested_initial=np.asarray(env.record['state'], np.float64),
                      goal_state=np.asarray(env.record['goal_state'], np.float64), goal_latent=env.goal,
                      initial_image=env.initial_image, goal_image=env.goal_image)
        result = execute(env, tree, selector, MODE, planner, ledger)
        capture(env, result, arrays, 'b0', True)
        return arrays, dict(reference=reference, role='mechanism_evaluation', kind='evaluation',
                            control=MODE, branches=[result], wall_seconds=time.monotonic()-started)
    except BaseException:
        if preserve is not None:
            partial, pending = partial_evidence(env, arrays)
            preserve(partial, dict(complete=False, reference=reference, control=MODE, inflight=pending))
        raise
    finally:
        env.close()
