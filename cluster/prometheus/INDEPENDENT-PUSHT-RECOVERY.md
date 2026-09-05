# Independent PushT study: execution and recovery

Branch: `independent-pusht-benchmark`. Frozen scientific source: `63f0440`.
Study root: `/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-63f0440`.
Source snapshot: `/lustreFS/data/superworld/ckontzias/thesis/snapshots/independent-pusht-63f0440`.
Source-manifest SHA256: `1b86846d65a9f59ca108fefca6ab77af01e2f543deaa2e4264d784dc9e97f662`.

## Current submitted chain

- Collection/validation/lock: `300326`.
- Stage0 evaluation: `300327` (450 tasks, at most four GPUs).
- Stage0 complete-grid analysis and independent reaggregation: `300328`.
- Verified-decision controller: `300329`.

The controller submits later registered stages only if the verified decision
requires continuation. It stops at all-three-boundaries crossed, the registered
strong-adverse futility boundary, or maximum6000. It cannot tune a model or
select a favorable subset. Missing/failed tasks block analysis.

Use scheduler state and exit codes to monitor execution. Read comparative
summaries only after `INDEPENDENT-VERIFICATION.json` verifies the corresponding
`SUMMARY.json`. Do not read individual outcomes to choose a fix or method.
For a genuine execution failure, preserve the failed files and diagnose logs.
Do not blindly resubmit an entire stage or delete completed results.

## Data durability

Source, protocol, tests, pilot reports and launch context are pushed to GitHub.
Large raw reference/episode arrays remain in the study directory on Prometheus.
After collection locking or a completed verified stage, run from WSL:

```bash
python3 /home/chris/thesis/cluster/prometheus/backup_independent_pusht.py \
  --study /lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-63f0440
```

This creates a separate copy under `/home/chris/thesis-artifacts/independent-pusht/`.
It checks reference hashes and only copies complete, independently verified
stage outputs. It does not invoke models, restart jobs, or create automation.
Record backup status and verified stage summaries in the Git branch afterward.
Never put raw gigabyte arrays, SSH keys, credentials, or unrelated files in Git.

## Interpretation

This is a new reachable-goal population generated using a weak random collection
policy. Initial proposals are uniform as specified, then reference trajectories
are conditioned on the declared full-trajectory validity rules. It is not the
original expert-trajectory distribution. H75/H150 are future-state offsets,
not minimal path lengths. New physical starts use R3's documented defaults.

Six final arms: unchanged five E18 variants and released native full SAGE.
SAGE's finite commands outside its declared Box are preserved and counted;
this is disclosed native behavior, not a secretly clipped weak baseline.
The explicit boxed-SAGE sensitivity pilot is preserved separately.

No result may be claimed until the scientific run and independent verification
actually complete. A scheduler submission is not a passed experiment.
