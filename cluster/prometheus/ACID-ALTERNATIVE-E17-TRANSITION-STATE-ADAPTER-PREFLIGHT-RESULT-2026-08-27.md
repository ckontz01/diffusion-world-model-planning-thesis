# E17 action-conditioned transition-state adapter preflight result

Date analyzed: 27 August 2026
Evidence role: P1 infrastructure preflight only
Claim status: no planner-efficacy claim

## Frozen decision

The action-conditioned transition-state adapter passed every frozen PushT
gate but failed the Cube maximum-coordinate error gate. The protocol required
both tasks to pass. The final decision is therefore
`stop_transition_adapter_preflight_failed`.

No matched continuation planner, SAGE comparison, full-horizon diffusion
model, or protected-holdout evaluation was created or run. The failed Cube
gate was not tuned, rescued, or rerun.

## Integrity and information barrier

- Frozen protocol SHA-256:
  `43ca72e15570c0aaeb26b5ce0f1e6a961d77fc7dd5b8d472938a8e8f00277c03`.
- Immutable source-manifest SHA-256:
  `9fb5a8c296feec81c7982a79272e502216eaf91ad987b0e70c156cb2c5ad9fc1`.
- Deterministic transition-cache array 299318 (with its second array task
  assigned job ID 299321), adapter array 299319 (second array task 299322),
  and dependent analyzer 299320 all completed successfully.
- Both cache checksum files, both model checksum files, and the aggregate
  analysis checksum file passed. All 189 files in the immutable source
  manifest also passed verification.
- The PushT cache contained 352,090 rows: 268,875 role-0 training rows and
  83,215 sealed role-1 validation rows. The Cube cache contained 358,743
  rows: 274,107 training rows and 84,636 validation rows.
- Both final EMA checkpoints were written at the frozen step 30,000 before
  any role-1 validation payload was opened. The recorded number of validation
  rows read before checkpoint creation was zero, and role 1 was not used for
  checkpoint selection.
- The analyzer produced exactly eight task-first rows in the registered order:
  task aggregate followed by durations 15, 20, and 25 for PushT, then Cube.
  Independent recomputation reproduced every duration and aggregate gate.
- No P2 outcome, D3 metric, D4 metric, D5 artifact, P3, P4, C1, or I1
  evidence was read.

## Frozen role-1 result

The adapter predicts the next standardized low-dimensional state from the
current state, current Le-WM latent, bounded first action chunk, and Le-WM
terminal latent. The copy-current baseline predicts that the state does not
change.

| Task | Validation rows | Model RMSE | Worst-coordinate RMSE | Median coordinate R-squared | Copy-current RMSE | Model / copy ratio | Frozen gate |
|---|---:|---:|---:|---:|---:|---:|---|
| PushT | 83,215 | 0.0988 | 0.2353 | 0.9989 | 0.9897 | 0.0998 | **Pass** |
| Cube | 84,636 | 0.3560 | **1.1626** | 0.9982 | 1.1921 | 0.2986 | **Fail** |

The aggregate gate required model RMSE at most 0.50, worst-coordinate RMSE
at most 0.85, median coordinate R-squared at least 0.50, and model RMSE at
most 90% of copy-current RMSE. Every duration also had to achieve RMSE at
most 0.65 and median coordinate R-squared at least 0.35.

| Task | Duration | Rows | Model RMSE | Median coordinate R-squared | Copy-current RMSE | Duration gate |
|---|---:|---:|---:|---:|---:|---|
| PushT | 15 | 29,601 | 0.0797 | 0.9992 | 0.9265 | Pass |
| PushT | 20 | 27,723 | 0.1005 | 0.9990 | 0.9964 | Pass |
| PushT | 25 | 25,891 | 0.1153 | 0.9986 | 1.0506 | Pass |
| Cube | 15 | 29,930 | 0.3089 | 0.9987 | 1.1088 | Pass |
| Cube | 20 | 28,258 | 0.3720 | 0.9982 | 1.2166 | Pass |
| Cube | 25 | 26,448 | 0.3869 | 0.9977 | 1.2548 | Pass |

Cube therefore failed one aggregate rule despite passing its overall RMSE,
median-R-squared, copy-current, and all three duration gates. This was not a
borderline numerical crossing: three of Cube's 28 state coordinates had
standardized RMSE above 0.85 (0.9633, 0.8825, and 1.1626). The fixed model
predicted most Cube coordinates very accurately, but it did not meet the
registered requirement that no individual state coordinate be poorly
predicted.

## Scientific interpretation

E17 improves the diagnosis without producing a planning result:

1. Adding the current state and proposed first action chunk solved the broad
   interface problem seen in E16. PushT improved from 0.2736 to 0.0988 RMSE;
   Cube improved from 0.8051 to 0.3560 RMSE and from 0.4011 to 0.9982 median
   coordinate R-squared.
2. Cube still retained a concentrated coordinate-level failure. Because a
   continuation planner would use the entire predicted state, the frozen
   worst-coordinate safeguard correctly blocks promotion.
3. E16's oracle shortlist headroom remains real, but E17 does not show that a
   learned reranker can realize it safely in closed loop.
4. The E11 and E13 paper results are unchanged. E17 is a transparent negative
   infrastructure result for the optional long-horizon extension, not
   evidence against the established short-horizon velocity-diffusion method.

Under the frozen protocol, E17 closes this action-conditioned continuation
attempt before planner evaluation. Any future work would need a new scientific
question and protocol rather than a threshold change or a rescue of this
failed preflight.
