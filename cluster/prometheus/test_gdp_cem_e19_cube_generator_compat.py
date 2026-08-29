from __future__ import annotations

from types import SimpleNamespace

from gdp_cem_e19_cube_generator_compat import (
    install_cube_generator_cache_compat,
)


def make_cube_module(events: list[tuple]):
    class GaussianCEM:
        def __init__(self, model):
            self.model = model

        def solve(self, info, init_action=None):
            events.append(("official_solve", info, init_action))
            return {"actions": "unchanged"}

    return SimpleNamespace(GaussianCEM=GaussianCEM)


def test_generator_cache_is_warmed_before_official_solver() -> None:
    events: list[tuple] = []
    cube = make_cube_module(events)

    class Model:
        generator = object()

        def local_goal(self, info):
            events.append(("local_goal", info))

    install_cube_generator_cache_compat(cube)
    info = {"goal": "unexpanded"}
    result = cube.GaussianCEM(Model()).solve(info, init_action=None)

    assert events == [
        ("local_goal", info),
        ("official_solve", info, None),
    ]
    assert result == {"actions": "unchanged"}


def test_base_cem_without_generator_is_unchanged() -> None:
    events: list[tuple] = []
    cube = make_cube_module(events)
    model = SimpleNamespace(generator=None)

    install_cube_generator_cache_compat(cube)
    info = {"goal": "unexpanded"}
    result = cube.GaussianCEM(model).solve(info, init_action="sentinel")

    assert events == [("official_solve", info, "sentinel")]
    assert result == {"actions": "unchanged"}


def test_install_is_idempotent() -> None:
    events: list[tuple] = []
    cube = make_cube_module(events)

    class Model:
        generator = object()

        def local_goal(self, info):
            events.append(("local_goal", info))

    install_cube_generator_cache_compat(cube)
    install_cube_generator_cache_compat(cube)
    cube.GaussianCEM(Model()).solve({"goal": "unexpanded"})

    assert [event[0] for event in events] == ["local_goal", "official_solve"]
