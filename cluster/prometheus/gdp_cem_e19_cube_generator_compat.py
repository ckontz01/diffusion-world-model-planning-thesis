#!/usr/bin/env python3
"""Run pinned SAGE Cube with its missing Gaussian-CEM subgoal-cache warmup."""

from __future__ import annotations


def install_cube_generator_cache_compat(cube_module) -> None:
    """Mirror the pinned PushT Gaussian-CEM cache warmup for Cube.

    The official Cube ``lewm_generator`` path expands planner inputs over CEM
    candidates before asking for its local goal.  Unlike the corresponding
    PushT path, it omits the unexpanded cache warmup, so multi-stage horizons
    pass candidate-expanded low-dimensional history to the generator and fail
    on incompatible token ranks before producing a result. Warming the existing
    Cube cache here preserves the official model, checkpoints, candidate bank,
    and scoring equations.
    """

    solver_type = cube_module.GaussianCEM
    original = solver_type.solve
    if getattr(original, "_e19_cube_cache_compat", False):
        return

    def solve(self, info, init_action=None):
        if getattr(self.model, "generator", None) is not None:
            self.model.local_goal(info)
        return original(self, info, init_action=init_action)

    solve._e19_cube_cache_compat = True
    solve.__name__ = original.__name__
    solve.__qualname__ = original.__qualname__
    solve.__doc__ = original.__doc__
    solver_type.solve = solve


def main() -> None:
    from sage.eval import cube

    install_cube_generator_cache_compat(cube)
    cube.main()


if __name__ == "__main__":
    main()
