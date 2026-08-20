# E7P P1 goal-conditioned action-sequence cache protocol

Date frozen: 2026-08-17  
Role: deterministic P1-only data derivation for GDP-CEM  
Outcome access: no D2, D3, C1, or I1 data or outcomes may be read

For each of PushT, Reacher, and Cube, use the already frozen flat Le-WM latent
cache and five-primitive-step transition cache. Both inputs must pass their
recorded SHA-256 lineage checks.

Within each episode, join the five transition rows whose source steps are
`t`, `t+5`, `t+10`, `t+15`, and `t+20`. Store:

- the latent-cache index at `t`;
- the latent-cache index at `t+25`;
- the five standardized planner macro-action blocks;
- episode index, source step, and original P1 train/validation role.

Reject noncontiguous transition steps, role changes within an episode,
cross-episode joins, goal offsets other than 25, non-finite actions, missing P1
roles, changed input hashes, and any existing output path. Preserve episode-level
P1 roles; do not resplit examples.

Store the exact latent statistics and released planner primitive-action
standardizer already present in the transition cache. Record P1-train 0.001 and
0.999 action quantiles for diagnostics only. They must not be computed from P1
validation.

This cache operation selects no model, hyperparameter, task, or result. Its
output is development data and cannot authorize D2, D3, C1, I1, or a thesis
claim.

