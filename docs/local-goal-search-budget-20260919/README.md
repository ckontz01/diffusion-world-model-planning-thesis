# LGP-RB1 completed development comparison

Completed20September2026:387 successful jobs,768 new plus384 reused episodes,
no failures/retries/training. Final source/endpoint/byte verification and
external SSD union backup passed. Continuation retained; no proposer promotion.

- [Final report](FINAL-REPORT.md): native successes, paired contrasts, measured costs and limitations.
- [All32 sources and all horizon/seed strata](FINAL-SOURCE-EFFECTS.md).
- [All episode identities/outcomes](FINAL-EPISODES.json), with original reuse provenance.
- [Aggregate projection](FINAL-AGGREGATE-PROJECTION.json), [accounting](FINAL-ACCOUNTING.json),
  [backup verification](FINAL-BACKUP-VERIFIED.json), [publication checks](FINAL-PUBLICATION-CHECKS.json).

## Historical preparation (unchanged scope; subsequently explicitly approved)

One frozen-model common-CEM-budget comparison requested after accepted LGP1.
Preparation only. No research launch. Continuation retained; no promotion.

- [Protocol](PROTOCOL.md): sole scientific change, identity, exact grid,
  coupling, endpoint, analysis, barrier and preservation.
- [Resource plan](RESOURCE-PLAN.md): measured scenarios and proposed caps.
- [Reuse lock](REUSE.json): actual executed source and six model identities,
  all192 original worker roots/seals and32 source IDs.
- [Direct cluster byte check](REMOTE-BYTE-COMPATIBILITY.json):17 matches;
  no checkpoint load, research inference, optimizer or simulation.
- [Exact grid](GRID.json): two compatibility jobs,384 new main jobs,one analysis.
- [Measured cost inputs](MEASURED-COST.json): no new experiment outcomes.

Implementation: `cluster/prometheus/lgprb1_{contract,evaluate,worker,dispatch,
launch,analysis,preserve,package}.py`, `run_lgprb1.sh`, and the narrow configurable
`Policy` extension in `lgp1_runtime.py`. The existing CEM already accepts a
round count; its decoder/projection/cost/tie/final-mean algorithm is unchanged.
`test_lgprb1.py` exercises actual policy/CEM using artificial neural weights
and an artificial vector-pool protocol, not a simulator.

Future approved execution commands (not run during preparation): export the
sealed package under Prometheus snapshots, create a **separate** approval
matching `APPROVAL-TEMPLATE.json` with explicit researcher authorization,
then use pinned host Python to run `lgprb1_launch.py --source <snapshot>
--approval <separate-approval>`. Do not edit the disabled template or source.
The controller submits the exact fixed grid and stops on technical failure.
After completed authentication use `lgprb1_preserve.py archive --source
<snapshot> --run <run>`, then the Windows `backup --request <POSIX-request>`
command to verify the old+new SSD archive union. No backup acknowledgment is
valid before actual member and whole-archive verification.

Only synthetic preparation tests and source packaging are authorized now.
No historic rerun, optimizer, research forward pass, physical environment,
reserved payload, confirmation source or automatic expansion.
