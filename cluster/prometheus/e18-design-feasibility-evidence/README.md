# Design/feasibility evidence, not confirmation data

- `metadata-v3/`: final identifier-only count audit and authorized historical
  E18 PushT outcome/timing projection. Verify its adjacent `sha256.txt`.
- `planning-v1/`: episode contrasts, leave-one-out/bootstrap planning uncertainty,
  20,000-replicate power/precision/null scenarios at82/400/600/800. Larger designs
  explicitly labelled unavailable. Verify its adjacent `sha256.txt`.
- `timing-job-300309/`: completed non-efficacy A6000 resource probe on one exposed
  record;80 solves, zero episode evaluations; four remote full-budget regression
  tests. Verify its adjacent `sha256.txt`.
- `workload.json`: counts and resource envelopes, separating measured solver
  cost from assumed native action/reset/I/O overhead.

No prospective episode list/start/model input or protected metric is contained
here. Exposure-set hashes are identifiers of exclusions, not a new selected
confirmation manifest. Exact LeWM training membership and a protected-allocation
release certificate remain unavailable. Read the package qualifications before
calling82 an unconditional final sample.

Reproduction from `/home/chris/thesis/cluster/prometheus`:

```sh
/home/chris/miniforge3/envs/thesis/bin/python e18_design_power.py \
  --inputs e18-design-feasibility-evidence/metadata-v3 \
  --out /tmp/e18-design-independent-check --replicates 20000
```

Use a new output path; the script refuses to overwrite. No remote data/model
access is required to reproduce this statistical calculation.
