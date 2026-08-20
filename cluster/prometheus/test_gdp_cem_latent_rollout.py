#!/usr/bin/env python3
"""Synthetic equivalence tests for cached-latent Le-WM rollout."""

from __future__ import annotations

import torch
from torch import nn

from gdp_cem_latent_rollout import (
    rollout_from_single_latent,
    selected_candidate_metrics,
    terminal_goal_cost,
)


class FakeWorld(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.action_encoder = nn.Linear(4, 6, bias=False)
        self.predictor = nn.Linear(8 + 6, 8, bias=False)

    def predict(self, embedding, action_embedding):
        return self.predictor(torch.cat((embedding, action_embedding), dim=-1))

    def reference(self, current, actions):
        values = [current[:, None]]
        active = []
        for step in range(actions.shape[1]):
            active.append(actions[:, step : step + 1])
            act = self.action_encoder(torch.cat(active, dim=1))
            emb = torch.cat(values, dim=1)
            nxt = self.predict(emb[:, -3:], act[:, -3:])[:, -1:]
            values.append(nxt)
        return torch.cat(values, dim=1)


def main() -> None:
    torch.manual_seed(41)
    model = FakeWorld()
    current = torch.randn(2, 8)
    actions = torch.randn(2, 3, 5, 4)
    actual = rollout_from_single_latent(
        model, current=current, macro_actions=actions
    )
    expected = torch.stack(
        [
            model.reference(
                current[index : index + 1].expand(actions.shape[1], -1),
                actions[index],
            )
            for index in range(2)
        ]
    )
    if not torch.allclose(actual, expected, rtol=1.0e-6, atol=1.0e-7):
        raise RuntimeError("GDP-CEM cached-latent rollout differs from reference")
    goal = torch.randn(2, 8)
    cost = terminal_goal_cost(actual, goal)
    metrics = selected_candidate_metrics(
        goal_cost=cost,
        candidates=actions,
        reference=torch.randn(2, 5, 4),
    )
    if any(value.shape != (2,) for value in metrics.values()):
        raise RuntimeError("GDP-CEM cached-latent metric shape differs")
    if torch.any(metrics["unique_candidates"] != 3):
        raise RuntimeError("GDP-CEM cached-latent uniqueness metric differs")
    print("GDP-CEM cached-latent rollout tests: ok")


if __name__ == "__main__":
    main()
