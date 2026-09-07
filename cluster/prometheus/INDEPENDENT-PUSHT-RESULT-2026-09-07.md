# Independent PushT study: verified terminal result

Verified 7 September 2026. The registered study stopped at its first look,
N=1,600 independent reference episodes, after all 450 shards and 57,600
arm/horizon/seed runs completed. The terminal decision is
`stop_futility_strong_adverse_signal`. No later stage was launched.
This is a predeclared scientific stop, not an execution or validity failure.

## Recorded success

| Method | H75 | H150 | Equal-horizon/seed mean |
|---|---:|---:|---:|
| VAD continuation | 21.1875% | 11.4167% | 16.3021% |
| Greedy VAD-300 | 20.5417% | 7.6458% | 14.0938% |
| Gaussian continuation | 17.4375% | 9.2917% | 13.3646% |
| Greedy VAD-576 | 21.4375% | 8.8125% | 15.1250% |
| GMM continuation | 19.3750% | 11.2292% | 15.3021% |
| Released native full SAGE | 26.4792% | 15.6042% | 21.0417% |

## Registered primary comparisons

| Control | VAD minus control (pp) | First-look lower bound (pp) | Superiority boundary crossed |
|---|---:|---:|---|
| Greedy VAD-300 | +2.2083 | +0.8226 | Yes |
| Gaussian continuation | +2.9375 | +1.5881 | Yes |
| SAGE | -4.7396 | -6.5324 | No |

These are the frozen one-sided paired Student lower bounds at alpha .001
per comparison for this look, within the across-look/comparison spending rule;
they are not ordinary post-stop 95% intervals. The SAGE contrast's registered
futility upper bound is -2.9468 pp, below zero, triggering the prospective stop.
Futility was defined as a resource rule, not a separate confirmatory inferiority
claim. The two internal superiority claims passed; the all-three objective did not.
The five-point effect was a planning alternative, not an observed-effect gate.

## Timing and interpretation

Median timed solver calls: VAD continuation 0.129690 s; SAGE 0.963857 s.
SAGE/VAD median ratio is 7.432. This excludes some surrounding preprocessing
and execution; it is not an end-to-end speed ratio or evidence of noninferiority.
Recorded planner failures: zero. SAGE delivered 160,137 out-of-Box action
coordinates under its preserved native finite-action behavior; E18 arms recorded
zero. This is disclosed execution behavior, not a post-result baseline alteration.

The evidence supports internal continuation/distribution-family gains in this
new weak-policy reachable-goal population, but not superiority over full SAGE.
It does not reproduce the historical expert-data distribution or explain E19's
paper-table discrepancy. Historical E11/E13/E18 results are not rewritten.
All 6,000 references were generated and validated; only the first 1,600 were
evaluated under this terminated protocol. No automatic use of the remaining
4,400 references is authorized by this terminal result.

## Verification and preservation

Live check at 2026-09-07T09:39:13Z validated config, registry, collection,
analysis seals, independent verification, and the terminal summary identity.
The remote independent verifier reaggregated all 57,600 rows. A separate local
standard-library check reconstructed the complete unique grid, every arm mean,
and every primary paired difference and standard error from the copied TSV.
All agreed within 1e-12. This local check did not rerun model inference or physics.

Summary SHA-256: `305be6aa678445dce5ceddda6bae14657a730810e448121df6c8783c4318da6d`.
Source manifest: `d79c5f0f5515011885a1309d61985e1464c8c6738c7d9f4a3b161378836381ec`.
Collection: `3cce1a2b74c84feeece9503dd2873d8db6abd609b546311ed374984ca4d93f68`.

The exact summary, report, compressed per-run table, episode tensor, checksums,
independent verification and terminal record are archived under
`independent-pusht-evidence/look-0/` and `independent-pusht-evidence/TERMINAL.json`.
The local recheck is `independent-pusht-evidence/LOCAL-RESULT-RECHECK-20260907.json`.
These have a new copy in the Windows recovery checkout, outside the repaired
WSL virtual disk. Full raw reference/trajectory arrays remain on Prometheus at
`experiments/independent-pusht/final-20260906-4a608e5` under the thesis root.
This publication does not certify recovery/catch-up of the older WSL raw backups;
that operational task remains separate. No new simulations or jobs were launched.

See [frozen protocol](INDEPENDENT-PUSHT-PROTOCOL.md),
[exact result](independent-pusht-evidence/look-0/SUMMARY.json), and
[terminal record](independent-pusht-evidence/TERMINAL.json).
