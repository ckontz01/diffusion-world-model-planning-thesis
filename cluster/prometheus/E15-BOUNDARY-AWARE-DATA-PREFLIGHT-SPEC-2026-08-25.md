# E15 boundary-aware data preflight specification

Date fixed: 25 August 2026  
Role: structural P1 data preparation only  
Model training authorized: **no**  
P2 evaluation authorized: **no**  
D3, D4, D5, P3, P4, C1, or I1 access authorized: **no**

## 1. Purpose

E14's variable-duration action diffusion (VAD) beat its matched diagonal
Gaussian on every registered offline proposal-quality comparison, but it
failed the frozen Cube boundary-validity rule. The post-E14 diagnostic showed
that this was genuine raw overshoot followed by hard clipping, while also
showing that legal expert actions legitimately saturate several Cube action
coordinates.

E15 is the one authorized boundary-aware redesign. Before its scientific
protocol is frozen, this preflight fixes a new episode-disjoint development
split and measures only the geometry of the expert actions under a common
smooth bounded parameterization. No learned model is created or evaluated by
this preflight. Its output may be used only to write expert-relative integrity
thresholds before E15 training begins.

## 2. Permitted source data

The only row source is the already checksum-verified E14 balanced P1 cache for
PushT and Cube. Only rows with E14 `role == 0` (`P1_train`) are eligible. The
40,000 E14 `P1_val` rows per task are excluded because their performance was
already inspected in E14.

The exact E14 cache, flat-latent cache, transition cache, raw dataset, and
their manifests must match the hashes pinned in
`gdp_cem_e15_data_specs.py`. No metric-bearing D3 or D4 artifact may be opened,
and no D5 or other protected split may be generated, read, or hashed.

The resulting E15 validation data are fresh with respect to E15 model fitting
and endpoint selection, but they are not globally untouched confirmation
evidence: their source episodes belonged to the earlier E14 training pool.
They therefore remain development data. Any paper claim still requires a
separately frozen untouched confirmation protocol.

## 3. Frozen episode split

For task name `task` and decimal episode identifier `episode`, compute

```text
SHA256(UTF8("gdp-cem-e15-split\0" + task + "\0" + episode))
```

Interpret the first eight digest bytes as an unsigned big-endian integer.
The episode is assigned to E15 validation iff that integer modulo four equals
zero; otherwise it is assigned to E15 training. Assignment is at episode
level, so no episode may occur in both roles.

Within each of the 45 valid `(delta, tau)` cells, select without replacement:

- exactly 6,500 E15-training rows; and
- exactly 2,000 E15-validation rows.

This yields exactly 292,500 training and 90,000 validation rows per task.
Selection uses NumPy `default_rng` (PCG64) with the deterministic seed returned
by `gdp_cem_e15_data_specs.derived_seed` for the complete task/role/cell label.
Rows are then shuffled within role with a separately derived seed. Any cell
with insufficient rows is a hard input-validity stop. Sampling with
replacement or changing the split salt is forbidden.

The availability check performed before this specification was written read
only E14 role, episode, `delta`, and `tau` arrays. It found minima of 6,564
training and 2,074 validation rows per cell on PushT and 6,617/2,074 on Cube;
therefore the frozen quotas are feasible without choosing them from model
outcomes.

## 4. Frozen smooth bounded-action representation

Both released environments declare primitive action space `Box(-1, 1)` in
every coordinate. Let

```text
s = nextafter(float32(1.0), float32(0.0))
r = float32(s * s)
```

For every active expert primitive action `a`, first project it to `[-r, r]`,
then define the unconstrained target

```text
u = atanh(a_projected / s).
```

At inference, every new learned E15 proposal family must use the same smooth
map

```text
a_generated = s * tanh(u_generated).
```

Thus generated actions are strictly inside the declared environment interval
in exact real arithmetic, while expert values at or microscopically outside a
limit receive a finite inverse target. The displacement is at most a few
float32 units for legal saturated expert actions. The builder must report the
projection rate and magnitude rather than hide it.

Raw source actions are joined directly from the checksum-pinned dataset. The
builder must independently verify that the released float32
`StandardScaler.transform` maps those source actions to the E14 cached planner
coordinates within the repository's four-float32-epsilon rounding envelope.
Candidate actions used by Le-WM will later be mapped from raw coordinates to
planner coordinates with the exact released two-operation float32 transform.

All E15 standardizers are fitted from E15-training rows only:

- latent mean and standard deviation over unique current, local, and far-goal
  latent indices used by E15 training;
- state mean and standard deviation over E15-training rows; and
- `u` mean and standard deviation over active E15-training action elements.

Inactive padded action positions are zero after `u` standardization and are
excluded from every action statistic.

## 5. Permitted structural outputs

For each task, role, local duration, and primitive action coordinate, the
preflight may report:

- row and episode counts and exact episode overlap;
- source/planner round-trip discrepancy;
- original legal-out-of-bounds rate;
- target-projection element and trajectory rate;
- absolute projection displacement quantiles and maximum;
- exact-limit and near-limit fractions at relative margins
  `1e-6, 1e-4, 1e-3, 1e-2, 5e-2`;
- pre-squash `|u|` quantiles;
- normalized tanh-Jacobian fractions below `1e-2`, `1e-3`, and `1e-4`;
- fitted train-only standardizers and their hashes; and
- every input/output content hash.

No learned proposal, Le-WM cost, success value, endpoint comparison, or P2
metric is permitted. The preflight result may set E15 integrity thresholds
relative to expert behavior, but it may not tune an architecture, optimizer,
candidate bank, endpoint, or performance gate.

## 6. Required checks before the scientific freeze

The cache is valid only if all of the following hold:

1. every pinned input hash and lineage field matches;
2. every selected row came from E14 `P1_train`;
3. every row has exact episode containment and exact `delta`/`tau` offsets;
4. every role/cell has its frozen quota and contains no duplicate cache row;
5. train and validation episode sets are disjoint;
6. raw dataset actions join to the declared episode and step;
7. the released planner transform reproduces the cached actions within the
   fixed rounding envelope;
8. all active bounded targets and `u` targets are finite;
9. all inactive padded targets are exactly zero;
10. every train-only standard deviation is finite and non-degenerate; and
11. the output records `d3_metric_read = false`, `d4_metric_read = false`,
    `d5_read = false`, and
    `protected_p3_p4_c1_i1_read = false`.

Passing this preflight authorizes only writing and freezing the full E15
scientific development protocol. It does not authorize model training until
that second freeze is complete.
