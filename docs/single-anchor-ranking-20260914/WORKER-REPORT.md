# WORKER REPORT — single-anchor ranking preparation

Branch: `single-anchor-ranking-preparation-20260914`.
Reviewed input commit: `5d437d7fe8c505c7744ab5570a90947781af51a2`.
Actual starting HEAD: `bb902bfc69236eb50c49791bd95750e94b85bbe2`;
the subsequent handoff documentation was preserved. No merge to main.
This report and implementation are identified by the Git commit containing them;
the response to the researcher supplies its verified full remote commit ID.

## Prepared, not executed

- Original solver called once at each designated anchor; both ranks computed
  in both arms using production torch arithmetic; only returned first plan changes.
- Original fresh construction, independent historical-prefix policy replay,
  action buffer/stage progression, decoder, models and full downstream policy.
  t30 is never initialized from a t0 treatment trajectory.
- Exact saved diagnostic-bank comparisons, historical control plan/RNG/action/
  state/termination checks, separately owned generators and same-index tail checks.
- Approval-gated CLI and serial fail-stop dispatcher, fixed per-job/aggregate/
  storage reservations and no automatic retries. Separate new experiment root.
- NumPy-only full-budget trace/score/decoder/provenance checker and reference-
  clustered repeat0 analysis; all seals precede array interpretation.
- [Protocol](PROTOCOL.md), [resource proposal](RESOURCE-PLAN.md), selected historical
  timing receipt [COST-PLANNING.json](COST-PLANNING.json), and source/input pins.

Code is in cluster/prometheus/single_anchor_ranking*.py,
verify_single_anchor_ranking.py and run_single_anchor_ranking.sh.
No historical runner, solver, initialization, verifier, result or selection file
was edited. Models/checkpoints and the original three E12 drafts remain unchanged.

## Tests and remaining real-runtime checks

18 focused synthetic CPU tests pass. They exercise the actual E18ScheduledPolicy
class extracted from its source with a fake BasePolicy/solver (no simulator),
synthetic torch tensors for capture/selection, complete t0/t30 budgets and both
cycle restarts, immediate/same-choice ties, no ranking RNG consumption, restoration
of hooks after errors, terminal first chunks and tails, no post-terminal stepping,
same-step success and angle-domain bounds, repeat0 clustering, approval/dispatch
guards, and independent saved-trace rejection mutations. A synthetic short-cap
edge and a test's expected exception type were corrected during preparation;
neither involved a real record or changed scientific tolerances.

The inherited 101 CPU/synthetic tests, shell syntax and Git whitespace checks
also pass. The local test environment, Python 3.10.20 / NumPy 2.2.6 /
torch 2.13.0+cpu, differs from the pinned cluster runtime. These passes establish
synthetic wiring, not real model/physics correctness or cluster performance.

Still UNTESTED and included in the proposed launch scope: cluster imports/package
resolution, real model/checkpoint bank regeneration, actual physical/controller/
pixel replay, full historical-control tail identity, branch-owned real generator
coupling and real costs/storage. The first reference's two processes are a fixed
technical pilot inside the 64 jobs; they must pass runner assertions/repeat equality
before remaining dispatch. No extra real preflight was quietly run now.

No unresolved scientific design choice is hidden in the implementation: the
researcher must approve/revise the proposed repeats and envelope. A concrete real
runtime mismatch would stop rather than trigger fallback or tolerance changes.

## Recommended approval package

Two process repeats for all 32 references, 8 branch executions/process:
64 jobs, 512 branch executions, 256 before repeats; independent scientific n=32.
Use repeat 0 only for estimates. No new reference or model seed is proposed.

Maximum two-repeat work: 107,520 post-anchor actions + 7,680 prefix actions = 115,200;
7,680 planning calls (6,656 continuation, 1,024 cycle-final first-only), 14,336 proposal
batches, 143,360 diffusion network forwards, 15,360 encoder calls, 6,656 adapter calls,
43,008 LeWM predictor calls and 64 model constructions. Physical/call bounds include
both arm prefixes; no uncharged helper replay or repeated pilot is planned.

Selected historical solve timings produce total planning scenarios of 86.26 min
(mean), 86.34 min (p95), 102.27 min (twice p95), 214.21 min (max at every call), INCLUDING
explicit unmeasured 30 s/process setup and 0.02 s/step allowances. These are uncertain
estimates, not a transfer of the earlier short-branch wall time.

Recommend one A6000, 4 CPUs, 24 GiB RAM, 15 min/job; a 4-hour aggregate GPU-allocation
review ceiling including failures/timeouts, excluding queues; a 2 GB run watermark,
64 MB dispatch reserve and 64 MiB per-file cap. Separately proposed CPU-only
10-minute import/test preflight and 30-minute final verifier, each 2 CPUs / 4 GiB. Reserve 6 GB
external backup space. If limits cannot accommodate the next full reservation,
stop with incomplete fixed grid—no automatic envelope expansion.

**No new real-model inference, simulator execution, GPU job, benchmark controller,
monitor, training, tail-policy experiment or protected-data access was launched.**
No launch approval file or cluster execution snapshot was created. After researcher
approval, freeze the approved source/protocol, bind their hashes to the explicit
approval record, run the bounded technical packaging/pilot gates, then execute.
The next decision is approval of this concrete experiment and resource envelope,
not another general audit of the accepted 32-reference diagnostic.
